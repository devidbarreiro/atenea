from django.urls import path, re_path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Password Reset
    path('password-reset/request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='login/password_reset_confirm.html', 
        success_url=reverse_lazy('core:login'),
        extra_context={'hide_header': True}
    ), name='password_reset_confirm'),


    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Library
    path('library/', views.LibraryView.as_view(), name='library'),
    path('library/upload/', views.UploadItemView.as_view(), name='library_upload'),
    
    # Projects
    path('projects/', views.ProjectsListView.as_view(), name='projects_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<uuid:project_uuid>/', views.ProjectOverviewView.as_view(), name='project_overview'),
    path('projects/<uuid:project_uuid>/detail/', views.ProjectDetailView.as_view(), name='project_detail'),
    # Estas rutas ahora apuntan a las vistas unificadas (ver más abajo)
    # path('projects/<uuid:project_uuid>/videos/', views.ProjectDetailView.as_view(), {'tab': 'videos'}, name='project_videos'),
    # path('projects/<uuid:project_uuid>/images/', views.ProjectDetailView.as_view(), {'tab': 'images'}, name='project_images'),
    # path('projects/<uuid:project_uuid>/audios/', views.ProjectDetailView.as_view(), {'tab': 'audios'}, name='project_audios'),
    # path('projects/<uuid:project_uuid>/music/', ...) - ELIMINADA (Music unificado con Audio)
    path('projects/<uuid:project_uuid>/scripts/', views.ProjectDetailView.as_view(), {'tab': 'scripts'}, name='project_scripts'),
    # Redirigir /agent/ a /agent/create/
    path('projects/<uuid:project_uuid>/agent/', views.redirect_to_agent_create, name='project_agent'),
    path('projects/<uuid:project_uuid>/update-name/', views.ProjectUpdateNameView.as_view(), name='project_update_name'),
    path('projects/<uuid:project_uuid>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('items/<str:item_id>/move/', views.ProjectItemsManagementView.move_item, name='move_item'),
    
    # Videos (nueva vista unificada - creación + biblioteca)
    path('videos/', views.VideoLibraryView.as_view(), name='video_library'),
    path('projects/<uuid:project_uuid>/videos/', views.VideoLibraryView.as_view(), name='project_videos_library'),
    path('videos/<uuid:video_uuid>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('projects/<uuid:project_uuid>/videos/<uuid:video_uuid>/', views.VideoDetailView.as_view(), name='project_video_detail'),
    path('videos/<uuid:video_uuid>/delete/', views.VideoDeleteView.as_view(), name='video_delete'),
    path('videos/<uuid:video_uuid>/generate/', views.VideoGenerateView.as_view(), name='video_generate'),
    path('videos/<uuid:video_uuid>/recreate/', views.VideoRecreateView.as_view(), name='video_recreate'),
    path('videos/<uuid:video_uuid>/status/', views.VideoStatusView.as_view(), name='video_status'),
    
    # Images (nueva vista unificada - creación + biblioteca)
    path('images/', views.ImageLibraryView.as_view(), name='image_library'),
    path('projects/<uuid:project_uuid>/images/', views.ImageLibraryView.as_view(), name='project_images_library'),
    path('images/<uuid:image_uuid>/', views.ImageDetailView.as_view(), name='image_detail'),
    path('projects/<uuid:project_uuid>/images/<uuid:image_uuid>/', views.ImageDetailView.as_view(), name='project_image_detail'),
    path('images/<uuid:image_uuid>/delete/', views.ImageDeleteView.as_view(), name='image_delete'),
    path('images/<uuid:image_uuid>/generate/', views.ImageGenerateView.as_view(), name='image_generate'),
    path('images/<uuid:image_uuid>/recreate/', views.ImageRecreateView.as_view(), name='image_recreate'),
    path('images/<uuid:image_uuid>/edit/', views.ImageEditView.as_view(), name='image_edit'),
    path('images/<uuid:image_uuid>/create-video/', views.ImageToVideoView.as_view(), name='image_to_video'),
    path('images/<uuid:image_uuid>/upscale/', views.ImageUpscaleView.as_view(), name='image_upscale'),
    path('images/<uuid:image_uuid>/remove-bg/', views.ImageRemoveBackgroundView.as_view(), name='image_remove_bg'),
    
    # Audios (nueva vista unificada - creación + biblioteca)
    path('audios/', views.AudioLibraryView.as_view(), name='audio_library'),
    path('projects/<uuid:project_uuid>/audios/', views.AudioLibraryView.as_view(), name='project_audios_library'),
    path('audios/<uuid:audio_uuid>/', views.AudioDetailView.as_view(), name='audio_detail'),
    path('projects/<uuid:project_uuid>/audios/<uuid:audio_uuid>/', views.AudioDetailView.as_view(), name='project_audio_detail'),
    path('audios/<uuid:audio_uuid>/delete/', views.AudioDeleteView.as_view(), name='audio_delete'),
    path('audios/<uuid:audio_uuid>/generate/', views.AudioGenerateView.as_view(), name='audio_generate'),
    
    # Music URLs eliminadas - usar /audios/ con type='music'
    
    # Scripts (standalone - sin proyecto)
    path('scripts/create/', views.ScriptCreateView.as_view(), name='script_create_standalone'),
    
    # Scripts (con proyecto)
    path('projects/<uuid:project_uuid>/scripts/create/', views.ScriptCreateView.as_view(), name='script_create'),
    path('projects/<uuid:project_uuid>/scripts/create/partial/', views.ScriptCreatePartialView.as_view(), name='script_create_partial'),
    path('scripts/<int:script_id>/', views.ScriptDetailView.as_view(), name='script_detail'),
    path('scripts/<int:script_id>/delete/', views.ScriptDeleteView.as_view(), name='script_delete'),
    path('scripts/<int:script_id>/retry/', views.ScriptRetryView.as_view(), name='script_retry'),
    
    # HTMX Partials
    path('videos/<uuid:video_uuid>/status-partial/', views.VideoStatusPartialView.as_view(), name='video_status_partial'),
    path('images/<uuid:image_uuid>/status-partial/', views.ImageStatusPartialView.as_view(), name='image_status_partial'),
    path('scripts/<int:script_id>/status-partial/', views.ScriptStatusPartialView.as_view(), name='script_status_partial'),
    
    # API endpoints
    path('api/models/config/', views.ModelConfigAPIView.as_view(), name='api_models_config'),
    path('api/models/<str:model_id>/capabilities/', views.ModelCapabilitiesAPIView.as_view(), name='api_model_capabilities'),
    path('api/video-models/', views.VideoModelsAPIView.as_view(), name='api_video_models'),
    path('api/models/estimate-cost/', views.EstimateCostAPIView.as_view(), name='api_estimate_cost'),
    path('videos/form-fields/', views.DynamicFormFieldsView.as_view(), name='dynamic_form_fields'),
    path('api/library/items/', views.LibraryItemsAPIView.as_view(), name='api_library_items'),
    path('api/items/<str:item_type>/<str:item_id>/', views.ItemDetailAPIView.as_view(), name='api_item_detail'),
    path('api/items/<str:item_type>/<str:item_id>/download/', views.ItemDownloadView.as_view(), name='api_item_download'),
    path('api/items/create/', views.CreateItemAPIView.as_view(), name='api_create_item'),
    path('api/avatars/', views.ListAvatarsView.as_view(), name='api_list_avatars'),
    path('api/voices/', views.ListVoicesView.as_view(), name='api_list_voices'),
    path('api/image-assets/', views.ListImageAssetsView.as_view(), name='api_list_image_assets'),
    path('api/elevenlabs/voices/', views.ListElevenLabsVoicesView.as_view(), name='api_list_elevenlabs_voices'),
    
    # Webhooks
    # DEPRECATED: N8nWebhookView está comentado, ya no se usa con LangChain
    # path('webhooks/n8n/', views.N8nWebhookView.as_view(), name='n8n_webhook'),
    
    # Agent Video Flow (con proyecto)
    path('projects/<uuid:project_uuid>/agent/create/', views.AgentCreateView.as_view(), name='agent_create'),
    path('projects/<uuid:project_uuid>/agent/ai-assistant/', views.AgentAIAssistantView.as_view(), name='agent_ai_assistant'),
    path('projects/<uuid:project_uuid>/agent/ai-assistant/init/', views.AgentAIAssistantInitView.as_view(), name='agent_ai_assistant_init'),
    path('projects/<uuid:project_uuid>/agent/ai-assistant/chat/', views.AgentAIAssistantChatView.as_view(), name='agent_ai_assistant_chat'),
    path('projects/<uuid:project_uuid>/agent/configure/', views.AgentConfigureView.as_view(), name='agent_configure'),
    path('projects/<uuid:project_uuid>/agent/scenes/', views.AgentScenesView.as_view(), name='agent_scenes'),
    path('projects/<uuid:project_uuid>/agent/final/', views.AgentFinalView.as_view(), name='agent_final'),
    
    # Agent Video Flow (sin proyecto - standalone)
    path('agent/create/', views.AgentCreateStandaloneView.as_view(), name='agent_create_standalone'),
    path('agent/configure/', views.AgentConfigureStandaloneView.as_view(), name='agent_configure_standalone'),
    path('agent/scenes/', views.AgentScenesStandaloneView.as_view(), name='agent_scenes_standalone'),
    path('agent/final/', views.AgentFinalStandaloneView.as_view(), name='agent_final_standalone'),
    
    # Agent Scene Actions
    path('scripts/<int:script_id>/scenes/create/', views.SceneCreateManualView.as_view(), name='scene_create_manual'),
    path('scenes/<int:scene_id>/upload-video/', views.SceneUploadVideoView.as_view(), name='scene_upload_video'),
    path('scenes/<int:scene_id>/upload-custom-image/', views.SceneUploadCustomImageView.as_view(), name='scene_upload_custom_image'),
    path('scenes/<int:scene_id>/generate-ai-image/', views.SceneGenerateAIImageView.as_view(), name='scene_generate_ai_image'),
    path('scenes/<int:scene_id>/generate/', views.SceneGenerateView.as_view(), name='scene_generate'),
    path('scenes/<int:scene_id>/status/', views.SceneStatusView.as_view(), name='scene_status'),
    path('scenes/<int:scene_id>/update/', views.SceneUpdateConfigView.as_view(), name='scene_update'),
    path('scenes/<int:scene_id>/generate-audio/', views.SceneGenerateAudioView.as_view(), name='scene_generate_audio'),
    path('scenes/<int:scene_id>/combine-audio/', views.SceneCombineAudioView.as_view(), name='scene_combine_audio'),
    path('scenes/<int:scene_id>/regenerate/', views.SceneRegenerateView.as_view(), name='scene_regenerate'),
    path('scenes/<int:scene_id>/versions/', views.SceneVersionsView.as_view(), name='scene_versions'),
    path('scenes/<int:scene_id>/delete/', views.SceneDeleteView.as_view(), name='scene_delete'),
    
    # Freepik API
    path('api/freepik/search/images/', views.FreepikSearchImagesView.as_view(), name='freepik_search_images'),
    path('api/freepik/search/videos/', views.FreepikSearchVideosView.as_view(), name='freepik_search_videos'),
    path('scenes/<int:scene_id>/set-freepik-image/', views.FreepikSetSceneImageView.as_view(), name='scene_set_freepik_image'),
    
    # Stock Search API (Unified)
    path('api/stock/search/', views.StockSearchView.as_view(), name='stock_search'),
    path('api/stock/sources/', views.StockSourcesView.as_view(), name='stock_sources'),
    
    # Stock Pages
    path('stock/', views.StockListView.as_view(), name='stock_list'),
    path('stock/photos/', views.StockListView.as_view(), {'type': 'image'}, name='stock_photos'),
    path('stock/videos/', views.StockListView.as_view(), {'type': 'video'}, name='stock_videos'),
    path('stock/audio/', views.StockListView.as_view(), {'type': 'audio'}, name='stock_audio'),
    path('api/stock/download/', views.StockDownloadView.as_view(), name='stock_download'),
    path('api/stock/video-proxy/', views.StockVideoProxyView.as_view(), name='stock_video_proxy'),
    
    # Vuela.ai API
    path('api/vuela/validate-token/', views.VuelaAIValidateTokenView.as_view(), name='vuela_validate_token'),
    path('api/vuela/videos/', views.VuelaAIListVideosView.as_view(), name='vuela_list_videos'),
    path('api/vuela/videos/<str:video_id>/', views.VuelaAIVideoDetailsView.as_view(), name='vuela_video_details'),

    # User Management
    path('users/menu/', views.UserMenuView.as_view(), name='user_menu'),
    path('users/activate/<uidb64>/<token>/', views.ActivateAccountView.as_view(extra_context={'hide_header': True}), name='activate_account'),
    path('no-permissions/', views.no_permissions, name='no_permissions'),
    path("credits/add/", views.AddCreditsView.as_view(), name="add_credits"),
    path('user/set-monthly-limit/', views.SetMonthlyLimitView.as_view(), name='set_monthly_limit'),
    path('users/credits/history/<int:user_id>/', views.UserCreditsHistoryAPI.as_view(), name='user-credits-history-api'),


    # Documentacion
    path('docs/structure/', views.docs_structure, name='docs_structure'),
    path('docs/<path:path>/', views.docs_md_view, name='docs_md'),
    re_path(r'^docs/?$', views.docs_home, name='docs_home'),
    
    # Project Invitations
    path('projects/<uuid:project_uuid>/invite/', views.ProjectInviteView.as_view(), name='project_invite'),
    path('projects/<uuid:project_uuid>/invite/partial/', views.ProjectInvitePartialView.as_view(), name='project_invite_partial'),
    path('projects/<uuid:project_uuid>/invitations/', views.ProjectInvitationsListView.as_view(), name='project_invitations'),
    path('projects/<uuid:project_uuid>/invitations/partial/', views.ProjectInvitationsPartialView.as_view(), name='project_invitations_partial'),
    path('invitations/<str:token>/accept/', views.AcceptInvitationView.as_view(), name='accept_invitation'),
    path('invitations/<int:invitation_id>/cancel/', views.CancelInvitationView.as_view(), name='cancel_invitation'),
    
    # Move to Project
    path('move-to-project/<str:item_type>/<str:item_id>/', views.MoveToProjectView.as_view(), name='move_to_project'),
    
    # Documentation Assistant (RAG)
    path('assistant/', views.DocumentationAssistantView.as_view(), name='doc_assistant'),
    path('assistant/chat/', views.DocumentationAssistantChatView.as_view(), name='doc_assistant_chat'),
    path('assistant/reindex/', views.DocumentationAssistantReindexView.as_view(), name='doc_assistant_reindex'),
    
    # Creation Agent (Chat de Creación)
    path('chat/', views.CreationAgentView.as_view(), name='creation_agent'),
    path('chat/message/', views.CreationAgentChatView.as_view(), name='creation_agent_chat'),
    
    # Credits Dashboard
    path('credits/', views.CreditsDashboardView.as_view(), name='credits_dashboard'),
    
    # Notifications
    path('notifications/panel/', views.NotificationsPanelView.as_view(), name='notifications_panel'),
    path('notifications/count/', views.NotificationsCountView.as_view(), name='notifications_count'),
    path('notifications/<uuid:notification_uuid>/read/', views.MarkNotificationReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='notifications_mark_all_read'),
    
    # Queues (Tareas de Generación)
    path('queues/', views.QueuesPanelView.as_view(), name='queues_panel'),
    path('queues/active-dropdown/', views.ActiveQueuesDropdownView.as_view(), name='active_queues_dropdown'),
    path('queues/task/<uuid:task_uuid>/', views.QueueTaskDetailView.as_view(), name='queue_task_detail'),
    path('queues/task/<uuid:task_uuid>/cancel/', views.CancelTaskView.as_view(), name='cancel_task'),
    
    # Prompt Templates API
    path('api/prompt-templates/', views.PromptTemplatesAPIView.as_view(), name='api_prompt_templates'),
    path('api/prompt-templates/<uuid:template_uuid>/', views.PromptTemplateDetailAPIView.as_view(), name='api_prompt_template_detail'),
    path('api/prompt-templates/<uuid:template_uuid>/vote/', views.PromptTemplateVoteAPIView.as_view(), name='api_prompt_template_vote'),
    path('api/prompt-templates/<uuid:template_uuid>/favorite/', views.PromptTemplateFavoriteAPIView.as_view(), name='api_prompt_template_favorite'),
]

