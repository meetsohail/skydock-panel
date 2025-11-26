"""
URLs for settings API.
"""
from django.urls import path
from . import settings_views

urlpatterns = [
    path('panel-port/', settings_views.panel_port, name='panel_port'),
]

