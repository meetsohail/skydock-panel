"""
Admin configuration for websites app.
"""
from django.contrib import admin
from .models import Website, DatabaseCredential


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    """Admin interface for Website model."""
    list_display = ['domain', 'user', 'type', 'web_server', 'php_version', 'status', 'created_at']
    list_filter = ['type', 'web_server', 'status', 'user', 'created_at']
    search_fields = ['domain', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']


@admin.register(DatabaseCredential)
class DatabaseCredentialAdmin(admin.ModelAdmin):
    """Admin interface for DatabaseCredential model."""
    list_display = ['website', 'db_name', 'db_user', 'db_host', 'created_at']
    list_filter = ['created_at']
    search_fields = ['website__domain', 'db_name', 'db_user']
    readonly_fields = ['created_at', 'updated_at']

