from django.urls import path, re_path
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),


    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Library
    path('library/', views.LibraryView.as_view(), name='library'),
    
    # Projects
    path('projects/', views.ProjectsListView.as_view(), name='projects_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:project_id>/videos/', views.ProjectDetailView.as_view(), {'tab': 'videos'}, name='project_videos'),
    path('projects/<int:project_id>/images/', views.ProjectDetailView.as_view(), {'tab': 'images'}, name='project_images'),
    path('projects/<int:project_id>/audios/', views.ProjectDetailView.as_view(), {'tab': 'audios'}, name='project_audios'),
    path('projects/<int:project_id>/music/', views.ProjectDetailView.as_view(), {'tab': 'music'}, name='project_music'),
    path('projects/<int:project_id>/scripts/', views.ProjectDetailView.as_view(), {'tab': 'scripts'}, name='project_scripts'),
    path('projects/<int:project_id>/agent/', views.ProjectDetailView.as_view(), {'tab': 'agent'}, name='project_agent'),
    path('projects/<int:project_id>/update-name/', views.ProjectUpdateNameView.as_view(), name='project_update_name'),
    path('projects/<int:project_id>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('items/<int:item_id>/move/', views.ProjectItemsManagementView.move_item, name='move_item'),
    
    # Videos (standalone - sin proyecto)
    path('videos/create/', views.VideoCreateView.as_view(), name='video_create_standalone'),
    
    # Videos (con proyecto)
    path('projects/<int:project_id>/videos/create/', views.VideoCreateView.as_view(), name='video_create'),
    path('projects/<int:project_id>/videos/create/partial/', views.VideoCreatePartialView.as_view(), name='video_create_partial'),
    path('videos/<int:video_id>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('videos/<int:video_id>/delete/', views.VideoDeleteView.as_view(), name='video_delete'),
    path('videos/<int:video_id>/generate/', views.VideoGenerateView.as_view(), name='video_generate'),
    path('videos/<int:video_id>/status/', views.VideoStatusView.as_view(), name='video_status'),
    
    # Images (standalone - sin proyecto)
    path('images/create/', views.ImageCreateView.as_view(), name='image_create_standalone'),
    
    # Images (con proyecto)
    path('projects/<int:project_id>/images/create/', views.ImageCreateView.as_view(), name='image_create'),
    path('projects/<int:project_id>/images/create/partial/', views.ImageCreatePartialView.as_view(), name='image_create_partial'),
    path('images/<int:image_id>/', views.ImageDetailView.as_view(), name='image_detail'),
    path('images/<int:image_id>/delete/', views.ImageDeleteView.as_view(), name='image_delete'),
    path('images/<int:image_id>/generate/', views.ImageGenerateView.as_view(), name='image_generate'),
    
    # Audios (standalone - sin proyecto)
    path('audios/create/', views.AudioCreateView.as_view(), name='audio_create_standalone'),
    
    # Audios (con proyecto)
    path('projects/<int:project_id>/audios/create/', views.AudioCreateView.as_view(), name='audio_create'),
    path('projects/<int:project_id>/audios/create/partial/', views.AudioCreatePartialView.as_view(), name='audio_create_partial'),
    path('audios/<int:audio_id>/', views.AudioDetailView.as_view(), name='audio_detail'),
    path('audios/<int:audio_id>/delete/', views.AudioDeleteView.as_view(), name='audio_delete'),
    path('audios/<int:audio_id>/generate/', views.AudioGenerateView.as_view(), name='audio_generate'),
    
    # Music (standalone - sin proyecto)
    path('music/create/', views.MusicCreateView.as_view(), name='music_create_standalone'),
    
    # Music (con proyecto)
    path('projects/<int:project_id>/music/create/', views.MusicCreateView.as_view(), name='music_create'),
    path('music/<int:music_id>/', views.MusicDetailView.as_view(), name='music_detail'),
    path('music/<int:music_id>/delete/', views.MusicDeleteView.as_view(), name='music_delete'),
    path('music/<int:music_id>/generate/', views.MusicGenerateView.as_view(), name='music_generate'),
    path('music/<int:music_id>/status/', views.MusicStatusView.as_view(), name='music_status'),
    path('music/<int:music_id>/composition-plan/', views.MusicCompositionPlanView.as_view(), name='music_composition_plan'),
    
    # Scripts (standalone - sin proyecto)
    path('scripts/create/', views.ScriptCreateView.as_view(), name='script_create_standalone'),
    
    # Scripts (con proyecto)
    path('projects/<int:project_id>/scripts/create/', views.ScriptCreateView.as_view(), name='script_create'),
    path('projects/<int:project_id>/scripts/create/partial/', views.ScriptCreatePartialView.as_view(), name='script_create_partial'),
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
    path('api/elevenlabs/voices/', views.ListElevenLabsVoicesView.as_view(), name='api_list_elevenlabs_voices'),
    
    # Webhooks
    # DEPRECATED: N8nWebhookView está comentado, ya no se usa con LangChain
    # path('webhooks/n8n/', views.N8nWebhookView.as_view(), name='n8n_webhook'),
    
    # Agent Video Flow
    path('projects/<int:project_id>/agent/create/', views.AgentCreateView.as_view(), name='agent_create'),
    path('projects/<int:project_id>/agent/ai-assistant/', views.AgentAIAssistantView.as_view(), name='agent_ai_assistant'),
    path('projects/<int:project_id>/agent/ai-assistant/init/', views.AgentAIAssistantInitView.as_view(), name='agent_ai_assistant_init'),
    path('projects/<int:project_id>/agent/ai-assistant/chat/', views.AgentAIAssistantChatView.as_view(), name='agent_ai_assistant_chat'),
    path('projects/<int:project_id>/agent/configure/', views.AgentConfigureView.as_view(), name='agent_configure'),
    path('projects/<int:project_id>/agent/scenes/', views.AgentScenesView.as_view(), name='agent_scenes'),
    path('projects/<int:project_id>/agent/final/', views.AgentFinalView.as_view(), name='agent_final'),
    
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
    
    # Freepik API
    path('api/freepik/search/images/', views.FreepikSearchImagesView.as_view(), name='freepik_search_images'),
    path('api/freepik/search/videos/', views.FreepikSearchVideosView.as_view(), name='freepik_search_videos'),
    path('scenes/<int:scene_id>/set-freepik-image/', views.FreepikSetSceneImageView.as_view(), name='scene_set_freepik_image'),
    
    # Vuela.ai API
    path('api/vuela/validate-token/', views.VuelaAIValidateTokenView.as_view(), name='vuela_validate_token'),
    path('api/vuela/videos/', views.VuelaAIListVideosView.as_view(), name='vuela_list_videos'),
    path('api/vuela/videos/<str:video_id>/', views.VuelaAIVideoDetailsView.as_view(), name='vuela_video_details'),

    # User Management
    path('users/menu/', views.UserMenuView.as_view(), name='user_menu'),
    path('users/activate/<uidb64>/<token>/', views.activate_account, name='activate_account'),
    path('no-permissions/', views.no_permissions, name='no_permissions'),

    # Documentacion
    path('docs/structure/', views.docs_structure, name='docs_structure'),
    path('docs/api/services/<path:path>/', views.docs_md_view, name='docs_md'),
    re_path(r'^docs/.*$', views.docs_home, name='docs_home'),
    
    # Project Invitations
    path('projects/<int:project_id>/invite/', views.ProjectInviteView.as_view(), name='project_invite'),
    path('projects/<int:project_id>/invite/partial/', views.ProjectInvitePartialView.as_view(), name='project_invite_partial'),
    path('projects/<int:project_id>/invitations/', views.ProjectInvitationsListView.as_view(), name='project_invitations'),
    path('projects/<int:project_id>/invitations/partial/', views.ProjectInvitationsPartialView.as_view(), name='project_invitations_partial'),
    path('invitations/<str:token>/accept/', views.AcceptInvitationView.as_view(), name='accept_invitation'),
    path('invitations/<int:invitation_id>/cancel/', views.CancelInvitationView.as_view(), name='cancel_invitation'),
    
    # Move to Project
    path('move-to-project/<str:item_type>/<int:item_id>/', views.MoveToProjectView.as_view(), name='move_to_project'),
    
    # Documentation Assistant (RAG)
    path('assistant/', views.DocumentationAssistantView.as_view(), name='doc_assistant'),
    path('assistant/chat/', views.DocumentationAssistantChatView.as_view(), name='doc_assistant_chat'),
    path('assistant/reindex/', views.DocumentationAssistantReindexView.as_view(), name='doc_assistant_reindex'),
]

