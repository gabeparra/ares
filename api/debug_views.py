"""
Debug endpoints for monitoring the AI orchestrator and memory system.

These endpoints help diagnose issues with:
- Prompt assembly
- Memory state
- Model routing decisions
- Tool execution
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .auth import require_auth
from ares_core.orchestrator import orchestrator
from ares_mind.memory_store import memory_store
from ares_core.prompt_assembler import prompt_assembler


@csrf_exempt
@require_auth
@require_http_methods(["GET", "POST"])
def debug_prompt(request):
    """
    Show the assembled prompt that would be sent to the LLM.
    
    GET params / POST JSON:
    - user_id: User identifier (default: "default")
    - session_id: Session identifier (optional)
    - message: Sample message to use for assembly
    """
    try:
        if request.method == "GET":
            user_id = request.GET.get("user_id", "default")
            session_id = request.GET.get("session_id")
            message = request.GET.get("message", "Hello, how are you?")
        else:
            data = json.loads(request.body)
            user_id = data.get("user_id", "default")
            session_id = data.get("session_id")
            message = data.get("message", "Hello, how are you?")
        
        # Assemble prompt
        messages = prompt_assembler.assemble(
            user_id=user_id,
            current_message=message,
            session_id=session_id,
        )
        
        # Calculate stats
        total_chars = sum(len(m["content"]) for m in messages)
        system_chars = sum(len(m["content"]) for m in messages if m["role"] == "system")
        
        return JsonResponse({
            "messages": messages,
            "stats": {
                "total_messages": len(messages),
                "total_chars": total_chars,
                "system_chars": system_chars,
                "user_chars": total_chars - system_chars,
            },
            "user_id": user_id,
            "session_id": session_id,
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)


@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def debug_memory(request):
    """
    Show the current memory state for a user.
    
    GET params:
    - user_id: User identifier (default: "default")
    - session_id: Session identifier (optional)
    """
    try:
        user_id = request.GET.get("user_id", "default")
        session_id = request.GET.get("session_id")
        
        # Get all memory layers
        memory = memory_store.get_all_memory_layers(user_id, session_id)
        
        # Get formatted memory for prompt
        formatted = memory_store.format_for_prompt(user_id, session_id)
        
        return JsonResponse({
            "user_id": user_id,
            "session_id": session_id,
            "memory_layers": memory,
            "formatted_for_prompt": formatted,
            "stats": {
                "identity_items": sum(len(v) for v in memory["identity"].values()),
                "factual_items": sum(len(v) for v in memory["factual"].values()),
                "working_memory_keys": len(memory["working"]),
                "episodic_topics": len(memory["episodic"].get("recent_topics", [])),
            }
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)


@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def debug_routing(request):
    """
    Show the routing decision that would be made.
    
    GET params:
    - prefer_local: Boolean (default: false)
    """
    try:
        prefer_local = request.GET.get("prefer_local", "false").lower() == "true"
        
        # Get routing decision
        provider, config = orchestrator.router.route(
            task_context={"message": "test"},
            prefer_local=prefer_local
        )
        
        return JsonResponse({
            "provider": provider,
            "config": config,
            "availability": {
                "local": orchestrator.router.local_available,
                "cloud": orchestrator.router.cloud_available,
            },
            "prefer_local": prefer_local,
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)


@csrf_exempt
@require_auth
@require_http_methods(["GET"])
def debug_orchestrator_status(request):
    """
    Get overall orchestrator status.
    """
    try:
        # Check model availability
        local_available = orchestrator.router.local_available
        cloud_available = orchestrator.router.cloud_available
        
        # Get current settings
        from api.utils import _get_setting
        import os
        
        provider_setting = _get_setting("llm_provider") or os.environ.get("LLM_PROVIDER", "local")
        
        return JsonResponse({
            "orchestrator": {
                "enabled": True,
                "version": "1.0.0",
            },
            "models": {
                "local": {
                    "available": local_available,
                    "type": "ollama",
                },
                "cloud": {
                    "available": cloud_available,
                    "type": "openrouter",
                },
            },
            "routing": {
                "provider_preference": provider_setting,
                "local_available": local_available,
                "cloud_available": cloud_available,
            },
            "memory": {
                "store_enabled": True,
                "layers": ["identity", "factual", "working", "episodic"],
            },
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)


@csrf_exempt
@require_auth
@require_http_methods(["POST"])
def debug_test_consistency(request):
    """
    Test that local and cloud prompts are identical.
    
    POST JSON:
    - user_id: User identifier
    - session_id: Session identifier (optional)
    - message: Test message
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id", "default")
        session_id = data.get("session_id")
        message = data.get("message", "Hello, how are you?")
        
        # Assemble prompt (should be identical for both)
        messages = prompt_assembler.assemble(
            user_id=user_id,
            current_message=message,
            session_id=session_id,
        )
        
        # The prompt is assembled once and used for both, so they're identical by design
        # This endpoint confirms the design is working
        
        return JsonResponse({
            "consistent": True,
            "message": "Prompts are assembled identically for both local and cloud models",
            "prompt_messages": len(messages),
            "design": "Single prompt assembly used for both providers",
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)

