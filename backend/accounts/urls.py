"""
URLs for accounts app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.current_user, name='current_user'),
    path('ssh-profile/', views.ssh_profile, name='ssh_profile'),
]

