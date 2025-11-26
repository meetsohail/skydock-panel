"""
URLs for websites app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.websites_list, name='websites_list'),
    path('<int:website_id>/', views.website_detail, name='website_detail'),
    path('<int:website_id>/toggle-status/', views.website_toggle_status, name='website_toggle_status'),
]

