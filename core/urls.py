from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Projects
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    
    # Videos
    path('projects/<int:project_id>/videos/create/', views.video_create, name='video_create'),
    path('videos/<int:video_id>/', views.video_detail, name='video_detail'),
    path('videos/<int:video_id>/delete/', views.video_delete, name='video_delete'),
    path('videos/<int:video_id>/generate/', views.video_generate, name='video_generate'),
    path('videos/<int:video_id>/status/', views.video_status, name='video_status'),
    
    # API endpoints for AJAX
    path('api/avatars/', views.api_list_avatars, name='api_list_avatars'),
    path('api/voices/', views.api_list_voices, name='api_list_voices'),
]

