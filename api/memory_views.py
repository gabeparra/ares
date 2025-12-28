"""
API views for ARES self-memory management.

Provides endpoints for:
- GET /api/v1/self-memory - List all self-memories (optionally filter by category)
- POST /api/v1/self-memory - Add/update a self-memory entry
- DELETE /api/v1/self-memory/<id> - Remove a self-memory entry
- POST /api/v1/self-memory/milestone - Record a milestone event
- GET /api/v1/self-memory/context - Get formatted context string for LLM injection
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from .models import AISelfMemory


def get_self_memory_context():
    """
    Build a formatted context string from self-memories for LLM injection.
    Groups memories by category and formats them for the system prompt.
    """
    memories = AISelfMemory.objects.all().order_by("-importance", "category", "memory_key")
    
    if not memories.exists():
        return ""
    
    # Group by category
    grouped = {}
    for mem in memories:
        if mem.category not in grouped:
            grouped[mem.category] = []
        grouped[mem.category].append(mem)
    
    # Build formatted string
    lines = ["## My Self-Knowledge\n"]
    
    # Order categories by importance
    category_order = ["identity", "milestone", "relationship", "observation", "preference"]
    
    for category in category_order:
        if category not in grouped:
            continue
        
        lines.append(f"### {category.title()}")
        for mem in grouped[category]:
            if category == "milestone":
                # Format milestones with timestamps
                lines.append(f"- [{mem.created_at.strftime('%B %d, %Y')}] {mem.memory_key}: {mem.memory_value}")
            else:
                lines.append(f"- {mem.memory_key}: {mem.memory_value}")
        lines.append("")
    
    return "\n".join(lines)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def self_memory(request):
    """
    GET: List all self-memories, optionally filtered by category.
    POST: Add or update a self-memory entry.
    """
    if request.method == "GET":
        category = request.GET.get("category")
        
        queryset = AISelfMemory.objects.all()
        if category:
            queryset = queryset.filter(category=category)
        
        memories = list(queryset.values(
            "id", "category", "memory_key", "memory_value",
            "importance", "created_at", "updated_at"
        ))
        
        # Convert datetime objects to ISO format strings
        for mem in memories:
            mem["created_at"] = mem["created_at"].isoformat() if mem["created_at"] else None
            mem["updated_at"] = mem["updated_at"].isoformat() if mem["updated_at"] else None
        
        return JsonResponse({
            "memories": memories,
            "formatted_context": get_self_memory_context(),
            "count": len(memories),
        })
    
    # POST: Add/update memory
    try:
        data = json.loads(request.body)
        category = data.get("category")
        key = data.get("key")
        value = data.get("value")
        importance = data.get("importance", 5)
        
        if not category or not key or not value:
            return JsonResponse({
                "error": "Missing required fields: category, key, value"
            }, status=400)
        
        # Validate category
        valid_categories = [c[0] for c in AISelfMemory.CATEGORY_CHOICES]
        if category not in valid_categories:
            return JsonResponse({
                "error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            }, status=400)
        
        # Validate importance
        if not isinstance(importance, int) or importance < 1 or importance > 10:
            return JsonResponse({
                "error": "Importance must be an integer between 1 and 10"
            }, status=400)
        
        # Create or update
        memory, created = AISelfMemory.objects.update_or_create(
            category=category,
            memory_key=key,
            defaults={
                "memory_value": value,
                "importance": importance,
            }
        )
        
        return JsonResponse({
            "success": True,
            "created": created,
            "memory": {
                "id": memory.id,
                "category": memory.category,
                "key": memory.memory_key,
                "value": memory.memory_value,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat(),
            }
        }, status=201 if created else 200)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def self_memory_delete(request, memory_id):
    """
    DELETE: Remove a self-memory entry by ID.
    """
    try:
        memory = AISelfMemory.objects.get(id=memory_id)
        memory_data = {
            "id": memory.id,
            "category": memory.category,
            "key": memory.memory_key,
        }
        memory.delete()
        
        return JsonResponse({
            "success": True,
            "deleted": memory_data,
        })
        
    except AISelfMemory.DoesNotExist:
        return JsonResponse({"error": "Memory not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def self_memory_milestone(request):
    """
    POST: Record a milestone event with automatic timestamp.
    
    Query params or JSON body:
    - event: The milestone key (e.g., "first_tool_use")
    - description: The milestone description
    - importance: Optional importance (1-10, default 7)
    """
    try:
        # Accept both query params and JSON body
        if request.content_type == "application/json":
            data = json.loads(request.body)
            event = data.get("event")
            description = data.get("description")
            importance = data.get("importance", 7)
        else:
            event = request.GET.get("event") or request.POST.get("event")
            description = request.GET.get("description") or request.POST.get("description")
            importance = int(request.GET.get("importance", 7) or request.POST.get("importance", 7))
        
        if not event or not description:
            return JsonResponse({
                "error": "Missing required fields: event, description"
            }, status=400)
        
        # Add timestamp to description
        timestamp = timezone.now().strftime("%B %d, %Y %H:%M")
        timestamped_description = f"[{timestamp}] {description}"
        
        memory, created = AISelfMemory.objects.update_or_create(
            category=AISelfMemory.CATEGORY_MILESTONE,
            memory_key=event,
            defaults={
                "memory_value": timestamped_description,
                "importance": importance,
            }
        )
        
        return JsonResponse({
            "success": True,
            "created": created,
            "milestone": {
                "id": memory.id,
                "event": memory.memory_key,
                "description": memory.memory_value,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat(),
            }
        }, status=201 if created else 200)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def self_memory_context(request):
    """
    GET: Get the formatted self-memory context string for LLM injection.
    """
    context = get_self_memory_context()
    return JsonResponse({
        "context": context,
        "has_memories": bool(context),
    })

