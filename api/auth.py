"""
Auth0 authentication utilities for Django REST Framework.
"""
import jwt
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


def get_token_auth_header(request):
    """Extract token from Authorization header"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if parts[0].lower() != 'bearer':
        return None
    
    if len(parts) == 1:
        raise Auth0Error('Token not found')
    
    if len(parts) > 2:
        raise Auth0Error('Authorization header must be Bearer token')
    
    return parts[1]


def verify_token(token):
    """Verify Auth0 JWT token"""
    if not settings.AUTH0_DOMAIN:
        raise Auth0Error('AUTH0_DOMAIN not configured')
    
    jwks_url = f'https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json'
    
    try:
        jwks = requests.get(jwks_url).json()
    except Exception as e:
        raise Auth0Error(f'Failed to fetch JWKS: {str(e)}')
    
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        raise Auth0Error(f'Invalid token header: {str(e)}')
    
    rsa_key = {}
    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
            break
    
    if not rsa_key:
        raise Auth0Error('Unable to find appropriate key')
    
    try:
        public_key = RSAAlgorithm.from_jwk(rsa_key)
        
        issuer = f'https://{settings.AUTH0_DOMAIN}/'
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=settings.AUTH0_AUDIENCE,
            issuer=issuer
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise Auth0Error('Token is expired')
    except jwt.InvalidAudienceError:
        raise Auth0Error('Invalid audience')
    except jwt.InvalidIssuerError:
        raise Auth0Error('Invalid issuer')
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


def require_auth(view_func):
    """Decorator to require Auth0 authentication"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = get_token_auth_header(request)
        
        if not token:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            payload = verify_token(token)
            request.auth0_user = payload
            return view_func(request, *args, **kwargs)
        except Auth0Error as e:
            return JsonResponse({'error': str(e)}, status=401)
        except Exception as e:
            return JsonResponse({'error': f'Authentication failed: {str(e)}'}, status=401)
    
    return wrapper

