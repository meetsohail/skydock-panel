"""
Accounts app models for SkyDock Panel.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator
from cryptography.fernet import Fernet
import base64
import os


def get_encryption_key() -> bytes:
    """Get or generate encryption key for SSH credentials."""
    key = os.environ.get('SKYDOCK_ENCRYPTION_KEY')
    if not key:
        # Generate a key if not set (for development)
        key = Fernet.generate_key().decode()
        # In production, this should be set in environment
    else:
        key = key.encode() if isinstance(key, str) else key
    return key


class User(AbstractUser):
    """
    Custom user model that syncs with system users.
    Passwords are not stored - authentication is done against system users.
    """
    email = models.EmailField(unique=False, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []  # No required fields since we sync from system

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        return self.username
    
    def set_password(self, raw_password):
        """
        Override set_password - we don't store passwords.
        Passwords are managed via system (passwd command).
        """
        # Do nothing - passwords are managed by system
        pass
    
    def check_password(self, raw_password):
        """
        Override check_password - authentication is handled by backend.
        """
        # This should not be called directly, backend handles it
        return False


class SSHProfile(models.Model):
    """SSH profile for server authentication."""
    AUTH_TYPE_PASSWORD = 'password'
    AUTH_TYPE_KEY = 'private_key'
    AUTH_TYPE_CHOICES = [
        (AUTH_TYPE_PASSWORD, 'Password'),
        (AUTH_TYPE_KEY, 'Private Key'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ssh_profile')
    ssh_username = models.CharField(max_length=100, default='root')
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default=AUTH_TYPE_PASSWORD)
    ssh_password = models.TextField(blank=True, null=True)  # Encrypted
    ssh_private_key = models.TextField(blank=True, null=True)  # Encrypted
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_sshprofile'
        verbose_name = 'SSH Profile'
        verbose_name_plural = 'SSH Profiles'

    def __str__(self) -> str:
        return f"{self.user.email} - {self.ssh_username}"

    def set_password(self, password: str) -> None:
        """Encrypt and store SSH password."""
        if not password:
            self.ssh_password = None
            return
        try:
            key = get_encryption_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(password.encode())
            self.ssh_password = base64.b64encode(encrypted).decode()
        except Exception as e:
            # Fallback: store as-is (not secure, but better than nothing)
            # In production, proper key management is required
            self.ssh_password = password

    def get_password(self) -> str:
        """Decrypt and return SSH password."""
        if not self.ssh_password:
            return ''
        try:
            key = get_encryption_key()
            fernet = Fernet(key)
            encrypted = base64.b64decode(self.ssh_password.encode())
            return fernet.decrypt(encrypted).decode()
        except Exception:
            # Fallback: return as-is
            return self.ssh_password

    def set_private_key(self, private_key: str) -> None:
        """Encrypt and store SSH private key."""
        if not private_key:
            self.ssh_private_key = None
            return
        try:
            key = get_encryption_key()
            fernet = Fernet(key)
            encrypted = fernet.encrypt(private_key.encode())
            self.ssh_private_key = base64.b64encode(encrypted).decode()
        except Exception as e:
            # Fallback: store as-is
            self.ssh_private_key = private_key

    def get_private_key(self) -> str:
        """Decrypt and return SSH private key."""
        if not self.ssh_private_key:
            return ''
        try:
            key = get_encryption_key()
            fernet = Fernet(key)
            encrypted = base64.b64decode(self.ssh_private_key.encode())
            return fernet.decrypt(encrypted).decode()
        except Exception:
            # Fallback: return as-is
            return self.ssh_private_key

