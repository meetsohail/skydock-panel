"""
Views for servers app.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .utils import get_system_info, check_service_status, manage_service, get_service_logs
from .models import Server
from .serializers import ServerSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def server_metrics(request):
    """Get current server metrics."""
    try:
        metrics = get_system_info()
        return Response(metrics)
    except Exception as e:
        return Response(
            {'error': f'Failed to get server metrics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def server_info(request):
    """Get server information (stored in database)."""
    try:
        server = Server.objects.filter(is_local=True).first()
        if not server:
            # Create local server entry if it doesn't exist
            system_info = get_system_info()
            server = Server.objects.create(
                hostname=system_info['hostname'],
                ip_address=system_info['ip_address'],
                os_name=system_info['os_name'],
                os_version=system_info['os_version'],
                total_ram=system_info['memory']['total'],
                total_disk=system_info['disk']['total'],
                cpu_count=system_info['cpu']['count'],
                is_local=True
            )
        
        serializer = ServerSerializer(server)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': f'Failed to get server info: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def services_list(request):
    """Get list of services and their status."""
    services = ['nginx', 'apache2', 'mysql']
    result = {}
    
    for service in services:
        result[service] = check_service_status(service)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def service_control(request):
    """Control a service (start/stop/restart)."""
    service_name = request.data.get('service')
    action = request.data.get('action')
    
    if not service_name or not action:
        return Response(
            {'error': 'Service name and action are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = manage_service(service_name, action)
    
    if result['success']:
        return Response(result)
    else:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_logs(request, service_name: str):
    """Get service logs."""
    lines = int(request.query_params.get('lines', 50))
    
    try:
        logs = get_service_logs(service_name, lines)
        return Response({'logs': logs})
    except Exception as e:
        return Response(
            {'error': f'Failed to get logs: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

