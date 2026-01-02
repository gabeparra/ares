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
from .model_selector import select_model_for_task, analyze_task
from ares_mind.memory_extraction import extract_memories_from_conversation
from .code_views import get_code_context
from .auth import require_auth
import re

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


def _process_telegram_send_commands(text, user_id="default"):
    """
    Parse and execute Telegram send commands in the AI response.
    
    Looks for patterns like [TELEGRAM_SEND:identifier:message] and executes them.
    Returns the text with markers replaced by confirmation messages.
    """
    # Pattern: [TELEGRAM_SEND:identifier:message]
    # Updated to handle multi-line messages better
    pattern = r'\[TELEGRAM_SEND:([^\]:]+):([^\]]+)\]'
    
    def replace_command(match):
        identifier = match.group(1).strip()
        message_text = match.group(2).strip()
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            from .telegram_views import _get_telegram_chat_id_by_identifier
            from django.conf import settings
            
            logger.info(f"Processing Telegram send command: identifier='{identifier}', message_length={len(message_text)}, user_id='{user_id}'")
            
            # Get Telegram chat ID (pass user_id from outer scope)
            chat_id = _get_telegram_chat_id_by_identifier(identifier, user_id=user_id)
            
            if not chat_id:
                logger.warning(f"Could not find Telegram user '{identifier}'")
                return f"[Note: Could not find Telegram user '{identifier}'. Make sure they have messaged the bot before. Use /api/v1/telegram/chats to see available chats.]"
            
            logger.info(f"Found chat_id={chat_id} for identifier='{identifier}'")
            
            # Check if Telegram is enabled
            token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or None
            if not token:
                logger.warning("TELEGRAM_BOT_TOKEN not configured")
                return "[Note: Telegram integration is not configured.]"
            
            enabled = _get_setting("telegram_enabled", "true").lower() == "true"
            if not enabled:
                logger.warning("Telegram integration is disabled")
                return "[Note: Telegram integration is disabled. Enable it via /api/v1/telegram/connect.]"
            
            # Send message via Telegram Bot API
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": int(chat_id),
                "text": message_text,
            }
            
            logger.info(f"Sending message to Telegram chat_id={chat_id}")
            with httpx.Client(timeout=10.0) as client:
                r = client.post(send_url, json=payload)
                if r.status_code == 200:
                    result = r.json()
                    if result.get("ok"):
                        logger.info(f"Successfully sent Telegram message to {identifier}")
                        return f"✓ Message sent to {identifier} via Telegram."
                    else:
                        error_desc = result.get("description") or "Unknown error"
                        logger.error(f"Telegram API returned error: {error_desc}")
                        return f"[Note: Failed to send Telegram message: {error_desc}]"
                else:
                    try:
                        error_data = r.json()
                        error_desc = error_data.get("description") or f"HTTP {r.status_code}"
                    except Exception:
                        error_desc = f"HTTP {r.status_code}"
                    logger.error(f"Telegram API HTTP error: {error_desc}")
                    return f"[Note: Failed to send Telegram message: {error_desc}]"
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending Telegram message: {e}\n{traceback.format_exc()}")
            return f"[Note: Error sending Telegram message: {str(e)}]"
    
    # Replace all TELEGRAM_SEND commands
    processed_text = re.sub(pattern, replace_command, text)
    return processed_text


def _call_openrouter(messages, model_config, model=None):
    """Call OpenRouter service (TypeScript SDK wrapper) and return assistant response."""
    # Get model from parameter, settings, or environment
    if not model:
        model = _get_setting("openrouter_model")
    if not model:
        model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
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


@csrf_exempt  # JWT auth - CSRF not needed for tokens in headers
@require_auth  # SECURITY: Requires authentication
@require_http_methods(["POST"])
def chat(request):
    """
    Unified /v1/chat endpoint for ARES.
    Accepts chat messages and routes them to Ollama.

    SECURITY: Requires Auth0 authentication with admin role.
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
        else:
            # Append Telegram messaging instructions to custom prompts if not already present
            if "[TELEGRAM_SEND:" not in system_prompt:
                telegram_instructions = """

## Telegram Messaging
You can send messages to Telegram users. When the user asks you to send a message to someone via Telegram, use this format in your response:
[TELEGRAM_SEND:identifier:message_text]

Where:
- identifier: The name, username, or nickname of the Telegram user (e.g., "gabu", "gabe", "@username")
- message_text: The actual message content to send

Example: If asked to "send hello to gabu", include in your response:
[TELEGRAM_SEND:gabu:Hello from ARES!]

After sending, the system will replace this marker with a confirmation. Always confirm that you've sent the message in your response.
"""
                system_prompt = system_prompt + telegram_instructions

        # Inject self-memory context into the system prompt (AI identity)
        self_memory_context = get_self_memory_context()
        if self_memory_context:
            system_prompt = system_prompt + "\n\n" + self_memory_context

        # Inject user memory context (user facts and preferences)
        user_memory_context = get_user_memory_context(user_id)
        if user_memory_context:
            system_prompt = system_prompt + "\n\n" + user_memory_context

        # Inject code context if available
        try:
            from .code_views import get_code_context_summary
            code_summary = get_code_context_summary()
            if code_summary:
                system_prompt = system_prompt + "\n\n" + code_summary
        except Exception as e:
            # Don't fail chat if code context fails
            print(f"[WARNING] Failed to get code context: {e}")

        # Inject calendar context if available and relevant
        try:
            from .calendar_views import get_calendar_context_summary
            calendar_summary = get_calendar_context_summary(user_id=user_id, message=message)
            if calendar_summary:
                system_prompt = system_prompt + "\n\n" + calendar_summary
        except Exception as e:
            # Don't fail chat if calendar context fails
            print(f"[WARNING] Failed to get calendar context: {e}")

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
                # Check if auto-selection is enabled
                auto_select = _get_setting("openrouter_auto_select")
                selected_model = None
                
                if auto_select and auto_select.lower() in ("true", "1", "yes"):
                    # Analyze task and select best model
                    selected_model = select_model_for_task(
                        message,
                        use_auto=True,  # Use OpenRouter's auto router
                    )
                    # Override the default model for this request
                    assistant_text, model_name = _call_openrouter(messages, model_config, model=selected_model)
                else:
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
                    'num_gpu': int(model_config.get('num_gpu', 40)),
                }
            }
            
            with httpx.Client(timeout=120.0) as client:
                response = client.post(ollama_url, json=payload)
                response.raise_for_status()
                result = response.json()
            
            assistant_text = result.get('message', {}).get('content', '')
            used_provider = "local"

        # Process Telegram send commands in the assistant response
        assistant_text = _process_telegram_send_commands(assistant_text, user_id=user_id)

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
            
            # Optionally extract memories from conversation
            # Only extract if conversation has enough messages and auto-extraction is enabled
            auto_extract = _get_setting("auto_extract_memories")
            if auto_extract and auto_extract.lower() in ("true", "1", "yes"):
                message_count = ConversationMessage.objects.filter(session=session).count()
                # Extract if conversation has at least 6 messages (3 exchanges)
                if message_count >= 6:
                    try:
                        # Extract in background (non-blocking)
                        extract_memories_from_conversation(
                            session_id=session_id,
                            user_id=user_id,
                            max_messages=50,
                        )
                    except Exception as e:
                        # Don't fail the chat request if extraction fails
                        print(f"[WARNING] Memory extraction failed: {e}")

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
