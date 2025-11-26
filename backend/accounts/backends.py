"""
Custom authentication backend for system user authentication.
"""
import pwd
import pexpect
import subprocess
import logging
import os
from pathlib import Path
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

# Enable info level logging for debugging
logging.basicConfig(level=logging.INFO)


class SystemUserBackend(BaseBackend):
    """
    Authenticate against system users using /etc/passwd.
    Uses a helper script to verify passwords via su command.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            logger.debug("Username or password is None")
            return None
        
        # Check if user exists in system
        try:
            pwd_entry = pwd.getpwnam(username)
        except KeyError:
            # User doesn't exist in system
            logger.warning(f"User {username} not found in system")
            return None
        
        # Try multiple authentication methods
        password_valid = False
        
        # Method 1: Try using crypt with /etc/shadow (fastest and most reliable)
        try:
            import spwd
            import crypt
            shadow_entry = spwd.getspnam(username)
            hashed = shadow_entry.sp_pwd
            
            # Skip locked accounts
            if hashed not in ['!', '*', 'x']:
                if crypt.crypt(password, hashed) == hashed:
                    password_valid = True
                    logger.info(f"Password verified using crypt method for user {username}")
        except (KeyError, PermissionError, ImportError) as e:
            logger.debug(f"Crypt method not available: {e}")
            # Fall through to other methods
        except Exception as e:
            logger.debug(f"Crypt method error: {e}")
        
        # Method 2: Use helper script if crypt didn't work
        if not password_valid:
            try:
                # Get path to helper script
                script_path = Path(__file__).parent / 'verify_password.py'
                
                # Make sure script is executable
                if script_path.exists():
                    os.chmod(script_path, 0o755)
                    
                    logger.debug(f"Attempting to authenticate user: {username} using helper script")
                    
                    # Run helper script with explicit python3 path
                    python3_paths = ['/usr/bin/python3', '/usr/local/bin/python3', 'python3']
                    python3_path = None
                    for path in python3_paths:
                        if os.path.exists(path) or path == 'python3':
                            python3_path = path
                            break
                    
                    if not python3_path:
                        logger.error("python3 not found")
                        return self._authenticate_direct(username, password, pwd_entry)
                    
                    # Run helper script
                    result = subprocess.run(
                        [python3_path, str(script_path), username, password],
                        capture_output=True,
                        timeout=20,
                        text=True
                    )
                    
                    logger.debug(f"Helper script exit code: {result.returncode}")
                    if result.stdout:
                        logger.debug(f"Helper script stdout: {result.stdout.strip()}")
                    if result.stderr and result.returncode != 0:
                        logger.debug(f"Helper script stderr: {result.stderr.strip()}")
                    
                    if result.returncode == 0:
                        password_valid = True
                        logger.info(f"Password verified successfully for user {username} using helper script")
                    else:
                        logger.debug(f"Helper script verification failed for user {username} (exit: {result.returncode})")
                else:
                    logger.warning(f"Helper script not found at {script_path}, using direct method")
                    return self._authenticate_direct(username, password, pwd_entry)
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout during password verification for user {username}")
                # Try direct method as fallback
                return self._authenticate_direct(username, password, pwd_entry)
            except Exception as e:
                logger.warning(f"Error during password verification for user {username}: {e}")
                # Fallback to direct method
                return self._authenticate_direct(username, password, pwd_entry)
        
        # Method 3: Direct pexpect if both methods failed
        if not password_valid:
            logger.debug("Trying direct authentication method")
            return self._authenticate_direct(username, password, pwd_entry)
        
        if password_valid:
            return self._create_user(username, pwd_entry)
        
        logger.warning(f"All authentication methods failed for user {username}")
        return None
    
    def _authenticate_direct(self, username, password, pwd_entry):
        """Fallback direct authentication method using pexpect with su."""
        password_valid = False
        try:
            env = os.environ.copy()
            env['LANG'] = 'C'
            env['LC_ALL'] = 'C'
            env['TERM'] = 'dumb'  # Prevent terminal issues
            
            # Use full path to su
            su_paths = ['/bin/su', '/usr/bin/su', 'su']
            su_path = None
            
            for path in su_paths:
                if os.path.exists(path) or path == 'su':
                    su_path = path
                    break
            
            if not su_path:
                logger.error("su command not found")
                return None
            
            logger.debug(f"Using su at {su_path} for direct authentication")
            
            # Use su with a simple command that requires password
            # Try different su command formats
            su_commands = [
                [su_path, '-c', 'true', username],  # Most common format
                [su_path, username, '-c', 'true'],   # Alternative format
            ]
            
            for su_cmd in su_commands:
                try:
                    child = pexpect.spawn(
                        su_cmd[0],
                        su_cmd[1:],
                        timeout=10,
                        encoding='utf-8',
                        echo=False,
                        env=env
                    )
                    
                    # Wait for password prompt with more patterns
                    patterns = [
                        'Password:',
                        'password:',
                        'Password for',
                        'password for',
                        'su:',
                        pexpect.EOF,
                        pexpect.TIMEOUT
                    ]
                    
                    try:
                        index = child.expect(patterns, timeout=10)
                        
                        # If we got EOF or TIMEOUT before prompt, try next command format
                        if index >= len(patterns) - 2:
                            child.close(force=True)
                            continue
                        
                        # Send password
                        child.sendline(password)
                        
                        # Wait for command to complete
                        child.expect(pexpect.EOF, timeout=10)
                        exit_status = child.exitstatus
                        child.close()
                        
                        # None or 0 both indicate success
                        if exit_status == 0 or exit_status is None:
                            password_valid = True
                            logger.info(f"Direct authentication succeeded for user {username}")
                            break
                        else:
                            logger.debug(f"su command failed with exit status: {exit_status}")
                            
                    except pexpect.TIMEOUT:
                        logger.debug("Timeout in direct authentication, trying next method")
                        child.close(force=True)
                        continue
                    except pexpect.EOF:
                        # Sometimes EOF happens but exit status is still valid
                        try:
                            exit_status = child.exitstatus
                            child.close()
                            if exit_status == 0 or exit_status is None:
                                password_valid = True
                                logger.info(f"Direct authentication succeeded (EOF) for user {username}")
                                break
                        except:
                            pass
                        continue
                        
                except Exception as e:
                    logger.debug(f"Error with su command format {su_cmd}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Direct authentication failed: {e}", exc_info=True)
            return None
        
        if password_valid:
            return self._create_user(username, pwd_entry)
        return None
    
    def _create_user(self, username, pwd_entry):
        """Create or get Django user."""
        User = get_user_model()
        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            try:
                if not user.email:
                    gecos = pwd_entry.pw_gecos.split(',')[0] if pwd_entry.pw_gecos else ''
                    if '@' in gecos:
                        user.email = gecos
                    else:
                        user.email = f"{username}@localhost"
                user.save()
            except Exception as e:
                logger.debug(f"Error updating user info: {e}")
            
            logger.info(f"User {username} authenticated successfully")
            return user
        except Exception as e:
            logger.error(f"Error creating/getting user: {e}")
            return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
