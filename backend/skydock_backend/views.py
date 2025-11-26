"""
Main views for SkyDock Panel frontend.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages


def login_view(request):
    """Login page view."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Username and password are required.')
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')


def logout_page(request):
    """Logout page view."""
    logout(request)
    return redirect('login')


def index_view(request):
    """Root/index view - redirect to appropriate page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')


@login_required
def dashboard(request):
    """Dashboard page."""
    return render(request, 'dashboard.html')


@login_required
def services(request):
    """Services page."""
    return render(request, 'services.html')


@login_required
def websites(request):
    """Websites page."""
    return render(request, 'websites.html')


@login_required
def settings(request):
    """Settings page."""
    return render(request, 'settings.html')

