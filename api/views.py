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
    Accepts chat messages and routes them to GEMMA AI API.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Route to GEMMA AI API
        gemma_url = f"{settings.GEMMA_AI_API_URL}/chat"
        
        payload = {
            'prompt': message,
            'max_length': 512,
            'temperature': 0.7,
            'top_p': 0.9,
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(gemma_url, json=payload)
            response.raise_for_status()
            result = response.json()
        
        return JsonResponse({
            'response': result.get('response', ''),
            'model': result.get('model', 'gemma'),
            'session_id': session_id,
        })
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            return JsonResponse({
                'error': 'GEMMA AI model is still loading. Please try again in a moment.'
            }, status=503)
        error_msg = str(e)
        try:
            error_data = e.response.json()
            error_msg = error_data.get('detail', error_msg)
        except Exception:
            pass
        return JsonResponse({'error': f'Error calling GEMMA AI API: {error_msg}'}, status=e.response.status_code)
    except httpx.ConnectError as e:
        return JsonResponse({
            'error': f'Cannot connect to GEMMA AI API at {settings.GEMMA_AI_API_URL}. Make sure the API is running and accessible.'
        }, status=503)
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
            # Check GEMMA AI API health to verify it's available
            health_url = f"{settings.GEMMA_AI_API_URL}/health"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(health_url)
                response.raise_for_status()
                result = response.json()
            
            # GEMMA AI API only has one model: "gemma"
            models = ['gemma']
            
            return JsonResponse({
                'models': models,
                'current_model': getattr(settings, 'CURRENT_MODEL', 'gemma'),
            })
        
        except httpx.ConnectError as e:
            return JsonResponse({
                'error': f'Cannot connect to GEMMA AI API at {settings.GEMMA_AI_API_URL}. Make sure the API is running and accessible.',
                'models': ['gemma'],  # Return model list even if API is unreachable
                'current_model': 'gemma',
            }, status=503)
        except httpx.TimeoutException as e:
            return JsonResponse({
                'error': f'Timeout connecting to GEMMA AI API at {settings.GEMMA_AI_API_URL}',
                'models': ['gemma'],
                'current_model': 'gemma',
            }, status=503)
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                error_msg = f"HTTP {e.response.status_code}: {error_msg}"
            return JsonResponse({
                'error': f'Error checking GEMMA AI API: {error_msg}',
                'models': ['gemma'],
                'current_model': 'gemma',
            }, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            model = data.get('model')
            
            if not model:
                return JsonResponse({'error': 'Model name is required'}, status=400)
            
            # GEMMA AI API only supports "gemma" model
            if model != 'gemma':
                return JsonResponse({'error': f'Model {model} not supported. Only "gemma" is available.'}, status=400)
            
            # In a real implementation, store this in database or cache
            # For now, just return success
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


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_prompt(request):
    """
    GET: Get the current chat system prompt
    POST: Update the chat system prompt
    """
    if request.method == 'GET':
        # TODO: Load from database
        # For now, return a default
        default_prompt = """You are Glup, an advanced AI assistant.

Core behavior:
- Answer the user's question directly and completely.
- Be concise, but not empty: always provide a substantive response.
- Do not repeat words, phrases, or sentences. If you notice repetition starting, stop and rephrase once.
- Avoid low-signal filler like "Okay", "I understand", or "Sure" unless followed by real content.
- If the user message is unclear, ask ONE clarifying question.

Output rules:
- No stuttering.
- No long preambles.
- Prefer short paragraphs and lists when helpful.
"""
        return JsonResponse({'prompt': default_prompt})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            prompt = data.get('prompt', '')
            
            if not prompt:
                return JsonResponse({'error': 'Prompt is required'}, status=400)
            
            # TODO: Save to database
            # For now, just return success
            return JsonResponse({
                'success': True,
                'message': 'Prompt updated successfully',
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

