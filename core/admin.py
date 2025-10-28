from django.contrib import admin
from .models import Project, Video, Image, Script, Scene


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'video_count', 'completed_videos', 'image_count', 'completed_images', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'type', 'status', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['title', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'external_id']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('project', 'title', 'type', 'status')
        }),
        ('Contenido', {
            'fields': ('script', 'config')
        }),
        ('Almacenamiento', {
            'fields': ('gcs_path', 'external_id')
        }),
        ('Metadatos', {
            'fields': ('duration', 'resolution', 'metadata')
        }),
        ('Control de Errores', {
            'fields': ('error_message',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'type', 'status', 'aspect_ratio', 'created_at']
    list_filter = ['type', 'status', 'aspect_ratio', 'created_at']
    search_fields = ['title', 'project__name', 'prompt']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'external_id']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('project', 'title', 'type', 'status')
        }),
        ('Contenido', {
            'fields': ('prompt', 'config')
        }),
        ('Almacenamiento', {
            'fields': ('gcs_path', 'external_id')
        }),
        ('Metadatos', {
            'fields': ('width', 'height', 'aspect_ratio', 'metadata')
        }),
        ('Control de Errores', {
            'fields': ('error_message',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'agent_flow', 'num_scenes', 'platform_mode', 'created_at']
    list_filter = ['status', 'agent_flow', 'platform_mode', 'language', 'created_at']
    search_fields = ['title', 'project__name', 'original_script']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'num_scenes', 'platform_mode', 'language', 'total_estimated_duration_min']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('project', 'title', 'status', 'agent_flow')
        }),
        ('Contenido', {
            'fields': ('original_script', 'desired_duration_min', 'processed_data')
        }),
        ('Video Final', {
            'fields': ('final_video',)
        }),
        ('Metadatos del Procesamiento', {
            'fields': ('platform_mode', 'num_scenes', 'language', 'total_estimated_duration_min')
        }),
        ('Control de Errores', {
            'fields': ('error_message',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ['scene_id', 'script', 'order', 'ai_service', 'video_status', 'preview_image_status', 'is_included', 'duration_sec']
    list_filter = ['video_status', 'preview_image_status', 'ai_service', 'avatar', 'is_included', 'created_at']
    search_fields = ['scene_id', 'script__title', 'summary', 'script_text']
    readonly_fields = ['created_at', 'updated_at', 'completed_at', 'external_id']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('script', 'project', 'scene_id', 'order', 'is_included')
        }),
        ('Contenido de la Escena', {
            'fields': ('summary', 'script_text', 'duration_sec', 'avatar', 'platform')
        }),
        ('Elementos Visuales', {
            'fields': ('broll', 'transition', 'text_on_screen', 'audio_notes')
        }),
        ('Preview Image', {
            'fields': ('preview_image_status', 'preview_image_gcs_path', 'preview_image_error')
        }),
        ('Configuración IA', {
            'fields': ('ai_service', 'ai_config')
        }),
        ('Video Generado', {
            'fields': ('video_status', 'video_gcs_path', 'external_id', 'error_message')
        }),
        ('Versiones', {
            'fields': ('version', 'parent_scene')
        }),
        ('Metadatos', {
            'fields': ('metadata',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
