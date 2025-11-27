"""
Tool para crear videos de citas usando Manim
Wrapper ligero que reutiliza la lógica existente
"""

from langchain.tools import tool
from typing import Dict, Optional
from django.contrib.auth.models import User

from core.services import VideoService, ValidationException, ServiceException, ProjectService
from core.models import Project


@tool
def create_quote_tool(
    quote: str,
    author: Optional[str] = None,
    title: Optional[str] = None,
    duration: Optional[float] = None,
    quality: Optional[str] = 'k',
    container_color: Optional[str] = None,
    text_color: Optional[str] = None,
    font_family: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: int = None
) -> Dict:
    """
    Crea un video de cita animada usando Manim desde texto.
    
    Args:
        quote: Texto de la cita a animar
        author: Nombre del autor (opcional)
        title: Título opcional para el video (si no se proporciona, se genera automáticamente)
        duration: Duración en segundos (opcional, se calcula automáticamente basado en longitud del texto)
        quality: Calidad de renderizado ('l'=baja, 'm'=media, 'h'=alta, 'k'=4K máxima, default: 'k')
        container_color: Color del contenedor en formato hex (ej: '#0066CC', default: '#0066CC' azul)
        text_color: Color del texto en formato hex (ej: '#FFFFFF', default: '#FFFFFF' blanco)
        font_family: Tipo de fuente ('normal', 'bold', 'italic', 'bold_italic', default: 'normal')
        project_id: ID del proyecto donde crear el video (opcional, se crea sin proyecto si no se especifica)
        user_id: ID del usuario que crea el video (requerido)
    
    Returns:
        Dict con:
            - status: 'success' o 'error'
            - video_id: ID del video creado
            - title: Título del video
            - message: Mensaje descriptivo
            - preview_url: URL de preview (si está disponible inmediatamente)
            - detail_url: URL para ver detalles del video
    """
    try:
        # Validaciones básicas
        if not quote or not quote.strip():
            return {
                'status': 'error',
                'message': 'El texto de la cita es requerido'
            }
        
        if not user_id:
            return {
                'status': 'error',
                'message': 'user_id es requerido'
            }
        
        # Obtener usuario
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {
                'status': 'error',
                'message': f'Usuario {user_id} no encontrado'
            }
        
        # Obtener proyecto (opcional, si no se especifica se crea sin proyecto)
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                # Validar permisos
                if not ProjectService.user_can_edit(project, user):
                    return {
                        'status': 'error',
                        'message': 'No tienes permisos para crear contenido en este proyecto'
                    }
            except Project.DoesNotExist:
                return {
                    'status': 'error',
                    'message': f'Proyecto {project_id} no encontrado'
                }
        # Si no se especifica project_id, project=None (sin proyecto)
        
        # Generar título si no se proporciona
        if not title:
            if author:
                title = f"Cita: {quote[:40]}..." if len(quote) > 40 else f"Cita: {quote}"
            else:
                title = f"Cita: {quote[:50]}..." if len(quote) > 50 else f"Cita: {quote}"
        
        # Validar calidad
        if quality not in ['l', 'm', 'h', 'k']:
            quality = 'k'  # Default a máxima calidad
        
        # Validar font_family
        if font_family not in ['normal', 'bold', 'italic', 'bold_italic']:
            font_family = 'normal'  # Default a normal
        
        # Validar colores (deben ser formato hex válido)
        if container_color and not container_color.startswith('#'):
            container_color = None  # Invalidar si no es hex
        if text_color and not text_color.startswith('#'):
            text_color = None  # Invalidar si no es hex
        
        # Crear video usando el servicio existente
        video_service = VideoService()
        
        # Configuración para Manim
        config = {
            'author': author,
            'duration': duration,
            'quality': quality,
            'container_color': container_color or '#0066CC',  # Default azul
            'text_color': text_color or '#FFFFFF',  # Default blanco
            'font_family': font_family or 'normal',  # Default normal
        }
        
        # Crear video en BD
        video = video_service.create_video(
            title=title,
            video_type='manim_quote',
            script=quote,  # El texto de la cita va en script
            config=config,
            created_by=user,
            project=project
        )
        
        # Generar video (Manim genera síncronamente)
        try:
            video_service.generate_video(video)
            
            # Refrescar video para obtener estado actualizado
            video.refresh_from_db()
            
            # Intentar obtener preview si está disponible inmediatamente
            preview_url = None
            if video.status == 'completed' and video.gcs_path:
                try:
                    from core.storage.gcs import gcs_storage
                    preview_url = gcs_storage.get_signed_url(video.gcs_path)
                except Exception:
                    pass  # Si no está disponible aún, no pasa nada
            
            return {
                'status': 'success',
                'video_id': video.id,
                'title': video.title,
                'message': f'Video de cita "{video.title}" creado exitosamente',
                'preview_url': preview_url,
                'detail_url': f'/videos/{video.id}/',
                'status_current': video.status  # 'pending', 'processing', 'completed', 'error'
            }
            
        except (ValidationException, ServiceException) as e:
            # Si falla la generación, el video ya está creado en BD
            return {
                'status': 'partial_success',
                'video_id': video.id,
                'title': video.title,
                'message': f'Video creado pero hubo un error al generarlo: {str(e)}',
                'detail_url': f'/videos/{video.id}/',
                'status_current': video.status
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error al crear video de cita: {str(e)}'
        }

