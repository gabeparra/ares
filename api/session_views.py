from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Max
import json

from .models import ChatSession, ConversationMessage
from .utils import _ensure_session


@require_http_methods(["GET"])
def sessions_list(request):
    """
    List conversation sessions.
    """
    try:
        limit = int(request.GET.get("limit", 200))
    except Exception:
        limit = 200

    qs = (
        ChatSession.objects.annotate(last_message_at=Max("messages__created_at"))
        .order_by("-pinned", "-updated_at")
    )[:limit]

    sessions = []
    for s in qs:
        sessions.append(
            {
                "session_id": s.session_id,
                "title": s.title,
                "pinned": bool(s.pinned),
                "model": s.model,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "last_message_at": (s.last_message_at.isoformat() if s.last_message_at else None),
            }
        )

    return JsonResponse({"sessions": sessions})


@require_http_methods(["GET", "PATCH", "DELETE"])
def session_detail(request, session_id):
    """
    Get, update, or delete a session.
    """
    if request.method == 'GET':
        session = ChatSession.objects.filter(session_id=session_id).first()
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)
        return JsonResponse(
            {
                "session_id": session.session_id,
                "title": session.title,
                "pinned": bool(session.pinned),
                "model": session.model,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
        )
    
    elif request.method == 'PATCH':
        try:
            data = json.loads(request.body or b"{}")
        except Exception:
            data = {}

        session = _ensure_session(session_id)

        if "title" in data:
            title = data.get("title")
            session.title = (str(title).strip() if title is not None else None) or None
        if "pinned" in data:
            session.pinned = bool(data.get("pinned"))
        if "model" in data:
            model = data.get("model")
            session.model = (str(model).strip() if model is not None else None) or None

        session.save(update_fields=["title", "pinned", "model", "updated_at"])
        return JsonResponse({"success": True})
    
    elif request.method == 'DELETE':
        ChatSession.objects.filter(session_id=session_id).delete()
        return JsonResponse({"success": True})


@require_http_methods(["GET"])
def conversations_list(request):
    """
    List conversations for a session.
    """
    session_id = request.GET.get('session_id')
    limit = int(request.GET.get('limit', 50))
    
    if not session_id:
        # Optional: return most recent messages across all sessions.
        msgs = list(ConversationMessage.objects.order_by("-created_at")[:limit])
        msgs.reverse()
    else:
        msgs = list(
            ConversationMessage.objects.filter(session__session_id=session_id).order_by("-created_at")[:limit]
        )
        msgs.reverse()

    conversations = []
    for m in msgs:
        conversations.append(
            {
                "session_id": m.session.session_id,
                "role": m.role,
                "message": m.message,
                "created_at": m.created_at.isoformat(),
            }
        )

    return JsonResponse({"conversations": conversations})

