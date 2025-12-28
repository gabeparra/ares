from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os
import httpx

from .utils import _get_setting, _set_setting, _get_default_system_prompt, _get_model_config


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_prompt(request):
    """
    GET: Get the current chat system prompt
    POST: Update the chat system prompt
    """
    if request.method == 'GET':
        stored = _get_setting("chat_system_prompt")
        prompt = stored if stored else _get_default_system_prompt()
        return JsonResponse({"prompt": prompt})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            prompt = data.get('prompt', '')
            
            if not prompt:
                return JsonResponse({'error': 'Prompt is required'}, status=400)
            
            _set_setting("chat_system_prompt", str(prompt))
            return JsonResponse({
                'success': True,
                'message': 'Prompt updated successfully',
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_model_config(request):
    """
    GET: Get the current model configuration (temperature, top_p, top_k, repeat_penalty)
    POST: Update the model configuration
    """
    config_keys = ["temperature", "top_p", "top_k", "repeat_penalty"]
    defaults = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
    }

    if request.method == 'GET':
        config = {}
        for key in config_keys:
            stored = _get_setting(f"model_{key}")
            if stored is not None:
                try:
                    config[key] = float(stored)
                except ValueError:
                    config[key] = defaults[key]
            else:
                config[key] = defaults[key]
        return JsonResponse({"config": config})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            config = data.get('config', {})
            
            for key in config_keys:
                if key in config:
                    value = config[key]
                    # Validate numeric
                    try:
                        float_val = float(value)
                        _set_setting(f"model_{key}", str(float_val))
                    except (ValueError, TypeError):
                        return JsonResponse({'error': f'Invalid value for {key}'}, status=400)
            
            return JsonResponse({
                'success': True,
                'message': 'Model configuration saved successfully',
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_provider(request):
    """
    GET: Get the current LLM provider
    POST: Update the LLM provider
    """
    valid_providers = ["local", "openrouter"]
    
    if request.method == 'GET':
        stored = _get_setting("llm_provider")
        provider = stored if stored else os.environ.get("LLM_PROVIDER", "local")
        # Normalize legacy provider values to valid ones
        if provider not in valid_providers:
            provider = "local"
        return JsonResponse({"provider": provider})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            provider = data.get('provider', '')
            
            if provider not in valid_providers:
                return JsonResponse({'error': f'Invalid provider. Must be one of: {", ".join(valid_providers)}'}, status=400)
            
            # Check if OpenRouter is configured when switching to it
            if provider == "openrouter":
                api_key = os.environ.get("OPENROUTER_API_KEY")
                if not api_key:
                    return JsonResponse({'error': 'OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable.'}, status=400)
            
            _set_setting("llm_provider", provider)
            return JsonResponse({
                'success': True,
                'provider': provider,
                'message': f'Provider changed to {provider}',
            })
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def settings_openrouter_models(request):
    """
    GET: Fetch available OpenRouter models
    Returns a curated list of popular models
    """
    # Get the currently selected model
    current_model = _get_setting("openrouter_model")
    if not current_model:
        current_model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    
    # Curated list of popular OpenRouter models
    models = [
        # Anthropic Claude
        {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "provider": "Anthropic"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic"},
        {"id": "anthropic/claude-3.5-haiku", "name": "Claude 3.5 Haiku", "provider": "Anthropic"},
        {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "provider": "Anthropic"},
        {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "Anthropic"},
        # OpenAI
        {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
        {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
        {"id": "openai/chatgpt-4o-latest", "name": "ChatGPT-4o Latest", "provider": "OpenAI"},
        {"id": "openai/o1", "name": "o1", "provider": "OpenAI"},
        {"id": "openai/o1-mini", "name": "o1 Mini", "provider": "OpenAI"},
        {"id": "openai/o1-preview", "name": "o1 Preview", "provider": "OpenAI"},
        {"id": "openai/o3-mini", "name": "o3 Mini", "provider": "OpenAI"},
        {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenAI"},
        {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI"},
        # Google
        {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash (Free)", "provider": "Google"},
        {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "provider": "Google"},
        {"id": "google/gemini-pro-1.5", "name": "Gemini Pro 1.5", "provider": "Google"},
        {"id": "google/gemini-flash-1.5", "name": "Gemini Flash 1.5", "provider": "Google"},
        {"id": "google/gemma-2-27b-it", "name": "Gemma 2 27B", "provider": "Google"},
        # Meta Llama
        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "provider": "Meta"},
        {"id": "meta-llama/llama-3.1-405b-instruct", "name": "Llama 3.1 405B", "provider": "Meta"},
        {"id": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B", "provider": "Meta"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "provider": "Meta"},
        # Mistral
        {"id": "mistralai/mistral-large-2411", "name": "Mistral Large 2411", "provider": "Mistral"},
        {"id": "mistralai/mistral-medium", "name": "Mistral Medium", "provider": "Mistral"},
        {"id": "mistralai/mistral-small-24b-instruct-2501", "name": "Mistral Small 24B", "provider": "Mistral"},
        {"id": "mistralai/mixtral-8x22b-instruct", "name": "Mixtral 8x22B", "provider": "Mistral"},
        {"id": "mistralai/mixtral-8x7b-instruct", "name": "Mixtral 8x7B", "provider": "Mistral"},
        {"id": "mistralai/codestral-2501", "name": "Codestral 2501", "provider": "Mistral"},
        # DeepSeek
        {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3", "provider": "DeepSeek"},
        {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "provider": "DeepSeek"},
        {"id": "deepseek/deepseek-r1-distill-llama-70b", "name": "DeepSeek R1 Distill 70B", "provider": "DeepSeek"},
        # Qwen
        {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B", "provider": "Qwen"},
        {"id": "qwen/qwen-2.5-coder-32b-instruct", "name": "Qwen 2.5 Coder 32B", "provider": "Qwen"},
        {"id": "qwen/qwq-32b-preview", "name": "QwQ 32B Preview", "provider": "Qwen"},
        # xAI
        {"id": "x-ai/grok-2-1212", "name": "Grok 2", "provider": "xAI"},
        {"id": "x-ai/grok-beta", "name": "Grok Beta", "provider": "xAI"},
        # Perplexity
        {"id": "perplexity/llama-3.1-sonar-large-128k-online", "name": "Sonar Large (Online)", "provider": "Perplexity"},
        {"id": "perplexity/llama-3.1-sonar-small-128k-online", "name": "Sonar Small (Online)", "provider": "Perplexity"},
        # Cohere
        {"id": "cohere/command-r-plus", "name": "Command R+", "provider": "Cohere"},
        {"id": "cohere/command-r", "name": "Command R", "provider": "Cohere"},
    ]
    
    return JsonResponse({
        "models": models,
        "current_model": current_model,
    })


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_openrouter_model(request):
    """
    GET: Get the currently selected OpenRouter model
    POST: Update the OpenRouter model
    """
    if request.method == 'GET':
        stored = _get_setting("openrouter_model")
        model = stored if stored else os.environ.get("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
        return JsonResponse({"model": model})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            model = data.get('model', '')
            
            if not model:
                return JsonResponse({'error': 'Model is required'}, status=400)
            
            _set_setting("openrouter_model", model)
            return JsonResponse({
                'success': True,
                'model': model,
                'message': f'OpenRouter model changed to {model}',
            })
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_agent(request):
    """
    GET: Get the current agent configuration
    POST: Update the agent configuration
    
    Agent settings:
    - agent_url: URL to the ARES agent (e.g., http://100.x.x.x:8100)
    - agent_api_key: Shared secret for authentication
    - agent_enabled: Whether agent functionality is enabled
    """
    if request.method == 'GET':
        agent_url = _get_setting("agent_url") or ""
        agent_api_key = _get_setting("agent_api_key") or ""
        agent_enabled = _get_setting("agent_enabled")
        # Convert stored string to boolean
        agent_enabled = agent_enabled == "true" if agent_enabled else False
        
        return JsonResponse({
            "agent_url": agent_url,
            "agent_api_key": agent_api_key,
            "agent_enabled": agent_enabled,
            # Mask API key for display (show last 4 chars only)
            "agent_api_key_masked": f"****{agent_api_key[-4:]}" if len(agent_api_key) > 4 else "****" if agent_api_key else "",
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Update agent URL if provided
            if 'agent_url' in data:
                url = data['agent_url'].strip()
                # Basic URL validation
                if url and not (url.startswith('http://') or url.startswith('https://')):
                    return JsonResponse({'error': 'Agent URL must start with http:// or https://'}, status=400)
                _set_setting("agent_url", url)
            
            # Update agent API key if provided
            if 'agent_api_key' in data:
                _set_setting("agent_api_key", data['agent_api_key'])
            
            # Update agent enabled if provided
            if 'agent_enabled' in data:
                enabled = data['agent_enabled']
                _set_setting("agent_enabled", "true" if enabled else "false")
            
            return JsonResponse({
                'success': True,
                'message': 'Agent configuration saved successfully',
            })
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

