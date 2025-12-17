from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import httpx


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """
    Unified /v1/chat endpoint for ARES.
    Accepts chat messages and routes them to local LLM (Ollama).
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id')
        model = data.get('model') or getattr(settings, 'DEFAULT_MODEL', None)
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Route to Ollama
        ollama_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        
        messages = [{'role': 'user', 'content': message}]
        
        payload = {
            'model': model or 'llama3.2:3b',
            'messages': messages,
            'stream': False,
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(ollama_url, json=payload)
            response.raise_for_status()
            result = response.json()
        
        return JsonResponse({
            'response': result.get('message', {}).get('content', ''),
            'model': model,
            'session_id': session_id,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
def models_list(request):
    """
    GET: List available models
    POST: Set current model
    """
    if request.method == 'GET':
        try:
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/tags"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(ollama_url)
                response.raise_for_status()
                result = response.json()
            
            models = [model['name'] for model in result.get('models', [])]
            
            return JsonResponse({
                'models': models,
                'current_model': getattr(settings, 'CURRENT_MODEL', None),
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            model = data.get('model')
            
            if not model:
                return JsonResponse({'error': 'Model name is required'}, status=400)
            
            # In a real implementation, store this in database or cache
            # For now, just validate the model exists
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/tags"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(ollama_url)
                response.raise_for_status()
                result = response.json()
            
            available_models = [m['name'] for m in result.get('models', [])]
            
            if model not in available_models:
                return JsonResponse({'error': f'Model {model} not found'}, status=404)
            
            return JsonResponse({'success': True, 'model': model})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def sessions_list(request):
    """
    List conversation sessions.
    """
    # TODO: Implement session storage in database
    return JsonResponse({'sessions': []})


@require_http_methods(["GET", "PATCH", "DELETE"])
def session_detail(request, session_id):
    """
    Get, update, or delete a session.
    """
    if request.method == 'GET':
        # TODO: Implement session retrieval from database
        return JsonResponse({'session_id': session_id, 'model': None})
    
    elif request.method == 'PATCH':
        # TODO: Implement session update
        return JsonResponse({'success': True})
    
    elif request.method == 'DELETE':
        # TODO: Implement session deletion
        return JsonResponse({'success': True})


@require_http_methods(["GET"])
def conversations_list(request):
    """
    List conversations for a session.
    """
    session_id = request.GET.get('session_id')
    limit = int(request.GET.get('limit', 50))
    
    # TODO: Implement conversation retrieval from database
    return JsonResponse({'conversations': []})

