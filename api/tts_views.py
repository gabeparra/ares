"""
Text-to-Speech API views using ElevenLabs.

Provides endpoints for:
- POST /api/v1/tts - Convert text to speech and return audio
- GET /api/v1/tts/voices - List available voices
- GET /api/v1/tts/config - Get TTS configuration
- POST /api/v1/tts/config - Update TTS configuration
"""

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import httpx
import os

# ElevenLabs API configuration
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"

def get_elevenlabs_api_key():
    """Get the ElevenLabs API key from environment."""
    return os.environ.get("ELEVENLABS_API_KEY", "")


def get_default_voice_id():
    """Get the default voice ID from environment or use a default."""
    # Default to "Rachel" voice if not specified
    return os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


def get_default_model_id():
    """Get the default model ID. Using v2 for better style support."""
    return os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")


@csrf_exempt
@require_http_methods(["POST"])
def text_to_speech(request):
    """
    POST: Convert text to speech using ElevenLabs.
    
    Request body:
    {
        "text": "Text to convert to speech",
        "voice_id": "optional voice ID",
        "model_id": "optional model ID",
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": true
    }
    
    Returns: audio/mpeg stream
    """
    api_key = get_elevenlabs_api_key()
    
    if not api_key:
        return JsonResponse({
            "error": "ElevenLabs API key not configured. Set ELEVENLABS_API_KEY environment variable."
        }, status=503)
    
    try:
        data = json.loads(request.body)
        text = data.get("text", "")
        
        if not text:
            return JsonResponse({
                "error": "Missing 'text' field"
            }, status=400)
        
        # Get voice and model settings
        voice_id = data.get("voice_id", get_default_voice_id())
        model_id = data.get("model_id", get_default_model_id())
        
        # Voice settings with defaults
        voice_settings = {
            "stability": data.get("stability", 0.5),
            "similarity_boost": data.get("similarity_boost", 0.75),
            "style": data.get("style", 0.0),
            "use_speaker_boost": data.get("use_speaker_boost", True),
        }
        
        # Log the settings being used
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"TTS Request - model: {model_id}, voice_id: {voice_id}, voice_settings: {voice_settings}")
        print(f"[TTS] model: {model_id}, voice_id: {voice_id}, settings: {voice_settings}")
        
        # Make request to ElevenLabs
        url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings,
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                # Return audio as response
                audio_response = HttpResponse(
                    response.content,
                    content_type="audio/mpeg"
                )
                audio_response["Content-Disposition"] = "inline"
                return audio_response
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", {}).get("message", str(error_data))
                except Exception:
                    error_msg = response.text
                
                return JsonResponse({
                    "error": f"ElevenLabs API error: {error_msg}"
                }, status=response.status_code)
                
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except httpx.ConnectError:
        return JsonResponse({
            "error": "Cannot connect to ElevenLabs API"
        }, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def list_voices(request):
    """
    GET: List available voices from ElevenLabs.
    """
    api_key = get_elevenlabs_api_key()
    
    if not api_key:
        return JsonResponse({
            "error": "ElevenLabs API key not configured",
            "voices": []
        }, status=503)
    
    try:
        url = f"{ELEVENLABS_API_URL}/voices"
        
        headers = {
            "xi-api-key": api_key,
            "Accept": "application/json",
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                voices = data.get("voices", [])
                
                # Format voices for frontend
                formatted_voices = [
                    {
                        "voice_id": v.get("voice_id"),
                        "name": v.get("name"),
                        "category": v.get("category", "custom"),
                        "labels": v.get("labels", {}),
                        "preview_url": v.get("preview_url"),
                    }
                    for v in voices
                ]
                
                return JsonResponse({
                    "voices": formatted_voices,
                    "default_voice_id": get_default_voice_id(),
                })
            else:
                return JsonResponse({
                    "error": f"Failed to fetch voices: {response.text}",
                    "voices": []
                }, status=response.status_code)
                
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "voices": []
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def tts_config(request):
    """
    GET: Get current TTS configuration.
    POST: Update TTS configuration.
    """
    from .models import AppSetting
    from .utils import _get_setting, _set_setting
    
    if request.method == "GET":
        return JsonResponse({
            "enabled": _get_setting("tts_enabled", "false") == "true",
            "voice_id": _get_setting("tts_voice_id", get_default_voice_id()),
            "model_id": _get_setting("tts_model_id", get_default_model_id()),
            "stability": float(_get_setting("tts_stability", "0.5")),
            "similarity_boost": float(_get_setting("tts_similarity_boost", "0.75")),
            "style": float(_get_setting("tts_style", "0.0")),
            "auto_play": _get_setting("tts_auto_play", "false") == "true",
            "api_configured": bool(get_elevenlabs_api_key()),
        })
    
    # POST: Update configuration
    try:
        data = json.loads(request.body)
        
        if "enabled" in data:
            _set_setting("tts_enabled", "true" if data["enabled"] else "false")
        if "voice_id" in data:
            _set_setting("tts_voice_id", data["voice_id"])
        if "model_id" in data:
            _set_setting("tts_model_id", data["model_id"])
        if "stability" in data:
            _set_setting("tts_stability", str(data["stability"]))
        if "similarity_boost" in data:
            _set_setting("tts_similarity_boost", str(data["similarity_boost"]))
        if "style" in data:
            _set_setting("tts_style", str(data["style"]))
        if "auto_play" in data:
            _set_setting("tts_auto_play", "true" if data["auto_play"] else "false")
        
        return JsonResponse({
            "success": True,
            "message": "TTS configuration updated"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

