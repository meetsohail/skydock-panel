"""
Websites app models for SkyDock Panel.
"""
from django.db import models
from django.core.validators import MinLengthValidator
from django.conf import settings


class Website(models.Model):
    """Website model - each website belongs to a user."""
    TYPE_PHP = 'php'
    TYPE_WORDPRESS = 'wordpress'
    TYPE_CHOICES = [
        (TYPE_PHP, 'PHP Application'),
        (TYPE_WORDPRESS, 'WordPress Site'),
    ]
    
    WEB_SERVER_NGINX = 'nginx'
    WEB_SERVER_APACHE = 'apache'
    WEB_SERVER_CHOICES = [
        (WEB_SERVER_NGINX, 'Nginx'),
        (WEB_SERVER_APACHE, 'Apache'),
    ]
    
    STATUS_ACTIVE = 'active'
    STATUS_DISABLED = 'disabled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DISABLED, 'Disabled'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='websites',
        help_text="Owner of this website"
    )
    domain = models.CharField(max_length=255, validators=[MinLengthValidator(3)])
    root_path = models.CharField(max_length=500, help_text="Document root path")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_PHP)
    web_server = models.CharField(max_length=20, choices=WEB_SERVER_CHOICES, default=WEB_SERVER_NGINX)
    php_version = models.CharField(max_length=10, default='8.1', help_text="PHP version (e.g., 8.1, 8.2)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    # WordPress specific fields
    wp_admin_email = models.EmailField(max_length=255, blank=True, null=True)
    wp_admin_user = models.CharField(max_length=100, blank=True, null=True)
    wp_admin_password = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'websites_website'
        verbose_name = 'Website'
        verbose_name_plural = 'Websites'
        ordering = ['-created_at']
        # Domain must be unique per user, not globally
        unique_together = [['user', 'domain']]

    def __str__(self) -> str:
        return f"{self.domain} ({self.type})"


class DatabaseCredential(models.Model):
    """Database credentials for WordPress sites."""
    website = models.OneToOneField(Website, on_delete=models.CASCADE, related_name='database')
    db_name = models.CharField(max_length=100)
    db_user = models.CharField(max_length=100)
    db_password = models.CharField(max_length=255)
    db_host = models.CharField(max_length=100, default='localhost')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'websites_databasecredential'
        verbose_name = 'Database Credential'
        verbose_name_plural = 'Database Credentials'

    def __str__(self) -> str:
        return f"{self.website.domain} - {self.db_name}"

