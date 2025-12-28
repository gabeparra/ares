from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
import json
import os
import httpx

from .models import ConversationMessage
from .utils import _get_setting, _ensure_session, _get_model_config, _get_default_system_prompt
from .memory_views import get_self_memory_context
from .user_memory_views import get_user_memory_context

# RAG indexing (lazy import to avoid startup errors if chromadb not installed)
_rag_store = None

def _get_rag_store():
    """Lazy load RAG store."""
    global _rag_store
    if _rag_store is None:
        try:
            from ares_mind.rag import rag_store
            _rag_store = rag_store
        except ImportError:
            _rag_store = False  # Mark as unavailable
    return _rag_store if _rag_store else None

def _index_message(msg, session_id, user_id="default"):
    """Index a message in the RAG store (non-blocking)."""
    rag_store = _get_rag_store()
    if rag_store:
        try:
            rag_store.index_message(
                message_id=f"msg_{msg.id}",
                content=msg.message,
                session_id=session_id,
                role=msg.role,
                user_id=user_id,
                timestamp=msg.created_at,
            )
        except Exception as e:
            print(f"[WARNING] RAG indexing failed: {e}")


def _call_openrouter(messages, model_config):
    """Call OpenRouter service (TypeScript SDK wrapper) and return assistant response."""
    # Get model from settings or environment
    model = _get_setting("openrouter_model")
    if not model:
        model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    
    # OpenRouter service URL (TypeScript SDK wrapper)
    service_url = os.environ.get("OPENROUTER_SERVICE_URL", "http://localhost:3100")
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": model_config.get('temperature', 0.7),
        "max_tokens": int(os.environ.get("OPENROUTER_MAX_TOKENS", "2048")),
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{service_url}/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
    
    # Extract content from OpenRouter response
    if "choices" in result and len(result["choices"]) > 0:
        return result["choices"][0].get("message", {}).get("content", ""), model
    
    return "", model


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """
    Unified /v1/chat endpoint for ARES.
    Accepts chat messages and routes them to Ollama.
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        session = None
        user_id = data.get('user_id', 'default')
        
        if session_id:
            session = _ensure_session(session_id)
            user_msg = ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_USER,
                message=message,
            )
            # Index user message in RAG store
            _index_message(user_msg, session_id, user_id)

        # Fetch the system prompt from settings
        system_prompt = _get_setting("chat_system_prompt")
        if not system_prompt:
            system_prompt = _get_default_system_prompt()

        # Inject self-memory context into the system prompt (AI identity)
        self_memory_context = get_self_memory_context()
        if self_memory_context:
            system_prompt = system_prompt + "\n\n" + self_memory_context

        # Inject user memory context (user facts and preferences)
        user_memory_context = get_user_memory_context(user_id)
        if user_memory_context:
            system_prompt = system_prompt + "\n\n" + user_memory_context

        # Build messages list for Ollama chat API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if session exists
        if session:
            history_messages = list(
                ConversationMessage.objects.filter(session=session)
                .order_by("-created_at")[:10]
            )
            history_messages.reverse()
            
            for msg in history_messages[:-1]:  # Exclude the current message
                role = "user" if msg.role == ConversationMessage.ROLE_USER else "assistant"
                messages.append({"role": role, "content": msg.message})
        
        # Add current user message
        messages.append({"role": "user", "content": message})

        # Get model configuration from settings
        model_config = _get_model_config()
        
        # Check which provider to use
        provider = _get_setting("llm_provider")
        if not provider:
            provider = os.environ.get("LLM_PROVIDER", "local")
        # Normalize legacy provider values
        if provider not in ["local", "openrouter"]:
            provider = "local"
        
        # Track which provider was actually used
        used_provider = provider
        model_name = None
        assistant_text = ""
        openrouter_error = None
        
        if provider == "openrouter":
            # Use OpenRouter API
            try:
                assistant_text, model_name = _call_openrouter(messages, model_config)
                used_provider = "openrouter"
            except httpx.ConnectError as e:
                openrouter_error = f"Cannot connect to OpenRouter: {e}"
                print(f"[ERROR] OpenRouter connection failed: {e}")
            except httpx.HTTPStatusError as e:
                # Extract error message from OpenRouter response
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except Exception:
                    error_msg = str(e)
                openrouter_error = f"OpenRouter API error: {error_msg}"
                print(f"[ERROR] OpenRouter API error: {error_msg}")
            except Exception as e:
                openrouter_error = f"OpenRouter error: {e}"
                print(f"[ERROR] OpenRouter failed: {e}")
            
            # If OpenRouter failed, return the error - don't silently fall back
            if openrouter_error and not assistant_text:
                return JsonResponse({
                    'error': openrouter_error,
                    'provider': 'openrouter',
                }, status=503)
        
        if provider == "local":
            # Use Ollama API
            model_name = getattr(settings, 'OLLAMA_MODEL', 'mistral')
            if session and session.model:
                model_name = session.model

            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/chat"
            
            payload = {
                'model': model_name,
                'messages': messages,
                'stream': False,
                'options': {
                    'temperature': model_config['temperature'],
                    'top_p': model_config['top_p'],
                    'top_k': model_config.get('top_k', 40),
                    'repeat_penalty': model_config.get('repeat_penalty', 1.1),
                }
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(ollama_url, json=payload)
                response.raise_for_status()
                result = response.json()
            
            assistant_text = result.get('message', {}).get('content', '')
            used_provider = "local"

        if session_id:
            session = _ensure_session(session_id)
            assistant_msg = ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_ASSISTANT,
                message=assistant_text,
            )
            # Index assistant message in RAG store
            _index_message(assistant_msg, session_id, user_id)
            
            # Touch session updated_at for sorting
            from .models import ChatSession
            ChatSession.objects.filter(session_id=session_id).update(updated_at=timezone.now())

        return JsonResponse({
            'response': assistant_text,
            'model': model_name,
            'provider': used_provider,
            'session_id': session_id,
        })
    
    except httpx.HTTPStatusError as e:
        error_msg = str(e)
        try:
            error_data = e.response.json()
            error_msg = error_data.get('error', error_msg)
        except Exception:
            pass
        return JsonResponse({'error': f'Error calling Ollama: {error_msg}'}, status=e.response.status_code)
    except httpx.ConnectError as e:
        return JsonResponse({
            'error': f'Cannot connect to Ollama at {settings.OLLAMA_BASE_URL}. Make sure Ollama is running and accessible via Tailscale.'
        }, status=503)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
