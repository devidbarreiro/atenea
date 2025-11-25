"""
Tool para crear videos usando VideoService
Es equivalente a create_image_tool, pero para video.
"""

from langchain.tools import tool
from typing import Dict, Optional
from django.contrib.auth.models import User

from core.services import VideoService, ValidationException, ServiceException, ProjectService
from core.models import Project


@tool
def create_video_tool(
    prompt: str,
    title: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: int = None
) -> Dict:
    """
    Crea un video usando Gemini Video desde un prompt de texto.
    
    Args:
        prompt: Descripción del video a generar
        title: Título opcional para el video (si no se proporciona, se genera automáticamente)
        project_id: ID del proyecto donde crear el video (opcional, se crea proyecto automático si no se especifica)
        user_id: ID del usuario que crea el video (requerido)
    
    Returns:
        Dict con:
            - status: 'success' o 'error'
            - image_id: ID de la imagen creada
            - title: Título de la imagen
            - message: Mensaje descriptivo
            - preview_url: URL de preview (si está disponible inmediatamente)
            - detail_url: URL para ver detalles de la imagen
    """
    try:
        # Validaciones
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

        # Configuración ejemplo (ajustar según tu implementación)
        config = {
            'model': 'veo-2.0-generate-001',
            'aspect_ratio': '16:9',
            'duration': '4s',          # opcional
            'safety_settings': 'default'
        }

        # Crear entidad Video en BD
        video = video_service.create_video(
            title=title,
            video_type='text_to_video',
            prompt=prompt,
            config=config,
            created_by=user,
            project=project
        )

        # Generar video (puede ser async o sync según tu sistema)
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
                'message': f'Video "{video.title}" creado exitosamente',
                'preview_url': preview_url,
                'detail_url': f'/videos/{video.id}/',
                'status_current': video.status  # pending | processing | completed
            }

        except (ValidationException, ServiceException) as e:
            return {
                'status': 'partial_success',
                'video_id': video.id,
                'title': video.title,
                'message': f'Video creado pero hubo un error durante la generación: {str(e)}',
                'detail_url': f'/videos/{video.id}/',
                'status_current': video.status
            }

    except Exception as e:
        return {'status': 'error', 'message': f'Error al crear video: {str(e)}'}
