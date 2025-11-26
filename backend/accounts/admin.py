"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SSHProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    list_display = ['email', 'username', 'is_staff', 'is_active', 'created_at']
    list_filter = ['is_staff', 'is_active', 'created_at']
    search_fields = ['email', 'username']
    ordering = ['-created_at']


@admin.register(SSHProfile)
class SSHProfileAdmin(admin.ModelAdmin):
    """Admin interface for SSHProfile model."""
    list_display = ['user', 'ssh_username', 'auth_type', 'created_at']
    list_filter = ['auth_type', 'created_at']
    search_fields = ['user__email', 'ssh_username']
    readonly_fields = ['created_at', 'updated_at']

