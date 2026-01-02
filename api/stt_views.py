"""
Speech-to-Text API views using OpenAI Whisper.

Provides endpoints for:
- POST /api/v1/stt - Convert speech to text using Whisper
- GET /api/v1/stt/config - Get STT configuration
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# OpenAI API configuration
OPENAI_API_URL = "https://api.openai.com/v1/audio/transcriptions"


def get_openai_api_key():
    """Get the OpenAI API key from environment."""
    return os.environ.get("OPENAI_API_KEY", "")


@csrf_exempt
@require_http_methods(["POST"])
def speech_to_text(request):
    """
    POST: Convert speech to text using OpenAI Whisper.
    
    Request: multipart/form-data with 'audio' file
    Optional form fields:
    - language: ISO-639-1 code (e.g., 'en', 'es') - if not provided, Whisper auto-detects
    - prompt: Optional text to guide the transcription style
    
    Returns: JSON with transcription
    {
        "text": "Transcribed text here",
        "language": "en"  # detected or specified language
    }
    """
    import httpx
    
    api_key = get_openai_api_key()
    
    if not api_key:
        return JsonResponse({
            "error": "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        }, status=503)
    
    try:
        # Get audio file from request
        audio_file = request.FILES.get('audio')
        
        if not audio_file:
            return JsonResponse({
                "error": "Missing 'audio' file in request"
            }, status=400)
        
        # Get optional parameters
        language = request.POST.get('language', '')  # Empty = auto-detect
        prompt = request.POST.get('prompt', '')  # Empty by default - prompt can leak into transcriptions
        
        # Read audio data
        audio_data = audio_file.read()
        
        if len(audio_data) == 0:
            return JsonResponse({
                "error": "Empty audio file"
            }, status=400)
        
        # Determine file extension from content type
        content_type = audio_file.content_type or 'audio/webm'
        ext_map = {
            'audio/webm': '.webm',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/mp3': '.mp3',
            'audio/mpeg': '.mp3',
            'audio/mp4': '.mp4',
            'audio/m4a': '.m4a',
            'audio/ogg': '.ogg',
            'audio/flac': '.flac',
        }
        ext = ext_map.get(content_type, '.webm')
        
        logger.info(f"STT Request - size: {len(audio_data)} bytes, type: {content_type}, language: {language or 'auto'}")
        
        # Create temp file for the audio
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # Prepare request to Whisper API
            headers = {
                "Authorization": f"Bearer {api_key}",
            }
            
            # Build form data
            form_data = {
                "model": "whisper-1",
                "response_format": "verbose_json",  # Get language detection info
            }
            
            if language:
                form_data["language"] = language
            
            if prompt:
                form_data["prompt"] = prompt
            
            # Make request to OpenAI
            with httpx.Client(timeout=60.0) as client:
                with open(temp_path, 'rb') as f:
                    files = {"file": (f"audio{ext}", f, content_type)}
                    response = client.post(
                        OPENAI_API_URL,
                        headers=headers,
                        data=form_data,
                        files=files
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "text": data.get("text", ""),
                        "language": data.get("language", language or "unknown"),
                    }
                    
                    # Include segments if available (for debugging/timing)
                    if "segments" in data:
                        result["duration"] = data.get("duration", 0)
                    
                    logger.info(f"STT Success - language: {result['language']}, text length: {len(result['text'])}")
                    
                    return JsonResponse(result)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", str(error_data))
                    except Exception:
                        error_msg = response.text
                    
                    logger.error(f"Whisper API error: {error_msg}")
                    
                    return JsonResponse({
                        "error": f"Whisper API error: {error_msg}"
                    }, status=response.status_code)
                    
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
                
    except Exception as e:
        logger.exception(f"STT error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def stt_config(request):
    """
    GET: Get STT configuration and status.
    """
    return JsonResponse({
        "api_configured": bool(get_openai_api_key()),
        "model": "whisper-1",
        "supported_formats": ["webm", "wav", "mp3", "mp4", "m4a", "ogg", "flac"],
        "max_file_size_mb": 25,  # Whisper API limit
        "features": {
            "auto_language_detection": True,
            "multilingual": True,
            "supported_languages": ["en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja", "ko", "ar", "hi", "and 90+ more"],
        }
    })

