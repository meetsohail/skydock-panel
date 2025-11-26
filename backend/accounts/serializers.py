"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SSHProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_staff', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class SSHProfileSerializer(serializers.ModelSerializer):
    """Serializer for SSHProfile model."""
    class Meta:
        model = SSHProfile
        fields = ['id', 'ssh_username', 'auth_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create SSH profile with encrypted credentials."""
        user = self.context['request'].user
        profile = SSHProfile.objects.create(user=user, **validated_data)
        
        # Handle password if provided
        password = self.context['request'].data.get('ssh_password')
        if password:
            profile.set_password(password)
            profile.save()
        
        # Handle private key if provided
        private_key = self.context['request'].data.get('ssh_private_key')
        if private_key:
            profile.set_private_key(private_key)
            profile.save()
        
        return profile

    def update(self, instance, validated_data):
        """Update SSH profile with encrypted credentials."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle password if provided
        password = self.context['request'].data.get('ssh_password')
        if password is not None:
            instance.set_password(password)
        
        # Handle private key if provided
        private_key = self.context['request'].data.get('ssh_private_key')
        if private_key is not None:
            instance.set_private_key(private_key)
        
        instance.save()
        return instance

