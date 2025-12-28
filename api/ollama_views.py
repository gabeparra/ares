"""
Ollama Management API views for ARES.

Provides endpoints for:
- GET /api/v1/ollama/status - Get Ollama server status and loaded models
- GET /api/v1/ollama/models - List available models
- GET /api/v1/ollama/modelfile - Get the current Modelfile content
- PUT /api/v1/ollama/modelfile - Update the Modelfile content
- POST /api/v1/ollama/rebuild - Rebuild the ARES model from Modelfile
- POST /api/v1/ollama/chat - Chat with a model
- POST /api/v1/ollama/generate - Generate text with a model
- POST /api/v1/ollama/unload - Unload a model from memory
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import httpx
import os
from pathlib import Path


def get_ollama_url():
    """Get the Ollama base URL from settings."""
    return getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')


def get_modelfile_path():
    """Get the path to the Modelfile."""
    # Look for Modelfile in the project root (BASE_DIR is /app in Docker)
    base_dir = Path(settings.BASE_DIR)
    modelfile_path = base_dir / 'Modelfile'
    return modelfile_path


@csrf_exempt
@require_http_methods(["GET"])
def ollama_status(request):
    """
    GET: Get Ollama server status, available models, and loaded models.
    """
    ollama_url = get_ollama_url()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Check if Ollama is running
            try:
                response = client.get(f"{ollama_url}/api/tags")
                response.raise_for_status()
                models_data = response.json()
            except (httpx.ConnectError, httpx.TimeoutException):
                return JsonResponse({
                    "status": "offline",
                    "ollama_host": ollama_url,
                    "error": f"Cannot connect to Ollama at {ollama_url}",
                    "available_models": [],
                    "loaded_models": [],
                })
            
            # Get available models
            available_models = models_data.get("models", [])
            
            # Get loaded models (currently running)
            try:
                ps_response = client.get(f"{ollama_url}/api/ps")
                ps_response.raise_for_status()
                ps_data = ps_response.json()
                loaded_models = ps_data.get("models", [])
            except Exception:
                loaded_models = []
            
            # Get the default model from settings
            default_model = getattr(settings, 'OLLAMA_MODEL', 'mistral')
            
            return JsonResponse({
                "status": "online",
                "ollama_host": ollama_url,
                "default_model": default_model,
                "available_models": available_models,
                "loaded_models": loaded_models,
            })
            
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "ollama_host": ollama_url,
            "available_models": [],
            "loaded_models": [],
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def ollama_models(request):
    """
    GET: List all available models in Ollama.
    """
    ollama_url = get_ollama_url()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            return JsonResponse({
                "models": data.get("models", []),
            })
            
    except httpx.ConnectError:
        return JsonResponse({
            "error": f"Cannot connect to Ollama at {ollama_url}",
            "models": [],
        }, status=503)
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "models": [],
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def ollama_modelfile(request):
    """
    GET: Get the current Modelfile content.
    PUT: Update the Modelfile content.
    """
    modelfile_path = get_modelfile_path()
    
    if request.method == "GET":
        try:
            if not modelfile_path.exists():
                return JsonResponse({
                    "error": f"Modelfile not found at {modelfile_path}",
                    "path": str(modelfile_path),
                }, status=404)
            
            content = modelfile_path.read_text()
            
            # Parse some basic info from the Modelfile
            parsed = {"base_model": None, "parameters": {}}
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("FROM "):
                    parsed["base_model"] = line[5:].strip()
                elif line.startswith("PARAMETER "):
                    parts = line[10:].split(None, 1)
                    if len(parts) == 2:
                        parsed["parameters"][parts[0]] = parts[1]
            
            return JsonResponse({
                "content": content,
                "path": str(modelfile_path),
                "parsed": parsed,
            })
            
        except Exception as e:
            return JsonResponse({
                "error": str(e),
            }, status=500)
    
    # PUT: Update Modelfile
    try:
        data = json.loads(request.body)
        content = data.get("content")
        
        if not content:
            return JsonResponse({
                "error": "Missing 'content' field",
            }, status=400)
        
        modelfile_path.write_text(content)
        
        return JsonResponse({
            "message": "Modelfile updated successfully",
            "path": str(modelfile_path),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def parse_modelfile(content):
    """
    Parse a Modelfile and extract base model, system prompt, and parameters.
    """
    parsed = {
        "from": None,
        "system": None,
        "parameters": {}
    }
    
    lines = content.split("\n")
    in_system = False
    system_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Handle FROM directive
        if stripped.startswith("FROM "):
            parsed["from"] = stripped[5:].strip()
            continue
        
        # Handle SYSTEM start (with triple quotes)
        if stripped.startswith('SYSTEM """'):
            in_system = True
            # Get content after SYSTEM """
            rest = stripped[10:]
            if rest.endswith('"""'):
                # Single-line system prompt
                parsed["system"] = rest[:-3]
                in_system = False
            else:
                system_lines.append(rest)
            continue
        
        # Handle SYSTEM content
        if in_system:
            if stripped.endswith('"""'):
                system_lines.append(stripped[:-3])
                parsed["system"] = "\n".join(system_lines)
                in_system = False
            else:
                system_lines.append(line)  # Keep original formatting
            continue
        
        # Handle PARAMETER directives
        if stripped.startswith("PARAMETER "):
            parts = stripped[10:].split(None, 1)
            if len(parts) == 2:
                key = parts[0]
                try:
                    # Try to parse as number
                    value = float(parts[1]) if "." in parts[1] else int(parts[1])
                except ValueError:
                    value = parts[1]
                parsed["parameters"][key] = value
    
    return parsed


