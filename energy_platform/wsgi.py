"""
Django WSGI config for energy_platform.
"""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'energy_platform.settings')
application = get_wsgi_application()
