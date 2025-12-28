"""
RAG API Views - Endpoints for managing the RAG store.

Provides endpoints for:
- GET /api/v1/rag/stats - Get RAG store statistics
- POST /api/v1/rag/reindex - Trigger full reindex of all conversations
- POST /api/v1/rag/search - Search for relevant conversations
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid startup errors if chromadb not installed
_rag_store = None


def _get_rag_store():
    """Lazy load RAG store."""
    global _rag_store
    if _rag_store is None:
        try:
            from ares_mind.rag import rag_store
            _rag_store = rag_store
        except ImportError as e:
            logger.warning(f"RAG store not available: {e}")
            _rag_store = False
    return _rag_store if _rag_store else None


@require_http_methods(["GET"])
@csrf_exempt
def rag_stats(request):
    """
    GET: Get RAG store statistics.
    
    Returns:
        - collection_name: Name of the ChromaDB collection
        - document_count: Number of indexed documents
        - persist_path: Path to ChromaDB storage
        - embedding_backend: Which embedding backend is being used
    """
    rag_store = _get_rag_store()
    if not rag_store:
        return JsonResponse({
            "error": "RAG store not available. ChromaDB may not be installed.",
            "available": False,
        }, status=503)
    
    try:
        stats = rag_store.get_stats()
        stats["available"] = True
        return JsonResponse(stats)
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return JsonResponse({
            "error": str(e),
            "available": False,
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def rag_reindex(request):
    """
    POST: Trigger full reindex of all conversation messages.
    
    This operation:
    1. Clears the existing collection
    2. Fetches all ConversationMessage records from Django DB
    3. Generates embeddings and indexes each message
    
    Optional body parameters:
    - batch_size: Number of messages to process at once (default: 100)
    
    Returns:
        - total: Total messages in database
        - indexed: Successfully indexed messages
        - failed: Failed to index messages
    """
    rag_store = _get_rag_store()
    if not rag_store:
        return JsonResponse({
            "error": "RAG store not available. ChromaDB may not be installed.",
        }, status=503)
    
    try:
        # Parse optional parameters
        batch_size = 100
        if request.body:
            try:
                data = json.loads(request.body)
                batch_size = data.get("batch_size", 100)
            except json.JSONDecodeError:
                pass
        
        result = rag_store.reindex_all(batch_size=batch_size)
        
        if "error" in result:
            return JsonResponse(result, status=500)
        
        return JsonResponse({
            "success": True,
            "message": f"Reindex complete: {result['indexed']} messages indexed",
            **result,
        })
    except Exception as e:
        logger.error(f"Error during reindex: {e}")
        return JsonResponse({
            "error": str(e),
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def rag_search(request):
    """
    POST: Search for relevant conversations.
    
    Body parameters:
    - query: Search query text (required)
    - n_results: Maximum number of results (default: 5)
    - user_id: Filter by user ID (optional)
    - exclude_session_id: Exclude messages from this session (optional)
    
    Returns:
        - results: List of matching documents with content, metadata, and distance
        - count: Number of results returned
    """
    rag_store = _get_rag_store()
    if not rag_store:
        return JsonResponse({
            "error": "RAG store not available. ChromaDB may not be installed.",
        }, status=503)
    
    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        
        if not query:
            return JsonResponse({
                "error": "Query is required",
            }, status=400)
        
        n_results = data.get("n_results", 5)
        user_id = data.get("user_id")
        exclude_session_id = data.get("exclude_session_id")
        
        results = rag_store.search(
            query=query,
            n_results=n_results,
            user_id=user_id,
            exclude_session_id=exclude_session_id,
        )
        
        return JsonResponse({
            "results": results,
            "count": len(results),
            "query": query,
        })
    except json.JSONDecodeError:
        return JsonResponse({
            "error": "Invalid JSON body",
        }, status=400)
    except Exception as e:
        logger.error(f"Error during RAG search: {e}")
        return JsonResponse({
            "error": str(e),
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def rag_clear(request):
    """
    POST: Clear all indexed documents from the RAG store.
    
    This is a destructive operation - use with caution.
    
    Returns:
        - success: Whether the clear operation succeeded
    """
    rag_store = _get_rag_store()
    if not rag_store:
        return JsonResponse({
            "error": "RAG store not available. ChromaDB may not be installed.",
        }, status=503)
    
    try:
        success = rag_store.clear()
        
        if success:
            return JsonResponse({
                "success": True,
                "message": "RAG store cleared successfully",
            })
        else:
            return JsonResponse({
                "success": False,
                "error": "Failed to clear RAG store",
            }, status=500)
    except Exception as e:
        logger.error(f"Error clearing RAG store: {e}")
        return JsonResponse({
            "error": str(e),
        }, status=500)

