"""
API views for memory extraction from conversations.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Avg
from django.utils import timezone
import json
import threading
import logging

from .models import MemorySpot, ChatSession, AICapability
from ares_mind.memory_extraction import (
    extract_memories_from_conversation,
    apply_memory_spot,
    auto_apply_high_confidence_memories,
    revise_memories,
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def extract_memories(request):
    """
    POST: Extract memories from a conversation session.
    
    Body:
    {
        "session_id": "session_123",
        "user_id": "default",
        "max_messages": 50
    }
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")
        user_id = data.get("user_id", "default")
        max_messages = data.get("max_messages", 50)
        
        if not session_id:
            return JsonResponse({
                "error": "session_id is required"
            }, status=400)
        
        count, errors = extract_memories_from_conversation(
            session_id=session_id,
            user_id=user_id,
            max_messages=max_messages,
        )
        
        return JsonResponse({
            "success": True,
            "extracted_count": count,
            "errors": errors,
            "session_id": session_id,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def memory_spots_list(request):
    """
    GET: List memory spots.
    
    Query params:
    - session_id: Filter by session
    - user_id: Filter by user
    - memory_type: Filter by type
    - status: Filter by status
    - limit: Limit results
    """
    try:
        session_id = request.GET.get("session_id")
        user_id = request.GET.get("user_id")
        memory_type = request.GET.get("memory_type")
        status = request.GET.get("status")
        limit = int(request.GET.get("limit", 50))
        
        queryset = MemorySpot.objects.all()
        
        if session_id:
            queryset = queryset.filter(session__session_id=session_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)
        if status:
            queryset = queryset.filter(status=status)
        
        spots = list(queryset.order_by("-extracted_at")[:limit].values(
            "id", "session__session_id", "user_id", "memory_type", "content",
            "metadata", "confidence", "importance", "status",
            "source_conversation", "extracted_at", "reviewed_at", "applied_at"
        ))
        
        # Convert datetime objects and rename session__session_id to session_id
        for spot in spots:
            # Rename session__session_id to session_id for frontend compatibility
            if "session__session_id" in spot:
                spot["session_id"] = spot.pop("session__session_id")
            for key in ["extracted_at", "reviewed_at", "applied_at"]:
                if spot.get(key):
                    spot[key] = spot[key].isoformat()
        
        return JsonResponse({
            "memory_spots": spots,
            "count": len(spots),
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def memory_spot_detail(request, spot_id):
    """
    GET: Get details of a specific memory spot.
    """
    try:
        spot = MemorySpot.objects.get(id=spot_id)
        
        return JsonResponse({
            "id": spot.id,
            "session_id": spot.session.session_id if spot.session else None,
            "user_id": spot.user_id,
            "memory_type": spot.memory_type,
            "content": spot.content,
            "metadata": spot.metadata,
            "confidence": spot.confidence,
            "importance": spot.importance,
            "status": spot.status,
            "source_conversation": spot.source_conversation,
            "extracted_at": spot.extracted_at.isoformat(),
            "reviewed_at": spot.reviewed_at.isoformat() if spot.reviewed_at else None,
            "applied_at": spot.applied_at.isoformat() if spot.applied_at else None,
        })
        
    except MemorySpot.DoesNotExist:
        return JsonResponse({"error": "Memory spot not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def memory_spot_apply(request, spot_id):
    """
    POST: Apply a memory spot to the memory system.
    """
    try:
        success, message = apply_memory_spot(spot_id)
        
        if success:
            return JsonResponse({
                "success": True,
                "message": message,
            })
        else:
            return JsonResponse({
                "success": False,
                "error": message,
            }, status=400)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def memory_spot_reject(request, spot_id):
    """
    POST: Reject a memory spot (mark as rejected).
    """
    try:
        spot = MemorySpot.objects.get(id=spot_id)
        spot.status = MemorySpot.STATUS_REJECTED
        spot.reviewed_at = timezone.now()
        spot.save()
        
        return JsonResponse({
            "success": True,
            "message": "Memory spot rejected",
        })
        
    except MemorySpot.DoesNotExist:
        return JsonResponse({"error": "Memory spot not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _extract_memories_background(session_ids, user_id):
    """
    Process memory extraction in background thread.
    This avoids HTTP timeouts for long-running operations.
    """
    try:
        results = []
        total_extracted = 0
        
        for session_id in session_ids:
            try:
                count, errors = extract_memories_from_conversation(
                    session_id=session_id,
                    user_id=user_id,
                )
                results.append({
                    "session_id": session_id,
                    "extracted_count": count,
                    "errors": errors,
                })
                total_extracted += count
                logger.info(f"Extracted {count} memories from session {session_id}")
            except Exception as e:
                logger.error(f"Error extracting from session {session_id}: {str(e)}")
                results.append({
                    "session_id": session_id,
                    "extracted_count": 0,
                    "errors": [str(e)],
                })
        
        logger.info(f"Background extraction complete: {total_extracted} memories from {len(results)} sessions")
    except Exception as e:
        logger.error(f"Error in background extraction: {str(e)}", exc_info=True)


@csrf_exempt
@require_http_methods(["POST"])
def extract_all_conversations(request):
    """
    POST: Extract memories from all conversations (or a batch).
    
    This endpoint returns immediately and processes extraction in the background
    to avoid HTTP timeouts.
    
    Body:
    {
        "user_id": "default",
        "limit": 50,  # Number of sessions to process
        "min_messages": 5,  # Minimum messages in session
        "reprocess": false  # If true, re-process sessions with "extracted" status only
    }
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id", "default")
        limit = data.get("limit", 50)
        min_messages = data.get("min_messages", 5)
        reprocess = data.get("reprocess", False)
        
        # Always exclude sessions that have been reviewed, applied, or rejected
        # These are final states and should never be reprocessed
        final_status_sessions = set(
            MemorySpot.objects.exclude(session__isnull=True)
            .filter(status__in=[
                MemorySpot.STATUS_REVIEWED,
                MemorySpot.STATUS_APPLIED,
                MemorySpot.STATUS_REJECTED
            ])
            .values_list("session__session_id", flat=True)
            .distinct()
        )
        
        if reprocess:
            # Re-process sessions that only have "extracted" status
            extracted_only_sessions = set(
                MemorySpot.objects.exclude(session__isnull=True)
                .filter(status=MemorySpot.STATUS_EXTRACTED)
                .values_list("session__session_id", flat=True)
                .distinct()
            )
            
            # Get sessions that have extracted memories but no final status memories
            sessions = ChatSession.objects.exclude(
                session_id__in=final_status_sessions
            ).filter(
                session_id__in=extracted_only_sessions
            ).annotate(
                message_count=Count("messages")
            ).filter(
                message_count__gte=min_messages
            ).order_by("-updated_at")[:limit]
        else:
            # Get sessions that haven't been processed at all OR only have "extracted" status
            # We exclude final status sessions (reviewed/applied/rejected)
            # But we allow sessions with only "extracted" status to be processed again
            
            # Get all sessions with MemorySpots (any status)
            all_processed_sessions = set(
                MemorySpot.objects.exclude(session__isnull=True)
                .values_list("session__session_id", flat=True)
                .distinct()
            )
            
            # Get sessions that have "extracted" status but NO final status
            # (these can be re-processed)
            extracted_only_sessions = set(
                MemorySpot.objects.exclude(session__isnull=True)
                .filter(status=MemorySpot.STATUS_EXTRACTED)
                .values_list("session__session_id", flat=True)
                .distinct()
            )
            # Remove any that also have final status
            extracted_only_sessions = extracted_only_sessions - final_status_sessions
            
            # Sessions to process:
            # 1. Have NOT been reviewed/applied/rejected (final_status_sessions) - already excluded
            # 2. Either have NO MemorySpots at all, OR only have "extracted" status
            # Build query: (no MemorySpots) OR (only extracted status)
            sessions = ChatSession.objects.exclude(
                session_id__in=final_status_sessions
            ).annotate(
                message_count=Count("messages")
            ).filter(
                message_count__gte=min_messages
            )
            
            # Filter to only include unprocessed or extracted-only sessions
            if extracted_only_sessions or not all_processed_sessions:
                # Use Q objects to combine conditions
                conditions = Q()
                if extracted_only_sessions:
                    conditions |= Q(session_id__in=extracted_only_sessions)
                if not all_processed_sessions:
                    # Include sessions not in all_processed_sessions
                    conditions |= ~Q(session_id__in=all_processed_sessions)
                sessions = sessions.filter(conditions)
            else:
                # All sessions are processed with final status, return empty
                sessions = sessions.none()
            
            sessions = sessions.order_by("-updated_at")[:limit]
        
        # Get list of session IDs to process
        session_ids = [session.session_id for session in sessions]
        
        if not session_ids:
            # Provide more detailed information about why no sessions were found
            total_sessions = ChatSession.objects.annotate(
                message_count=Count("messages")
            ).filter(message_count__gte=min_messages).count()
            
            logger.info(f"No sessions to process: total={total_sessions}, final_status={len(final_status_sessions)}, limit={limit}, min_messages={min_messages}")
            
            return JsonResponse({
                "success": True,
                "message": f"No sessions found to process. Total sessions with {min_messages}+ messages: {total_sessions}. All may have been processed or reviewed.",
                "processed_sessions": 0,
                "total_extracted": 0,
                "total_sessions": total_sessions,
                "final_status_sessions": len(final_status_sessions),
            })
        
        # Start background processing
        thread = threading.Thread(
            target=_extract_memories_background,
            args=(session_ids, user_id),
            daemon=True
        )
        thread.start()
        
        # Return immediately
        return JsonResponse({
            "success": True,
            "message": f"Started processing {len(session_ids)} sessions in background",
            "sessions_queued": len(session_ids),
            "status": "processing",
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in extract_all_conversations: {str(e)}\n{error_trace}")
        return JsonResponse({
            "error": str(e),
            "error_type": type(e).__name__
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def auto_apply_memories(request):
    """
    POST: Automatically apply high-confidence memory spots.
    
    Body:
    {
        "confidence_threshold": 0.8
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        confidence_threshold = data.get("confidence_threshold", 0.8)
        
        applied_count, errors = auto_apply_high_confidence_memories(confidence_threshold)
        
        return JsonResponse({
            "success": True,
            "applied_count": applied_count,
            "errors": errors,
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def capabilities_list(request):
    """
    GET: List AI capabilities.
    
    Query params:
    - domain: Filter by domain
    - min_proficiency: Minimum proficiency level
    """
    try:
        domain = request.GET.get("domain")
        min_proficiency = int(request.GET.get("min_proficiency", 1))
        
        queryset = AICapability.objects.filter(proficiency_level__gte=min_proficiency)
        
        if domain:
            queryset = queryset.filter(domain=domain)
        
        capabilities = list(queryset.values(
            "id", "capability_name", "domain", "description",
            "proficiency_level", "evidence", "last_demonstrated",
            "improvement_notes", "created_at", "updated_at"
        ))
        
        # Convert datetime objects
        for cap in capabilities:
            for key in ["last_demonstrated", "created_at", "updated_at"]:
                if cap.get(key):
                    cap[key] = cap[key].isoformat()
        
        return JsonResponse({
            "capabilities": capabilities,
            "count": len(capabilities),
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def memory_extraction_stats(request):
    """
    GET: Get statistics about memory extraction.
    """
    try:
        from .models import MemorySpot
        
        total_spots = MemorySpot.objects.count()
        by_type = {}
        by_status = {}
        
        for mem_type, _ in MemorySpot.TYPE_CHOICES:
            by_type[mem_type] = MemorySpot.objects.filter(memory_type=mem_type).count()
        
        for status, _ in MemorySpot.STATUS_CHOICES:
            by_status[status] = MemorySpot.objects.filter(status=status).count()
        
        # Get average confidence
        avg_confidence = MemorySpot.objects.aggregate(
            avg_confidence=Avg("confidence")
        )["avg_confidence"] or 0.0
        
        return JsonResponse({
            "total_memory_spots": total_spots,
            "by_type": by_type,
            "by_status": by_status,
            "average_confidence": round(avg_confidence, 2),
            "capabilities_count": AICapability.objects.count(),
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def revise_memories_endpoint(request):
    """
    POST: Revise memories from conversations (re-analyze to see what changed).
    
    This runs the memory revision process which compares existing memories
    with new extractions to show what stayed, what changed, and what's new.
    
    Body:
    {
        "limit": 20,  # Number of sessions to process
        "days_back": null  # How many days back to look (null = all)
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        limit = data.get("limit", 20)
        days_back = data.get("days_back")
        
        # Run revision process
        stats = revise_memories(limit=limit, days_back=days_back)
        
        if "error" in stats:
            return JsonResponse({
                "success": False,
                "error": stats["error"],
            }, status=500)
        
        return JsonResponse({
            "success": True,
            "stats": stats,
            "message": f"Revised {stats.get('sessions_processed', 0)} sessions, extracted {stats.get('total_extracted', 0)} memories",
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        import traceback
        logger.error(f"Error in revise_memories_endpoint: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({"error": str(e)}, status=500)

