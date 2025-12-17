from django.urls import path
from . import views
from . import auth_views

app_name = 'api'

urlpatterns = [
    # Authentication endpoints
    path('auth/config', auth_views.auth_config, name='auth_config'),
    path('auth/user', auth_views.user_info, name='user_info'),
    path('auth/verify', auth_views.verify_token_view, name='verify_token'),
    
    # API endpoints
    path('chat', views.chat, name='chat'),
    path('models', views.models_list, name='models'),
    path('sessions', views.sessions_list, name='sessions'),
    path('sessions/<str:session_id>', views.session_detail, name='session_detail'),
    path('conversations', views.conversations_list, name='conversations'),
]

