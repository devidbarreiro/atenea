"""
Tool para crear videos usando VideoService
Soporta múltiples servicios: Gemini Veo, Sora, Vuela AI, HeyGen
"""

from langchain.tools import tool
from typing import Dict, Optional, Literal
from django.contrib.auth.models import User

from core.services import VideoService, ValidationException, ServiceException, ProjectService
from core.models import Project


@tool
def create_video_tool(
    prompt: str,
    service: Literal['gemini_veo', 'sora', 'heygen'] = 'gemini_veo',
    title: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: int = None,
    # Parámetros específicos por servicio
    veo_model: Optional[str] = None,  # Modelo de Veo (ej: 'veo-2.0-generate-001', 'veo-3.0-generate-001')
    duration: Optional[int] = None,  # Duración en segundos
    aspect_ratio: Optional[str] = None,  # '16:9' o '9:16'
    # Parámetros para HeyGen
    avatar_id: Optional[str] = None,
    voice_id: Optional[str] = None,
        # Parámetros para Sora
        sora_model: Optional[str] = None,  # 'sora-2' por defecto
        sora_size: Optional[str] = None,  # '1280x720' por defecto
) -> Dict:
    """
    Crea un video usando diferentes servicios de IA (Gemini Veo, Sora, HeyGen).
    
    Args:
        prompt: Descripción del video a generar (o guión para HeyGen)
        service: Servicio a usar ('gemini_veo', 'sora', 'heygen')
        title: Título opcional para el video
        project_id: ID del proyecto donde crear el video (opcional)
        user_id: ID del usuario que crea el video (requerido)
        
        # Parámetros para Gemini Veo
        veo_model: Modelo de Veo a usar (default: 'veo-2.0-generate-001')
        duration: Duración en segundos (default según modelo: 5-8s para Veo 2.0, 4-8s para Veo 3.0)
        aspect_ratio: Relación de aspecto ('16:9' o '9:16', default: '16:9')
        
        # Parámetros para HeyGen
        avatar_id: ID del avatar de HeyGen (requerido para HeyGen)
        voice_id: ID de la voz de HeyGen (requerido para HeyGen)
        
        # Parámetros para Sora
        sora_model: Modelo de Sora ('sora-2' por defecto)
        sora_size: Tamaño del video ('1280x720' por defecto)
        
        # Parámetros para Vuela AI
        vuela_voice_id: ID de voz de Vuela AI
        vuela_voice_style: Estilo de voz ('narrative', 'expressive', 'dynamic')
    
    Returns:
        Dict con status, video_id, title, message, preview_url, detail_url, status_current
    """
    try:
        # Validaciones básicas
        if not prompt or not prompt.strip():
            return {'status': 'error', 'message': 'El prompt es requerido'}

        if not user_id:
            return {'status': 'error', 'message': 'user_id es requerido'}

        # Obtener usuario
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {'status': 'error', 'message': f'Usuario {user_id} no encontrado'}

        # Obtener o validar proyecto
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                if not ProjectService.user_can_edit(project, user):
                    return {'status': 'error', 'message': 'No tienes permisos para este proyecto'}
            except Project.DoesNotExist:
                return {'status': 'error', 'message': f'Proyecto {project_id} no encontrado'}

        # Generar título automático
        if not title:
            title = f"Video: {prompt[:50]}..." if len(prompt) > 50 else f"Video: {prompt}"

        # Crear servicio
        video_service = VideoService()

        # Configurar según el servicio
        video_type = None
        config = {}

        if service == 'gemini_veo':
            video_type = 'gemini_veo'
            config = {
                'veo_model': veo_model or 'veo-2.0-generate-001',
                'aspect_ratio': aspect_ratio or '16:9',
                'duration': duration or 5,  # Mínimo 5s para veo-2.0, 4s para veo-3.0
                'enhance_prompt': True
            }
            
        elif service == 'sora':
            video_type = 'sora'
            config = {
                'sora_model': sora_model or 'sora-2',
                'size': sora_size or '1280x720',
                'duration': duration or 8  # Sora: 4, 8 o 12 segundos
            }
            
        elif service == 'heygen':
            if not avatar_id or not voice_id:
                return {
                    'status': 'error',
                    'message': 'avatar_id y voice_id son requeridos para HeyGen. Usa list_avatars_tool y list_voices_tool para obtenerlos.'
                }
            video_type = 'heygen_avatar_v2'
            config = {
                'avatar_id': avatar_id,
                'voice_id': voice_id,
                'aspect_ratio': aspect_ratio or '16:9',
                'voice_speed': 1.0,
                'voice_pitch': 50,
                'voice_emotion': 'Excited'
            }
        else:
            return {'status': 'error', 'message': f'Servicio no soportado: {service}'}

        # Crear entidad Video en BD usando el servicio existente
        video = video_service.create_video(
            created_by=user,
            project=project,
            title=title,
            video_type=video_type,
            script=prompt,
            config=config
        )

        # Generar video usando el servicio existente (con todas sus validaciones)
        try:
            video_service.generate_video(video)

            preview_url = None
            if video.status == 'completed' and video.gcs_path:
                try:
                    video_data = video_service.get_video_with_signed_url(video)
                    preview_url = video_data.get('signed_url')
                except Exception:
                    pass

            return {
                'status': 'success',
                'video_id': video.id,
                'title': video.title,
                'message': f'Video "{video.title}" creado exitosamente con {service}',
                'preview_url': preview_url,
                'detail_url': f'/videos/{video.uuid}/',
                'status_current': video.status
            }

        except (ValidationException, ServiceException) as e:
            return {
                'status': 'partial_success',
                'video_id': video.id,
                'title': video.title,
                'message': f'Video creado pero hubo un error durante la generación: {str(e)}',
                'detail_url': f'/videos/{video.uuid}/',
                'status_current': video.status
            }

    except Exception as e:
        return {'status': 'error', 'message': f'Error al crear video: {str(e)}'}
