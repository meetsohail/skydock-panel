"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SSHProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (read-only for profile)."""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_staff', 'is_active', 'created_at']
        read_only_fields = ['id', 'email', 'username', 'is_staff', 'is_active', 'created_at']


class SSHProfileSerializer(serializers.ModelSerializer):
    """Serializer for SSHProfile model (password only)."""
    class Meta:
        model = SSHProfile
        fields = ['id', 'ssh_username', 'auth_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'auth_type', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create SSH profile with encrypted password."""
        user = self.context['request'].user
        # Force auth_type to password
        validated_data['auth_type'] = SSHProfile.AUTH_TYPE_PASSWORD
        profile = SSHProfile.objects.create(user=user, **validated_data)
        
        # Handle password if provided
        password = self.context['request'].data.get('ssh_password')
        if password:
            profile.set_password(password)
            profile.save()
        
        return profile

    def update(self, instance, validated_data):
        """Update SSH profile with encrypted password."""
        # Force auth_type to password
        validated_data['auth_type'] = SSHProfile.AUTH_TYPE_PASSWORD
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle password if provided (only update if new password is provided)
        password = self.context['request'].data.get('ssh_password')
        if password and password.strip():
            instance.set_password(password)
        
        instance.save()
        return instance

