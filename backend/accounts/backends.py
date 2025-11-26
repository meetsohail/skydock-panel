"""
Custom authentication backend for system user authentication.
"""
import pwd
import pexpect
import logging
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class SystemUserBackend(BaseBackend):
    """
    Authenticate against system users using /etc/passwd.
    Uses pexpect to verify passwords via su command.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Check if user exists in system
        try:
            pwd_entry = pwd.getpwnam(username)
        except KeyError:
            # User doesn't exist in system
            logger.debug(f"User {username} not found in system")
            return None
        
        # Verify password using pexpect with su
        password_valid = False
        try:
            # Use su to verify password
            child = pexpect.spawn(
                'su',
                ['-c', 'exit 0', username],
                timeout=10,
                encoding='utf-8',
                echo=False
            )
            
            # Wait for password prompt - try multiple patterns
            patterns = [
                'Password:',
                'password:',
                'Password for',
                'password for',
                pexpect.EOF,
                pexpect.TIMEOUT
            ]
            
            index = child.expect(patterns, timeout=10)
            
            # If we got EOF or TIMEOUT before prompt, authentication failed
            if index >= len(patterns) - 2:  # EOF or TIMEOUT
                logger.debug(f"No password prompt for user {username}")
                child.close(force=True)
                return None
            
            # Send password
            child.sendline(password)
            
            # Wait for command to complete
            child.expect(pexpect.EOF, timeout=10)
            
            # Get exit status before closing
            exit_status = child.exitstatus
            child.close()
            
            if exit_status == 0:
                password_valid = True
                logger.debug(f"Password verified successfully for user {username}")
            else:
                logger.debug(f"Password verification failed for user {username} (exit: {exit_status})")
                
        except pexpect.TIMEOUT:
            logger.debug(f"Timeout during password verification for user {username}")
            try:
                child.close(force=True)
            except:
                pass
            return None
        except pexpect.EOF:
            logger.debug(f"Unexpected EOF during password verification for user {username}")
            return None
        except Exception as e:
            logger.error(f"Error during password verification for user {username}: {e}")
            return None
        
        if password_valid:
            # Password is correct, get or create Django user
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            # Update user info from system
            try:
                if not user.email:
                    # Try to set email from GECOS field if available
                    gecos = pwd_entry.pw_gecos.split(',')[0] if pwd_entry.pw_gecos else ''
                    if '@' in gecos:
                        user.email = gecos
                    else:
                        # Set a default email based on username
                        user.email = f"{username}@localhost"
                user.save()
            except Exception as e:
                logger.debug(f"Error updating user info: {e}")
            
            logger.info(f"User {username} authenticated successfully")
            return user
        
        return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
