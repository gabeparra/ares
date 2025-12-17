"""
Authentication views for Auth0.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .auth import require_auth, get_token_auth_header, verify_token


@csrf_exempt
@require_http_methods(["GET"])
def auth_config(request):
    """
    Return Auth0 configuration for frontend.
    Public endpoint - no authentication required.
    """
    return JsonResponse({
        'domain': settings.AUTH0_DOMAIN,
        'clientId': settings.AUTH0_CLIENT_ID,
        'audience': settings.AUTH0_AUDIENCE,
    })


@csrf_exempt
@require_http_methods(["GET"])
@require_auth
def user_info(request):
    """
    Get current user information from Auth0 token.
    """
    user = request.auth0_user
    return JsonResponse({
        'sub': user.get('sub'),
        'email': user.get('email'),
        'name': user.get('name'),
        'nickname': user.get('nickname'),
        'picture': user.get('picture'),
    })


@csrf_exempt
@require_http_methods(["POST"])
def verify_token_view(request):
    """
    Verify an Auth0 token and return user info.
    """
    try:
        token = get_token_auth_header(request)
        if not token:
            # Try to get from request body
            import json
            data = json.loads(request.body)
            token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Token required'}, status=400)
        
        payload = verify_token(token)
        return JsonResponse({
            'valid': True,
            'sub': payload.get('sub'),
            'email': payload.get('email'),
            'name': payload.get('name'),
        })
    except Exception as e:
        return JsonResponse({'valid': False, 'error': str(e)}, status=401)

