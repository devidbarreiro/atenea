from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods
from .models import Project, Video
from .ai_services.heygen import HeyGenClient
from .ai_services.gemini_veo import GeminiVeoClient
from .storage.gcs import gcs_storage
import logging

logger = logging.getLogger(__name__)


def dashboard(request):
    """Dashboard principal con lista de proyectos"""
    projects = Project.objects.all()
    
    context = {
        'projects': projects,
        'total_videos': Video.objects.count(),
        'completed_videos': Video.objects.filter(status='completed').count(),
        'processing_videos': Video.objects.filter(status='processing').count(),
    }
    
    return render(request, 'dashboard/index.html', context)


def project_create(request):
    """Crear nuevo proyecto"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            project = Project.objects.create(name=name)
            messages.success(request, f'Proyecto "{name}" creado exitosamente')
            return redirect('core:project_detail', project_id=project.id)
        else:
            messages.error(request, 'El nombre del proyecto es requerido')
    
    return render(request, 'projects/create.html')


def project_detail(request, project_id):
    """Detalle de un proyecto con sus videos"""
    project = get_object_or_404(Project, id=project_id)
    videos = project.videos.all()
    
    context = {
        'project': project,
        'videos': videos,
    }
    
    return render(request, 'projects/detail.html', context)


def project_delete(request, project_id):
    """Eliminar un proyecto"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Proyecto "{project_name}" eliminado')
        return redirect('core:dashboard')
    
    return render(request, 'projects/delete.html', {'project': project})


