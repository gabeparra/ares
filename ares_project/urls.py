"""
URL configuration for ARES project.
"""
from django.contrib import admin
from django.urls import path, include
from api.auth_redirect import auth0_callback_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    # Redirect /api/ to root for Auth0 callbacks
    path('api/', auth0_callback_redirect, name='auth0_callback_redirect'),
]

