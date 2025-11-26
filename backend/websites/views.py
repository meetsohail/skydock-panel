"""
Views for websites app.
"""
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Website, DatabaseCredential
from .serializers import WebsiteSerializer, DatabaseCredentialSerializer
from .utils import create_php_site, create_wordpress_site, disable_website

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def websites_list(request):
    """List all websites for the current user or create a new one."""
    if request.method == 'GET':
        # Only show websites belonging to the current user
        websites = Website.objects.filter(user=request.user)
        serializer = WebsiteSerializer(websites, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Create new website for the current user
        domain = request.data.get('domain', '').strip()
        website_type = request.data.get('type', Website.TYPE_PHP)
        # Always use nginx as reverse proxy to apache
        web_server = Website.WEB_SERVER_NGINX
        php_version = request.data.get('php_version', '8.1')
        
        if not domain:
            return Response(
                {'error': 'Domain is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate domain format
        import re
        domain_regex = re.compile(r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$', re.IGNORECASE)
        if not domain_regex.match(domain):
            return Response(
                {'error': 'Invalid domain format. Please enter a valid domain name (e.g., example.com)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For WordPress, require admin credentials
        wp_email = None
        wp_username = None
        wp_password = None
        
        if website_type == Website.TYPE_WORDPRESS:
            wp_email = request.data.get('wp_email', '').strip()
            wp_username = request.data.get('wp_username', '').strip()
            wp_password = request.data.get('wp_password', '').strip()
            
            if not wp_email or not wp_username or not wp_password:
                return Response(
                    {'error': 'WordPress admin email, username, and password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if user already has a website with this domain
        if Website.objects.filter(user=request.user, domain=domain).exists():
            return Response(
                {'error': 'You already have a website with this domain'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate root path - use username in path for organization
        root_path = os.path.join(settings.SKYDOCK_WEB_ROOT, request.user.username, domain)
        
        # Create website record
        website = Website.objects.create(
            user=request.user,
            domain=domain,
            root_path=root_path,
            type=website_type,
            web_server=web_server,  # Always nginx (as reverse proxy)
            php_version=php_version,
            status=Website.STATUS_ACTIVE,
            wp_admin_email=wp_email if website_type == Website.TYPE_WORDPRESS else None,
            wp_admin_user=wp_username if website_type == Website.TYPE_WORDPRESS else None,
            wp_admin_password=wp_password if website_type == Website.TYPE_WORDPRESS else None,
        )
        
        # Create the actual site
        if website_type == Website.TYPE_WORDPRESS:
            wp_email = request.data.get('wp_email')
            wp_username = request.data.get('wp_username')
            wp_password = request.data.get('wp_password')
            result = create_wordpress_site(website, wp_email, wp_username, wp_password)
        else:
            result = create_php_site(website)
        
        if not result['success']:
            website.delete()
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = WebsiteSerializer(website)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def website_detail(request, website_id: int):
    """Get, update, or delete a website (only if owned by current user)."""
    try:
        # Only allow access to websites owned by the current user
        website = Website.objects.get(id=website_id, user=request.user)
    except Website.DoesNotExist:
        return Response(
            {'error': 'Website not found or you do not have permission to access it'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        from .utils import get_website_storage
        
        serializer = WebsiteSerializer(website)
        data = serializer.data
        
        # Add storage information
        storage_info = get_website_storage(website)
        data['storage'] = storage_info
        
        # Add database credentials if available
        try:
            db_cred = DatabaseCredential.objects.get(website=website)
            data['database'] = {
                'name': db_cred.db_name,
                'user': db_cred.db_user,
                'password': db_cred.db_password,
                'host': db_cred.db_host
            }
        except DatabaseCredential.DoesNotExist:
            data['database'] = None
        
        return Response(data)
    
    elif request.method == 'PUT':
        serializer = WebsiteSerializer(website, data=request.data, partial=True)
        if serializer.is_valid():
            # Ensure user cannot be changed
            serializer.save(user=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Disable website first
        disable_website(website)
        website.delete()
        return Response({'message': 'Website deleted successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def website_toggle_status(request, website_id: int):
    """Enable or disable a website (only if owned by current user)."""
    try:
        # Only allow access to websites owned by the current user
        website = Website.objects.get(id=website_id, user=request.user)
    except Website.DoesNotExist:
        return Response(
            {'error': 'Website not found or you do not have permission to access it'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if website.status == Website.STATUS_ACTIVE:
        result = disable_website(website)
        if result['success']:
            website.status = Website.STATUS_DISABLED
            website.save()
            return Response({'message': 'Website disabled successfully'})
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    else:
        from .utils import enable_website
        result = enable_website(website)
        if result['success']:
            website.status = Website.STATUS_ACTIVE
            website.save()
            return Response({'message': 'Website enabled successfully'})
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

