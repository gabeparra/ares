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
    GET: Get the current model configuration (temperature, top_p, top_k, repeat_penalty, num_gpu)
    POST: Update the model configuration
    """
    config_keys = ["temperature", "top_p", "top_k", "repeat_penalty", "num_gpu"]
    defaults = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "num_gpu": 40,
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
    Returns all available models organized by company/provider
    """
    # Get the currently selected model
    current_model = _get_setting("openrouter_model")
    if not current_model:
        current_model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    # Fetch all models from OpenRouter API
    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    models = []
    providers_dict = {}
    
    # Add Auto Router as a special option
    models.append({
        "id": "openrouter/auto",
        "name": "🤖 Auto Router (Smart Selection)",
        "provider": "OpenRouter",
        "description": "Automatically selects the best model for each task"
    })
    providers_dict["OpenRouter"] = ["openrouter/auto"]
    
    # Try to fetch models from OpenRouter API
    if api_key:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{base_url}/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                    }
                )
                response.raise_for_status()
                data = response.json()
                api_models = data.get("data", [])
                
                # Process each model from the API
                for model_data in api_models:
                    model_id = model_data.get("id", "")
                    if not model_id:
                        continue
                    
                    # Extract provider from model ID (format: provider/model-name)
                    provider_raw = model_id.split("/")[0] if "/" in model_id else "Unknown"
                    provider_raw_lower = provider_raw.lower()
                    
                    # Special handling for known providers (case-insensitive)
                    provider_mapping = {
                        "openai": "OpenAI",
                        "anthropic": "Anthropic",
                        "google": "Google",
                        "meta-llama": "Meta",
                        "meta": "Meta",
                        "mistralai": "Mistral",
                        "mistral": "Mistral",
                        "deepseek": "DeepSeek",
                        "qwen": "Qwen",
                        "x-ai": "xAI",
                        "xai": "xAI",
                        "cohere": "Cohere",
                        "perplexity": "Perplexity",
                        "openrouter": "OpenRouter",
                    }
                    # Get normalized provider name, or format it nicely if not in mapping
                    provider_name = provider_mapping.get(provider_raw_lower)
                    if not provider_name:
                        # Format unknown providers nicely
                        provider_name = provider_raw.replace("-", " ").title()
                    
                    # Get model name and description
                    model_name = model_data.get("name", model_id)
                    context_length = model_data.get("context_length")
                    pricing = model_data.get("pricing", {})
                    
                    # Build description
                    description_parts = []
                    if context_length:
                        description_parts.append(f"{context_length:,} context")
                    if pricing:
                        prompt_price = pricing.get("prompt", "")
                        completion_price = pricing.get("completion", "")
                        if prompt_price or completion_price:
                            price_str = f"${prompt_price}/${completion_price} per 1M tokens"
                            description_parts.append(price_str)
                    description = " - ".join(description_parts) if description_parts else ""
                    
                    # Add model to list
                    model_entry = {
                        "id": model_id,
                        "name": model_name,
                        "provider": provider_name,
                        "description": description
                    }
                    models.append(model_entry)
                    
                    # Track by provider
                    if provider_name not in providers_dict:
                        providers_dict[provider_name] = []
                    providers_dict[provider_name].append(model_id)
                    
        except Exception as e:
            # If API fetch fails, log error but continue with empty list
            # The frontend will handle the empty list gracefully
            print(f"[WARNING] Failed to fetch OpenRouter models: {e}")
            # Fall back to a minimal curated list if API fails
            models = [
                {"id": "openrouter/auto", "name": "🤖 Auto Router (Smart Selection)", "provider": "OpenRouter", "description": "Automatically selects the best model for each task"},
                {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat (FREE) ⭐ Default", "provider": "DeepSeek", "description": "Free, excellent for general tasks and coding"},
            ]
            providers_dict = {"OpenRouter": ["openrouter/auto"], "DeepSeek": ["deepseek/deepseek-chat"]}
    else:
        # No API key, return minimal list
        models = [
            {"id": "openrouter/auto", "name": "🤖 Auto Router (Smart Selection)", "provider": "OpenRouter", "description": "Automatically selects the best model for each task"},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat (FREE) ⭐ Default", "provider": "DeepSeek", "description": "Free, excellent for general tasks and coding"},
        ]
        providers_dict = {"OpenRouter": ["openrouter/auto"], "DeepSeek": ["deepseek/deepseek-chat"]}
    
    # Sort models: OpenAI first, then alphabetically by provider, then by model name
    def sort_key(model):
        provider = model.get("provider", "ZZZ")
        name = model.get("name", "")
        # OpenAI gets priority
        if provider == "OpenAI":
            return (0, provider, name)
        return (1, provider, name)
    
    models.sort(key=sort_key)
    
    # Verify all OpenAI models are included (special focus)
    openai_models = [m for m in models if m.get("provider") == "OpenAI"]
    openai_model_ids = [m.get("id", "") for m in openai_models]
    
    return JsonResponse({
        "models": models,
        "current_model": current_model,
        "providers": list(providers_dict.keys()),
        "openai_model_count": len(openai_models),
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
        model = stored if stored else os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
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
def settings_openrouter_auto_select(request):
    """
    GET: Get whether auto model selection is enabled
    POST: Enable/disable auto model selection
    """
    if request.method == 'GET':
        auto_select = _get_setting("openrouter_auto_select")
        auto_select = auto_select and auto_select.lower() in ("true", "1", "yes")
        return JsonResponse({"auto_select": auto_select})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            auto_select = data.get('auto_select', False)
            _set_setting("openrouter_auto_select", "true" if auto_select else "false")
            return JsonResponse({
                'success': True,
                'auto_select': auto_select,
                'message': f'Auto model selection {"enabled" if auto_select else "disabled"}',
            })
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
            # Empty string means clear the key (user explicitly cleared it)
            # If key is not in data, preserve existing value
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


@require_http_methods(["GET", "POST"])
@csrf_exempt
def settings_tab_visibility(request):
    """
    GET: Get tab visibility settings
    POST: Update tab visibility settings
    
    Controls which tabs are visible in the UI.
    """
    if request.method == 'GET':
        # Default visibility (all tabs visible by default)
        defaults = {
            "sdapi": True,
        }
        
        visibility = {}
        for tab_id, default_value in defaults.items():
            stored = _get_setting(f"tab_visibility_{tab_id}")
            if stored is not None:
                visibility[tab_id] = stored.lower() in ("true", "1", "yes")
            else:
                visibility[tab_id] = default_value
        
        return JsonResponse({"visibility": visibility})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            visibility = data.get('visibility', {})
            
            # Update each tab visibility setting
            for tab_id, is_visible in visibility.items():
                _set_setting(f"tab_visibility_{tab_id}", "true" if is_visible else "false")
            
            return JsonResponse({
                'success': True,
                'message': 'Tab visibility settings saved successfully',
            })
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