@csrf_exempt
@require_http_methods(["POST"])
def ollama_rebuild(request):
    """
    POST: Rebuild the ARES model from the Modelfile.
    
    Uses Ollama 0.13+ API format with 'from', 'system', and 'parameters'.
    """
    ollama_url = get_ollama_url()
    modelfile_path = get_modelfile_path()
    
    try:
        if not modelfile_path.exists():
            return JsonResponse({
                "error": f"Modelfile not found at {modelfile_path}",
            }, status=404)
        
        content = modelfile_path.read_text()
        parsed = parse_modelfile(content)
        
        if not parsed["from"]:
            return JsonResponse({
                "error": "Modelfile must contain a FROM directive",
            }, status=400)
        
        # Build the create request for Ollama 0.13+
        create_request = {
            "model": "ares",
            "from": parsed["from"],
            "stream": False,
        }
        
        if parsed["system"]:
            create_request["system"] = parsed["system"]
        
        if parsed["parameters"]:
            create_request["parameters"] = parsed["parameters"]
        
        # Use Ollama's create API (0.13+ format)
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{ollama_url}/api/create",
                json=create_request,
            )
            
            try:
                result = response.json()
            except Exception:
                result = {"raw": response.text}
            
            if response.status_code == 200 and result.get("status") == "success":
                return JsonResponse({
                    "message": "Model 'ares' rebuilt successfully",
                    "status": "success",
                    "base_model": parsed["from"],
                    "has_system": bool(parsed["system"]),
                    "parameters": parsed["parameters"],
                })
            else:
                error_msg = result.get("error", result.get("raw", response.text))
                
                return JsonResponse({
                    "error": f"Failed to rebuild model: {error_msg}",
                    "status": "failed",
                }, status=response.status_code if response.status_code != 200 else 500)
                
    except httpx.ConnectError:
        return JsonResponse({
            "error": f"Cannot connect to Ollama at {ollama_url}",
        }, status=503)
    except Exception as e:
        return JsonResponse({
            "error": str(e),
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ollama_chat(request):
    """
    POST: Chat with a model.
    
    Request body:
    {
        "messages": [{"role": "user", "content": "Hello"}],
        "model": "ares",
        "stream": false,
        "temperature": 0.7,
        "top_p": 0.9,
        "num_ctx": 4096
    }
    """
    ollama_url = get_ollama_url()
    
    try:
        data = json.loads(request.body)
        messages = data.get("messages", [])
        model = data.get("model", "ares")
        stream = data.get("stream", False)
        
        if not messages:
            return JsonResponse({
                "error": "Missing 'messages' field",
            }, status=400)
        
        # Build the request
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        # Optional parameters
        options = {}
        if "temperature" in data:
            options["temperature"] = data["temperature"]
        if "top_p" in data:
            options["top_p"] = data["top_p"]
        if "num_ctx" in data:
            options["num_ctx"] = data["num_ctx"]
        
        if options:
            payload["options"] = options
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{ollama_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            
            return JsonResponse(result)
            
    except httpx.ConnectError:
        return JsonResponse({
            "error": f"Cannot connect to Ollama at {ollama_url}",
        }, status=503)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ollama_generate(request):
    """
    POST: Generate text with a model.
    
    Request body:
    {
        "prompt": "Hello, world!",
        "model": "ares",
        "stream": false
    }
    """
    ollama_url = get_ollama_url()
    
    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "")
        model = data.get("model", "ares")
        stream = data.get("stream", False)
        
        if not prompt:
            return JsonResponse({
                "error": "Missing 'prompt' field",
            }, status=400)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        
        # Optional parameters
        options = {}
        if "temperature" in data:
            options["temperature"] = data["temperature"]
        if "top_p" in data:
            options["top_p"] = data["top_p"]
        if "num_ctx" in data:
            options["num_ctx"] = data["num_ctx"]
        
        if options:
            payload["options"] = options
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{ollama_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            
            return JsonResponse(result)
            
    except httpx.ConnectError:
        return JsonResponse({
            "error": f"Cannot connect to Ollama at {ollama_url}",
        }, status=503)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ollama_unload(request):
    """
    POST: Unload a model from memory.
    
    Request body:
    {
        "model": "ares"
    }
    """
    ollama_url = get_ollama_url()
    
    try:
        data = json.loads(request.body)
        model = data.get("model", "ares")
        
        # Ollama doesn't have a direct unload API, but we can set keep_alive to 0
        # which tells Ollama to unload the model after the request
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "",
                    "keep_alive": 0,
                }
            )
            
            if response.status_code == 200:
                return JsonResponse({
                    "message": f"Model '{model}' unloaded successfully",
                    "status": "success",
                })
            else:
                return JsonResponse({
                    "error": f"Failed to unload model: {response.text}",
                    "status": "failed",
                }, status=response.status_code)
                
    except httpx.ConnectError:
        return JsonResponse({
            "error": f"Cannot connect to Ollama at {ollama_url}",
        }, status=503)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

