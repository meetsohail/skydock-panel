"""
URLs for servers app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('metrics/', views.server_metrics, name='server_metrics'),
    path('info/', views.server_info, name='server_info'),
    path('services/', views.services_list, name='services_list'),
    path('services/control/', views.service_control, name='service_control'),
    path('services/<str:service_name>/logs/', views.service_logs, name='service_logs'),
]

