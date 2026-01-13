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
from . import memory_extraction_views
from . import account_linking_views
from . import ollama_views
from . import tts_views
from . import stt_views
from . import rag_views
from . import agent_views
from . import code_views
from . import calendar_views
from . import user_manager_views
from . import debug_views
from . import user_account_linking_views

app_name = 'api'

urlpatterns = [
    # Authentication endpoints
    path('auth/config', auth_views.auth_config, name='auth_config'),
    path('auth/user', auth_views.user_info, name='user_info'),
    path('auth/verify', auth_views.verify_token_view, name='verify_token'),
    path('auth/check-admin', auth_views.check_admin_role, name='check_admin_role'),
    
    # Dev admin endpoints (only work in DEBUG mode)
    path('auth/dev-admin/config', auth_views.dev_admin_config, name='dev_admin_config'),
    path('auth/dev-admin/login', auth_views.dev_admin_login, name='dev_admin_login'),
    
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
    path('settings/openrouter-auto-select', settings_views.settings_openrouter_auto_select, name='settings_openrouter_auto_select'),
    path('settings/agent', settings_views.settings_agent, name='settings_agent'),
    path('settings/tab-visibility', settings_views.settings_tab_visibility, name='settings_tab_visibility'),
    
    # Telegram integration endpoints
    path('telegram/status', telegram_views.telegram_status, name='telegram_status'),
    path('telegram/disconnect', telegram_views.telegram_disconnect, name='telegram_disconnect'),
    path('telegram/connect', telegram_views.telegram_connect, name='telegram_connect'),
    path('telegram/webhook', telegram_views.telegram_webhook, name='telegram_webhook'),
    path('telegram/send', telegram_views.telegram_send, name='telegram_send'),
    path('telegram/chats', telegram_views.telegram_chats, name='telegram_chats'),
    
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
    
    # Memory extraction endpoints
    path('memory/extract', memory_extraction_views.extract_memories, name='extract_memories'),
    path('memory/extract-all', memory_extraction_views.extract_all_conversations, name='extract_all_conversations'),
    path('memory/spots', memory_extraction_views.memory_spots_list, name='memory_spots_list'),
    path('memory/spots/<int:spot_id>', memory_extraction_views.memory_spot_detail, name='memory_spot_detail'),
    path('memory/spots/<int:spot_id>/apply', memory_extraction_views.memory_spot_apply, name='memory_spot_apply'),
    path('memory/spots/<int:spot_id>/reject', memory_extraction_views.memory_spot_reject, name='memory_spot_reject'),
    path('memory/auto-apply', memory_extraction_views.auto_apply_memories, name='auto_apply_memories'),
    path('memory/extraction-stats', memory_extraction_views.memory_extraction_stats, name='memory_extraction_stats'),
    path('memory/revise', memory_extraction_views.revise_memories_endpoint, name='revise_memories'),
    path('capabilities', memory_extraction_views.capabilities_list, name='capabilities_list'),
    
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
    
    # Speech-to-Text (OpenAI Whisper) endpoints
    path('stt', stt_views.speech_to_text, name='stt'),
    path('stt/config', stt_views.stt_config, name='stt_config'),
    
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
    path('agent/logs', agent_views.agent_logs, name='agent_logs'),
    
    # Code indexing and revision endpoints
    path('code/index', code_views.index_codebase, name='code_index'),
    path('code/context', code_views.get_code_context, name='code_context'),
    path('code/files', code_views.list_code_files, name='code_files'),
    path('code/search', code_views.search_code, name='code_search'),
    path('code/file', code_views.get_file_content, name='code_file'),
    path('code/revise', code_views.revise_code, name='code_revise'),
    path('code/memories', code_views.get_code_memories, name='code_memories'),
    path('code/extract-memories', code_views.extract_code_memories_endpoint, name='code_extract_memories'),
    
    # Google Calendar integration endpoints
    path('calendar/status', calendar_views.calendar_status, name='calendar_status'),
    path('calendar/connect', calendar_views.calendar_connect, name='calendar_connect'),
    path('calendar/oauth/callback', calendar_views.calendar_oauth_callback, name='calendar_oauth_callback'),
    path('calendar/disconnect', calendar_views.calendar_disconnect, name='calendar_disconnect'),
    path('calendar/events', calendar_views.calendar_events, name='calendar_events'),
    path('calendar/sync', calendar_views.calendar_sync, name='calendar_sync'),
    path('calendar/context-debug', calendar_views.calendar_context_debug, name='calendar_context_debug'),
    
    # User management endpoints (admin)
    path('users', user_manager_views.list_users, name='list_users'),
    path('users/telegram', user_manager_views.list_telegram_users, name='list_telegram_users'),
    path('users/telegram/link', user_manager_views.link_telegram_account, name='link_telegram_account'),
    path('users/telegram/unlink', user_manager_views.unlink_telegram_account, name='unlink_telegram_account'),
    path('users/telegram/nickname', user_manager_views.set_telegram_nickname, name='set_telegram_nickname'),
    path('users/telegram/nicknames', user_manager_views.get_telegram_nicknames, name='get_telegram_nicknames'),
    path('users/telegram/nickname/<str:nickname>', user_manager_views.delete_telegram_nickname, name='delete_telegram_nickname'),
    path('users/<path:user_id>', user_manager_views.get_user_details, name='get_user_details'),
    
    # User account linking endpoints (link local accounts to Auth0)
    path('account-links', user_account_linking_views.list_all_links, name='list_all_account_links'),
    path('account-links/my', user_account_linking_views.my_account_links, name='my_account_links'),
    path('account-links/create', user_account_linking_views.create_account_link, name='create_account_link'),
    path('account-links/delete', user_account_linking_views.delete_account_link, name='delete_account_link'),
    path('account-links/verify', user_account_linking_views.verify_account_link, name='verify_account_link'),
    path('account-links/linked', user_account_linking_views.get_linked_accounts, name='get_linked_accounts'),
    path('account-links/stats', user_account_linking_views.get_link_data_stats, name='get_link_data_stats'),
    path('account-links/<int:link_id>', user_account_linking_views.get_link_by_id, name='get_link_by_id'),
    
    # Debug endpoints for orchestrator and memory system
    path('debug/prompt', debug_views.debug_prompt, name='debug_prompt'),
    path('debug/memory', debug_views.debug_memory, name='debug_memory'),
    path('debug/routing', debug_views.debug_routing, name='debug_routing'),
    path('debug/status', debug_views.debug_orchestrator_status, name='debug_orchestrator_status'),
    path('debug/test-consistency', debug_views.debug_test_consistency, name='debug_test_consistency'),
]

# Conditionally add SD integration routes
try:
    from . import sd_integration
    urlpatterns.append(path('settings/sd', sd_integration.sd_settings, name='sd_settings'))
    urlpatterns.append(path('settings/sd/prompt-history', sd_integration.sd_prompt_history, name='sd_prompt_history'))
except ImportError:
    pass  # SD integration not available

