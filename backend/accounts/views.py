"""
Views for accounts app.
"""
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import SSHProfile
from .serializers import UserSerializer, SSHProfileSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data
        })
    else:
        return Response(
            {'error': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint."""
    logout(request)
    return Response({'message': 'Logout successful'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Get current authenticated user."""
    return Response({
        'user': UserSerializer(request.user).data
    })


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def ssh_profile(request):
    """Get or update SSH profile (password only)."""
    profile, created = SSHProfile.objects.get_or_create(
        user=request.user,
        defaults={'auth_type': SSHProfile.AUTH_TYPE_PASSWORD}
    )

    if request.method == 'GET':
        serializer = SSHProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    elif request.method in ['POST', 'PUT']:
        serializer = SSHProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change system user password."""
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response(
            {'success': False, 'error': 'Current password and new password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(new_password) < 6:
        return Response(
            {'success': False, 'error': 'New password must be at least 6 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify current password
    from django.contrib.auth import authenticate
    user = authenticate(request, username=request.user.username, password=current_password)
    if user is None:
        return Response(
            {'success': False, 'error': 'Current password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Change password using passwd command
    import pexpect
    import os
    
    try:
        # Find passwd command
        passwd_paths = ['/usr/bin/passwd', '/bin/passwd', 'passwd']
        passwd_path = None
        
        for path in passwd_paths:
            if os.path.exists(path) or path == 'passwd':
                passwd_path = path
                break
        
        if not passwd_path:
            return Response(
                {'success': False, 'error': 'passwd command not found'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Use pexpect to change password
        env = os.environ.copy()
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        
        child = pexpect.spawn(
            passwd_path,
            [request.user.username],
            timeout=15,
            encoding='utf-8',
            echo=False,
            env=env
        )
        
        # Wait for password prompts
        patterns = [
            'New password:',
            'new password:',
            'password:',
            pexpect.EOF,
            pexpect.TIMEOUT
        ]
        
        index = child.expect(patterns, timeout=10)
        if index >= len(patterns) - 2:
            child.close(force=True)
            return Response(
                {'success': False, 'error': 'Password prompt not found'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        child.sendline(new_password)
        
        # Wait for confirmation prompt
        patterns2 = [
            'Retype new password:',
            'retype new password:',
            'password:',
            pexpect.EOF,
            pexpect.TIMEOUT
        ]
        
        index = child.expect(patterns2, timeout=10)
        if index >= len(patterns2) - 2:
            child.close(force=True)
            return Response(
                {'success': False, 'error': 'Confirmation prompt not found'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        child.sendline(new_password)
        
        child.expect(pexpect.EOF, timeout=10)
        exit_status = child.exitstatus
        child.close()
        
        # Check exit status (None or 0 means success)
        if exit_status == 0 or exit_status is None:
            return Response({'success': True, 'message': 'Password updated successfully'})
        else:
            return Response(
                {'success': False, 'error': 'Failed to update password. Please check password requirements.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except pexpect.TIMEOUT:
        return Response(
            {'success': False, 'error': 'Password change timeout'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'success': False, 'error': f'Error updating password: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

