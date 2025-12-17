"""
Celery tasks para generación de contenido

Las tareas delegan toda la lógica de selección de servicios a los métodos
generate_* de los servicios existentes. Esto permite que añadir nuevos
servicios no requiera modificar estas tareas.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from core.models import GenerationTask, Video, Image, Audio, Scene, Notification
from core.services import VideoService, ImageService, AudioService

# rembg imports are done lazily inside the task to avoid CI failures
# (rembg requires onnxruntime which is heavy and not needed for tests)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_video_task(self, task_uuid, video_uuid, user_id, **kwargs):
    """
    Tarea para generar un video
    
    Args:
        task_uuid: UUID de la GenerationTask
        video_uuid: UUID del Video
        user_id: ID del usuario
        **kwargs: Parámetros adicionales (no se usan, el video ya tiene toda la info)
    
    Nota: El VideoService.generate_video() ya maneja internamente la selección
    del servicio correcto según video.type. No necesitamos hacerlo aquí.
    """
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        task.mark_as_processing()
        
        user = User.objects.get(id=user_id)
        
        # Buscar video: primero por UUID desde metadata, luego por UUID de la tarea
        item_uuid = task.metadata.get('item_uuid')
        if item_uuid:
            video = Video.objects.get(uuid=item_uuid)
        else:
            video = Video.objects.get(uuid=video_uuid)
        
        # El servicio ya maneja la selección del servicio correcto según video.type
        video_service = VideoService()
        external_id = video_service.generate_video(video=video)
        
        # Recargar para ver el estado actual
        video.refresh_from_db()
        
        # Para Veo (asíncrono): el video queda en 'processing', NO marcar como completed
        # El polling task se encargará de verificar cuando termine
        # Para servicios síncronos: el video ya está en 'completed'
        
        if video.status == 'completed':
            # Servicio síncrono - ya terminó
            task.mark_as_completed()
            from core.models import Notification
            Notification.create_notification(
                user=user,
                type='generation_completed',
                title='Video generado',
                message=f'Tu video "{video.title}" está listo',
                action_url=f'/videos/{video.uuid}/',
                action_label='Ver video',
                metadata={'item_type': 'video', 'item_uuid': str(video.uuid)}
            )
            logger.info(f"Video {video.uuid} generado exitosamente (síncrono).")
            return {'status': 'completed', 'video_uuid': str(video.uuid), 'external_id': external_id}
        else:
            # Servicio asíncrono (Veo) - solo se envió, hay que hacer polling
            # Programar primer poll en 30 segundos (Veo tarda ~2-5 minutos)
            poll_video_status_task.apply_async(
                args=[str(task_uuid), str(video.uuid), user_id],
                countdown=30  # Primer check en 30 segundos
            )
            logger.info(f"Video {video.uuid} enviado a generación asíncrona. Polling programado. External ID: {external_id}")
            return {'status': 'processing', 'video_uuid': str(video.uuid), 'external_id': external_id}
        
    except Exception as exc:
        logger.error(f"Error generando video {video_uuid}: {exc}", exc_info=True)
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            task.mark_as_failed(str(exc))
            
            # Obtener título del video si está disponible
            video_title = "sin título"
            try:
                item_uuid = task.metadata.get('item_uuid')
                if item_uuid:
                    vid = Video.objects.filter(uuid=item_uuid).first()
                    if vid:
                        video_title = vid.title
            except Exception:
                pass  # Ignorar errores al obtener título para notificación
            
            # Crear notificación de error solo si no se va a reintentar
            if task.retry_count >= task.max_retries:
                from core.models import Notification
                Notification.create_notification(
                    user=user,
                    type='generation_failed',
                    title='Error al generar video',
                    message=f'No se pudo generar el video "{video_title}": {str(exc)[:100]}',
                    metadata={'item_type': 'video', 'item_uuid': str(video_uuid), 'error': str(exc)}
                )
            
            # Reintentar si no se ha alcanzado el máximo
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.save(update_fields=['retry_count'])
                raise self.retry(exc=exc, countdown=60 * (2 ** task.retry_count))
        except Exception as inner_exc:
            logger.error(f"Error adicional al manejar fallo: {inner_exc}")
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def generate_image_task(self, task_uuid, image_uuid, user_id, **kwargs):
    """
    Tarea para generar una imagen
    
    Args:
        task_uuid: UUID de la GenerationTask
        image_uuid: UUID de la Image
        user_id: ID del usuario
        **kwargs: Parámetros adicionales (no se usan, la imagen ya tiene toda la info)
    
    Nota: El ImageService.generate_image() ya maneja internamente la selección
    del servicio correcto según image.config['model_id']. No necesitamos hacerlo aquí.
    """
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        task.mark_as_processing()
        
        user = User.objects.get(id=user_id)
        
        # Buscar imagen: primero por UUID desde metadata, luego por UUID de la tarea
        item_uuid = task.metadata.get('item_uuid')
        if item_uuid:
            image = Image.objects.filter(uuid=item_uuid).first()
        else:
            image = Image.objects.filter(uuid=image_uuid).first()
        
        # Si la imagen no existe, marcar tarea como fallida sin reintentar
        if not image:
            error_msg = f"Imagen no encontrada (UUID: {item_uuid or image_uuid}). Puede haber sido eliminada."
            logger.warning(f"[generate_image_task] {error_msg}")
            task.mark_as_failed(error_msg)
            # No crear notificación porque la imagen ya no existe
            return {'status': 'failed', 'error': error_msg, 'image_uuid': str(item_uuid or image_uuid)}
        
        # Marcar imagen como processing ANTES de generar (para evitar doble procesamiento)
        if image.status != 'processing':
            image.status = 'processing'
            image.save(update_fields=['status', 'updated_at'])
        
        # El servicio ya maneja la selección del servicio correcto según image.config
        image_service = ImageService()
        # Pasar skip_status_check=True para evitar validación de estado (ya la validamos arriba)
        gcs_path = image_service.generate_image(image=image, skip_status_check=True)
        
        task.mark_as_completed()
        
        # Crear notificación de éxito
        from core.models import Notification
        Notification.create_notification(
            user=user,
            type='generation_completed',
            title='Imagen generada',
            message=f'Tu imagen "{image.title}" está lista',
            action_url=f'/images/{image.uuid}/',
            action_label='Ver imagen',
            metadata={'item_type': 'image', 'item_uuid': str(image.uuid)}
        )
        
        logger.info(f"Imagen {image_uuid} generada exitosamente. GCS Path: {gcs_path}")
        return {'status': 'completed', 'image_uuid': str(image_uuid), 'gcs_path': gcs_path}
        
    except Exception as exc:
        logger.error(f"Error generando imagen {image_uuid}: {exc}", exc_info=True)
        task = None
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            task.mark_as_failed(str(exc))
            
            # Obtener título de imagen si está disponible
            image_title = "sin título"
            try:
                item_uuid = task.metadata.get('item_uuid')
                if item_uuid:
                    img = Image.objects.filter(uuid=item_uuid).first()
                    if img:
                        image_title = img.title
            except Exception:
                pass  # Ignorar errores al obtener título para notificación
            
            # Crear notificación de error solo si no se va a reintentar
            if task.retry_count >= task.max_retries:
                from core.models import Notification
                try:
                    user = User.objects.get(id=user_id)
                    Notification.create_notification(
                        user=user,
                        type='generation_failed',
                        title='Error al generar imagen',
                        message=f'No se pudo generar la imagen "{image_title}": {str(exc)[:100]}',
                        metadata={'item_type': 'image', 'item_uuid': str(image_uuid), 'error': str(exc)}
                    )
                except User.DoesNotExist:
                    pass
        except Exception as inner_exc:
            logger.error(f"Error adicional al manejar fallo: {inner_exc}")
        
        # Solo reintentar si pudimos obtener la task
        if task and task.retry_count < task.max_retries:
            task.retry_count += 1
            task.save(update_fields=['retry_count'])
    
    @shared_task(bind=True, max_retries=3)
    def upscale_image_task(self, task_uuid, image_uuid, user_id, **kwargs):
        """
        Tarea para escalar una imagen usando Vertex AI Imagen Upscale
        
        Args:
            task_uuid: UUID de la GenerationTask
            image_uuid: UUID de la Image escalada (la nueva imagen creada)
            user_id: ID del usuario
            **kwargs: Parámetros adicionales
        """
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            task.mark_as_processing()
            
            user = User.objects.get(id=user_id)
            
            # Buscar imagen escalada: primero por UUID desde metadata, luego por UUID de la tarea
            item_uuid = task.metadata.get('item_uuid') or task.metadata.get('upscaled_image_uuid')
            if item_uuid:
                upscaled_image = Image.objects.filter(uuid=item_uuid).first()
            else:
                upscaled_image = Image.objects.filter(uuid=image_uuid).first()
            
            # Si la imagen no existe, marcar tarea como fallida sin reintentar
            if not upscaled_image:
                error_msg = f"Imagen escalada no encontrada (UUID: {item_uuid or image_uuid}). Puede haber sido eliminada."
                logger.warning(f"[upscale_image_task] {error_msg}")
                task.mark_as_failed(error_msg)
                return {'status': 'failed', 'error': error_msg, 'image_uuid': str(item_uuid or image_uuid)}
            
            # Obtener imagen original desde metadata
            original_image_uuid = task.metadata.get('original_image_uuid')
            if not original_image_uuid:
                raise ValueError("No se encontró UUID de imagen original en metadata")
            
            original_image = Image.objects.filter(uuid=original_image_uuid).first()
            if not original_image:
                raise ValueError(f"Imagen original no encontrada: {original_image_uuid}")
            
            # Obtener parámetros desde metadata
            upscale_factor = task.metadata.get('upscale_factor', 'x4')
            output_mime_type = task.metadata.get('output_mime_type', 'image/png')
            
            # Marcar imagen como processing
            if upscaled_image.status != 'processing':
                upscaled_image.status = 'processing'
                upscaled_image.save(update_fields=['status', 'updated_at'])
            
            # Ejecutar upscale
            image_service = ImageService()
            upscaled_gcs_path = image_service.upscale_image(
                image=original_image,
                upscale_factor=upscale_factor,
                output_mime_type=output_mime_type
            )
            
            # Actualizar imagen escalada con el resultado
            upscaled_image.gcs_path = upscaled_gcs_path
            upscaled_image.mark_as_completed(gcs_path=upscaled_gcs_path)
            
            task.mark_as_completed()
            
            # Crear notificación de éxito
            Notification.create_notification(
                user=user,
                type='generation_completed',
                title='Imagen escalada',
                message=f'Tu imagen "{upscaled_image.title}" está lista',
                action_url=f'/images/{upscaled_image.uuid}/',
                action_label='Ver imagen',
                metadata={'item_type': 'image', 'item_uuid': str(upscaled_image.uuid)}
            )
            
            logger.info(f"Imagen escalada {upscaled_image.uuid} completada exitosamente. GCS Path: {upscaled_gcs_path}")
            return {'status': 'completed', 'image_uuid': str(upscaled_image.uuid), 'gcs_path': upscaled_gcs_path}
            
        except Exception as exc:
            logger.error(f"Error escalando imagen {image_uuid}: {exc}", exc_info=True)
            task = None
            try:
                task = GenerationTask.objects.get(uuid=task_uuid)
                task.mark_as_failed(str(exc))
                
                # Obtener título de imagen si está disponible
                image_title = "sin título"
                try:
                    item_uuid = task.metadata.get('item_uuid') or task.metadata.get('upscaled_image_uuid')
                    if item_uuid:
                        img = Image.objects.filter(uuid=item_uuid).first()
                        if img:
                            image_title = img.title
                            # Marcar imagen como error
                            img.mark_as_error(str(exc))
                except Exception:
                    pass
                
                # Crear notificación de error solo si no se va a reintentar
                if task.retry_count >= task.max_retries:
                    try:
                        user = User.objects.get(id=user_id)
                        Notification.create_notification(
                            user=user,
                            type='generation_failed',
                            title='Error al escalar imagen',
                            message=f'No se pudo escalar la imagen "{image_title}": {str(exc)[:100]}',
                            metadata={'item_type': 'image', 'item_uuid': str(image_uuid), 'error': str(exc)}
                        )
                    except User.DoesNotExist:
                        pass
            except Exception as inner_exc:
                logger.error(f"Error adicional al manejar fallo: {inner_exc}")
            
            # Solo reintentar si pudimos obtener la task
            if task and task.retry_count < task.max_retries:
                task.retry_count += 1
                task.save(update_fields=['retry_count'])
                raise self.retry(exc=exc, countdown=60 * (task.retry_count + 1))  # Backoff exponencial
            
            return {'status': 'failed', 'error': str(exc), 'image_uuid': str(image_uuid)}
            raise self.retry(exc=exc, countdown=60 * (2 ** task.retry_count))
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def generate_audio_task(self, task_uuid, audio_uuid, user_id, **kwargs):
    """
    Tarea para generar un audio
    
    Args:
        task_uuid: UUID de la GenerationTask
        audio_uuid: UUID del Audio
        user_id: ID del usuario
        **kwargs: Parámetros adicionales (with_timestamps, etc.)
    
    Nota: El AudioService.generate_audio() ya maneja internamente la selección
    del servicio correcto (ElevenLabs). No necesitamos hacerlo aquí.
    """
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        task.mark_as_processing()
        
        user = User.objects.get(id=user_id)
        
        # Buscar audio: primero por UUID desde metadata, luego por UUID de la tarea
        item_uuid = task.metadata.get('item_uuid')
        if item_uuid:
            audio = Audio.objects.get(uuid=item_uuid)
        else:
            audio = Audio.objects.get(uuid=audio_uuid)
        
        # El servicio ya maneja la selección del servicio correcto
        # with_timestamps viene de task.metadata, no de kwargs (que siempre está vacío)
        with_timestamps = task.metadata.get('with_timestamps', False)
        gcs_path = AudioService.generate_audio(audio=audio, with_timestamps=with_timestamps)
        
        task.mark_as_completed()
        
        # Crear notificación de éxito
        from core.models import Notification
        Notification.create_notification(
            user=user,
            type='generation_completed',
            title='Audio generado',
            message=f'Tu audio "{audio.title}" está listo',
            action_url=f'/audios/{audio.uuid}/',
            action_label='Ver audio',
            metadata={'item_type': 'audio', 'item_uuid': str(audio.uuid)}
        )
        
        logger.info(f"Audio {audio.uuid} generado exitosamente. GCS Path: {gcs_path}")
        return {'status': 'completed', 'audio_uuid': str(audio.uuid), 'gcs_path': gcs_path}
        
    except Exception as exc:
        logger.error(f"Error generando audio {audio_uuid}: {exc}", exc_info=True)
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            task.mark_as_failed(str(exc))
            
            # Obtener título del audio si está disponible
            audio_title = "sin título"
            try:
                item_uuid = task.metadata.get('item_uuid')
                if item_uuid:
                    aud = Audio.objects.filter(uuid=item_uuid).first()
                    if aud:
                        audio_title = aud.title
            except Exception:
                pass  # Ignorar errores al obtener título para notificación
            
            # Crear notificación de error solo si no se va a reintentar
            if task.retry_count >= task.max_retries:
                from core.models import Notification
                try:
                    user = User.objects.get(id=user_id)
                    Notification.create_notification(
                        user=user,
                        type='generation_failed',
                        title='Error al generar audio',
                        message=f'No se pudo generar el audio "{audio_title}": {str(exc)[:100]}',
                        metadata={'item_type': 'audio', 'item_uuid': str(audio_uuid), 'error': str(exc)}
                    )
                except User.DoesNotExist:
                    pass
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.save(update_fields=['retry_count'])
                raise self.retry(exc=exc, countdown=60 * (2 ** task.retry_count))
        except GenerationTask.DoesNotExist:
            pass
        except Exception as inner_exc:
            logger.error(f"Error adicional al manejar fallo: {inner_exc}")
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def generate_scene_preview_task(self, task_uuid, scene_id, user_id, **kwargs):
    """
    Tarea para generar imagen preview de una escena usando Gemini Image
    
    Args:
        task_uuid: UUID de la GenerationTask
        scene_id: ID numérico de la Scene (Scene usa id, no uuid)
        user_id: ID del usuario
        **kwargs: Parámetros adicionales (custom_prompt opcional)
    """
    from core.services import SceneService
    
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        task.mark_as_processing()
        
        user = User.objects.get(id=user_id)
        
        # Scene usa id numérico, no UUID
        try:
            scene_id_int = int(scene_id)
        except (ValueError, TypeError):
            raise ValueError(f"scene_id debe ser un entero, recibido: {scene_id}")
        
        scene = Scene.objects.get(id=scene_id_int)
        
        # Generar preview usando SceneService
        scene_service = SceneService()
        
        # Si hay un prompt personalizado en metadata, usarlo
        custom_prompt = task.metadata.get('custom_prompt')
        if custom_prompt:
            gcs_path = scene_service.generate_preview_image_with_prompt(scene, custom_prompt)
        else:
            gcs_path = scene_service.generate_preview_image(scene)
        
        task.mark_as_completed()
        
        # Crear notificación de éxito
        from core.models import Notification
        Notification.create_notification(
            user=user,
            type='generation_completed',
            title='Preview de escena generado',
            message=f'La imagen preview de la escena "{scene.scene_id}" está lista',
            action_url=f'/projects/{scene.project.uuid}/agent/scenes/' if scene.project else None,
            action_label='Ver escenas',
            metadata={'item_type': 'scene_preview', 'scene_id': scene_id_int}
        )
        
        logger.info(f"Preview de escena {scene_id} generado exitosamente. GCS Path: {gcs_path}")
        return {'status': 'completed', 'scene_id': scene_id_int, 'gcs_path': gcs_path}
        
    except Exception as exc:
        logger.error(f"Error generando preview de escena {scene_id}: {exc}", exc_info=True)
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            task.mark_as_failed(str(exc))
            
            # Crear notificación de error solo si no se va a reintentar
            if task.retry_count >= task.max_retries:
                try:
                    user = User.objects.get(id=user_id)
                    from core.models import Notification
                    Notification.create_notification(
                        user=user,
                        type='generation_failed',
                        title='Error al generar preview',
                        message=f'No se pudo generar el preview de la escena: {str(exc)[:100]}',
                        metadata={'item_type': 'scene_preview', 'scene_id': scene_id, 'error': str(exc)}
                    )
                except User.DoesNotExist:
                    pass
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.save(update_fields=['retry_count'])
                raise self.retry(exc=exc, countdown=60 * (2 ** task.retry_count))
        except GenerationTask.DoesNotExist:
            pass
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, max_retries=3)
def combine_video_audio_task(self, task_uuid, scene_id, user_id, **kwargs):
    """
    Tarea para combinar video y audio de una escena usando FFmpeg
    
    Esta tarea combina el video generado de una escena con su audio TTS,
    creando un video final con el audio narrado.
    
    Args:
        task_uuid: UUID de la GenerationTask
        scene_id: ID numérico de la Scene (Scene usa id, no uuid)
        user_id: ID del usuario
        **kwargs: Parámetros adicionales
    """
    from core.services import SceneService
    
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        task.mark_as_processing()
        
        user = User.objects.get(id=user_id)
        
        # Scene usa id numérico, no UUID
        try:
            scene_id_int = int(scene_id)
        except (ValueError, TypeError):
            raise ValueError(f"scene_id debe ser un entero, recibido: {scene_id}")
        
        scene = Scene.objects.get(id=scene_id_int)
        
        # Verificar que la escena tiene video y audio listos
        if scene.video_status != 'completed' or not scene.video_gcs_path:
            raise ValueError(f"La escena {scene.scene_id} no tiene video completado")
        
        if scene.audio_status != 'completed' or not scene.audio_gcs_path:
            raise ValueError(f"La escena {scene.scene_id} no tiene audio completado")
        
        # Combinar video y audio usando SceneService
        scene_service = SceneService()
        scene_service._auto_combine_video_audio_if_ready(scene)
        
        # Recargar escena para verificar resultado
        scene.refresh_from_db()
        
        if scene.final_video_status == 'completed':
            task.mark_as_completed()
            
            # Crear notificación de éxito
            from core.models import Notification
            Notification.create_notification(
                user=user,
                type='generation_completed',
                title='Video combinado',
                message=f'El video de la escena "{scene.scene_id}" se ha combinado con el audio',
                action_url=f'/projects/{scene.project.uuid}/agent/scenes/' if scene.project else None,
                action_label='Ver escenas',
                metadata={'item_type': 'scene_final_video', 'scene_id': scene_id_int}
            )
            
            logger.info(f"Video+audio combinados para escena {scene_id}. GCS Path: {scene.final_video_gcs_path}")
            return {'status': 'completed', 'scene_id': scene_id_int, 'gcs_path': scene.final_video_gcs_path}
        else:
            error_msg = scene.final_video_error_message or 'Error desconocido al combinar'
            task.mark_as_failed(error_msg)
            return {'status': 'failed', 'scene_id': scene_id_int, 'error': error_msg}
        
    except Exception as exc:
        logger.error(f"Error combinando video y audio de escena {scene_id}: {exc}", exc_info=True)
        try:
            task = GenerationTask.objects.get(uuid=task_uuid)
            task.mark_as_failed(str(exc))
            
            # Crear notificación de error solo si no se va a reintentar
            if task.retry_count >= task.max_retries:
                try:
                    user = User.objects.get(id=user_id)
                    from core.models import Notification
                    Notification.create_notification(
                        user=user,
                        type='generation_failed',
                        title='Error al combinar video',
                        message=f'No se pudo combinar el video con el audio: {str(exc)[:100]}',
                        metadata={'item_type': 'scene_final_video', 'scene_id': scene_id, 'error': str(exc)}
                    )
                except User.DoesNotExist:
                    pass
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.save(update_fields=['retry_count'])
                raise self.retry(exc=exc, countdown=60 * (2 ** task.retry_count))
        except GenerationTask.DoesNotExist:
            pass
        
        return {'status': 'failed', 'error': str(exc)}


@shared_task
def poll_video_status_task(task_uuid, video_uuid, user_id=None):
    """
    Tarea periódica para verificar estado de generación de video
    
    Args:
        task_uuid: UUID de la GenerationTask
        video_uuid: UUID del Video
        user_id: ID del usuario (para notificaciones)
    
    Nota: El VideoService ya tiene métodos _check_*_status que manejan
    la selección del servicio correcto según video.type. Usaremos esos métodos.
    """
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        video = Video.objects.get(uuid=video_uuid)
        
        # Si ya no está en processing, no hacer nada
        if video.status not in ['pending', 'processing']:
            if video.status == 'completed' and task.status != 'completed':
                task.mark_as_completed()
            return {'status': video.status}
        
        previous_status = video.status
        
        # VideoService.check_video_status hace el dispatch internamente
        video_service = VideoService()
        video_service.check_video_status(video)
        
        # Recargar video para ver si cambió
        video.refresh_from_db()
        
        # Si el video terminó, actualizar task y enviar notificación
        if video.status == 'completed' and previous_status != 'completed':
            task.mark_as_completed()
            
            # Enviar notificación
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    from core.models import Notification
                    Notification.create_notification(
                        user=user,
                        type='generation_completed',
                        title='Video generado',
                        message=f'Tu video "{video.title}" está listo',
                        action_url=f'/videos/{video.uuid}/',
                        action_label='Ver video',
                        metadata={'item_type': 'video', 'item_uuid': str(video.uuid)}
                    )
                    logger.info(f"Video {video.uuid} completado. Notificación enviada.")
                except User.DoesNotExist:
                    logger.warning(f"Usuario {user_id} no encontrado para notificación")
            
            return {'status': 'completed', 'video_uuid': str(video.uuid)}
        
        elif video.status == 'error':
            task.mark_as_failed(video.error_message or 'Error desconocido')
            
            # Enviar notificación de error
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    from core.models import Notification
                    Notification.create_notification(
                        user=user,
                        type='generation_failed',
                        title='Error al generar video',
                        message=f'No se pudo generar el video "{video.title}"',
                        metadata={'item_type': 'video', 'item_uuid': str(video.uuid), 'error': video.error_message}
                    )
                except User.DoesNotExist:
                    pass
            
            return {'status': 'error', 'video_uuid': str(video.uuid)}
        
        # Sigue en processing - programar siguiente poll en 30 segundos
        poll_video_status_task.apply_async(
            args=[str(task_uuid), str(video_uuid), user_id],
            countdown=30
        )
        return {'status': 'processing', 'video_uuid': str(video.uuid)}
        
    except Exception as exc:
        logger.error(f"Error en polling de video {video_uuid}: {exc}", exc_info=True)
        return {'status': 'error', 'error': str(exc)}


@shared_task
def poll_image_status_task(task_uuid, image_uuid):
    """
    Tarea periódica para verificar estado de generación de imagen
    """
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        image = Image.objects.get(uuid=image_uuid)
        
        # TODO: Implementar polling según servicio
        
    except Exception as exc:
        logger.error(f"Error en polling de imagen {image_uuid}: {exc}", exc_info=True)


@shared_task
def poll_audio_status_task(task_uuid, audio_uuid):
    """
    Tarea periódica para verificar estado de generación de audio
    """
    try:
        task = GenerationTask.objects.get(uuid=task_uuid)
        audio = Audio.objects.get(uuid=audio_uuid)
        
        # TODO: Implementar polling según servicio
        
    except Exception as exc:
        logger.error(f"Error en polling de audio {audio_uuid}: {exc}", exc_info=True)


@shared_task
def cleanup_old_notifications():
    """
    Tarea periódica para eliminar notificaciones antiguas (más de 1 mes)
    """
    from core.models import Notification
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = Notification.objects.filter(created_at__lt=cutoff_date).delete()[0]
    logger.info(f"Eliminadas {deleted_count} notificaciones antiguas")
    return deleted_count


@shared_task
def check_stuck_tasks():
    """
    Tarea periódica para verificar tareas atascadas (más de 2 horas en processing)
    """
    from datetime import timedelta
    
    cutoff_time = timezone.now() - timedelta(hours=2)
    stuck_tasks = GenerationTask.objects.filter(
        status='processing',
        started_at__lt=cutoff_time
    )
    
    for task in stuck_tasks:
        task.mark_as_failed("Tarea atascada - timeout después de 2 horas")
        logger.warning(f"Tarea {task.uuid} marcada como fallida por timeout")
    
    return stuck_tasks.count()


@shared_task(bind=True, max_retries=2)
def remove_image_background_task(self, image_uuid, new_image_uuid=None):
    """
    Tarea asíncrona para remover el fondo de una imagen usando rembg con BiRefNet
    
    Args:
        image_uuid: UUID de la imagen original a procesar
        new_image_uuid: UUID de la imagen destino (creada con status='processing')
    
    Returns:
        dict con resultado: {'success': True/False, 'new_image_uuid': '...', 'error': '...'}
    """
    try:
        import os
        from io import BytesIO
        from PIL import Image as PILImage
        from rembg import new_session, remove
        
        # Configurar ONNXRuntime para usar solo CPU (sin CUDA)
        os.environ['ONNXRUNTIME_EXECUTION_PROVIDERS'] = 'CPUExecutionProvider'
        os.environ['ORT_CUDA_PATHS'] = ''  # Desactivar CUDA
        
        # Configurar Numba para usar TBB (thread-safe)
        os.environ['NUMBA_THREADING_LAYER'] = 'tbb'
        
        # Obtener imagen original
        image = Image.objects.get(uuid=image_uuid)
        image_service = ImageService()
        
        logger.info(f"Iniciando remoción de fondo para imagen {image_uuid}: {image.title}")
        
        # Descargar imagen de GCS
        image_data = image_service._download_image_from_gcs(image.gcs_path)
        logger.info(f"Imagen descargada de GCS: {image.gcs_path}")
        
        # Procesar con rembg + BiRefNet (PIXEL PERFECT)
        logger.info("Iniciando sesión BiRefNet...")
        session = new_session('birefnet-general')
        
        output_image = remove(
            image_data,
            session=session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,  # Strict: solo detalles claros
            alpha_matting_background_threshold=10,   # Strict: solo fondo claro
            alpha_matting_erode_size=1,              # Limpieza quirúrgica
            alpha_matting_base_size=4096,            # Máxima resolución
            post_process_mask=False                  # Preservar detalles microscópicos
        )
        logger.info("Fondo removido exitosamente")
        
        # Obtener dimensiones
        pil_image = PILImage.open(BytesIO(output_image))
        width = pil_image.width
        height = pil_image.height
        logger.info(f"Dimensiones de imagen procesada: {width}x{height}")
        
        # Obtener o crear la imagen destino
        if new_image_uuid:
            # La imagen ya fue creada desde la view con status='processing'
            new_image = Image.objects.get(uuid=new_image_uuid)
            logger.info(f"Usando imagen existente: {new_image.uuid}")
        else:
            # Fallback: crear nueva imagen si no se pasó UUID
            new_image = Image.objects.create(
                title=f"{image.title} (Sin Fondo)",
                type='text_to_image',
                prompt=f"Versión sin fondo de: {image.prompt}",
                created_by=image.created_by,
                project=image.project,
                width=width,
                height=height,
                status='processing'
            )
            logger.info(f"Registro de imagen creado: {new_image.uuid}")
        
        # Actualizar dimensiones si es necesario
        new_image.width = width
        new_image.height = height
        
        # Guardar en GCS y marcar como completada
        gcs_path = image_service._save_generated_image(
            output_image,
            project=image.project,
            image_uuid=str(new_image.uuid)
        )
        new_image.gcs_path = gcs_path
        new_image.status = 'completed'
        new_image.save(update_fields=['gcs_path', 'status', 'width', 'height'])
        logger.info(f"Imagen guardada en GCS: {gcs_path}")
        
        # Notificar usuario
        # Construir URL según si la imagen tiene proyecto o no
        if image.project:
            action_url = f'/projects/{image.project.uuid}/images/{new_image.uuid}/'
        else:
            action_url = f'/images/{new_image.uuid}/'
        
        Notification.create_notification(
            user=image.created_by,
            type='generation_completed',
            title='Fondo removido',
            message=f'Se creó versión sin fondo de "{image.title}"',
            action_url=action_url,
            action_label='Ver imagen',
            metadata={'item_type': 'image', 'item_uuid': str(new_image.uuid)}
        )
        
        logger.info(f"Tarea completada exitosamente. Nueva imagen: {new_image.uuid}")
        return {
            'success': True,
            'new_image_uuid': str(new_image.uuid),
            'title': new_image.title
        }
        
    except Image.DoesNotExist:
        error_msg = f"Imagen {image_uuid} no encontrada"
        logger.error(error_msg)
        
        # Marcar imagen destino como fallida si existe
        if new_image_uuid:
            try:
                new_image = Image.objects.get(uuid=new_image_uuid)
                new_image.status = 'error'
                new_image.save(update_fields=['status'])
                logger.warning(f"Imagen destino {new_image_uuid} marcada como fallida")
            except Image.DoesNotExist:
                pass
        
        return {'success': False, 'error': error_msg}
        
    except Exception as exc:
        logger.error(f"Error removiendo fondo de imagen {image_uuid}: {exc}", exc_info=True)
        
        # Marcar imagen destino como fallida si existe
        if new_image_uuid:
            try:
                new_image = Image.objects.get(uuid=new_image_uuid)
                new_image.status = 'error'
                new_image.save(update_fields=['status'])
                logger.warning(f"Imagen destino {new_image_uuid} marcada como fallida")
            except Image.DoesNotExist:
                pass
        
        # Crear notificación de error
        try:
            image = Image.objects.get(uuid=image_uuid)
            Notification.create_notification(
                user=image.created_by,
                type='generation_failed',
                title='Error al remover fondo',
                message=f'No se pudo procesar "{image.title}": {str(exc)[:100]}',
                metadata={'item_type': 'image', 'item_uuid': str(image.uuid)}
            )
        except Exception:
            pass  # Ignorar error si no se puede crear notificación
        
        # Reintentar si no se ha alcanzado el máximo
        if self.request.retries < self.max_retries:
            logger.info(f"Reintentando remoción de fondo en 60 segundos (intento {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc, countdown=60)
        
        return {'success': False, 'error': str(exc)}
