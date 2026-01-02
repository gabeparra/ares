"""
Agent Views - API endpoints for controlling the ARES Agent.

The agent runs on the 4090 rig and handles:
- Stable Diffusion control (start/stop with VRAM modes)
- Ollama control (start/stop, parameter adjustment)
- System resource monitoring
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from ares_core.agent_client import get_agent_client, AVAILABLE_ACTIONS
from .auth import require_auth


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["GET"])
def agent_status(request):
    """
    GET: Get the agent connection status and system resources.
    
    Returns:
        - status: "online", "offline", or "error"
        - resources: GPU/VRAM/CPU usage (if online)
        - services: Status of SD and Ollama (if online)
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "status": "disabled",
            "message": "Agent is not configured or disabled. Configure in Settings.",
        })
    
    try:
        status = client.get_status()
        return JsonResponse(status)
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["GET"])
def agent_resources(request):
    """
    GET: Get detailed system resource usage from the agent.
    
    Returns GPU memory, VRAM usage, CPU usage, etc.
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "error": "Agent is not configured or disabled",
        }, status=400)
    
    try:
        resources = client.get_resources()
        return JsonResponse(resources)
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["GET"])
def agent_actions(request):
    """
    GET: List available agent actions with their risk levels.
    
    Returns a list of actions the agent can perform.
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "actions": [],
            "message": "Agent is not configured or disabled",
        })
    
    try:
        actions = client.get_actions()
        return JsonResponse({"actions": actions})
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["POST"])
def agent_action(request):
    """
    POST: Execute an action on the agent.
    
    Request body:
        - action: Action ID (e.g., "start_sd", "stop_sd")
        - parameters: Optional dict of parameters
        - force: Skip auto-approval check (for UI confirmations)
    
    Returns:
        - success: True/False
        - message: Result message
        - data: Optional action-specific data
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "success": False,
            "error": "Agent is not configured or disabled",
        }, status=400)
    
    try:
        data = json.loads(request.body)
        action_id = data.get('action')
        parameters = data.get('parameters', {})
        force = data.get('force', False)
        
        if not action_id:
            return JsonResponse({
                "success": False,
                "error": "Action ID is required",
            }, status=400)
        
        # Check if action requires approval (unless forced from UI)
        if not force and not client.is_action_auto_approved(action_id):
            # Find action info
            action_info = next(
                (a for a in AVAILABLE_ACTIONS if a.id == action_id),
                None
            )
            return JsonResponse({
                "success": False,
                "requires_approval": True,
                "action": action_id,
                "risk": action_info.risk.value if action_info else "unknown",
                "message": f"Action '{action_id}' requires user approval",
            })
        
        # Execute the action
        result = client.execute_action(action_id, parameters)
        
        # Log the result for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Agent action {action_id} result: {result}")
        
        return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON",
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
        }, status=500)
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["POST"])
def agent_start_sd(request):
    """
    POST: Convenience endpoint to start Stable Diffusion.
    
    Request body:
        - vram_mode: "low", "medium", or "full" (default: "low")
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "success": False,
            "error": "Agent is not configured or disabled",
        }, status=400)
    
    try:
        data = json.loads(request.body) if request.body else {}
        vram_mode = data.get('vram_mode', 'low')
        
        if vram_mode not in ['low', 'medium', 'full']:
            return JsonResponse({
                "success": False,
                "error": "Invalid vram_mode. Must be 'low', 'medium', or 'full'",
            }, status=400)
        
        result = client.execute_action('start_sd', {'vram_mode': vram_mode})
        return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON",
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
        }, status=500)
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["POST"])
def agent_stop_sd(request):
    """
    POST: Convenience endpoint to stop Stable Diffusion.
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "success": False,
            "error": "Agent is not configured or disabled",
        }, status=400)
    
    try:
        result = client.execute_action('stop_sd')
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
        }, status=500)
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["GET"])
def agent_logs(request):
    """
    GET: Get agent logs.
    
    Returns:
        Log data from the agent
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "error": "Agent is not configured or disabled",
        }, status=400)
    
    try:
        logs = client.get_logs()
        return JsonResponse(logs)
    finally:
        client.close()


@csrf_exempt  # JWT auth
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["POST"])
def agent_adjust_ollama(request):
    """
    POST: Adjust Ollama runtime parameters.
    
    Request body:
        - num_ctx: Context length (optional)
        - num_gpu: Number of GPU layers (optional)
    """
    client = get_agent_client()
    
    if not client:
        return JsonResponse({
            "success": False,
            "error": "Agent is not configured or disabled",
        }, status=400)
    
    try:
        data = json.loads(request.body) if request.body else {}
        parameters = {}
        
        if 'num_ctx' in data:
            parameters['num_ctx'] = int(data['num_ctx'])
        if 'num_gpu' in data:
            parameters['num_gpu'] = int(data['num_gpu'])
        
        if not parameters:
            return JsonResponse({
                "success": False,
                "error": "At least one parameter (num_ctx or num_gpu) is required",
            }, status=400)
        
        result = client.execute_action('adjust_ollama_params', parameters)
        return JsonResponse(result)
    
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({
            "success": False,
            "error": f"Invalid input: {e}",
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
        }, status=500)
    finally:
        client.close()

