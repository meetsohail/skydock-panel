"""
WSGI config for skydock_backend project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skydock_backend.settings')

application = get_wsgi_application()

