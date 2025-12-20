"""
Auth0 authentication utilities for Django REST Framework.
"""
import jwt
import time
from jwt.algorithms import RSAAlgorithm
import requests
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class Auth0Error(Exception):
    """Custom exception for Auth0 errors"""
    pass


# Admin role ID from Auth0
ADMIN_ROLE_ID = 'rol_BysmqyxaOLmdalmX'

# Cache for Management API token
_management_api_token = None
_management_api_token_expiry = 0


def get_management_api_token():
    """Get an access token for Auth0 Management API using M2M client credentials"""
    global _management_api_token, _management_api_token_expiry
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Return cached token if still valid
    if _management_api_token and time.time() < _management_api_token_expiry:
        logger.debug('Using cached Management API token')
        return _management_api_token
    
    if not settings.AUTH0_DOMAIN:
        raise Auth0Error('AUTH0_DOMAIN not configured')
    if not settings.AUTH0_M2M_CLIENT_ID:
        raise Auth0Error('AUTH0_M2M_CLIENT_ID not configured (need Machine-to-Machine app)')
    if not settings.AUTH0_M2M_CLIENT_SECRET:
        raise Auth0Error('AUTH0_M2M_CLIENT_SECRET not configured (need Machine-to-Machine app)')
    
    # Auth0 Management API endpoint
    domain = settings.AUTH0_DOMAIN
    token_url = f'https://{domain}/oauth/token'
    
    # Management API audience
    audience = f'https://{domain}/api/v2/'
    
    payload = {
        'client_id': settings.AUTH0_M2M_CLIENT_ID,
        'client_secret': settings.AUTH0_M2M_CLIENT_SECRET,
        'audience': audience,
        'grant_type': 'client_credentials'
    }
    
    logger.info(f'Requesting Management API token from {token_url} with M2M client {settings.AUTH0_M2M_CLIENT_ID}')
    
    try:
        response = requests.post(token_url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f'Management API token request failed: {response.status_code} - {response.text}')
        response.raise_for_status()
        token_data = response.json()
        _management_api_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)
        _management_api_token_expiry = time.time() + expires_in - 60  # Refresh 60s early
        logger.info('Successfully obtained Management API token')
        return _management_api_token
    except requests.exceptions.HTTPError as e:
        error_msg = f'HTTP error getting Management API token: {e.response.status_code} - {e.response.text}'
        logger.error(error_msg)
        raise Auth0Error(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f'Failed to get Management API token: {str(e)}'
        logger.error(error_msg)
        raise Auth0Error(error_msg)


def check_user_has_role(user_id, role_id):
    """Check if a user has a specific role using Auth0 Management API
    Returns: (has_role: bool, roles_list: list, debug_info: dict)
    """
    if not user_id:
        return False, [], {'error': 'No user_id provided'}
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        token = get_management_api_token()
        if not token:
            logger.error('Failed to get Management API token')
            raise Auth0Error('Failed to get Management API token')
        
        domain = settings.AUTH0_DOMAIN
        from urllib.parse import quote
        encoded_user_id = quote(user_id, safe='')
        url = f'https://{domain}/api/v2/users/{encoded_user_id}/roles'
        
        logger.info(f'Checking roles for user {user_id} (encoded: {encoded_user_id}) at {url}')
        print(f'[AUTH] Checking roles for user {user_id} at {url}')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f'Management API returned status {response.status_code}: {error_text}')
            print(f'[AUTH ERROR] Management API returned status {response.status_code}: {error_text}')
            response.raise_for_status()
        
        roles = response.json()
        role_names = [r.get("name") for r in roles]
        role_ids = [r.get("id") for r in roles]
        logger.info(f'User {user_id} has {len(roles)} roles: {role_names}')
        print(f'[AUTH] User {user_id} has {len(roles)} roles: {role_names}')
        print(f'[AUTH] Role IDs: {role_ids}')
        print(f'[AUTH] Looking for admin role ID: {role_id}')
        
        # Check if user has the admin role (by ID or name)
        has_admin = False
        match_details = {}
        for role in roles:
            role_name = role.get('name', '').lower()
            role_id_from_api = role.get('id')
            logger.debug(f'Checking role: id={role_id_from_api}, name={role.get("name")}')
            print(f'[AUTH] Checking role: id={role_id_from_api}, name={role.get("name")}')
            
            if role_id_from_api == role_id:
                has_admin = True
                match_details = {'matched_by': 'id', 'role_id': role_id_from_api, 'role_name': role.get('name')}
                logger.info(f'User {user_id} has admin role (matched by ID)')
                print(f'[AUTH] ✓ Matched by ID: {role_id_from_api}')
                break
            elif role_name == 'admin':
                has_admin = True
                match_details = {'matched_by': 'name', 'role_id': role_id_from_api, 'role_name': role.get('name')}
                logger.info(f'User {user_id} has admin role (matched by name)')
                print(f'[AUTH] ✓ Matched by name: {role.get("name")}')
                break
        
        if not has_admin:
            logger.info(f'User {user_id} does not have admin role')
            print(f'[AUTH] ✗ No admin role found. User has {len(roles)} role(s)')
        
        debug_info = {
            'user_id': user_id,
            'roles_found': len(roles),
            'role_names': role_names,
            'role_ids': role_ids,
            'looking_for_role_id': role_id,
            'has_admin': has_admin,
            'match_details': match_details if has_admin else None
        }
        
        return has_admin, roles, debug_info
        
    except requests.exceptions.HTTPError as e:
        error_msg = f'HTTP error checking user roles: {e.response.status_code} - {e.response.text}'
        logger.error(error_msg)
        raise Auth0Error(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f'Failed to check user roles: {str(e)}'
        logger.error(error_msg)
        raise Auth0Error(error_msg)


def has_admin_role(payload, return_debug=False):
    """Check if the user has the admin role using Auth0 Management API
    If return_debug=True, returns (has_role, debug_info) tuple
    """
    user_id = payload.get('sub')
    if not user_id:
        if return_debug:
            return False, {'error': 'No user_id in token payload', 'payload_keys': list(payload.keys())}
        return False
    
    try:
        has_role, roles, debug_info = check_user_has_role(user_id, ADMIN_ROLE_ID)
        if return_debug:
            return has_role, debug_info
        return has_role
    except Auth0Error as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Failed to check admin role for user {user_id}: {str(e)}')
        if return_debug:
            return False, {'error': str(e), 'user_id': user_id}
        return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Unexpected error checking admin role for user {user_id}: {str(e)}')
        if return_debug:
            return False, {'error': str(e), 'user_id': user_id}
        return False


def get_token_auth_header(request):
    """Extract token from Authorization header"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check various possible header locations
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        # Try alternative header name (some proxies modify this)
        auth_header = request.META.get('Authorization', '')
    
    if not auth_header:
        logger.debug(f'No Authorization header. Available headers: {list(k for k in request.META.keys() if "AUTH" in k.upper() or "HEADER" in k.upper())}')
        print(f'[AUTH DEBUG] No Authorization header found. Available auth-related headers: {[k for k in request.META.keys() if "AUTH" in k.upper()]}')
        return None
    
    parts = auth_header.split()
    
    if len(parts) == 0:
        return None
    
    if parts[0].lower() != 'bearer':
        logger.warning(f'Authorization header does not start with "Bearer", got: {parts[0]}')
        print(f'[AUTH] Authorization header does not start with "Bearer", got: {parts[0]}')
        return None
    
    if len(parts) == 1:
        raise Auth0Error('Token not found in Authorization header')
    
    if len(parts) > 2:
        raise Auth0Error('Authorization header must be Bearer token')
    
    token = parts[1]
    logger.debug(f'Extracted token (length: {len(token)})')
    return token


def verify_token(token):
    """Verify Auth0 JWT token (access token or ID token)"""
    import logging
    logger = logging.getLogger(__name__)
    
    if not settings.AUTH0_DOMAIN:
        raise Auth0Error('AUTH0_DOMAIN not configured')
    
    jwks_url = f'https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json'
    
    try:
        jwks = requests.get(jwks_url).json()
    except Exception as e:
        raise Auth0Error(f'Failed to fetch JWKS: {str(e)}')
    
    try:
        unverified_header = jwt.get_unverified_header(token)
        logger.info(f'Token header: {unverified_header}')
        print(f'[AUTH] Token header: {unverified_header}')
    except Exception as e:
        raise Auth0Error(f'Invalid token header: {str(e)}')
    
    # Check if token has 'kid' field (required for signed JWTs)
    if 'kid' not in unverified_header:
        header_fields = list(unverified_header.keys())
        error_msg = f'Token header missing "kid" field. Header fields: {header_fields}. Token appears to be encrypted (JWE). Use ID token instead, or configure Auth0 API to issue signed tokens.'
        logger.error(error_msg)
        print(f'[AUTH ERROR] {error_msg}')
        raise Auth0Error(error_msg)
    
    # Check algorithm
    alg = unverified_header.get('alg', 'unknown')
    if alg not in ['RS256', 'RS384', 'RS512']:
        error_msg = f'Token uses unsupported algorithm: {alg}. Expected RS256, RS384, or RS512.'
        logger.error(error_msg)
        print(f'[AUTH ERROR] {error_msg}')
        raise Auth0Error(error_msg)
    
    rsa_key = {}
    token_kid = unverified_header['kid']
    for key in jwks['keys']:
        if key.get('kid') == token_kid:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
            break
    
    if not rsa_key:
        raise Auth0Error(f'Unable to find key with kid="{token_kid}" in JWKS')
    
    try:
        public_key = RSAAlgorithm.from_jwk(rsa_key)
        issuer = f'https://{settings.AUTH0_DOMAIN}/'
        
        # Initialize variables for exception handler
        token_audience = None
        is_id_token = False
        
        # First decode without verification to check the audience
        try:
            unverified_payload = jwt.decode(token, public_key, algorithms=['RS256'], options={"verify_signature": False, "verify_exp": False})
            token_audience = unverified_payload.get('aud')
            
            # Determine if this is an ID token (audience = client_id) or access token (audience = API identifier)
            if settings.AUTH0_CLIENT_ID and (token_audience == settings.AUTH0_CLIENT_ID or 
                (isinstance(token_audience, list) and settings.AUTH0_CLIENT_ID in token_audience)):
                is_id_token = True
                logger.info('Token is ID token (audience matches client_id)')
                print('[AUTH] Token is ID token')
        except Exception as e:
            logger.warning(f'Could not decode token to check audience: {str(e)}')
            print(f'[AUTH] Could not decode token to check audience: {str(e)}')
        
        # Now verify with proper audience
        if is_id_token:
            # ID token - verify with client_id as audience
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                issuer=issuer,
                audience=settings.AUTH0_CLIENT_ID
            )
        elif settings.AUTH0_AUDIENCE:
            # Access token - verify with API audience
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                issuer=issuer,
                audience=settings.AUTH0_AUDIENCE
            )
        else:
            # No audience configured - verify without audience check
            logger.warning('No AUTH0_AUDIENCE configured, verifying token without audience check')
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                issuer=issuer,
                options={"verify_aud": False}
            )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise Auth0Error('Token is expired')
    except jwt.InvalidAudienceError as e:
        expected_audience = settings.AUTH0_CLIENT_ID if is_id_token else settings.AUTH0_AUDIENCE
        raise Auth0Error(f'Invalid audience. Token audience: {token_audience}, Expected: {expected_audience}')
    except jwt.InvalidIssuerError:
        raise Auth0Error(f'Invalid issuer. Expected: {issuer}')
    except Exception as e:
        raise Auth0Error(f'Invalid token: {str(e)}')


class Auth0Authentication(BaseAuthentication):
    """
    Custom authentication class for Auth0 JWT tokens.
    """
    def authenticate(self, request):
        token = get_token_auth_header(request)
        
        if not token:
            return None
        
        try:
            payload = verify_token(token)
            
            # Check if user has admin role
            if not has_admin_role(payload):
                raise AuthenticationFailed('Access denied. This application is restricted to users with admin role.')
            
            # Return a user object and the token
            # For now, we'll use the sub (subject) from the token as the user identifier
            user = type('User', (), {
                'is_authenticated': True,
                'sub': payload.get('sub'),
                'email': payload.get('email'),
                'name': payload.get('name'),
                'payload': payload
            })()
            return (user, token)
        except Auth0Error as e:
            raise AuthenticationFailed(str(e))
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')


def verify_auth_only(view_func):
    """Decorator to verify Auth0 authentication without role checking"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        token = get_token_auth_header(request)
        
        if not token:
            logger.warning('No token found in request headers')
            print('[AUTH] No token found in request headers')
            return JsonResponse({
                'error': 'Authentication required',
                'debug': 'No Authorization header found'
            }, status=401)
        
        try:
            logger.info(f'Verifying token (first 20 chars): {token[:20]}...')
            print(f'[AUTH] Verifying token (first 20 chars): {token[:20]}...')
            payload = verify_token(token)
            logger.info(f'Token verified successfully for user: {payload.get("sub")}')
            print(f'[AUTH] Token verified successfully for user: {payload.get("sub")}')
            request.auth0_user = payload
            return view_func(request, *args, **kwargs)
        except Auth0Error as e:
            logger.error(f'Auth0Error verifying token: {str(e)}')
            print(f'[AUTH ERROR] Auth0Error: {str(e)}')
            return JsonResponse({
                'error': str(e),
                'error_type': 'Auth0Error'
            }, status=401)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f'Exception verifying token: {str(e)}\n{error_trace}')
            print(f'[AUTH ERROR] Exception: {str(e)}\n{error_trace}')
            return JsonResponse({
                'error': f'Authentication failed: {str(e)}',
                'error_type': 'Exception'
            }, status=401)
    
    return wrapper


def require_auth(view_func):
    """Decorator to require Auth0 authentication with admin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = get_token_auth_header(request)
        
        if not token:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            payload = verify_token(token)
            
            # Check if user has admin role
            if not has_admin_role(payload):
                return JsonResponse({
                    'error': 'Access denied. This application is restricted to users with admin role.'
                }, status=403)
            
            request.auth0_user = payload
            return view_func(request, *args, **kwargs)
        except Auth0Error as e:
            return JsonResponse({'error': str(e)}, status=401)
        except Exception as e:
            return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=401)
    
    return wrapper

