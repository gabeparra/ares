from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
import json
import httpx
import logging
import re
import threading
from datetime import datetime

from .models import ConversationMessage
from .auth import require_auth
from .utils import _get_setting, _set_setting, _ensure_session, _get_model_config, _get_default_system_prompt
from .chat_views import _call_openrouter, _process_telegram_send_commands


def _get_daily_telegram_session_id(from_id):
    """
    Generate a daily Telegram session ID.
    
    Format: telegram_user_{from_id}_{YYYY-MM-DD}
    Creates a new session each day for the same user.
    """
    today = timezone.now().date()
    return f"telegram_user_{from_id}_{today.isoformat()}"


def _handle_basic_help_command(chat_id, token):
    """
    Handle /help command when SD integration is not available.
    Provides basic help for chat functionality.
    """
    help_text = """🤖 ARES Bot - Command Reference

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 CHAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Just type normally to chat with ARES!
Your conversation is saved daily.

/new - Start a fresh conversation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ INFO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/help - Show this command list

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Image generation commands are available
   when SD integration is configured."""
    
    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        with httpx.Client(timeout=10.0) as client:
            client.post(send_url, json={"chat_id": int(chat_id), "text": help_text})
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to send help message: {e}")
    
    return JsonResponse({"ok": True})


def _get_new_telegram_session_id(from_id):
    """
    Generate a new unique Telegram session ID for starting a fresh conversation.
    
    Format: telegram_user_{from_id}_{YYYY-MM-DD}_{HHMMSS}
    This allows multiple sessions per day when explicitly requested.
    """
    now = timezone.now()
    return f"telegram_user_{from_id}_{now.strftime('%Y-%m-%d_%H%M%S')}"


def _handle_new_command(chat_id, from_id, token, username, first_name, last_name):
    """
    Handle /new command to start a fresh conversation session.
    """
    logger = logging.getLogger(__name__)
    
    # Create a new unique session
    session_id = _get_new_telegram_session_id(from_id)
    session = _ensure_session(session_id)
    
    # Set title with timestamp
    display = None
    if username:
        display = f"@{username}"
    else:
        name = " ".join([p for p in [first_name, last_name] if p])
        display = name or str(from_id)
    
    now = timezone.now()
    session.title = f"Telegram {display} ({now.strftime('%b %d %H:%M')})"
    session.save(update_fields=["title", "updated_at"])
    
    # Store this as the active session for this user
    from .models import UserPreference
    UserPreference.objects.update_or_create(
        user_id="default",
        preference_key=f"telegram_active_session_{from_id}",
        defaults={"preference_value": session_id}
    )
    
    # Send confirmation
    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        message = f"✨ Started a new conversation!\n\nSession: {now.strftime('%b %d, %H:%M')}\n\nYour previous conversations are saved and can be viewed in the ARES web interface."
        with httpx.Client(timeout=10.0) as client:
            client.post(send_url, json={"chat_id": int(chat_id), "text": message})
    except Exception as e:
        logger.error(f"Failed to send new session confirmation: {e}")
    
    logger.info(f"Created new Telegram session for user {from_id}: {session_id}")
    return JsonResponse({"ok": True, "session_id": session_id})


def _extract_chat_id_from_session_id(session_id):
    """
    Extract the Telegram chat_id from a session_id.
    
    Handles both formats:
    - Old: telegram_user_{chat_id}
    - New: telegram_user_{chat_id}_{YYYY-MM-DD}
    
    Returns the chat_id portion.
    """
    if not session_id.startswith("telegram_user_"):
        return None
    
    # Remove the prefix
    remainder = session_id.replace("telegram_user_", "", 1)
    
    # Check if it has a date suffix (format: chat_id_YYYY-MM-DD)
    parts = remainder.rsplit("_", 1)
    if len(parts) == 2:
        # Check if the last part looks like a date (YYYY-MM-DD)
        potential_date = parts[1]
        if len(potential_date) == 10 and potential_date.count("-") == 2:
            try:
                # Validate it's a real date
                datetime.strptime(potential_date, "%Y-%m-%d")
                return parts[0]  # Return chat_id without date
            except ValueError:
                pass
    
    # No date suffix, return the whole remainder
    return remainder


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


