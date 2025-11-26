"""
Serializers for servers app.
"""
from rest_framework import serializers
from .models import Server


class ServerSerializer(serializers.ModelSerializer):
    """Serializer for Server model."""
    class Meta:
        model = Server
        fields = [
            'id', 'hostname', 'ip_address', 'os_name', 'os_version',
            'total_ram', 'total_disk', 'cpu_count', 'is_local',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

