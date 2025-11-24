"""
Tool para crear imágenes usando ImageService
Wrapper ligero que reutiliza la lógica existente
"""

from langchain.tools import tool
from typing import Dict, Optional
from django.contrib.auth.models import User

from core.services import ImageService, ValidationException, ServiceException, ProjectService
from core.models import Project


@tool
def create_image_tool(
    prompt: str,
    title: Optional[str] = None,
    project_id: Optional[int] = None,
    user_id: int = None
) -> Dict:
    """
    Crea una imagen usando Gemini Image desde un prompt de texto.
    
    Args:
        prompt: Descripción de la imagen a generar
        title: Título opcional para la imagen (si no se proporciona, se genera automáticamente)
        project_id: ID del proyecto donde crear la imagen (opcional, se crea proyecto automático si no se especifica)
        user_id: ID del usuario que crea la imagen (requerido)
    
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
        # Validaciones básicas
        if not prompt or not prompt.strip():
            return {
                'status': 'error',
                'message': 'El prompt es requerido'
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
            title = f"Imagen: {prompt[:50]}..." if len(prompt) > 50 else f"Imagen: {prompt}"
        
        # Crear imagen usando el servicio existente
        image_service = ImageService()
        
        # Configuración por defecto para text_to_image
        config = {
            'model': 'gemini-2.0-flash-exp',
            'aspect_ratio': '16:9',
            'safety_settings': 'default'
        }
        
        # Crear imagen en BD
        image = image_service.create_image(
            title=title,
            image_type='text_to_image',
            prompt=prompt,
            config=config,
            created_by=user,
            project=project
        )
        
        # Generar imagen (esto puede ser asíncrono o síncrono según el servicio)
        try:
            image_service.generate_image(image)
            
            # Intentar obtener preview si está disponible inmediatamente
            preview_url = None
            if image.status == 'completed' and image.gcs_path:
                try:
                    image_data = image_service.get_image_with_signed_url(image)
                    preview_url = image_data.get('signed_url')
                except Exception:
                    pass  # Si no está disponible aún, no pasa nada
            
            return {
                'status': 'success',
                'image_id': image.id,
                'title': image.title,
                'message': f'Imagen "{image.title}" creada exitosamente',
                'preview_url': preview_url,
                'detail_url': f'/images/{image.id}/',
                'status_current': image.status  # 'pending', 'processing', 'completed', 'error'
            }
            
        except (ValidationException, ServiceException) as e:
            # Si falla la generación, la imagen ya está creada en BD
            return {
                'status': 'partial_success',
                'image_id': image.id,
                'title': image.title,
                'message': f'Imagen creada pero hubo un error al generarla: {str(e)}',
                'detail_url': f'/images/{image.id}/',
                'status_current': image.status
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error al crear imagen: {str(e)}'
        }

