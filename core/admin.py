from django.contrib import admin
from .models import Project, Video


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'video_count', 'completed_videos', 'created_at']
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
