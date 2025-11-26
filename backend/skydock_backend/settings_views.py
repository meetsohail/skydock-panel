"""
Settings views for SkyDock Panel.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def panel_port(request):
    """Get panel port from settings."""
    return Response({'port': settings.SKYDOCK_PANEL_PORT})

