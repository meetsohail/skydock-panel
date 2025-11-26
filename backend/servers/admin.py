"""
Admin configuration for servers app.
"""
from django.contrib import admin
from .models import Server


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    """Admin interface for Server model."""
    list_display = ['hostname', 'ip_address', 'os_name', 'os_version', 'is_local', 'created_at']
    list_filter = ['is_local', 'os_name', 'created_at']
    search_fields = ['hostname', 'ip_address']
    readonly_fields = ['created_at', 'updated_at']

