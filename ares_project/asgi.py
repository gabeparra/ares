"""
ASGI config for ARES project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ares_project.settings')

application = get_asgi_application()

