"""
Redirect view for Auth0 callbacks that land on /api/ instead of root.
"""
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@require_http_methods(["GET"])
def auth0_callback_redirect(request):
    """
    Redirect Auth0 callbacks from /api/ to root /.
    This handles cases where Auth0 redirects to the wrong URL.
    """
    # Preserve query parameters (code, state, etc.)
    query_string = request.META.get('QUERY_STRING', '')
    redirect_url = '/'
    if query_string:
        redirect_url = f'/?{query_string}'
    
    return HttpResponseRedirect(redirect_url)

