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
            return None
        
        # Check if user exists in system
        try:
            pwd_entry = pwd.getpwnam(username)
        except KeyError:
            # User doesn't exist in system
            logger.warning(f"User {username} not found in system")
            return None
        
        # Verify password using helper script (more reliable)
        password_valid = False
        
        try:
            # Get path to helper script
            script_path = Path(__file__).parent / 'verify_password.py'
            
            # Make sure script is executable
            if script_path.exists():
                os.chmod(script_path, 0o755)
                
                logger.info(f"Attempting to authenticate user: {username}")
                
                # Run helper script
                result = subprocess.run(
                    ['python3', str(script_path), username, password],
                    capture_output=True,
                    timeout=20,
                    text=True
                )
                
                logger.info(f"Helper script exit code: {result.returncode}")
                if result.stdout:
                    logger.info(f"Helper script stdout: {result.stdout.strip()}")
                if result.stderr:
                    logger.warning(f"Helper script stderr: {result.stderr.strip()}")
                
                # Log the actual command being run for debugging
                logger.info(f"Ran: python3 {script_path} {username} <password>")
                
                if result.returncode == 0:
                    password_valid = True
                    logger.info(f"Password verified successfully for user {username}")
                else:
                    logger.warning(f"Password verification failed for user {username} (exit: {result.returncode})")
            else:
                logger.error(f"Helper script not found at {script_path}")
                # Fallback to direct pexpect
                return self._authenticate_direct(username, password, pwd_entry)
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout during password verification for user {username}")
            return None
        except Exception as e:
            logger.error(f"Error during password verification for user {username}: {e}", exc_info=True)
            # Fallback to direct method
            return self._authenticate_direct(username, password, pwd_entry)
        
        if password_valid:
            return self._create_user(username, pwd_entry)
        
        logger.warning(f"Authentication failed for user {username}")
        return None
    
    def _authenticate_direct(self, username, password, pwd_entry):
        """Fallback direct authentication method."""
        password_valid = False
        try:
            env = os.environ.copy()
            env['LANG'] = 'C'
            env['LC_ALL'] = 'C'
            
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
            
            child = pexpect.spawn(
                su_path,
                ['-c', 'exit 0', username],
                timeout=15,
                encoding='utf-8',
                echo=False,
                env=env
            )
            
            patterns = [
                'Password:',
                'password:',
                'Password for',
                'password for',
                pexpect.EOF,
                pexpect.TIMEOUT
            ]
            
            index = child.expect(patterns, timeout=15)
            
            if index >= len(patterns) - 2:
                child.close(force=True)
                return None
            
            child.sendline(password)
            child.expect(pexpect.EOF, timeout=15)
            exit_status = child.exitstatus
            child.close()
            
            if exit_status == 0:
                password_valid = True
        except Exception as e:
            logger.error(f"Direct authentication failed: {e}")
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
