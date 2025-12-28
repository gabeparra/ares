"""
API views for user memory management.

Provides endpoints for:
- GET /api/v1/user-memory - List user facts and preferences
- POST /api/v1/user-memory/fact - Add/update a user fact
- DELETE /api/v1/user-memory/fact/<id> - Remove a user fact
- POST /api/v1/user-memory/preference - Add/update a preference
- DELETE /api/v1/user-memory/preference/<id> - Remove a preference
- GET /api/v1/user-memory/context - Get formatted context for LLM
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import UserFact, UserPreference, ConversationSummary


def get_user_memory_context(user_id: str = "default") -> str:
    """
    Build a formatted context string from user memory for LLM injection.
    """
    lines = []
    
    # Get user facts
    facts = UserFact.objects.filter(user_id=user_id).order_by("fact_type", "fact_key")
    if facts.exists():
        lines.append("## User Information\n")
        
        current_type = None
        for fact in facts:
            if fact.fact_type != current_type:
                current_type = fact.fact_type
                lines.append(f"### {current_type.title()}")
            lines.append(f"- {fact.fact_key}: {fact.fact_value}")
        lines.append("")
    
    # Get user preferences
    prefs = UserPreference.objects.filter(user_id=user_id)
    if prefs.exists():
        lines.append("## User Preferences")
        for pref in prefs:
            lines.append(f"- {pref.preference_key}: {pref.preference_value}")
        lines.append("")
    
    return "\n".join(lines)


@csrf_exempt
@require_http_methods(["GET"])
def user_memory(request):
    """
    GET: List all user facts and preferences.
    
    Query params:
    - user_id: User identifier (default: "default")
    - type: Filter facts by type (identity, professional, personal, context)
    """
    user_id = request.GET.get("user_id", "default")
    fact_type = request.GET.get("type")
    
    # Get facts
    facts_qs = UserFact.objects.filter(user_id=user_id)
    if fact_type:
        facts_qs = facts_qs.filter(fact_type=fact_type)
    
    facts = list(facts_qs.values(
        "id", "user_id", "fact_type", "fact_key", "fact_value",
        "source", "confidence", "created_at", "updated_at"
    ))
    
    # Get preferences
    prefs = list(UserPreference.objects.filter(user_id=user_id).values(
        "id", "user_id", "preference_key", "preference_value",
        "created_at", "updated_at"
    ))
    
    # Convert datetime objects
    for item in facts + prefs:
        for key in ["created_at", "updated_at"]:
            if item.get(key):
                item[key] = item[key].isoformat()
    
    return JsonResponse({
        "user_id": user_id,
        "facts": facts,
        "preferences": prefs,
        "formatted_context": get_user_memory_context(user_id),
        "counts": {
            "facts": len(facts),
            "preferences": len(prefs),
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def user_memory_add_fact(request):
    """
    POST: Add or update a user fact.
    
    Body:
    {
        "user_id": "default",
        "type": "identity",
        "key": "name",
        "value": "Gabe",
        "source": "api",
        "confidence": 1.0
    }
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id", "default")
        fact_type = data.get("type")
        key = data.get("key")
        value = data.get("value")
        source = data.get("source", "api")
        confidence = data.get("confidence", 1.0)
        
        if not fact_type or not key or not value:
            return JsonResponse({
                "error": "Missing required fields: type, key, value"
            }, status=400)
        
        # Validate fact_type
        valid_types = [t[0] for t in UserFact.TYPE_CHOICES]
        if fact_type not in valid_types:
            return JsonResponse({
                "error": f"Invalid type. Must be one of: {', '.join(valid_types)}"
            }, status=400)
        
        # Validate source
        valid_sources = [s[0] for s in UserFact.SOURCE_CHOICES]
        if source not in valid_sources:
            return JsonResponse({
                "error": f"Invalid source. Must be one of: {', '.join(valid_sources)}"
            }, status=400)
        
        # Create or update
        fact, created = UserFact.objects.update_or_create(
            user_id=user_id,
            fact_type=fact_type,
            fact_key=key,
            defaults={
                "fact_value": value,
                "source": source,
                "confidence": confidence,
            }
        )
        
        return JsonResponse({
            "success": True,
            "created": created,
            "fact": {
                "id": fact.id,
                "user_id": fact.user_id,
                "type": fact.fact_type,
                "key": fact.fact_key,
                "value": fact.fact_value,
                "source": fact.source,
                "confidence": fact.confidence,
                "created_at": fact.created_at.isoformat(),
                "updated_at": fact.updated_at.isoformat(),
            }
        }, status=201 if created else 200)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def user_memory_delete_fact(request, fact_id):
    """
    DELETE: Remove a user fact by ID.
    """
    try:
        fact = UserFact.objects.get(id=fact_id)
        fact_data = {
            "id": fact.id,
            "user_id": fact.user_id,
            "type": fact.fact_type,
            "key": fact.fact_key,
        }
        fact.delete()
        
        return JsonResponse({
            "success": True,
            "deleted": fact_data,
        })
        
    except UserFact.DoesNotExist:
        return JsonResponse({"error": "Fact not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def user_memory_add_preference(request):
    """
    POST: Add or update a user preference.
    
    Body:
    {
        "user_id": "default",
        "key": "communication_style",
        "value": "technical"
    }
    """
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id", "default")
        key = data.get("key")
        value = data.get("value")
        
        if not key or not value:
            return JsonResponse({
                "error": "Missing required fields: key, value"
            }, status=400)
        
        # Create or update
        pref, created = UserPreference.objects.update_or_create(
            user_id=user_id,
            preference_key=key,
            defaults={
                "preference_value": value,
            }
        )
        
        return JsonResponse({
            "success": True,
            "created": created,
            "preference": {
                "id": pref.id,
                "user_id": pref.user_id,
                "key": pref.preference_key,
                "value": pref.preference_value,
                "created_at": pref.created_at.isoformat(),
                "updated_at": pref.updated_at.isoformat(),
            }
        }, status=201 if created else 200)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def user_memory_delete_preference(request, pref_id):
    """
    DELETE: Remove a user preference by ID.
    """
    try:
        pref = UserPreference.objects.get(id=pref_id)
        pref_data = {
            "id": pref.id,
            "user_id": pref.user_id,
            "key": pref.preference_key,
        }
        pref.delete()
        
        return JsonResponse({
            "success": True,
            "deleted": pref_data,
        })
        
    except UserPreference.DoesNotExist:
        return JsonResponse({"error": "Preference not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def user_memory_context(request):
    """
    GET: Get the formatted user memory context string for LLM injection.
    """
    user_id = request.GET.get("user_id", "default")
    context = get_user_memory_context(user_id)
    
    return JsonResponse({
        "user_id": user_id,
        "context": context,
        "has_memory": bool(context),
    })


@csrf_exempt
@require_http_methods(["GET"])
def memory_stats(request):
    """
    GET: Get memory system statistics.
    """
    from .models import AISelfMemory
    
    # Get counts by category for self-memory
    self_memory_by_category = {}
    for cat, _ in AISelfMemory.CATEGORY_CHOICES:
        self_memory_by_category[cat] = AISelfMemory.objects.filter(category=cat).count()
    
    # Get counts by type for user facts
    user_facts_by_type = {}
    for t, _ in UserFact.TYPE_CHOICES:
        user_facts_by_type[t] = UserFact.objects.filter(fact_type=t).count()
    
    # Get unique user count
    unique_users = UserFact.objects.values("user_id").distinct().count()
    
    return JsonResponse({
        "self_memory": {
            "total": AISelfMemory.objects.count(),
            "by_category": self_memory_by_category,
        },
        "user_facts": {
            "total": UserFact.objects.count(),
            "by_type": user_facts_by_type,
        },
        "user_preferences": {
            "total": UserPreference.objects.count(),
        },
        "conversation_summaries": {
            "total": ConversationSummary.objects.count(),
        },
        "unique_users": unique_users,
    })

