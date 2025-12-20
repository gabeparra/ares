"""
Authentication views for Auth0.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .auth import require_auth, verify_auth_only, get_token_auth_header, verify_token, has_admin_role, Auth0Error


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
@verify_auth_only
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
@require_http_methods(["GET"])
def check_admin_role(request):
    """
    Check if the current user has admin role.
    This endpoint verifies the token but doesn't require admin role to call it.
    Returns detailed debugging information.
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    response_data = {
        'has_admin_role': False,
        'user_id': None,
        'email': None,
        'debug': {},
        'errors': []
    }
    
    # Verify token first (manually call the decorator logic)
    try:
        token = get_token_auth_header(request)
        
        if not token:
            response_data['errors'].append('No Authorization header found')
            logger.warning('No token found in request headers')
            print('[AUTH] No token found in request headers')
            return JsonResponse(response_data, status=200)
        
        try:
            logger.info(f'Verifying token (first 20 chars): {token[:20]}...')
            print(f'[AUTH] Verifying token (first 20 chars): {token[:20]}...')
            payload = verify_token(token)
            logger.info(f'Token verified successfully for user: {payload.get("sub")}')
            print(f'[AUTH] Token verified successfully for user: {payload.get("sub")}')
            request.auth0_user = payload
        except Auth0Error as auth_error:
            error_msg = str(auth_error)
            logger.error(f'Auth0Error verifying token: {error_msg}')
            print(f'[AUTH ERROR] Auth0Error: {error_msg}')
            response_data['errors'].append(f'Token verification failed: {error_msg}')
            return JsonResponse(response_data, status=200)
        except Exception as auth_error:
            error_msg = str(auth_error)
            error_trace = traceback.format_exc()
            logger.error(f'Exception verifying token: {error_msg}\n{error_trace}')
            print(f'[AUTH ERROR] Exception: {error_msg}\n{error_trace}')
            response_data['errors'].append(f'Token verification exception: {error_msg}')
            return JsonResponse(response_data, status=200)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error extracting token: {error_msg}')
        print(f'[AUTH ERROR] Error extracting token: {error_msg}')
        response_data['errors'].append(f'Error extracting token: {error_msg}')
        return JsonResponse(response_data, status=200)
    
    # Now check admin role
    try:
        if not hasattr(request, 'auth0_user') or not request.auth0_user:
            response_data['errors'].append('No auth0_user in request after verification')
            return JsonResponse(response_data, status=200)
        
        user_payload = request.auth0_user
        user_id = user_payload.get('sub')
        email = user_payload.get('email')
        
        response_data['user_id'] = user_id
        response_data['email'] = email
        
        logger.info(f'Checking admin role for user: {user_id}, email: {email}')
        print(f'[AUTH] Checking admin role for user: {user_id}, email: {email}')
        
        # Include debug info in response
        response_data['debug'] = {
            'user_id': user_id,
            'email': email,
            'payload_keys': list(user_payload.keys()) if user_payload else [],
        }
        
        try:
            is_admin, role_debug_info = has_admin_role(user_payload, return_debug=True)
            response_data['has_admin_role'] = is_admin
            response_data['debug']['role_check'] = role_debug_info
            logger.info(f'Admin role check result for {user_id}: {is_admin}')
            print(f'[AUTH] Admin role check result for {user_id}: {is_admin}')
            print(f'[AUTH] Role debug info: {role_debug_info}')
            
            return JsonResponse(response_data)
        except Auth0Error as role_check_error:
            error_msg = str(role_check_error)
            logger.error(f'Auth0Error checking admin role: {error_msg}', exc_info=True)
            print(f'[AUTH ERROR] Auth0Error checking roles: {error_msg}')
            response_data['errors'].append(f'Auth0Error checking roles: {error_msg}')
            return JsonResponse(response_data, status=200)
        except Exception as role_check_error:
            error_msg = str(role_check_error)
            error_trace = traceback.format_exc()
            logger.error(f'Error checking admin role: {error_msg}\n{error_trace}', exc_info=True)
            print(f'[AUTH ERROR] Exception checking roles: {error_msg}\n{error_trace}')
            response_data['errors'].append(f'Exception checking roles: {error_msg}')
            return JsonResponse(response_data, status=200)
        
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.error(f'Error in check_admin_role endpoint: {error_msg}\n{error_trace}', exc_info=True)
        print(f'[AUTH ERROR] Endpoint error: {error_msg}\n{error_trace}')
        response_data['errors'].append(f'Endpoint error: {error_msg}')
        if hasattr(request, 'auth0_user') and request.auth0_user:
            response_data['user_id'] = request.auth0_user.get('sub')
            response_data['email'] = request.auth0_user.get('email')
        return JsonResponse(response_data, status=200)


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

