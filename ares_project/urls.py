"""
URL configuration for ARES project.
"""
from django.contrib import admin
from django.urls import path, include
from api.auth_redirect import auth0_callback_redirect
from api import upscale_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    # Redirect /api/ to root for Auth0 callbacks
    path('api/', auth0_callback_redirect, name='auth0_callback_redirect'),
    # SD API upscaling endpoints (intercept before nginx proxy)
    # Note: Only specific endpoints are handled by Django, others are proxied by nginx
    path('sdapi/v1/upscale', upscale_views.upscale, name='sdapi_upscale'),
    path('sdapi/v1/upscale-batch', upscale_views.upscale_batch, name='sdapi_upscale_batch'),
    path('sdapi/v1/upscalers', upscale_views.upscalers, name='sdapi_upscalers'),
    # All other /sdapi/ requests should be proxied by nginx, not handled by Django
]

