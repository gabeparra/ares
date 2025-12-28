from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import httpx


@require_http_methods(["GET", "POST"])
@csrf_exempt
def models_list(request):
    """
    GET: List available models from Ollama
    POST: Switch to a different model
    """
    if request.method == 'GET':
        try:
            # Fetch available models from Ollama
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/tags"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(ollama_url)
                response.raise_for_status()
                result = response.json()
            
            # Extract models from Ollama response
            ollama_models = result.get('models', [])
            models = [
                {"name": m.get('name', ''), "full_name": m.get('name', '')}
                for m in ollama_models
            ]
            
            current_model = getattr(settings, 'OLLAMA_MODEL', 'mistral')
            
            return JsonResponse({
                'models': models,
                'current_model': current_model,
                'model_loaded': True,
            })
        
        except httpx.ConnectError:
            return JsonResponse({
                'error': f'Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. Make sure Ollama is running and accessible via Tailscale.',
                'models': [],
                'current_model': getattr(settings, 'OLLAMA_MODEL', 'mistral'),
                'model_loaded': False,
            }, status=503)
        except httpx.TimeoutException:
            return JsonResponse({
                'error': f'Timeout connecting to Ollama at {settings.OLLAMA_BASE_URL}',
                'models': [],
                'current_model': getattr(settings, 'OLLAMA_MODEL', 'mistral'),
                'model_loaded': False,
            }, status=503)
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                error_msg = f"HTTP {e.response.status_code}: {error_msg}"
            return JsonResponse({
                'error': f'Error fetching models from Ollama: {error_msg}',
                'models': [],
                'current_model': getattr(settings, 'OLLAMA_MODEL', 'mistral'),
                'model_loaded': False,
            }, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            model = data.get('model')
            
            if not model:
                return JsonResponse({'error': 'Model name is required'}, status=400)
            
            # Verify model exists in Ollama
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/tags"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(ollama_url)
                response.raise_for_status()
                result = response.json()
            
            ollama_models = result.get('models', [])
            model_names = [m.get('name', '') for m in ollama_models]
            
            if model not in model_names:
                return JsonResponse({
                    'error': f'Model "{model}" not found in Ollama. Available models: {", ".join(model_names)}'
                }, status=404)
            
            # Update the model setting (note: this only affects the current process)
            # For persistent changes, update the environment variable
            settings.OLLAMA_MODEL = model
            
            return JsonResponse({
                'success': True,
                'model': model,
                'message': f'Switched to model: {model}',
            })
        
        except httpx.ConnectError:
            return JsonResponse({
                'error': f'Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}',
            }, status=503)
        except httpx.TimeoutException:
            return JsonResponse({
                'error': 'Timeout while connecting to Ollama.',
            }, status=504)
        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', error_msg)
            except Exception:
                pass
            return JsonResponse({'error': error_msg}, status=e.response.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
