"""
URL configuration for skydock_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/servers/', include('servers.urls')),
    path('api/websites/', include('websites.urls')),
    path('api/installer/', include('installer.urls')),
    # Frontend pages
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('services/', views.services, name='services'),
    path('websites/', views.websites, name='websites'),
    path('settings/', views.settings, name='settings'),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]

