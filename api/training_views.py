"""Training data export API endpoints."""

import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import ChatSession, ConversationMessage


@csrf_exempt
@require_http_methods(["GET"])
def export_training_data(request):
    """
    Export conversation data for fine-tuning.
    
    Query params:
        format: 'jsonl' (default), 'json', 'openai'
        session_id: Optional specific session to export
        min_turns: Minimum conversation turns to include (default: 2)
        include_system: Include system messages (default: false)
        include_errors: Include error messages (default: false)
    
    Returns conversation data in the requested format.
    """
    export_format = request.GET.get('format', 'jsonl')
    session_id = request.GET.get('session_id')
    min_turns = int(request.GET.get('min_turns', 2))
    include_system = request.GET.get('include_system', 'false').lower() == 'true'
    include_errors = request.GET.get('include_errors', 'false').lower() == 'true'
    
    # Build role filter
    allowed_roles = ['user', 'assistant']
    if include_system:
        allowed_roles.append('system')
    if include_errors:
        allowed_roles.append('error')
    
    # Get sessions
    if session_id:
        sessions = ChatSession.objects.filter(session_id=session_id)
    else:
        sessions = ChatSession.objects.all().order_by('created_at')
    
    conversations = []
    for session in sessions.prefetch_related('messages'):
        messages = list(
            session.messages.filter(role__in=allowed_roles)
            .order_by('created_at')
            .values('role', 'message', 'created_at')
        )
        
        # Filter by minimum turns (user+assistant pairs)
        user_count = sum(1 for m in messages if m['role'] == 'user')
        assistant_count = sum(1 for m in messages if m['role'] == 'assistant')
        
        if min(user_count, assistant_count) < min_turns // 2:
            continue
        
        conv_messages = []
        for msg in messages:
            conv_messages.append({
                'role': msg['role'],
                'content': msg['message']
            })
        
        if conv_messages:
            conversations.append({
                'session_id': session.session_id,
                'title': session.title,
                'model': session.model,
                'created_at': session.created_at.isoformat(),
                'messages': conv_messages
            })
    
    if export_format == 'json':
        return JsonResponse({'conversations': conversations, 'count': len(conversations)})
    
    elif export_format == 'openai':
        # OpenAI fine-tuning format: {"messages": [...]}
        openai_data = []
        for conv in conversations:
            openai_data.append({'messages': conv['messages']})
        
        response = HttpResponse(
            '\n'.join(json.dumps(item) for item in openai_data),
            content_type='application/jsonl'
        )
        response['Content-Disposition'] = 'attachment; filename="training_data_openai.jsonl"'
        return response
    
    else:  # jsonl (default)
        response = HttpResponse(
            '\n'.join(json.dumps(conv) for conv in conversations),
            content_type='application/jsonl'
        )
        response['Content-Disposition'] = 'attachment; filename="training_data.jsonl"'
        return response


@csrf_exempt
@require_http_methods(["GET"])
def export_stats(request):
    """
    Get statistics about stored conversation data.
    
    Returns counts and metadata about available training data.
    """
    total_sessions = ChatSession.objects.count()
    total_messages = ConversationMessage.objects.count()
    
    # Role breakdown
    role_counts = {}
    for role in ['user', 'assistant', 'system', 'error']:
        role_counts[role] = ConversationMessage.objects.filter(role=role).count()
    
    # Sessions with sufficient data (at least 2 user + 2 assistant messages)
    from django.db.models import Count, Q
    sessions_with_data = ChatSession.objects.annotate(
        user_count=Count('messages', filter=Q(messages__role='user')),
        assistant_count=Count('messages', filter=Q(messages__role='assistant'))
    ).filter(user_count__gte=1, assistant_count__gte=1).count()
    
    # Models used
    models_used = list(
        ChatSession.objects.exclude(model__isnull=True)
        .exclude(model='')
        .values_list('model', flat=True)
        .distinct()
    )
    
    return JsonResponse({
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'sessions_with_training_data': sessions_with_data,
        'role_counts': role_counts,
        'models_used': models_used
    })


@csrf_exempt
@require_http_methods(["GET"])
def export_raw_messages(request):
    """
    Export raw messages with full metadata.
    
    Query params:
        session_id: Optional specific session
        limit: Maximum messages (default: 10000)
        offset: Pagination offset (default: 0)
    
    Returns raw message data with all fields.
    """
    session_id = request.GET.get('session_id')
    limit = min(int(request.GET.get('limit', 10000)), 50000)
    offset = int(request.GET.get('offset', 0))
    
    queryset = ConversationMessage.objects.select_related('session').order_by('created_at')
    
    if session_id:
        queryset = queryset.filter(session__session_id=session_id)
    
    total = queryset.count()
    messages = list(queryset[offset:offset + limit])
    
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'session_id': msg.session.session_id,
            'session_title': msg.session.title,
            'role': msg.role,
            'message': msg.message,
            'created_at': msg.created_at.isoformat()
        })
    
    return JsonResponse({
        'messages': data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total
    })

