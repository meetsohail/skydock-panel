"""
Servers app models for SkyDock Panel.
"""
from django.db import models
from django.core.validators import MinValueValidator


class Server(models.Model):
    """Server model to store server information."""
    hostname = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    os_name = models.CharField(max_length=100)
    os_version = models.CharField(max_length=100)
    total_ram = models.BigIntegerField(help_text="Total RAM in bytes", validators=[MinValueValidator(0)])
    total_disk = models.BigIntegerField(help_text="Total disk space in bytes", validators=[MinValueValidator(0)])
    cpu_count = models.IntegerField(validators=[MinValueValidator(1)])
    is_local = models.BooleanField(default=True, help_text="Whether this is the local server")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'servers_server'
        verbose_name = 'Server'
        verbose_name_plural = 'Servers'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.hostname} ({self.ip_address})"

