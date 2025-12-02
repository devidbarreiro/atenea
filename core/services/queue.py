"""
Servicio para manejar el encolado de tareas de generación
"""
import logging
import uuid
from typing import Optional, Dict, Any
from django.contrib.auth.models import User
from celery import current_app
from core.models import GenerationTask, Video, Image, Audio, Scene

logger = logging.getLogger(__name__)


class QueueService:
    """Servicio para encolar tareas de generación"""
    
    # Mapeo de tipos de item a tipos de tarea y colas
    TASK_MAPPING = {
        'video': {
            'task': 'core.tasks.generate_video_task',
            'queue': 'video_generation',
            'priority': 5,
        },
        'image': {
            'task': 'core.tasks.generate_image_task',
            'queue': 'image_generation',
            'priority': 5,
        },
        'audio': {
            'task': 'core.tasks.generate_audio_task',
            'queue': 'audio_generation',
            'priority': 5,
        },
        'scene_preview': {
            'task': 'core.tasks.generate_scene_preview_task',
            'queue': 'scene_processing',
            'priority': 10,  # Previews tienen alta prioridad
        },
        'scene_combine': {
            'task': 'core.tasks.combine_video_audio_task',
            'queue': 'scene_processing',
            'priority': 5,
        },
    }
    
    @classmethod
    def enqueue_generation(
        cls,
        item,
        user: User,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None
    ) -> GenerationTask:
        """
        Encola una tarea de generación
        
        Args:
            item: Objeto Video, Image, Audio o Scene
            user: Usuario que crea la tarea
            task_type: Tipo de tarea ('video', 'image', 'audio', 'scene_preview', 'scene_combine')
            metadata: Metadata adicional (prompt, parámetros, etc.)
            priority: Prioridad opcional (sobrescribe la default)
        
        Returns:
            GenerationTask creada
        
        Raises:
            ValueError: Si el tipo de tarea no es válido
        """
        if task_type not in cls.TASK_MAPPING:
            raise ValueError(f"Tipo de tarea no válido: {task_type}. Opciones: {list(cls.TASK_MAPPING.keys())}")
        
        config = cls.TASK_MAPPING[task_type]
        
        # Obtener UUID del item (o convertir id a UUID temporalmente)
        def get_item_uuid(item_obj):
            """Obtiene el UUID del item, o genera uno desde el id si no existe"""
            if hasattr(item_obj, 'uuid') and item_obj.uuid:
                return item_obj.uuid
            # Si no tiene uuid, generar uno determinístico desde el id
            # Usar un namespace UUID v5 para mantener consistencia
            namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Namespace DNS
            return uuid.uuid5(namespace, f"{item_obj.__class__.__name__}:{item_obj.id}")
        
        if isinstance(item, Video):
            item_uuid = get_item_uuid(item)
        elif isinstance(item, Image):
            item_uuid = get_item_uuid(item)
        elif isinstance(item, Audio):
            item_uuid = get_item_uuid(item)
        elif isinstance(item, Scene):
            item_uuid = get_item_uuid(item)
        else:
            raise ValueError(f"Tipo de item no soportado: {type(item)}")
        
        # Verificar límite de tareas simultáneas por usuario
        active_tasks = GenerationTask.objects.filter(
            user=user,
            status__in=['queued', 'processing']
        ).count()
        
        max_concurrent = 10  # TODO: Hacer configurable por tipo de suscripción
        if active_tasks >= max_concurrent:
            raise ValueError(
                f"Límite de tareas simultáneas alcanzado ({max_concurrent}). "
                f"Tienes {active_tasks} tareas en cola o procesando."
            )
        
        # Guardar item_uuid en metadata para búsqueda
        task_metadata = metadata or {}
        if isinstance(item, (Image, Video, Audio)):
            task_metadata['item_uuid'] = str(item.uuid)
        elif isinstance(item, Scene):
            task_metadata['item_id'] = item.id  # Scene aún no tiene uuid
        
        # Crear GenerationTask
        task_uuid = uuid.uuid4()
        task = GenerationTask.objects.create(
            uuid=task_uuid,
            task_id=None,  # Se actualizará después de encolar (null para evitar UNIQUE constraint)
            user=user,
            task_type=task_type.split('_')[0],  # 'video', 'image', 'audio', 'scene'
            item_uuid=item_uuid,
            status='queued',
            queue_name=config['queue'],
            priority=priority or config['priority'],
            metadata=task_metadata
        )
        
        # Encolar tarea en Celery
        # Para Scene, pasar el ID numérico; para otros items, pasar el UUID string
        if isinstance(item, Scene):
            item_identifier = item.id  # Scene usa id numérico
        else:
            item_identifier = str(item_uuid)  # Video, Image, Audio usan UUID
        
        celery_task = current_app.send_task(
            config['task'],
            args=[str(task_uuid), item_identifier, user.id],
            kwargs={},
            queue=config['queue'],
            priority=priority or config['priority']
        )
        
        # Actualizar task_id
        task.task_id = celery_task.id
        task.save(update_fields=['task_id'])
        
        logger.info(
            f"Tarea encolada: {task_type} para {item.__class__.__name__} {item_uuid} "
            f"(Task ID: {celery_task.id}, Queue: {config['queue']})"
        )
        
        return task
    
    @classmethod
    def cancel_task(cls, task_uuid: uuid.UUID, reason: str = None) -> bool:
        """
        Cancela una tarea pendiente
        
        Args:
            task_uuid: UUID de la GenerationTask
            reason: Razón de cancelación
        
        Returns:
            True si se canceló exitosamente, False si no estaba en estado cancelable
        """
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            
            # Solo cancelar si está en cola o procesando
            if task.status not in ['queued', 'processing']:
                logger.warning(f"Tarea {task_uuid} no puede ser cancelada (estado: {task.status})")
                return False
            
            # Cancelar en Celery
            try:
                current_app.control.revoke(task.task_id, terminate=True)
            except Exception as e:
                logger.warning(f"Error cancelando tarea en Celery {task.task_id}: {e}")
            
            # Marcar como cancelada
            task.mark_as_cancelled(reason=reason)
            
            logger.info(f"Tarea {task_uuid} cancelada: {reason or 'Sin razón especificada'}")
            return True
            
        except GenerationTask.DoesNotExist:
            logger.error(f"Tarea {task_uuid} no encontrada")
            return False
    
    @classmethod
    def get_user_active_tasks(cls, user: User) -> int:
        """
        Obtiene el número de tareas activas de un usuario
        
        Args:
            user: Usuario
        
        Returns:
            Número de tareas en cola o procesando
        """
        return GenerationTask.objects.filter(
            user=user,
            status__in=['queued', 'processing']
        ).count()
    
    @classmethod
    def get_user_tasks(cls, user: User, status: str = None, limit: int = 50):
        """
        Obtiene las tareas de un usuario
        
        Args:
            user: Usuario
            status: Filtrar por estado (opcional)
            limit: Límite de resultados
        
        Returns:
            QuerySet de GenerationTask
        """
        queryset = GenerationTask.objects.filter(user=user)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')[:limit]

