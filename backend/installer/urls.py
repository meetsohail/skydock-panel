"""
URLs for installer app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('status/', views.install_status, name='install_status'),
]