def _process_telegram_message_background(token, chat_id, from_id, text, session_id, canonical_user_id):
    """
    Process a Telegram message in the background and send a reply.
    This function runs in a separate thread to avoid webhook timeouts.
    
    NOW USING ORCHESTRATOR: All LLM calls go through the orchestrator
    for consistent memory management and identical prompts across providers.
    """
    logger = logging.getLogger(__name__)
    
    try:
        from ares_core.orchestrator import orchestrator
        
        session = _ensure_session(session_id)
        
        # =====================================================================
        # USE ORCHESTRATOR - This replaces all the manual prompt assembly above
        # =====================================================================
        
        logger.info(f"[TELEGRAM] Processing message via ORCHESTRATOR for user_id={canonical_user_id}")
        
        try:
            response = orchestrator.process_chat_request(
                user_id=canonical_user_id,
                message=text,
                session_id=session_id,
                system_prompt_override=None,  # Use default system prompt
                prefer_local=True,  # Prefer local for Telegram (faster)
            )
            
            assistant_text = response.content
            model_name = response.model
            logger.info(f"[TELEGRAM] Successfully processed via orchestrator: provider={response.provider}, model={model_name}")
            
        except Exception as e:
            # If orchestrator fails, provide a fallback message
            logger.error(f"[TELEGRAM] Orchestrator failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Log error to session
            ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_ERROR,
                message=f"Orchestrator error: {str(e)}",
            )
            
            assistant_text = "⚠️ I received your message, but I'm currently unable to process it. Your message has been saved, and I'll be back shortly."
            model_name = "error"

        if assistant_text:
            ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_ASSISTANT,
                message=assistant_text,
            )
            from .models import ChatSession
            ChatSession.objects.filter(session_id=session_id).update(updated_at=timezone.now())

            # Reply back to Telegram chat
            # Note: This message should NOT trigger the webhook again because:
            # 1. Telegram doesn't send webhooks for messages the bot sends
            # 2. We check for is_bot above to prevent processing bot messages
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(send_url, json={"chat_id": int(chat_id), "text": assistant_text})
                    if response.status_code != 200:
                        logger.error(f"Failed to send Telegram message: HTTP {response.status_code}")
                        ConversationMessage.objects.create(
                            session=session,
                            role=ConversationMessage.ROLE_ERROR,
                            message=f"Telegram sendMessage failed: HTTP {response.status_code}",
                        )
                    else:
                        logger.info(f"Sent Telegram message to chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Exception sending Telegram message: {e}")
                ConversationMessage.objects.create(
                    session=session,
                    role=ConversationMessage.ROLE_ERROR,
                    message=f"Telegram sendMessage failed: {str(e)}",
                )
        else:
            # This should rarely happen now since error handlers set assistant_text,
            # but keep as a safety fallback
            logger.warning(f"No assistant_text generated for Telegram message from user {from_id}")
            assistant_text = "⚠️ I received your message, but I'm currently unable to process it. Please try again in a moment."
            # Save the fallback message and send it
            ConversationMessage.objects.create(
                session=session,
                role=ConversationMessage.ROLE_ASSISTANT,
                message=assistant_text,
            )
            from .models import ChatSession
            ChatSession.objects.filter(session_id=session_id).update(updated_at=timezone.now())
            
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(send_url, json={"chat_id": int(chat_id), "text": assistant_text})
                    if response.status_code != 200:
                        logger.error(f"Failed to send Telegram message: HTTP {response.status_code}")
                    else:
                        logger.info(f"Sent Telegram fallback message to chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Exception sending Telegram fallback message: {e}")
    except Exception as e:
        logger.error(f"Error in background Telegram message processing: {e}", exc_info=True)
        # Try to send an error message to the user
        try:
            error_msg = "⚠️ I encountered an error processing your message. Please try again."
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            with httpx.Client(timeout=10.0) as client:
                client.post(send_url, json={"chat_id": int(chat_id), "text": error_msg})
        except Exception:
            pass  # If we can't send the error message, just log it


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

    # SECURITY: Mandatory secret token validation to prevent fake webhooks
    expected_secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    if not expected_secret:
        return JsonResponse({"error": "Telegram webhook secret not configured"}, status=500)

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
    
    # Ignore messages from bots to prevent feedback loops
    is_bot = from_user.get("is_bot", False)
    if is_bot:
        logging.getLogger(__name__).info(f"Ignoring message from bot (user_id={from_id})")
        return JsonResponse({"ok": True, "ignored": True, "reason": "bot_message"})

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
        # No text content, acknowledge but don't process
        logging.getLogger(__name__).debug(f"Empty text message from user {from_id}, acknowledging")
        return JsonResponse({"ok": True, "ignored": True, "reason": "empty_text"})

    # Handle /new command to start a fresh conversation
    if text.startswith("/new"):
        username = from_user.get("username")
        first_name = from_user.get("first_name")
        last_name = from_user.get("last_name")
        return _handle_new_command(chat_id, from_id, token, username, first_name, last_name)

    # Handle SD commands if SD integration is available
    try:
        from . import sd_integration
        if text.startswith("/sdfrompcconfi"):
            return sd_integration._handle_sdfrompcconfi_command(text, chat_id, token, from_id)
        elif text.startswith("/sdconfig"):
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
        # SD integration not available - provide basic help
        if text.startswith("/help"):
            return _handle_basic_help_command(chat_id, token)
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

    # Check for an active session set by /new command, otherwise use daily session
    from .models import UserPreference
    active_session_pref = UserPreference.objects.filter(
        user_id="default",
        preference_key=f"telegram_active_session_{from_id}"
    ).first()
    
    # Get today's date string (YYYY-MM-DD format)
    today = timezone.now().date()
    today_str = today.isoformat()
    today_prefix = f"telegram_user_{from_id}_{today_str}"
    
    # Determine which session to use
    if active_session_pref and active_session_pref.preference_value.startswith(today_prefix):
        # Use the active session if it's from today (from /new command)
        session_id = active_session_pref.preference_value
        logging.getLogger(__name__).debug(
            f"Using active session for user {from_id}: {session_id}"
        )
    else:
        # Use daily session (default behavior) - creates new session each day
        session_id = _get_daily_telegram_session_id(from_id)
        logging.getLogger(__name__).info(
            f"Using daily session for user {from_id}: {session_id} (today: {today_str})"
        )
        # Clear stale active session preference if it exists
        if active_session_pref:
            logging.getLogger(__name__).debug(
                f"Clearing stale active session preference for user {from_id}: {active_session_pref.preference_value}"
            )
            active_session_pref.delete()
    
    session = _ensure_session(session_id)

    # Set a friendly title on first sight (includes date for daily sessions).
    if not session.title:
        display = None
        if username:
            display = f"@{username}"
        else:
            name = " ".join([p for p in [first_name, last_name] if p])
            display = name or str(from_id)
        today = timezone.now().date()
        session.title = f"Telegram {display} ({today.strftime('%b %d')})"
        session.save(update_fields=["title", "updated_at"])

    # Get the canonical user_id for this Telegram user (linked to ARES user_id if available)
    from .utils import _get_canonical_user_id
    canonical_user_id = _get_canonical_user_id(str(from_id), default_user_id="default")

    # Save the user message immediately
    ConversationMessage.objects.create(
        session=session,
        role=ConversationMessage.ROLE_USER,
        message=text,
    )

    # Process message in background thread to avoid webhook timeout
    # Telegram webhooks timeout after ~60 seconds, but Ollama can take up to 120 seconds
    thread = threading.Thread(
        target=_process_telegram_message_background,
        args=(token, chat_id, from_id, text, session_id, canonical_user_id),
        daemon=True
    )
    thread.start()

    # Return immediately to acknowledge receipt to Telegram
    # This prevents Telegram from timing out and retrying the webhook
    return JsonResponse({"ok": True, "session_id": session_id})


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def telegram_send(request):
    """
    Send a message to a Telegram chat.
    
    Required parameters:
    - chat_id: Telegram chat ID (user ID for direct messages)
    - message: Text message to send
    
    Optional parameters:
    - parse_mode: Markdown or HTML formatting (optional)
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None) or None
    if not token:
        return JsonResponse({"error": "TELEGRAM_BOT_TOKEN is not configured"}, status=400)
    
    enabled = _get_setting("telegram_enabled", "true").lower() == "true"
    if not enabled:
        return JsonResponse({"error": "Telegram integration is disabled"}, status=403)
    
    try:
        data = json.loads(request.body)
        chat_id = data.get("chat_id")
        message = data.get("message")
        parse_mode = data.get("parse_mode")  # Optional: "Markdown", "HTML", or None
        
        if not chat_id:
            return JsonResponse({"error": "chat_id is required"}, status=400)
        if not message:
            return JsonResponse({"error": "message is required"}, status=400)
        
        # Send message via Telegram Bot API
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": int(chat_id),
            "text": message,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        
        with httpx.Client(timeout=10.0) as client:
            r = client.post(send_url, json=payload)
            if r.status_code == 200:
                result = r.json()
                if result.get("ok"):
                    return JsonResponse({
                        "success": True,
                        "message_id": result.get("result", {}).get("message_id"),
                    })
                else:
                    error_desc = result.get("description") or "Unknown error"
                    return JsonResponse(
                        {"error": f"Telegram API error: {error_desc}"},
                        status=502,
                    )
            else:
                try:
                    error_data = r.json()
                    error_desc = error_data.get("description") or f"HTTP {r.status_code}"
                except Exception:
                    error_desc = f"HTTP {r.status_code}"
                return JsonResponse(
                    {"error": f"Failed to send message: {error_desc}"},
                    status=502,
                )
    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logging.getLogger(__name__).error(f"telegram_send error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@require_auth
def telegram_chats(request):
    """
    List available Telegram chats (sessions that have telegram_user_ prefix).
    
    Returns a list of Telegram chat sessions with their chat_id extracted from session_id.
    Supports both old format (telegram_user_{chat_id}) and new daily format 
    (telegram_user_{chat_id}_{YYYY-MM-DD}).
    """
    enabled = _get_setting("telegram_enabled", "true").lower() == "true"
    if not enabled:
        return JsonResponse({"error": "Telegram integration is disabled"}, status=403)
    
    from .models import ChatSession
    
    # Find all sessions that start with "telegram_user_"
    telegram_sessions = ChatSession.objects.filter(
        session_id__startswith="telegram_user_"
    ).order_by("-updated_at")
    
    chats = []
    for session in telegram_sessions:
        # Extract chat_id from session_id (handles both old and new daily formats)
        try:
            chat_id = _extract_chat_id_from_session_id(session.session_id)
            if chat_id:
                chats.append({
                    "chat_id": chat_id,
                    "session_id": session.session_id,
                    "title": session.title or "Telegram Chat",
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                })
        except Exception:
            # Skip sessions with invalid format
            continue
    
    return JsonResponse({"chats": chats})


def _get_telegram_chat_id_by_identifier(identifier, user_id="default"):
    """
    Find Telegram chat_id by user identifier (name, username, or nickname).
    
    Searches in order:
    1. User preferences (telegram_chat_id_{identifier})
    2. User facts (telegram_chat_id fact_type)
    3. Session title (contains identifier, with smart matching)
    4. Session ID (telegram_user_{chat_id} or telegram_user_{chat_id}_{date})
    
    Returns chat_id if found, None otherwise.
    """
    from .models import ChatSession, UserPreference, UserFact
    
    identifier_lower = identifier.lower().strip()
    # Normalize identifier: remove @ if present
    identifier_normalized = identifier_lower.lstrip('@').strip()
    
    # 1. Check user preferences first (telegram_chat_id_{identifier})
    pref_key = f"telegram_chat_id_{identifier_normalized}"
    preference = UserPreference.objects.filter(user_id=user_id, preference_key=pref_key).first()
    if preference:
        return preference.preference_value.strip()
    
    # 2. Check user facts (look for telegram_chat_id fact with matching key)
    fact = UserFact.objects.filter(
        user_id=user_id,
        fact_key__iexact=identifier_normalized,
        fact_value__startswith="telegram_user_"
    ).first()
    if fact:
        # Extract chat_id from fact_value (handles both old and daily formats)
        chat_id = _extract_chat_id_from_session_id(fact.fact_value)
        if chat_id:
            return chat_id
    
    # Also check if fact_key is something like "telegram_chat_id" and fact_value is the chat_id
    fact = UserFact.objects.filter(
        user_id=user_id,
        fact_key__iexact=f"telegram_chat_id_{identifier_normalized}"
    ).first()
    if fact:
        # fact_value should be the chat_id directly (or prefixed with telegram_user_)
        fact_value = fact.fact_value.strip()
        if fact_value.startswith("telegram_user_"):
            chat_id = _extract_chat_id_from_session_id(fact_value)
        else:
            chat_id = fact_value
        if chat_id:
            return chat_id
    
    # 3. Search Telegram sessions by title
    telegram_sessions = ChatSession.objects.filter(
        session_id__startswith="telegram_user_"
    ).order_by("-updated_at")
    
    for session in telegram_sessions:
        # Check if title matches (case-insensitive, with smart parsing)
        if session.title:
            title_lower = session.title.lower()
            # Remove "telegram" prefix, date suffix patterns, and normalize
            # Title format might be "Telegram @username (Jan 02)"
            title_normalized = title_lower.replace("telegram", "").strip().lstrip('@').strip()
            # Remove date suffix like "(jan 02)" or "(2026-01-02)"
            title_normalized = re.sub(r'\s*\([^)]*\)\s*$', '', title_normalized).strip()
            
            # Check various matching strategies:
            # 1. Direct substring match (identifier in title or vice versa)
            if identifier_normalized in title_normalized or title_normalized in identifier_normalized:
                chat_id = _extract_chat_id_from_session_id(session.session_id)
                return chat_id
            
            # 2. Word-based matching (check if identifier matches any word in title)
            title_words = title_normalized.split()
            if identifier_normalized in title_words:
                chat_id = _extract_chat_id_from_session_id(session.session_id)
                return chat_id
            
            # 3. Check if identifier starts with title or vice versa (for partial matches)
            if title_normalized.startswith(identifier_normalized) or identifier_normalized.startswith(title_normalized):
                chat_id = _extract_chat_id_from_session_id(session.session_id)
                return chat_id
        
        # 4. Also check session ID itself (in case identifier is the chat_id)
        chat_id = _extract_chat_id_from_session_id(session.session_id)
        if chat_id and (identifier_normalized == chat_id or identifier_normalized == chat_id.lower()):
            return chat_id
    
    return None

