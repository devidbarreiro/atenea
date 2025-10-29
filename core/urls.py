from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Login
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Projects
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:project_id>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    
    # Videos
    path('projects/<int:project_id>/videos/create/', views.VideoCreateView.as_view(), name='video_create'),
    path('videos/<int:video_id>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('videos/<int:video_id>/delete/', views.VideoDeleteView.as_view(), name='video_delete'),
    path('videos/<int:video_id>/generate/', views.VideoGenerateView.as_view(), name='video_generate'),
    path('videos/<int:video_id>/status/', views.VideoStatusView.as_view(), name='video_status'),
    
    # Images
    path('projects/<int:project_id>/images/create/', views.ImageCreateView.as_view(), name='image_create'),
    path('images/<int:image_id>/', views.ImageDetailView.as_view(), name='image_detail'),
    path('images/<int:image_id>/delete/', views.ImageDeleteView.as_view(), name='image_delete'),
    path('images/<int:image_id>/generate/', views.ImageGenerateView.as_view(), name='image_generate'),
    
    # Scripts
    path('projects/<int:project_id>/scripts/create/', views.ScriptCreateView.as_view(), name='script_create'),
    path('scripts/<int:script_id>/', views.ScriptDetailView.as_view(), name='script_detail'),
    path('scripts/<int:script_id>/delete/', views.ScriptDeleteView.as_view(), name='script_delete'),
    path('scripts/<int:script_id>/retry/', views.ScriptRetryView.as_view(), name='script_retry'),
    
    # HTMX Partials
    path('videos/<int:video_id>/status-partial/', views.VideoStatusPartialView.as_view(), name='video_status_partial'),
    path('images/<int:image_id>/status-partial/', views.ImageStatusPartialView.as_view(), name='image_status_partial'),
    path('scripts/<int:script_id>/status-partial/', views.ScriptStatusPartialView.as_view(), name='script_status_partial'),
    
    # API endpoints
    path('api/avatars/', views.ListAvatarsView.as_view(), name='api_list_avatars'),
    path('api/voices/', views.ListVoicesView.as_view(), name='api_list_voices'),
    path('api/image-assets/', views.ListImageAssetsView.as_view(), name='api_list_image_assets'),
    
    # Webhooks
    path('webhooks/n8n/', views.N8nWebhookView.as_view(), name='n8n_webhook'),
    
    # Agent Video Flow
    path('projects/<int:project_id>/agent/create/', views.AgentCreateView.as_view(), name='agent_create'),
    path('projects/<int:project_id>/agent/ai-assistant/', views.AgentAIAssistantView.as_view(), name='agent_ai_assistant'),
    path('projects/<int:project_id>/agent/ai-assistant/init/', views.AgentAIAssistantInitView.as_view(), name='agent_ai_assistant_init'),
    path('projects/<int:project_id>/agent/ai-assistant/chat/', views.AgentAIAssistantChatView.as_view(), name='agent_ai_assistant_chat'),
    path('projects/<int:project_id>/agent/configure/', views.AgentConfigureView.as_view(), name='agent_configure'),
    path('projects/<int:project_id>/agent/scenes/', views.AgentScenesView.as_view(), name='agent_scenes'),
    path('projects/<int:project_id>/agent/final/', views.AgentFinalView.as_view(), name='agent_final'),
    
    # Agent Scene Actions
    path('scenes/<int:scene_id>/generate/', views.SceneGenerateView.as_view(), name='scene_generate'),
    path('scenes/<int:scene_id>/status/', views.SceneStatusView.as_view(), name='scene_status'),
    path('scenes/<int:scene_id>/update/', views.SceneUpdateConfigView.as_view(), name='scene_update'),
    path('scenes/<int:scene_id>/regenerate/', views.SceneRegenerateView.as_view(), name='scene_regenerate'),
    path('scenes/<int:scene_id>/versions/', views.SceneVersionsView.as_view(), name='scene_versions'),
]