def video_create(request, project_id):
    """Crear nuevo video en un proyecto"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        video_type = request.POST.get('type')
        script = request.POST.get('script')
        
        # Configuración según el tipo de video
        config = {}
        
        if video_type == 'heygen_avatar':
            config = {
                'avatar_id': request.POST.get('avatar_id'),
                'voice_id': request.POST.get('voice_id'),
                'has_background': request.POST.get('has_background') == 'on',
                'background_url': request.POST.get('background_url', ''),
                'voice_speed': float(request.POST.get('voice_speed', 1.0)),
                'voice_pitch': int(request.POST.get('voice_pitch', 50)),
                'voice_emotion': request.POST.get('voice_emotion', 'Excited'),
            }
        elif video_type == 'gemini_veo':
            config = {
                'duration': int(request.POST.get('duration', 5)),
                'aspect_ratio': request.POST.get('aspect_ratio', '16:9'),
            }
        
        video = Video.objects.create(
            project=project,
            title=title,
            type=video_type,
            script=script,
            config=config
        )
        
        messages.success(request, f'Video "{title}" creado. Ahora puedes generarlo.')
        return redirect('core:video_detail', video_id=video.id)
    
    context = {
        'project': project,
    }
    
    return render(request, 'videos/create.html', context)


def video_detail(request, video_id):
    """Detalle de un video"""
    video = get_object_or_404(Video, id=video_id)
    
    # Generar URL firmada si el video está completado
    signed_url = None
    if video.status == 'completed' and video.gcs_path:
        try:
            signed_url = gcs_storage.get_signed_url(video.gcs_path)
        except Exception as e:
            logger.error(f"Error al generar URL firmada: {str(e)}")
    
    context = {
        'video': video,
        'signed_url': signed_url,
    }
    
    return render(request, 'videos/detail.html', context)


def video_delete(request, video_id):
    """Eliminar un video"""
    video = get_object_or_404(Video, id=video_id)
    project_id = video.project.id
    
    if request.method == 'POST':
        # Eliminar archivo de GCS si existe
        if video.gcs_path:
            try:
                gcs_storage.delete_file(video.gcs_path)
            except Exception as e:
                logger.error(f"Error al eliminar archivo de GCS: {str(e)}")
        
        video_title = video.title
        video.delete()
        messages.success(request, f'Video "{video_title}" eliminado')
        return redirect('core:project_detail', project_id=project_id)
    
    return render(request, 'videos/delete.html', {'video': video})


@require_http_methods(["POST"])
def video_generate(request, video_id):
    """Genera el video usando la API correspondiente"""
    video = get_object_or_404(Video, id=video_id)
    
    # Validar que no esté ya procesando o completado
    if video.status in ['processing', 'completed']:
        messages.warning(request, f'El video ya está en estado: {video.get_status_display()}')
        return redirect('core:video_detail', video_id=video.id)
    
    try:
        video.mark_as_processing()
        
        if video.type == 'heygen_avatar':
            # Validar API key
            if not settings.HEYGEN_API_KEY:
                raise ValueError('HEYGEN_API_KEY no está configurada')
            
            # Validar configuración requerida
            if not video.config.get('avatar_id'):
                raise ValueError('Avatar ID es requerido')
            if not video.config.get('voice_id'):
                raise ValueError('Voice ID es requerido')
            
            client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
            
            response = client.generate_video(
                script=video.script,
                title=video.title,
                avatar_id=video.config.get('avatar_id'),
                voice_id=video.config.get('voice_id'),
                has_background=video.config.get('has_background', False),
                background_url=video.config.get('background_url'),
                voice_speed=video.config.get('voice_speed', 1.0),
                voice_pitch=video.config.get('voice_pitch', 50),
                voice_emotion=video.config.get('voice_emotion', 'Excited'),
            )
            
            # Guardar el external_id
            video.external_id = response.get('data', {}).get('video_id')
            video.save()
            
            messages.success(request, 'Video enviado a HeyGen. El proceso puede tardar varios minutos.')
            
        elif video.type == 'gemini_veo':
            if not settings.GEMINI_API_KEY:
                raise ValueError('GEMINI_API_KEY no está configurada')
            
            client = GeminiVeoClient(api_key=settings.GEMINI_API_KEY)
            
            response = client.generate_video(
                prompt=video.script,
                title=video.title,
                duration=video.config.get('duration', 5),
                aspect_ratio=video.config.get('aspect_ratio', '16:9'),
            )
            
            video.external_id = response.get('video_id')
            video.save()
            
            messages.success(request, 'Video enviado a Gemini Veo para procesamiento')
        
        logger.info(f"Video {video.id} enviado. External ID: {video.external_id}")
        
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}")
        video.mark_as_error(str(e))
        messages.error(request, f'Error de configuración: {str(e)}')
    except Exception as e:
        logger.error(f"Error al generar video: {str(e)}")
        video.mark_as_error(str(e))
        messages.error(request, f'Error al generar video: {str(e)}')
    
    return redirect('core:video_detail', video_id=video.id)


@require_http_methods(["GET"])
def video_status(request, video_id):
    """Consulta el estado de un video en la API externa"""
    video = get_object_or_404(Video, id=video_id)
    
    if not video.external_id:
        return JsonResponse({
            'error': 'Video no tiene external_id',
            'status': video.status
        }, status=400)
    
    # Si ya está completado o con error, no consultar de nuevo
    if video.status in ['completed', 'error']:
        return JsonResponse({
            'status': video.status,
            'message': 'Video ya procesado',
            'updated_at': video.updated_at.isoformat()
        })
    
    try:
        if video.type == 'heygen_avatar':
            if not settings.HEYGEN_API_KEY:
                return JsonResponse({'error': 'HEYGEN_API_KEY no configurada'}, status=400)
            
            client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
            status_data = client.get_video_status(video.external_id)
            
            # Actualizar estado si está completado
            if status_data.get('status') == 'completed':
                video_url = status_data.get('video_url')
                if video_url:
                    try:
                        # Descargar y subir a GCS
                        gcs_path = f"projects/{video.project.id}/videos/{video.id}/final_video.mp4"
                        gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                        
                        # Extraer metadata adicional
                        metadata = {
                            'duration': status_data.get('duration'),
                            'video_url_original': video_url,
                            'thumbnail': status_data.get('thumbnail'),
                        }
                        
                        video.mark_as_completed(
                            gcs_path=gcs_full_path,
                            metadata=metadata
                        )
                        logger.info(f"Video {video.id} completado y subido a GCS")
                    except Exception as e:
                        logger.error(f"Error al subir a GCS: {str(e)}")
                        video.mark_as_error(f"Error al subir a storage: {str(e)}")
            
            elif status_data.get('status') == 'failed' or status_data.get('error'):
                error_msg = status_data.get('error', 'Video generation failed')
                video.mark_as_error(error_msg)
                logger.error(f"Video {video.id} failed: {error_msg}")
            
        elif video.type == 'gemini_veo':
            if not settings.GEMINI_API_KEY:
                return JsonResponse({'error': 'GEMINI_API_KEY no configurada'}, status=400)
            
            client = GeminiVeoClient(api_key=settings.GEMINI_API_KEY)
            status_data = client.get_video_status(video.external_id)
        
        return JsonResponse({
            'status': video.status,
            'external_status': status_data,
            'updated_at': video.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error al consultar estado: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'status': video.status
        }, status=500)


# API Endpoints para AJAX

@require_http_methods(["GET"])
def api_list_avatars(request):
    """Lista avatares disponibles de HeyGen"""
    if not settings.HEYGEN_API_KEY:
        return JsonResponse({
            'error': 'HEYGEN_API_KEY no configurada',
            'avatars': []
        }, status=400)
    
    try:
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        avatars = client.list_avatars()
        return JsonResponse({'avatars': avatars})
    except Exception as e:
        logger.error(f"Error al listar avatares: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'avatars': []
        }, status=500)


@require_http_methods(["GET"])
def api_list_voices(request):
    """Lista voces disponibles de HeyGen"""
    if not settings.HEYGEN_API_KEY:
        return JsonResponse({
            'error': 'HEYGEN_API_KEY no configurada',
            'voices': []
        }, status=400)
    
    try:
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        voices = client.list_voices()
        return JsonResponse({'voices': voices})
    except Exception as e:
        logger.error(f"Error al listar voces: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'voices': []
        }, status=500)
