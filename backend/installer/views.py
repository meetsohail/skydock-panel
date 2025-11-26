"""
Views for installer app (health check, installation status).
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'service': 'SkyDock Panel'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def install_status(request):
    """Check installation status."""
    # This can be expanded to check for required services, dependencies, etc.
    return Response({
        'installed': True,
        'version': '1.0.0'
    })

