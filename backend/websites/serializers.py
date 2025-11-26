"""
Serializers for websites app.
"""
from rest_framework import serializers
from .models import Website, DatabaseCredential


class DatabaseCredentialSerializer(serializers.ModelSerializer):
    """Serializer for DatabaseCredential model."""
    class Meta:
        model = DatabaseCredential
        fields = ['id', 'db_name', 'db_user', 'db_host', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        # Note: db_password is intentionally excluded for security


class WebsiteSerializer(serializers.ModelSerializer):
    """Serializer for Website model."""
    database = DatabaseCredentialSerializer(read_only=True)
    
    class Meta:
        model = Website
        fields = [
            'id', 'domain', 'root_path', 'type', 'web_server',
            'php_version', 'status', 'created_at', 'updated_at', 'database'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

