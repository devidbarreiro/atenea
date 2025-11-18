"""
EJEMPLO: Celery Tasks - Mejores Prácticas
==========================================

Implementación de tareas asíncronas con Celery
"""

from celery import shared_task, Task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from core.models import Video
from core.services import VideoService

logger = get_task_logger(__name__)


# ====================
# CUSTOM TASK BASE CLASS
# ====================

class CallbackTask(Task):
    """Task base con callbacks para retry y error"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Callback cuando falla la tarea"""
        logger.error(f'Task {task_id} failed: {exc}')
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Callback cuando se reintenta"""
        logger.warning(f'Task {task_id} retrying: {exc}')
        super().on_retry(exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Callback cuando tiene éxito"""
        logger.info(f'Task {task_id} succeeded')
        super().on_success(retval, task_id, args, kwargs)


# ====================
# VIDEO GENERATION TASKS
# ====================

@shared_task(
    base=CallbackTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def generate_video_task(self, video_id):
    """
    Tarea para generar un video
    
    Args:
        video_id: ID del video a generar
    """
    logger.info(f'Iniciando generación de video {video_id}')
    
    try:
        video = Video.objects.get(id=video_id)
        service = VideoService()
        
        external_id = service.generate_video(video)
        
        logger.info(f'Video {video_id} enviado. External ID: {external_id}')
        
        # Programar tarea de polling
        poll_video_status_task.apply_async(
            args=[video_id],
            countdown=30  # Empezar a consultar después de 30 segundos
        )
        
        return {
            'video_id': video_id,
            'external_id': external_id,
            'status': 'processing'
        }
        
    except Video.DoesNotExist:
        logger.error(f'Video {video_id} no encontrado')
        raise
    
    except Exception as e:
        logger.error(f'Error generando video {video_id}: {str(e)}')
        # Reintentar después de 60 segundos
        raise self.retry(exc=e, countdown=60)


@shared_task(
    base=CallbackTask,
    bind=True,
    max_retries=120,  # 120 reintentos = 1 hora con intervalos de 30s
    default_retry_delay=30
)
def poll_video_status_task(self, video_id):
    """
    Tarea para consultar el estado de un video periódicamente
    
    Args:
        video_id: ID del video a consultar
    """
    logger.info(f'Consultando estado de video {video_id}')
    
    try:
        video = Video.objects.select_for_update().get(id=video_id)
        
        # Si ya está en estado final, no hacer nada
        if video.status in ['completed', 'error']:
            logger.info(f'Video {video_id} ya está en estado final: {video.status}')
            return {'video_id': video_id, 'status': video.status}
        
        service = VideoService()
        status_data = service.check_video_status(video)
        
        # Refrescar desde DB
        video.refresh_from_db()
        
        if video.status == 'completed':
            logger.info(f'✅ Video {video_id} completado!')
            
            # Enviar notificación
            notify_video_completed.delay(video_id)
            
            return {'video_id': video_id, 'status': 'completed'}
        
        elif video.status == 'error':
            logger.error(f'❌ Video {video_id} falló: {video.error_message}')
            
            # Enviar notificación de error
            notify_video_failed.delay(video_id)
            
            return {'video_id': video_id, 'status': 'error'}
        
        else:
            # Aún procesando - reintentar en 30 segundos
            logger.info(f'⏳ Video {video_id} aún procesando, reintentando...')
            raise self.retry(countdown=30)
    
    except Video.DoesNotExist:
        logger.error(f'Video {video_id} no encontrado')
        raise
    
    except Exception as e:
        logger.error(f'Error consultando estado: {str(e)}')
        raise self.retry(exc=e, countdown=30)


# ====================
# NOTIFICATION TASKS
# ====================

@shared_task(bind=True, max_retries=3)
def notify_video_completed(self, video_id):
    """
    Envía notificación cuando un video se completa
    
    Args:
        video_id: ID del video completado
    """
    try:
        video = Video.objects.get(id=video_id)
        
        # TODO: Enviar email al usuario cuando se implemente autenticación
        logger.info(f'📧 Notificación: Video {video.title} completado')
        
        # Ejemplo de envío de email
        # send_mail(
        #     subject=f'Video "{video.title}" completado',
        #     message=f'Tu video "{video.title}" ha sido generado exitosamente.',
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[video.project.owner.email],
        #     fail_silently=False,
        # )
        
        # TODO: Enviar notificación push
        # TODO: Crear notificación en-app
        
        return {'video_id': video_id, 'notification_sent': True}
        
    except Exception as e:
        logger.error(f'Error enviando notificación: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def notify_video_failed(self, video_id):
    """
    Envía notificación cuando un video falla
    
    Args:
        video_id: ID del video que falló
    """
    try:
        video = Video.objects.get(id=video_id)
        
        logger.warning(f'⚠️ Notificación: Video {video.title} falló')
        
        # TODO: Enviar email al usuario
        # send_mail(
        #     subject=f'Error en video "{video.title}"',
        #     message=f'Hubo un error al generar el video "{video.title}": {video.error_message}',
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[video.project.owner.email],
        #     fail_silently=False,
        # )
        
        return {'video_id': video_id, 'notification_sent': True}
        
    except Exception as e:
        logger.error(f'Error enviando notificación de fallo: {str(e)}')
        raise self.retry(exc=e, countdown=60)


# ====================
# CLEANUP TASKS
# ====================

@shared_task
def cleanup_old_temp_files():
    """
    Limpia archivos temporales antiguos
    Ejecutar diariamente
    """
    import os
    from datetime import datetime, timedelta
    
    logger.info('Limpiando archivos temporales antiguos')
    
    temp_dir = settings.BASE_DIR / 'temp_uploads'
    if not temp_dir.exists():
        return
    
    # Eliminar archivos más antiguos de 7 días
    cutoff_date = datetime.now() - timedelta(days=7)
    deleted_count = 0
    
    for filename in os.listdir(temp_dir):
        file_path = temp_dir / filename
        
        if file_path.is_file():
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if file_time < cutoff_date:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f'Eliminado: {filename}')
                except Exception as e:
                    logger.error(f'Error eliminando {filename}: {e}')
    
    logger.info(f'Limpieza completada. {deleted_count} archivos eliminados')
    return {'deleted_count': deleted_count}


@shared_task
def cleanup_failed_videos():
    """
    Elimina videos en estado de error después de 30 días
    Ejecutar semanalmente
    """
    from datetime import datetime, timedelta
    
    logger.info('Limpiando videos fallidos antiguos')
    
    cutoff_date = datetime.now() - timedelta(days=30)
    old_failed_videos = Video.objects.filter(
        status='error',
        updated_at__lt=cutoff_date
    )
    
    count = old_failed_videos.count()
    old_failed_videos.delete()
    
    logger.info(f'{count} videos fallidos antiguos eliminados')
    return {'deleted_count': count}


# ====================
# MONITORING TASKS
# ====================

@shared_task
def check_stuck_videos():
    """
    Detecta videos atascados en estado 'processing' por mucho tiempo
    Ejecutar cada hora
    """
    from datetime import datetime, timedelta
    
    logger.info('Verificando videos atascados')
    
    # Videos procesando por más de 2 horas
    cutoff_time = datetime.now() - timedelta(hours=2)
    stuck_videos = Video.objects.filter(
        status='processing',
        updated_at__lt=cutoff_time
    )
    
    for video in stuck_videos:
        logger.warning(f'⚠️ Video {video.id} atascado en processing')
        
        # Reintentar consultar estado
        poll_video_status_task.delay(video.id)
    
    return {'stuck_videos_count': stuck_videos.count()}


@shared_task
def generate_daily_report():
    """
    Genera reporte diario de videos
    Ejecutar diariamente a las 9 AM
    """
    from datetime import datetime, timedelta
    
    logger.info('Generando reporte diario')
    
    yesterday = datetime.now() - timedelta(days=1)
    
    stats = {
        'date': yesterday.date().isoformat(),
        'total_videos_created': Video.objects.filter(
            created_at__date=yesterday.date()
        ).count(),
        'videos_completed': Video.objects.filter(
            status='completed',
            completed_at__date=yesterday.date()
        ).count(),
        'videos_failed': Video.objects.filter(
            status='error',
            updated_at__date=yesterday.date()
        ).count(),
    }
    
    logger.info(f'Reporte diario: {stats}')
    
    # TODO: Enviar por email a administradores
    # send_mail(
    #     subject=f'Reporte Diario - {stats["date"]}',
    #     message=f'Estadísticas:\n{stats}',
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[email for name, email in settings.ADMINS],
    # )
    
    return stats


# ====================
# CELERY BEAT SCHEDULE
# ====================

"""
# En settings.py o celery.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Limpieza de archivos temporales (diaria a las 3 AM)
    'cleanup-temp-files': {
        'task': 'core.tasks.cleanup_old_temp_files',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Limpieza de videos fallidos (semanal, domingos a las 4 AM)
    'cleanup-failed-videos': {
        'task': 'core.tasks.cleanup_failed_videos',
        'schedule': crontab(day_of_week=0, hour=4, minute=0),
    },
    
    # Verificar videos atascados (cada hora)
    'check-stuck-videos': {
        'task': 'core.tasks.check_stuck_videos',
        'schedule': crontab(minute=0),  # Cada hora en el minuto 0
    },
    
    # Reporte diario (9 AM)
    'daily-report': {
        'task': 'core.tasks.generate_daily_report',
        'schedule': crontab(hour=9, minute=0),
    },
}
"""


# ====================
# CELERY.PY CONFIGURATION
# ====================

"""
# atenea/celery.py

import os
from celery import Celery
from django.conf import settings

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')

app = Celery('atenea')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# En atenea/__init__.py:

from .celery import app as celery_app

__all__ = ('celery_app',)
"""


# ====================
# CÓMO EJECUTAR
# ====================

"""
1. Instalar Redis:
   docker run -d -p 6379:6379 redis

2. Instalar dependencias:
   pip install celery redis django-celery-beat django-celery-results

3. Iniciar worker de Celery:
   celery -A atenea worker -l info

4. Iniciar Celery Beat (tareas programadas):
   celery -A atenea beat -l info

5. Ambos en un solo comando (desarrollo):
   celery -A atenea worker -B -l info

6. Monitor (Flower):
   pip install flower
   celery -A atenea flower

7. Producción (con supervisor o systemd):
   # /etc/supervisor/conf.d/celery.conf
   [program:celery]
   command=/path/to/venv/bin/celery -A atenea worker -l info
   directory=/path/to/project
   user=www-data
   autostart=true
   autorestart=true
"""


# ====================
# TESTING CELERY TASKS
# ====================

"""
# En tests.py

from unittest.mock import patch
from django.test import TestCase
from core.tasks import generate_video_task

class CeleryTaskTests(TestCase):
    
    @patch('core.services.VideoService.generate_video')
    def test_generate_video_task(self, mock_generate):
        mock_generate.return_value = 'external123'
        
        video = Video.objects.create(...)
        
        # Ejecutar tarea síncronamente (sin Celery)
        result = generate_video_task.apply(args=[video.id])
        
        self.assertTrue(result.successful())
        self.assertEqual(result.result['external_id'], 'external123')
"""

