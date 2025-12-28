from django.urls import path
from . import auth_views
from . import chat_views
from . import model_views
from . import session_views
from . import settings_views
from . import telegram_views
from . import system_views
from . import upscale_views
from . import training_views
from . import memory_views
from . import user_memory_views
from . import account_linking_views
from . import ollama_views
from . import tts_views
from . import rag_views
from . import agent_views

app_name = 'api'

urlpatterns = [
    # Authentication endpoints
    path('auth/config', auth_views.auth_config, name='auth_config'),
    path('auth/user', auth_views.user_info, name='user_info'),
    path('auth/verify', auth_views.verify_token_view, name='verify_token'),
    path('auth/check-admin', auth_views.check_admin_role, name='check_admin_role'),
    
    # Account linking endpoints
    path('auth/check-duplicates', account_linking_views.check_duplicate_accounts, name='check_duplicates'),
    path('auth/link-accounts', account_linking_views.link_user_accounts, name='link_accounts'),
    path('auth/my-identities', account_linking_views.my_identities, name='my_identities'),
    
    # Chat endpoints
    path('chat', chat_views.chat, name='chat'),
    
    # Model management endpoints
    path('models', model_views.models_list, name='models'),
    
    # Session and conversation endpoints
    path('sessions', session_views.sessions_list, name='sessions'),
    path('sessions/<str:session_id>', session_views.session_detail, name='session_detail'),
    path('conversations', session_views.conversations_list, name='conversations'),
    
    # Settings endpoints
    path('settings/prompt', settings_views.settings_prompt, name='settings_prompt'),
    path('settings/model-config', settings_views.settings_model_config, name='settings_model_config'),
    path('settings/provider', settings_views.settings_provider, name='settings_provider'),
    path('settings/openrouter-models', settings_views.settings_openrouter_models, name='settings_openrouter_models'),
    path('settings/openrouter-model', settings_views.settings_openrouter_model, name='settings_openrouter_model'),
    path('settings/agent', settings_views.settings_agent, name='settings_agent'),
    
    # Telegram integration endpoints
    path('telegram/status', telegram_views.telegram_status, name='telegram_status'),
    path('telegram/disconnect', telegram_views.telegram_disconnect, name='telegram_disconnect'),
    path('telegram/connect', telegram_views.telegram_connect, name='telegram_connect'),
    path('telegram/webhook', telegram_views.telegram_webhook, name='telegram_webhook'),
    
    # System management endpoints
    path('logs/tail', system_views.logs_tail, name='logs_tail'),
    path('services/restart', system_views.restart_service, name='restart_service'),
    
    # SD API upscaling endpoints (handled by Django backend)
    # Note: These are specific endpoints handled by Django, not proxied
    path('sdapi/v1/upscale', upscale_views.upscale, name='upscale'),
    path('sdapi/v1/upscale-batch', upscale_views.upscale_batch, name='upscale_batch'),
    path('sdapi/v1/upscalers', upscale_views.upscalers, name='upscalers'),
    
    # Training data export endpoints (for fine-tuning)
    path('training/export', training_views.export_training_data, name='training_export'),
    path('training/stats', training_views.export_stats, name='training_stats'),
    path('training/messages', training_views.export_raw_messages, name='training_messages'),
    
    # ARES self-memory endpoints (AI identity)
    path('self-memory', memory_views.self_memory, name='self_memory'),
    path('self-memory/<int:memory_id>', memory_views.self_memory_delete, name='self_memory_delete'),
    path('self-memory/milestone', memory_views.self_memory_milestone, name='self_memory_milestone'),
    path('self-memory/context', memory_views.self_memory_context, name='self_memory_context'),
    
    # User memory endpoints (user facts and preferences)
    path('user-memory', user_memory_views.user_memory, name='user_memory'),
    path('user-memory/fact', user_memory_views.user_memory_add_fact, name='user_memory_add_fact'),
    path('user-memory/fact/<int:fact_id>', user_memory_views.user_memory_delete_fact, name='user_memory_delete_fact'),
    path('user-memory/preference', user_memory_views.user_memory_add_preference, name='user_memory_add_preference'),
    path('user-memory/preference/<int:pref_id>', user_memory_views.user_memory_delete_preference, name='user_memory_delete_preference'),
    path('user-memory/context', user_memory_views.user_memory_context, name='user_memory_context'),
    
    # Memory system stats
    path('memory/stats', user_memory_views.memory_stats, name='memory_stats'),
    
    # Ollama Management API endpoints
    path('ollama/status', ollama_views.ollama_status, name='ollama_status'),
    path('ollama/models', ollama_views.ollama_models, name='ollama_models'),
    path('ollama/modelfile', ollama_views.ollama_modelfile, name='ollama_modelfile'),
    path('ollama/rebuild', ollama_views.ollama_rebuild, name='ollama_rebuild'),
    path('ollama/chat', ollama_views.ollama_chat, name='ollama_chat'),
    path('ollama/generate', ollama_views.ollama_generate, name='ollama_generate'),
    path('ollama/unload', ollama_views.ollama_unload, name='ollama_unload'),
    
    # Text-to-Speech (ElevenLabs) endpoints
    path('tts', tts_views.text_to_speech, name='tts'),
    path('tts/voices', tts_views.list_voices, name='tts_voices'),
    path('tts/config', tts_views.tts_config, name='tts_config'),
    
    # RAG (Retrieval-Augmented Generation) endpoints
    path('rag/stats', rag_views.rag_stats, name='rag_stats'),
    path('rag/reindex', rag_views.rag_reindex, name='rag_reindex'),
    path('rag/search', rag_views.rag_search, name='rag_search'),
    path('rag/clear', rag_views.rag_clear, name='rag_clear'),
    
    # Agent control endpoints (4090 rig)
    path('agent/status', agent_views.agent_status, name='agent_status'),
    path('agent/resources', agent_views.agent_resources, name='agent_resources'),
    path('agent/actions', agent_views.agent_actions, name='agent_actions'),
    path('agent/action', agent_views.agent_action, name='agent_action'),
    path('agent/start-sd', agent_views.agent_start_sd, name='agent_start_sd'),
    path('agent/stop-sd', agent_views.agent_stop_sd, name='agent_stop_sd'),
    path('agent/adjust-ollama', agent_views.agent_adjust_ollama, name='agent_adjust_ollama'),
]

# Conditionally add SD integration routes
try:
    from . import sd_integration
    urlpatterns.append(path('settings/sd', sd_integration.sd_settings, name='sd_settings'))
    urlpatterns.append(path('settings/sd/prompt-history', sd_integration.sd_prompt_history, name='sd_prompt_history'))
except ImportError:
    pass  # SD integration not available

