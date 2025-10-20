from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
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
    
    # API endpoints
    path('api/avatars/', views.ListAvatarsView.as_view(), name='api_list_avatars'),
    path('api/voices/', views.ListVoicesView.as_view(), name='api_list_voices'),
    path('api/image-assets/', views.ListImageAssetsView.as_view(), name='api_list_image_assets'),
]

