"""
Custom authentication backend for system user authentication.
"""
import pwd
import pexpect
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model


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
            return None
        
        # Verify password using pexpect with su
        try:
            # Use su to verify password
            child = pexpect.spawn('su', ['-c', 'exit 0', username], timeout=3)
            child.expect('Password:', timeout=3)
            child.sendline(password)
            child.expect(pexpect.EOF, timeout=3)
            
            if child.exitstatus == 0:
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
                except Exception:
                    pass
                
                return user
        except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect):
            # Password verification failed
            return None
        except Exception:
            # Other errors
            return None
        
        return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
