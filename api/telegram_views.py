from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
import json
import httpx
import logging

from .models import ConversationMessage
from .auth import require_auth
from .utils import _get_setting, _set_setting, _ensure_session, _get_model_config, _get_default_system_prompt


@require_http_methods(["GET"])
@require_auth
def telegram_status(request):
    """
    Report Telegram integration status.

    "connected" means: token configured AND not disabled via DB toggle AND token validates with Telegram.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or None
    token_configured = bool(token)
    enabled = _get_setting("telegram_enabled", "true").lower() == "true"

    connected = False
    error = None
    webhook_url = None
    webhook_ok = None

    if not enabled:
        error = "Disabled by user"
    elif token_configured:
        try:
            # Validate token quickly
            url = f"https://api.telegram.org/bot{token}/getMe"
            with httpx.Client(timeout=5.0) as client:
                r = client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    connected = bool(data.get("ok") is True)
                    if not connected:
                        # Telegram may return ok=false with error details even on 200.
                        error = data.get("description") or "Telegram returned ok=false"
                else:
                    detail = None
                    try:
                        body = r.json()
                        detail = body.get("description") or body.get("error") or None
                    except Exception:
                        detail = None
                    error = f"Telegram getMe failed: HTTP {r.status_code}" + (f" ({detail})" if detail else "")
        except Exception as e:
            error = str(e)

    # Best-effort: check webhook configuration for inbound delivery.
    if token_configured:
        try:
            info_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
            with httpx.Client(timeout=5.0) as client:
                r = client.get(info_url)
                if r.status_code == 200:
                    data = r.json() or {}
                    result = data.get("result") or {}
                    webhook_url = result.get("url") or ""
                    webhook_ok = bool(webhook_url)
                else:
                    webhook_ok = None
        except Exception:
            webhook_ok = None

    return JsonResponse(
        {
            "token_configured": token_configured,
            "enabled": enabled,
            "connected": connected,
            "error": error,
            "webhook_url": webhook_url,
            "webhook_ok": webhook_ok,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def telegram_disconnect(request):
    """
    Disable Telegram integration without changing environment variables.
    """
    _set_setting("telegram_enabled", "false")
    return JsonResponse({"success": True, "enabled": False})


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def telegram_connect(request):
    """
    Enable Telegram integration (requires TELEGRAM_BOT_TOKEN to be configured).

    Also configures Telegram webhook automatically so inbound messages are delivered.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or None
    if not token:
        return JsonResponse({"error": "TELEGRAM_BOT_TOKEN is not configured"}, status=400)

    # Determine the public webhook URL from the current request (behind nginx).
    proto = request.META.get("HTTP_X_FORWARDED_PROTO") or request.scheme or "https"
    host = request.get_host()
    webhook_url = f"{proto}://{host}/api/v1/telegram/webhook"

    expected_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", None) or None
    payload = {"url": webhook_url, "drop_pending_updates": True}
    if expected_secret:
        payload["secret_token"] = expected_secret

    try:
        set_url = f"https://api.telegram.org/bot{token}/setWebhook"
        with httpx.Client(timeout=10.0) as client:
            r = client.post(set_url, json=payload)
            data = r.json() if r.status_code == 200 else {}
            if r.status_code != 200 or not data.get("ok"):
                detail = data.get("description") or f"HTTP {r.status_code}"
                return JsonResponse(
                    {
                        "error": f"Failed to set webhook: {detail}",
                        "webhook_url": webhook_url,
                    },
                    status=502,
                )
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to set webhook: {str(e)}", "webhook_url": webhook_url},
            status=502,
        )

    # Register SD commands if SD integration is available
    try:
        from . import sd_integration
        sd_integration.register_sd_commands(token)
    except ImportError:
        pass  # SD integration not available

    _set_setting("telegram_enabled", "true")
    return JsonResponse({"success": True, "enabled": True, "webhook_url": webhook_url})


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """
    Inbound Telegram webhook receiver.

    Telegram will POST Update payloads here if you configure setWebhook().
    This endpoint creates a DB chat session per Telegram user and stores messages.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or None
    if not token:
        return JsonResponse({"error": "TELEGRAM_BOT_TOKEN is not configured"}, status=503)

    enabled = _get_setting("telegram_enabled", "true").lower() == "true"
    if not enabled:
        # Acknowledge quickly; do not process.
        return JsonResponse({"ok": True, "ignored": True})

    # Optional secret token validation (recommended).
    expected_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", None) or None
    if expected_secret:
        got_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if got_secret != expected_secret:
            return JsonResponse({"error": "Invalid Telegram webhook secret"}, status=403)

    try:
        update = json.loads(request.body or b"{}")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message_obj = update.get("message") or update.get("edited_message")
    if not message_obj:
        # Nothing to do (e.g. callback_query). Acknowledge.
        return JsonResponse({"ok": True})

    chat = message_obj.get("chat") or {}
    chat_id = chat.get("id")

    from_user = message_obj.get("from") or {}
    from_id = from_user.get("id")

    # Handle photo/document messages first (for upscaling support)
    photo = message_obj.get("photo")
    document = message_obj.get("document")
    text = (message_obj.get("text") or message_obj.get("caption") or "").strip()
    
    # Check if message contains a photo or image document
    is_image_document = False
    if document:
        mime_type = document.get("mime_type", "")
        file_name = document.get("file_name", "")
        # Check mime type or file extension
        if mime_type.startswith("image/"):
            is_image_document = True
        elif file_name:
            # Check file extension
            ext = file_name.lower().split('.')[-1] if '.' in file_name else ""
            if ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp"]:
                is_image_document = True
    
    if photo or is_image_document:
        try:
            from . import sd_integration
            import base64
            
            logging.getLogger(__name__).info(f"Processing photo/document message from user {from_id}, photo={bool(photo)}, document={is_image_document}")
            
            # Get the largest photo or download document
            file_id = None
            if photo and isinstance(photo, list) and len(photo) > 0:
                # Get largest photo (last item in array is usually largest, or use max file_size)
                largest_photo = max(photo, key=lambda p: p.get("file_size", 0) if p.get("file_size") else 0)
                file_id = largest_photo.get("file_id")
                logging.getLogger(__name__).info(f"Extracted file_id from photo: {file_id[:20] if file_id else None}...")
            elif document and is_image_document:
                file_id = document.get("file_id")
                logging.getLogger(__name__).info(f"Extracted file_id from document: {file_id[:20] if file_id else None}...")
            
            if file_id:
                # Download file from Telegram
                get_file_url = f"https://api.telegram.org/bot{token}/getFile"
                with httpx.Client(timeout=30.0) as client:
                    file_response = client.post(get_file_url, json={"file_id": file_id})
                    if file_response.status_code == 200:
                        file_info = file_response.json()
                        if file_info.get("ok"):
                            file_path = file_info["result"].get("file_path")
                            if file_path:
                                # Download actual file
                                download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                                file_data_response = client.get(download_url, timeout=60.0)
                                if file_data_response.status_code == 200:
                                    # Convert to base64
                                    image_base64 = base64.b64encode(file_data_response.content).decode('utf-8')
                                    # Save for upscaling
                                    sd_integration._save_last_generated_image(from_id, image_base64)
                                    logging.getLogger(__name__).info(f"Saved image for upscaling from user {from_id}")
                                    
                                    # Send confirmation
                                    try:
                                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                                        with httpx.Client(timeout=10.0) as client:
                                            confirmation_text = "✅ Image received and saved! Use /upscale to upscale it."
                                            if text and text.startswith("/upscale"):
                                                confirmation_text = "✅ Image received! Processing upscale..."
                                            client.post(send_url, json={
                                                "chat_id": int(chat_id),
                                                "text": confirmation_text
                                            })
                                    except Exception as e:
                                        logging.getLogger(__name__).warning(f"Failed to send confirmation: {e}")
                                    
                                    # If caption contains /upscale, handle it
                                    if text and text.startswith("/upscale"):
                                        return sd_integration._handle_upscale_command(text, chat_id, token, from_id)
                                    
                                    # Return success response after processing photo
                                    return JsonResponse({"ok": True})
                                else:
                                    logging.getLogger(__name__).error(f"Failed to download file: HTTP {file_data_response.status_code}")
                            else:
                                logging.getLogger(__name__).error(f"No file_path in getFile response: {file_info}")
                        else:
                            logging.getLogger(__name__).error(f"getFile returned ok=false: {file_info}")
                    else:
                        logging.getLogger(__name__).error(f"getFile request failed: HTTP {file_response.status_code}")
            else:
                logging.getLogger(__name__).warning("Photo/document found but no file_id extracted")
                # Still return ok to acknowledge the message
                return JsonResponse({"ok": True})
        except ImportError:
            logging.getLogger(__name__).warning("SD integration not available")
            # If SD integration not available, still acknowledge photo message
            if photo or is_image_document:
                return JsonResponse({"ok": True})
        except Exception as e:
            import traceback
            logging.getLogger(__name__).error(f"Failed to process photo: {e}\n{traceback.format_exc()}")
            # Still acknowledge the message even if processing failed
            if photo or is_image_document:
                return JsonResponse({"ok": True})
    
    # Handle text messages and commands
    if not text:
        return JsonResponse({"ok": True})

    # Handle SD commands if SD integration is available
    try:
        from . import sd_integration
        if text.startswith("/sdconfig"):
            return sd_integration._handle_sdconfig_command(text, chat_id, token, from_id)
        elif text.startswith("/sd "):
            return sd_integration._handle_sd_command(text, chat_id, token, from_id)
        elif text == "/sd":
            return sd_integration._handle_sd_command(text, chat_id, token, from_id)
        elif text.startswith("/upscale"):
            return sd_integration._handle_upscale_command(text, chat_id, token, from_id)
        elif text.startswith("/prompts"):
            return sd_integration._handle_prompts_command(chat_id, token, from_id)
        elif text.startswith("/prompt "):
            return sd_integration._handle_prompt_command(text, chat_id, token, from_id)
        elif text.startswith("/sdsave"):
            return sd_integration._handle_sdsave_command(text, chat_id, token, from_id)
        elif text.startswith("/samplers"):
            return sd_integration._handle_samplers_command(chat_id, token)
        elif text.startswith("/upscalers"):
            return sd_integration._handle_upscalers_command(chat_id, token)
        elif (text.split(maxsplit=1)[0] == "/hr") or (text.split(maxsplit=1)[0].startswith("/hr@")):
            return sd_integration._handle_hr_command(chat_id, token, from_id)
        elif text.startswith("/settings"):
            return sd_integration._handle_settings_help_command(chat_id, token)
        elif text.startswith("/help"):
            return sd_integration._handle_help_command(chat_id, token)
    except ImportError:
        pass  # SD integration not available
    username = from_user.get("username")
    first_name = from_user.get("first_name")
    last_name = from_user.get("last_name")

    if not from_id or not chat_id:
        return JsonResponse({"ok": True})

    logging.getLogger(__name__).info(
        "telegram_webhook: from_id=%s chat_id=%s text=%s",
        from_id,
        chat_id,
        text[:200],
    )

    # One conversation per Telegram user (as requested).
    session_id = f"telegram_user_{from_id}"
    session = _ensure_session(session_id)

    # Set a friendly title on first sight.
    if not session.title:
        display = None
        if username:
            display = f"@{username}"
        else:
            name = " ".join([p for p in [first_name, last_name] if p])
            display = name or str(from_id)
        session.title = f"Telegram {display}"
        session.save(update_fields=["title", "updated_at"])

    ConversationMessage.objects.create(
        session=session,
        role=ConversationMessage.ROLE_USER,
        message=text,
    )

    # Generate a reply via Ollama using the default system prompt and conversation history.
    assistant_text = None
    try:
        # Fetch the system prompt from settings (same as the site uses)
        system_prompt = _get_setting("chat_system_prompt")
        if not system_prompt:
            system_prompt = _get_default_system_prompt()

        # Build messages list for Ollama chat API
        messages = [{"role": "system", "content": system_prompt}]

        # Fetch conversation history for context
        history_messages = list(
            ConversationMessage.objects.filter(session=session)
            .order_by("-created_at")[:10]
        )
        history_messages.reverse()
        
        # Add conversation history (excluding the current message we just added)
        for msg in history_messages[:-1]:
            role = "user" if msg.role == ConversationMessage.ROLE_USER else "assistant"
            if msg.role in (ConversationMessage.ROLE_USER, ConversationMessage.ROLE_ASSISTANT):
                messages.append({"role": role, "content": msg.message})
        
        # Add current user message
        messages.append({"role": "user", "content": text})

        # Get model configuration from settings
        model_config = _get_model_config()
        
        # Use session-specific model if set, otherwise use default
        model_name = getattr(settings, 'OLLAMA_MODEL', 'mistral')
        if session and session.model:
            model_name = session.model

        # Route to Ollama API
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
            r = client.post(ollama_url, json=payload)
            r.raise_for_status()
            result = r.json() or {}
            assistant_text = (result.get("message", {}).get("content") or "").strip()
    except Exception as e:
        logging.getLogger(__name__).error(f"Ollama API error: {e}")
        ConversationMessage.objects.create(
            session=session,
            role=ConversationMessage.ROLE_ERROR,
            message=f"Telegram reply generation failed: {str(e)}",
        )

    if assistant_text:
        ConversationMessage.objects.create(
            session=session,
            role=ConversationMessage.ROLE_ASSISTANT,
            message=assistant_text,
        )
        from .models import ChatSession
        ChatSession.objects.filter(session_id=session_id).update(updated_at=timezone.now())

        # Reply back to Telegram chat
        try:
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            with httpx.Client(timeout=10.0) as client:
                client.post(send_url, json={"chat_id": int(chat_id), "text": assistant_text})
        except Exception as e:
            ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_ERROR,
                message=f"Telegram sendMessage failed: {str(e)}",
            )

    return JsonResponse({"ok": True, "session_id": session_id})

