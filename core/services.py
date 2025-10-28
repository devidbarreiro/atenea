"""
Capa de servicios para manejar la lógica de negocio
"""

import logging
import json
import redis
from typing import Dict, Optional, List
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from datetime import datetime

from .models import Project, Video, Image, Script
from .ai_services.heygen import HeyGenClient
from .ai_services.gemini_veo import GeminiVeoClient
from .ai_services.gemini_image import GeminiImageClient
from .ai_services.sora import SoraClient
from .storage.gcs import gcs_storage

logger = logging.getLogger(__name__)


# ====================
# EXCEPTIONS
# ====================

class ServiceException(Exception):
    """Excepción base para servicios"""
    pass


class VideoGenerationException(ServiceException):
    """Error al generar video"""
    pass


class ImageGenerationException(ServiceException):
    """Error al generar imagen"""
    pass


class StorageException(ServiceException):
    """Error de almacenamiento"""
    pass


class ValidationException(ServiceException):
    """Error de validación"""
    pass


# ====================
# PROJECT SERVICE
# ====================

class ProjectService:
    """Servicio para manejar lógica de proyectos"""
    
    @staticmethod
    def create_project(name: str, owner=None) -> Project:
        """
        Crea un nuevo proyecto
        
        Args:
            name: Nombre del proyecto
            owner: Usuario propietario (opcional)
        
        Returns:
            Project creado
        
        Raises:
            ValidationException: Si el nombre no es válido
        """
        if len(name.strip()) < 3:
            raise ValidationException('El nombre debe tener al menos 3 caracteres')
        
        project = Project.objects.create(name=name.strip())
        logger.info(f"Proyecto creado: {project.id} - {project.name}")
        
        return project
    
    @staticmethod
    def get_user_projects(user=None) -> List[Project]:
        """Obtiene proyectos del usuario (preparado para multi-tenant)"""
        # TODO: Filtrar por usuario cuando se implemente autenticación
        return Project.objects.all().order_by('-created_at')
    
    @staticmethod
    def get_project_with_videos(project_id: int) -> Project:
        """Obtiene proyecto con sus videos optimizado"""
        try:
            return Project.objects.prefetch_related(
                'videos'
            ).get(id=project_id)
        except Project.DoesNotExist:
            raise ValidationException(f'Proyecto {project_id} no encontrado')
    
    @staticmethod
    def delete_project(project: Project) -> None:
        """
        Elimina un proyecto y todos sus videos
        
        Args:
            project: Proyecto a eliminar
        """
        project_name = project.name
        video_count = project.videos.count()
        
        # Eliminar archivos de GCS de todos los videos
        for video in project.videos.all():
            if video.gcs_path:
                try:
                    gcs_storage.delete_file(video.gcs_path)
                    logger.info(f"Archivo GCS eliminado: {video.gcs_path}")
                except Exception as e:
                    logger.error(f"Error al eliminar archivo GCS: {e}")
        
        # Eliminar proyecto (cascade eliminará videos)
        project.delete()
        
        logger.info(f"Proyecto eliminado: {project_name} ({video_count} videos)")


# ====================
# VIDEO SERVICE
# ====================

class VideoService:
    """Servicio principal para manejar videos"""
    
    def __init__(self):
        self.heygen_client = None
        self.veo_client = None
        self.sora_client = None
    
    def _get_heygen_client(self) -> HeyGenClient:
        """Lazy initialization de HeyGen client"""
        if not self.heygen_client:
            if not settings.HEYGEN_API_KEY:
                raise ValidationException('HEYGEN_API_KEY no está configurada')
            self.heygen_client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        return self.heygen_client
    
    def _get_veo_client(self, model_name: str = 'veo-2.0-generate-001') -> GeminiVeoClient:
        """Lazy initialization de Veo client"""
        if not settings.GEMINI_API_KEY:
            raise ValidationException('GEMINI_API_KEY no está configurada')
        return GeminiVeoClient(api_key=settings.GEMINI_API_KEY, model_name=model_name)
    
    def _get_sora_client(self) -> SoraClient:
        """Lazy initialization de Sora client"""
        if not self.sora_client:
            if not settings.OPENAI_API_KEY:
                raise ValidationException('OPENAI_API_KEY no está configurada')
            self.sora_client = SoraClient(api_key=settings.OPENAI_API_KEY)
        return self.sora_client
    
    # ----------------
    # CREAR VIDEO
    # ----------------
    
    def create_video(
        self,
        project: Project,
        title: str,
        video_type: str,
        script: str,
        config: Dict
    ) -> Video:
        """
        Crea un nuevo video (sin generarlo)
        
        Args:
            project: Proyecto al que pertenece
            title: Título del video
            video_type: Tipo de video
            script: Guión
            config: Configuración específica del tipo
        
        Returns:
            Video creado
        """
        video = Video.objects.create(
            project=project,
            title=title,
            type=video_type,
            script=script,
            config=config
        )
        
        logger.info(f"Video creado: {video.id} - {video.title} ({video.type})")
        return video
    
    # ----------------
    # AVATAR UPLOADS
    # ----------------
    
    def upload_avatar_image(
        self,
        image: UploadedFile,
        project: Project
    ) -> Dict[str, str]:
        """
        Sube imagen de avatar a GCS
        
        Args:
            image: Archivo de imagen
            project: Proyecto relacionado
        
        Returns:
            Dict con 'gcs_path' y 'filename'
        
        Raises:
            StorageException: Si falla la subida
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = image.name.replace(' ', '_')
            gcs_destination = f"avatar_images/project_{project.id}/{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo avatar a GCS: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(image, gcs_destination)
            
            return {
                'gcs_path': gcs_path,
                'filename': image.name
            }
        except Exception as e:
            logger.error(f"Error al subir avatar: {e}")
            raise StorageException(f"Error al subir imagen: {str(e)}")
    
    def upload_veo_input_image(
        self,
        image: UploadedFile,
        project: Project
    ) -> Dict[str, str]:
        """
        Sube imagen inicial para Veo (imagen-a-video)
        
        Args:
            image: Archivo de imagen
            project: Proyecto relacionado
        
        Returns:
            Dict con 'gcs_path' y 'mime_type'
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = image.name.replace(' ', '_')
            gcs_destination = f"veo_input_images/project_{project.id}/{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo imagen inicial Veo: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(image, gcs_destination)
            
            return {
                'gcs_path': gcs_path,
                'mime_type': image.content_type or 'image/jpeg'
            }
        except Exception as e:
            logger.error(f"Error al subir imagen Veo: {e}")
            raise StorageException(f"Error al subir imagen: {str(e)}")
    
    def upload_veo_reference_images(
        self,
        images: List[UploadedFile],
        reference_types: List[str],
        project: Project
    ) -> List[Dict]:
        """
        Sube imágenes de referencia para Veo
        
        Args:
            images: Lista de archivos de imagen
            reference_types: Lista de tipos ('asset' o 'style')
            project: Proyecto relacionado
        
        Returns:
            Lista de dicts con datos de las imágenes subidas
        """
        reference_images = []
        
        for i, (image, ref_type) in enumerate(zip(images, reference_types)):
            if image:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_filename = image.name.replace(' ', '_')
                    gcs_destination = f"veo_reference_images/project_{project.id}/{timestamp}_{i+1}_{safe_filename}"
                    
                    logger.info(f"Subiendo imagen de referencia {i+1} ({ref_type}): {safe_filename}")
                    gcs_path = gcs_storage.upload_django_file(image, gcs_destination)
                    
                    reference_images.append({
                        'gcs_uri': gcs_path,
                        'reference_type': ref_type,
                        'mime_type': image.content_type or 'image/jpeg'
                    })
                    
                    logger.info(f"✅ Imagen de referencia {i+1} subida: {gcs_path}")
                except Exception as e:
                    logger.error(f"Error al subir imagen de referencia {i+1}: {str(e)}")
                    # No bloqueamos la creación si falla una imagen de referencia
        
        return reference_images
    
    def upload_sora_input_reference(
        self,
        image: UploadedFile,
        project: Project
    ) -> Dict[str, str]:
        """
        Sube imagen de referencia para Sora
        
        Args:
            image: Archivo de imagen
            project: Proyecto relacionado
        
        Returns:
            Dict con 'gcs_path' y 'mime_type'
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = image.name.replace(' ', '_')
            gcs_destination = f"sora_input_references/project_{project.id}/{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo imagen de referencia Sora: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(image, gcs_destination)
            
            return {
                'gcs_path': gcs_path,
                'mime_type': image.content_type or 'image/jpeg'
            }
        except Exception as e:
            logger.error(f"Error al subir imagen de referencia Sora: {e}")
            raise StorageException(f"Error al subir imagen: {str(e)}")
    
    # ----------------
    # GENERAR VIDEO
    # ----------------
    
    def generate_video(self, video: Video) -> str:
        """
        Genera un video usando la API correspondiente
        
        Args:
            video: Objeto Video a generar
        
        Returns:
            external_id del video generado
        
        Raises:
            VideoGenerationException: Si falla la generación
        """
        # Validar estado
        if video.status in ['processing', 'completed']:
            raise ValidationException(f'El video ya está en estado: {video.get_status_display()}')
        
        # Marcar como procesando
        video.mark_as_processing()
        
        try:
            if video.type in ['heygen_avatar_v2', 'heygen_avatar_iv']:
                external_id = self._generate_heygen_video(video)
            elif video.type == 'gemini_veo':
                external_id = self._generate_veo_video(video)
            elif video.type == 'sora':
                external_id = self._generate_sora_video(video)
            else:
                raise ValidationException(f'Tipo de video no soportado: {video.type}')
            
            # Guardar external_id
            video.external_id = external_id
            video.save(update_fields=['external_id', 'updated_at'])
            
            logger.info(f"Video {video.id} enviado. External ID: {external_id}")
            return external_id
            
        except Exception as e:
            logger.error(f"Error al generar video {video.id}: {e}")
            video.mark_as_error(str(e))
            raise VideoGenerationException(str(e))
    
    def _generate_heygen_video(self, video: Video) -> str:
        """Genera video con HeyGen"""
        client = self._get_heygen_client()
        
        if video.type == 'heygen_avatar_v2':
            # Validar configuración
            if not video.config.get('avatar_id') or not video.config.get('voice_id'):
                raise ValidationException('Avatar ID y Voice ID son requeridos')
            
            response = client.generate_video(
                script=video.script,
                title=video.title,
                avatar_id=video.config['avatar_id'],
                voice_id=video.config['voice_id'],
                has_background=video.config.get('has_background', False),
                background_url=video.config.get('background_url'),
                voice_speed=video.config.get('voice_speed', 1.0),
                voice_pitch=video.config.get('voice_pitch', 50),
                voice_emotion=video.config.get('voice_emotion', 'Excited'),
            )
        else:  # heygen_avatar_iv
            # Lógica para Avatar IV
            image_key = self._get_or_upload_avatar_iv_image(video, client)
            
            response = client.generate_avatar_iv_video(
                script=video.script,
                image_key=image_key,
                voice_id=video.config['voice_id'],
                title=video.title,
                video_orientation=video.config.get('video_orientation', 'portrait'),
                fit=video.config.get('fit', 'cover'),
            )
        
        return response.get('data', {}).get('video_id')
    
    def _get_or_upload_avatar_iv_image(self, video: Video, client: HeyGenClient) -> str:
        """Obtiene o sube imagen para Avatar IV"""
        image_source = video.config.get('image_source', 'upload')
        
        if image_source == 'upload':
            if not video.config.get('gcs_avatar_path'):
                raise ValidationException('Imagen de avatar es requerida')
            
            # Obtener URL firmada y subir a HeyGen
            gcs_path = video.config['gcs_avatar_path']
            avatar_url = gcs_storage.get_signed_url(gcs_path, expiration=600)
            image_key = client.upload_asset_from_url(avatar_url)
            
            # Guardar image_key para futuro uso
            video.config['image_key'] = image_key
            video.save(update_fields=['config'])
            
            return image_key
        else:
            # Usar imagen existente
            if not video.config.get('existing_image_id'):
                raise ValidationException('ID de imagen existente es requerido')
            
            # Buscar image_key en assets
            assets = client.list_image_assets()
            for asset in assets:
                if asset.get('id') == video.config['existing_image_id']:
                    image_key = asset.get('image_key') or asset.get('id')
                    video.config['image_key'] = image_key
                    video.save(update_fields=['config'])
                    return image_key
            
            raise ValidationException(f'Asset no encontrado: {video.config["existing_image_id"]}')
    
    def _generate_veo_video(self, video: Video) -> str:
        """Genera video con Gemini Veo"""
        model_name = video.config.get('veo_model', 'veo-2.0-generate-001')
        client = self._get_veo_client(model_name)
        
        # Preparar storage URI
        storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/projects/{video.project.id}/videos/{video.id}/"
        
        # Parámetros
        params = {
            'prompt': video.script,
            'title': video.title,
            'duration': video.config.get('duration', 8),
            'aspect_ratio': video.config.get('aspect_ratio', '16:9'),
            'sample_count': video.config.get('sample_count', 1),
            'negative_prompt': video.config.get('negative_prompt'),
            'enhance_prompt': video.config.get('enhance_prompt', True),
            'person_generation': video.config.get('person_generation', 'allow_adult'),
            'compression_quality': video.config.get('compression_quality', 'optimized'),
            'seed': video.config.get('seed'),
            'storage_uri': storage_uri,
        }
        
        # Imagen inicial (imagen-a-video)
        if video.config.get('input_image_gcs_uri'):
            params['input_image_gcs_uri'] = video.config['input_image_gcs_uri']
            params['input_image_mime_type'] = video.config.get('input_image_mime_type', 'image/jpeg')
        
        # Imágenes de referencia
        if video.config.get('reference_images'):
            params['reference_images'] = video.config['reference_images']
        
        response = client.generate_video(**params)
        return response.get('video_id')
    
    def _generate_sora_video(self, video: Video) -> str:
        """Genera video con OpenAI Sora"""
        client = self._get_sora_client()
        
        # Obtener configuración
        model = video.config.get('sora_model', 'sora-2')
        duration = int(video.config.get('duration', 8))  # Asegurar que es int
        size = video.config.get('size', '1280x720')
        use_input_reference = video.config.get('use_input_reference', False)
        
        # Generar video
        if use_input_reference and video.config.get('input_reference_gcs_path'):
            # Descargar imagen desde GCS a un archivo temporal
            import tempfile
            import os
            
            gcs_path = video.config['input_reference_gcs_path']
            mime_type = video.config.get('input_reference_mime_type', 'image/jpeg')
            
            # Determinar extensión
            ext_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/webp': '.webp'
            }
            ext = ext_map.get(mime_type, '.jpg')
            
            # Descargar a archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_path = tmp_file.name
                
                # Descargar desde GCS
                blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                blob = gcs_storage.bucket.blob(blob_name)
                blob.download_to_filename(tmp_path)
                
                logger.info(f"Imagen de referencia descargada a: {tmp_path}")
            
            try:
                response = client.generate_video_with_image(
                    prompt=video.script,
                    input_reference_path=tmp_path,
                    model=model,
                    seconds=duration,
                    size=size
                )
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    logger.info(f"Archivo temporal eliminado: {tmp_path}")
        else:
            # Generación text-to-video
            response = client.generate_video(
                prompt=video.script,
                model=model,
                seconds=duration,
                size=size
            )
        
        return response.get('video_id')
    
    # ----------------
    # CONSULTAR ESTADO
    # ----------------
    
    def check_video_status(self, video: Video) -> Dict:
        """
        Consulta el estado de un video en la API externa
        
        Args:
            video: Video a consultar
        
        Returns:
            Dict con estado actualizado
        """
        if not video.external_id:
            raise ValidationException('Video no tiene external_id')
        
        # Si ya está en estado final, no consultar
        if video.status in ['completed', 'error']:
            return {
                'status': video.status,
                'message': 'Video ya procesado'
            }
        
        try:
            if video.type in ['heygen_avatar_v2', 'heygen_avatar_iv']:
                return self._check_heygen_status(video)
            elif video.type == 'gemini_veo':
                return self._check_veo_status(video)
            elif video.type == 'sora':
                return self._check_sora_status(video)
        except Exception as e:
            logger.error(f"Error al consultar estado: {e}")
            raise ServiceException(str(e))
    
    def _check_heygen_status(self, video: Video) -> Dict:
        """Consulta estado en HeyGen"""
        client = self._get_heygen_client()
        status_data = client.get_video_status(video.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            video_url = status_data.get('video_url')
            if video_url:
                gcs_path = f"projects/{video.project.id}/videos/{video.id}/final_video.mp4"
                gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                
                metadata = {
                    'duration': status_data.get('duration'),
                    'video_url_original': video_url,
                    'thumbnail': status_data.get('thumbnail'),
                    'caption_url': status_data.get('caption_url'),
                }
                
                video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                logger.info(f"Video {video.id} completado: {gcs_full_path}")
        
        elif api_status == 'failed':
            error_msg = status_data.get('error', 'Video generation failed')
            video.mark_as_error(error_msg)
        
        return status_data
    
    def _check_veo_status(self, video: Video) -> Dict:
        """Consulta estado en Gemini Veo"""
        client = self._get_veo_client()
        status_data = client.get_video_status(video.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            all_video_urls = status_data.get('all_video_urls', [])
            if all_video_urls:
                # Procesar todos los videos
                all_gcs_paths = []
                for idx, video_data in enumerate(all_video_urls):
                    url = video_data['url']
                    filename = f"video_{idx + 1}.mp4" if len(all_video_urls) > 1 else "video.mp4"
                    gcs_path = f"projects/{video.project.id}/videos/{video.id}/{filename}"
                    
                    if url.startswith('gs://'):
                        if url.startswith(f"gs://{settings.GCS_BUCKET_NAME}/"):
                            gcs_full_path = url
                        else:
                            gcs_full_path = gcs_storage.copy_from_gcs(url, gcs_path)
                    elif url.startswith('http'):
                        gcs_full_path = gcs_storage.upload_from_url(url, gcs_path)
                    else:
                        # Base64
                        gcs_full_path = gcs_storage.upload_base64(url, gcs_path)
                    
                    all_gcs_paths.append({
                        'index': idx,
                        'gcs_path': gcs_full_path,
                        'original_url': url,
                        'mime_type': video_data.get('mime_type', 'video/mp4')
                    })
                
                metadata = {
                    'sample_count': len(all_gcs_paths),
                    'all_videos': all_gcs_paths,
                    'rai_filtered_count': status_data.get('rai_filtered_count', 0),
                    'videos_raw': status_data.get('videos', []),
                    'operation_data': status_data.get('operation_data', {}),
                }
                
                video.mark_as_completed(
                    gcs_path=all_gcs_paths[0]['gcs_path'],
                    metadata=metadata
                )
        
        elif api_status in ['failed', 'error']:
            error_msg = status_data.get('error', 'Video generation failed')
            video.mark_as_error(error_msg)
        
        return status_data
    
    def _check_sora_status(self, video: Video) -> Dict:
        """Consulta estado en OpenAI Sora"""
        client = self._get_sora_client()
        status_data = client.get_video_status(video.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            # Descargar video desde Sora API
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Descargar video
                success = client.download_video(video.external_id, tmp_path)
                
                if success:
                    # Subir a GCS
                    gcs_path = f"projects/{video.project.id}/videos/{video.id}/video.mp4"
                    
                    with open(tmp_path, 'rb') as video_file:
                        gcs_full_path = gcs_storage.upload_from_bytes(
                            file_content=video_file.read(),
                            destination_path=gcs_path,
                            content_type='video/mp4'
                        )
                    
                    # Preparar metadata
                    metadata = {
                        'model': status_data.get('model'),
                        'duration': status_data.get('seconds'),
                        'size': status_data.get('size'),
                        'progress': status_data.get('progress'),
                        'created_at': status_data.get('created_at'),
                        'completed_at': status_data.get('completed_at'),
                        'expires_at': status_data.get('expires_at'),
                    }
                    
                    # Intentar descargar thumbnail también
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as thumb_file:
                            thumb_path = thumb_file.name
                        
                        if client.download_thumbnail(video.external_id, thumb_path):
                            thumb_gcs_path = f"projects/{video.project.id}/videos/{video.id}/thumbnail.webp"
                            
                            with open(thumb_path, 'rb') as thumb:
                                thumb_gcs_full = gcs_storage.upload_from_bytes(
                                    file_content=thumb.read(),
                                    destination_path=thumb_gcs_path,
                                    content_type='image/webp'
                                )
                            
                            metadata['thumbnail_gcs_path'] = thumb_gcs_full
                            logger.info(f"Thumbnail guardado: {thumb_gcs_full}")
                        
                        if os.path.exists(thumb_path):
                            os.unlink(thumb_path)
                    except Exception as e:
                        logger.warning(f"No se pudo descargar thumbnail: {e}")
                    
                    video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                    logger.info(f"Video Sora {video.id} completado: {gcs_full_path}")
                else:
                    video.mark_as_error("No se pudo descargar el video desde Sora")
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif api_status == 'failed':
            error_msg = status_data.get('error', 'Video generation failed')
            video.mark_as_error(error_msg)
        
        return status_data
    
    # ----------------
    # UTILIDADES
    # ----------------
    
    def get_video_with_signed_urls(self, video: Video) -> Dict:
        """
        Obtiene un video con todas sus URLs firmadas generadas
        
        Args:
            video: Video a procesar
        
        Returns:
            Dict con video y URLs firmadas
        """
        result = {
            'video': video,
            'signed_url': None,
            'all_videos': [],
            'reference_images': [],
            'input_image_url': None
        }
        
        # URL firmada del video principal
        if video.status == 'completed' and video.gcs_path:
            try:
                result['signed_url'] = gcs_storage.get_signed_url(video.gcs_path)
            except Exception as e:
                logger.error(f"Error al generar URL firmada: {e}")
        
        # URLs de todos los videos (si hay múltiples)
        if video.status == 'completed' and video.metadata.get('all_videos'):
            try:
                for video_data in video.metadata['all_videos']:
                    gcs_path = video_data.get('gcs_path')
                    if gcs_path:
                        signed = gcs_storage.get_signed_url(gcs_path, expiration=3600)
                        result['all_videos'].append({
                            'index': video_data.get('index', 0),
                            'gcs_path': gcs_path,
                            'signed_url': signed,
                            'mime_type': video_data.get('mime_type', 'video/mp4')
                        })
            except Exception as e:
                logger.error(f"Error al generar URLs firmadas para múltiples videos: {e}")
        
        # URLs de imágenes de referencia
        if video.config.get('reference_images'):
            try:
                for idx, ref_img in enumerate(video.config['reference_images']):
                    gcs_uri = ref_img.get('gcs_uri')
                    if gcs_uri:
                        signed = gcs_storage.get_signed_url(gcs_uri, expiration=3600)
                        result['reference_images'].append({
                            'index': idx,
                            'gcs_uri': gcs_uri,
                            'signed_url': signed,
                            'reference_type': ref_img.get('reference_type', 'asset'),
                            'mime_type': ref_img.get('mime_type', 'image/jpeg')
                        })
            except Exception as e:
                logger.error(f"Error al generar URLs firmadas para imágenes de referencia: {e}")
        
        # URL de imagen inicial
        if video.config.get('input_image_gcs_uri'):
            try:
                result['input_image_url'] = gcs_storage.get_signed_url(
                    video.config['input_image_gcs_uri'], 
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada para imagen inicial: {e}")
        
        return result


# ====================
# API SERVICE
# ====================

class APIService:
    """Servicio para endpoints de API externa"""
    
    def __init__(self):
        self.heygen_client = None
    
    def _get_heygen_client(self) -> HeyGenClient:
        """Lazy initialization de HeyGen client"""
        if not self.heygen_client:
            if not settings.HEYGEN_API_KEY:
                raise ValidationException('HEYGEN_API_KEY no está configurada')
            self.heygen_client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        return self.heygen_client
    
    def list_avatars(self) -> List[Dict]:
        """Lista avatares disponibles de HeyGen"""
        try:
            client = self._get_heygen_client()
            return client.list_avatars()
        except Exception as e:
            logger.error(f"Error al listar avatares: {e}")
            raise ServiceException(str(e))
    
    def list_voices(self) -> List[Dict]:
        """Lista voces disponibles de HeyGen"""
        try:
            client = self._get_heygen_client()
            return client.list_voices()
        except Exception as e:
            logger.error(f"Error al listar voces: {e}")
            raise ServiceException(str(e))
    
    def list_image_assets(self) -> List[Dict]:
        """Lista imágenes disponibles en HeyGen"""
        try:
            client = self._get_heygen_client()
            return client.list_image_assets()
        except Exception as e:
            logger.error(f"Error al listar image assets: {e}")
            raise ServiceException(str(e))


# ====================
# IMAGE SERVICE
# ====================

class ImageService:
    """Servicio principal para manejar imágenes generadas por IA"""
    
    def __init__(self):
        self.gemini_client = None
    
    def _get_gemini_client(self) -> GeminiImageClient:
        """Lazy initialization de Gemini Image client"""
        if not self.gemini_client:
            if not settings.GEMINI_API_KEY:
                raise ValidationException('GEMINI_API_KEY no está configurada')
            self.gemini_client = GeminiImageClient(api_key=settings.GEMINI_API_KEY)
        return self.gemini_client
    
    # ----------------
    # CREAR IMAGEN
    # ----------------
    
    def create_image(
        self,
        project: Project,
        title: str,
        image_type: str,
        prompt: str,
        config: Dict
    ) -> Image:
        """
        Crea una nueva imagen (sin generarla)
        
        Args:
            project: Proyecto al que pertenece
            title: Título de la imagen
            image_type: Tipo de imagen (text_to_image, image_to_image, multi_image)
            prompt: Prompt descriptivo
            config: Configuración específica del tipo
        
        Returns:
            Image creada
        """
        image = Image.objects.create(
            project=project,
            title=title,
            type=image_type,
            prompt=prompt,
            config=config
        )
        
        logger.info(f"Imagen creada: {image.id} - {image.title} ({image.type})")
        return image
    
    # ----------------
    # SUBIR IMÁGENES DE ENTRADA
    # ----------------
    
    def upload_input_image(
        self,
        image_file: UploadedFile,
        project: Project
    ) -> Dict[str, str]:
        """
        Sube imagen de entrada para image-to-image
        
        Args:
            image_file: Archivo de imagen
            project: Proyecto relacionado
        
        Returns:
            Dict con 'gcs_path' y 'mime_type'
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = image_file.name.replace(' ', '_')
            gcs_destination = f"image_inputs/project_{project.id}/{timestamp}_{safe_filename}"
            
            logger.info(f"Subiendo imagen de entrada: {safe_filename}")
            gcs_path = gcs_storage.upload_django_file(image_file, gcs_destination)
            
            return {
                'gcs_path': gcs_path,
                'mime_type': image_file.content_type or 'image/jpeg'
            }
        except Exception as e:
            logger.error(f"Error al subir imagen de entrada: {e}")
            raise StorageException(f"Error al subir imagen: {str(e)}")
    
    def upload_multiple_input_images(
        self,
        image_files: List[UploadedFile],
        project: Project
    ) -> List[Dict]:
        """
        Sube múltiples imágenes de entrada para composición
        
        Args:
            image_files: Lista de archivos de imagen
            project: Proyecto relacionado
        
        Returns:
            Lista de dicts con datos de las imágenes subidas
        """
        input_images = []
        
        for i, image_file in enumerate(image_files):
            if image_file:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_filename = image_file.name.replace(' ', '_')
                    gcs_destination = f"image_inputs/project_{project.id}/{timestamp}_{i+1}_{safe_filename}"
                    
                    logger.info(f"Subiendo imagen de entrada {i+1}: {safe_filename}")
                    gcs_path = gcs_storage.upload_django_file(image_file, gcs_destination)
                    
                    input_images.append({
                        'gcs_path': gcs_path,
                        'mime_type': image_file.content_type or 'image/jpeg',
                        'index': i
                    })
                    
                    logger.info(f"✅ Imagen {i+1} subida: {gcs_path}")
                except Exception as e:
                    logger.error(f"Error al subir imagen {i+1}: {str(e)}")
        
        return input_images
    
    # ----------------
    # GENERAR IMAGEN
    # ----------------
    
    def generate_image(self, image: Image) -> str:
        """
        Genera una imagen usando Gemini Image API
        
        Args:
            image: Objeto Image a generar
        
        Returns:
            Path de GCS de la imagen generada
        
        Raises:
            ImageGenerationException: Si falla la generación
        """
        # Validar estado
        if image.status in ['processing', 'completed']:
            raise ValidationException(f'La imagen ya está en estado: {image.get_status_display()}')
        
        # Marcar como procesando
        image.mark_as_processing()
        
        try:
            client = self._get_gemini_client()
            
            # Obtener configuración
            aspect_ratio = image.config.get('aspect_ratio', '1:1')
            response_modalities = image.config.get('response_modalities')
            
            # Generar según el tipo
            if image.type == 'text_to_image':
                result = client.generate_image_from_text(
                    prompt=image.prompt,
                    aspect_ratio=aspect_ratio,
                    response_modalities=response_modalities
                )
            
            elif image.type == 'image_to_image':
                # Obtener imagen de entrada desde GCS
                input_gcs_path = image.config.get('input_image_gcs_path')
                if not input_gcs_path:
                    raise ValidationException('Imagen de entrada es requerida para image-to-image')
                
                # Descargar imagen desde GCS
                input_image_data = self._download_image_from_gcs(input_gcs_path)
                
                result = client.generate_image_from_image(
                    prompt=image.prompt,
                    input_image_data=input_image_data,
                    aspect_ratio=aspect_ratio,
                    response_modalities=response_modalities
                )
            
            elif image.type == 'multi_image':
                # Obtener imágenes de entrada desde GCS
                input_images_config = image.config.get('input_images', [])
                if not input_images_config:
                    raise ValidationException('Imágenes de entrada son requeridas para multi_image')
                
                # Descargar imágenes desde GCS
                input_images_data = []
                for img_config in input_images_config:
                    img_data = self._download_image_from_gcs(img_config['gcs_path'])
                    input_images_data.append(img_data)
                
                result = client.generate_image_from_multiple_images(
                    prompt=image.prompt,
                    input_images_data=input_images_data,
                    aspect_ratio=aspect_ratio,
                    response_modalities=response_modalities
                )
            
            else:
                raise ValidationException(f'Tipo de imagen no soportado: {image.type}')
            
            # Subir imagen generada a GCS
            gcs_path = self._save_generated_image(
                image_data=result['image_data'],
                project=image.project,
                image_id=image.id
            )
            
            # Preparar metadata
            metadata = {
                'width': result['width'],
                'height': result['height'],
                'aspect_ratio': result['aspect_ratio'],
                'text_response': result.get('text_response'),
            }
            
            # Actualizar imagen en BD
            image.width = result['width']
            image.height = result['height']
            image.aspect_ratio = result['aspect_ratio']
            image.mark_as_completed(gcs_path=gcs_path, metadata=metadata)
            
            logger.info(f"Imagen {image.id} generada exitosamente: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logger.error(f"Error al generar imagen {image.id}: {e}")
            image.mark_as_error(str(e))
            raise ImageGenerationException(str(e))
    
    def _download_image_from_gcs(self, gcs_path: str) -> bytes:
        """Descarga imagen desde GCS y retorna bytes"""
        try:
            # Extraer blob name del path
            blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = gcs_storage.bucket.blob(blob_name)
            
            # Descargar como bytes
            image_data = blob.download_as_bytes()
            logger.info(f"Imagen descargada desde GCS: {len(image_data)} bytes")
            return image_data
            
        except Exception as e:
            logger.error(f"Error al descargar imagen desde GCS: {e}")
            raise StorageException(f"Error al descargar imagen: {str(e)}")
    
    def _save_generated_image(
        self,
        image_data: bytes,
        project: Project,
        image_id: int
    ) -> str:
        """Guarda imagen generada en GCS"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            gcs_destination = f"images/project_{project.id}/image_{image_id}/{timestamp}_generated.png"
            
            logger.info(f"Guardando imagen generada en GCS: {gcs_destination}")
            gcs_path = gcs_storage.upload_from_bytes(
                file_content=image_data,
                destination_path=gcs_destination,
                content_type='image/png'
            )
            
            return gcs_path
            
        except Exception as e:
            logger.error(f"Error al guardar imagen generada: {e}")
            raise StorageException(f"Error al guardar imagen: {str(e)}")
    
    # ----------------
    # UTILIDADES
    # ----------------
    
    def get_image_with_signed_url(self, image: Image) -> Dict:
        """
        Obtiene una imagen con su URL firmada
        
        Args:
            image: Imagen a procesar
        
        Returns:
            Dict con image y URLs firmadas
        """
        result = {
            'image': image,
            'signed_url': None,
            'input_images_urls': []
        }
        
        # URL firmada de la imagen generada
        if image.status == 'completed' and image.gcs_path:
            try:
                result['signed_url'] = gcs_storage.get_signed_url(image.gcs_path)
            except Exception as e:
                logger.error(f"Error al generar URL firmada: {e}")
        
        # URLs de imágenes de entrada (para image-to-image y multi_image)
        if image.type == 'image_to_image' and image.config.get('input_image_gcs_path'):
            try:
                input_url = gcs_storage.get_signed_url(
                    image.config['input_image_gcs_path'], 
                    expiration=3600
                )
                result['input_images_urls'].append({
                    'index': 0,
                    'gcs_path': image.config['input_image_gcs_path'],
                    'signed_url': input_url
                })
            except Exception as e:
                logger.error(f"Error al generar URL firmada para imagen de entrada: {e}")
        
        if image.type == 'multi_image' and image.config.get('input_images'):
            try:
                for idx, img_config in enumerate(image.config['input_images']):
                    gcs_path = img_config.get('gcs_path')
                    if gcs_path:
                        signed_url = gcs_storage.get_signed_url(gcs_path, expiration=3600)
                        result['input_images_urls'].append({
                            'index': idx,
                            'gcs_path': gcs_path,
                            'signed_url': signed_url
                        })
            except Exception as e:
                logger.error(f"Error al generar URLs firmadas para imágenes de entrada: {e}")
        
        return result


# ====================
# SCENE SERVICE
# ====================

class SceneService:
    """Servicio para manejar escenas del agente de video"""
    
    def __init__(self):
        self.image_service = ImageService()
        self.video_service = VideoService()
    
    @staticmethod
    def create_scenes_from_n8n_data(script, scenes_data: List[Dict]) -> List:
        """
        Crea objetos Scene desde los datos procesados por n8n
        
        Args:
            script: Objeto Script al que pertenecen las escenas
            scenes_data: Lista de dicts con datos de escenas desde n8n
            
        Returns:
            Lista de objetos Scene creados
        
        Raises:
            ValidationException: Si los datos son inválidos
        """
        from .models import Scene
        
        created_scenes = []
        
        for idx, scene_data in enumerate(scenes_data):
            try:
                # Validar campos requeridos
                required_fields = ['id', 'summary', 'script_text', 'duration_sec', 'avatar', 'platform']
                for field in required_fields:
                    if field not in scene_data:
                        raise ValidationException(f"Campo requerido '{field}' faltante en escena {idx + 1}")
                
                # Determinar ai_service inicial basado en platform de n8n
                ai_service = scene_data.get('platform', 'gemini_veo').lower()
                if ai_service == 'hedra':  # Por si viene de prompts antiguos
                    ai_service = 'gemini_veo'
                if ai_service not in ['gemini_veo', 'sora', 'heygen']:
                    ai_service = 'gemini_veo'  # Default
                
                # Preparar config básica según el servicio
                ai_config = {}
                if ai_service == 'heygen' and scene_data.get('avatar') == 'si':
                    # Config por defecto para HeyGen (se puede editar después)
                    ai_config = {
                        'avatar_id': '',  # El usuario lo configurará
                        'voice_id': '',   # El usuario lo configurará
                        'voice_speed': 1.0,
                        'voice_pitch': 50,
                        'voice_emotion': 'Excited'
                    }
                elif ai_service == 'gemini_veo':
                    ai_config = {
                        'veo_model': 'veo-2.0-generate-001',
                        'duration': min(8, scene_data.get('duration_sec', 8)),  # Max 8s
                        'aspect_ratio': '16:9',
                        'sample_count': 1,
                        'enhance_prompt': True,
                        'person_generation': 'allow_adult',
                        'compression_quality': 'optimized'
                    }
                elif ai_service == 'sora':
                    ai_config = {
                        'sora_model': 'sora-2',
                        'duration': min(12, scene_data.get('duration_sec', 8)),  # Max 12s
                        'size': '1280x720'
                    }
                
                # Crear escena
                scene = Scene.objects.create(
                    script=script,
                    project=script.project,
                    scene_id=scene_data.get('id'),
                    summary=scene_data.get('summary', ''),
                    script_text=scene_data.get('script_text', ''),
                    duration_sec=scene_data.get('duration_sec', 0),
                    avatar=scene_data.get('avatar', 'no'),
                    platform=scene_data.get('platform', 'gemini_veo'),
                    broll=scene_data.get('broll', []),
                    transition=scene_data.get('transition', 'corte'),
                    text_on_screen=scene_data.get('text_on_screen', ''),
                    audio_notes=scene_data.get('audio_notes', ''),
                    order=idx,
                    is_included=True,
                    ai_service=ai_service,
                    ai_config=ai_config,
                    preview_image_status='pending',
                    video_status='pending'
                )
                
                created_scenes.append(scene)
                logger.info(f"Escena creada: {scene.scene_id} para script {script.id}")
                
            except Exception as e:
                logger.error(f"Error al crear escena {idx + 1}: {e}")
                # Continuar con las demás escenas
        
        logger.info(f"✓ {len(created_scenes)} escenas creadas para script {script.id}")
        return created_scenes
    
    def generate_preview_image(self, scene):
        """
        Genera imagen preview para una escena usando Gemini Image
        
        Args:
            scene: Objeto Scene
            
        Returns:
            GCS path de la imagen generada
            
        Raises:
            ImageGenerationException: Si falla la generación
        """
        from .models import Scene
        
        try:
            # Marcar como generando
            scene.mark_preview_as_generating()
            
            # Construir prompt optimizado para el preview
            prompt = f"""
Create a cinematic preview image for a video scene.

Scene summary: {scene.summary}
Scene content: {scene.script_text[:200]}...

Visual elements to include: {', '.join(scene.broll[:3]) if scene.broll else 'general scene'}

Style: Photorealistic, professional video production, cinematic lighting, high quality, 16:9 aspect ratio.
This is a preview thumbnail for a video, make it visually engaging and representative of the content.
"""
            
            # Usar ImageService con Gemini
            client = GeminiImageClient(api_key=settings.GEMINI_API_KEY)
            
            result = client.generate_image_from_text(
                prompt=prompt,
                aspect_ratio='16:9',
                response_modalities=['Image']
            )
            
            # Subir a GCS
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            gcs_destination = f"scene_previews/project_{scene.project.id}/scene_{scene.id}/{timestamp}_preview.png"
            
            logger.info(f"Guardando preview de escena {scene.scene_id} en GCS: {gcs_destination}")
            gcs_path = gcs_storage.upload_from_bytes(
                file_content=result['image_data'],
                destination_path=gcs_destination,
                content_type='image/png'
            )
            
            # Actualizar scene
            scene.mark_preview_as_completed(gcs_path)
            
            logger.info(f"✓ Preview generado para escena {scene.scene_id}: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            error_msg = f"Error al generar preview: {str(e)}"
            logger.error(f"✗ {error_msg} para escena {scene.scene_id}")
            scene.mark_preview_as_error(error_msg)
            raise ImageGenerationException(error_msg)
    
    def generate_scene_video(self, scene):
        """
        Genera video para una escena según su ai_service configurado
        
        Args:
            scene: Objeto Scene
            
        Returns:
            external_id del video generado
            
        Raises:
            VideoGenerationException: Si falla la generación
        """
        try:
            # Validar que la configuración esté completa
            if not scene.ai_service:
                raise ValidationException("La escena no tiene servicio de IA configurado")
            
            # Marcar como procesando
            scene.mark_video_as_processing()
            
            # Generar según el servicio
            if scene.ai_service == 'heygen':
                external_id = self._generate_heygen_scene_video(scene)
            elif scene.ai_service == 'gemini_veo':
                external_id = self._generate_veo_scene_video(scene)
            elif scene.ai_service == 'sora':
                external_id = self._generate_sora_scene_video(scene)
            else:
                raise ValidationException(f"Servicio de IA no soportado: {scene.ai_service}")
            
            # Guardar external_id
            scene.external_id = external_id
            scene.save(update_fields=['external_id', 'updated_at'])
            
            logger.info(f"✓ Video de escena {scene.scene_id} enviado. External ID: {external_id}")
            return external_id
            
        except Exception as e:
            error_msg = f"Error al generar video de escena: {str(e)}"
            logger.error(f"✗ {error_msg}")
            scene.mark_video_as_error(error_msg)
            raise VideoGenerationException(error_msg)
    
    def _generate_heygen_scene_video(self, scene):
        """Genera video de escena con HeyGen"""
        from .ai_services.heygen import HeyGenClient
        
        if not settings.HEYGEN_API_KEY:
            raise ValidationException('HEYGEN_API_KEY no está configurada')
        
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        
        # Validar configuración
        if not scene.ai_config.get('avatar_id') or not scene.ai_config.get('voice_id'):
            raise ValidationException('Avatar ID y Voice ID son requeridos para HeyGen')
        
        response = client.generate_video(
            script=scene.script_text,
            title=f"{scene.scene_id} - {scene.script.title}",
            avatar_id=scene.ai_config['avatar_id'],
            voice_id=scene.ai_config['voice_id'],
            has_background=scene.ai_config.get('has_background', False),
            background_url=scene.ai_config.get('background_url'),
            voice_speed=scene.ai_config.get('voice_speed', 1.0),
            voice_pitch=scene.ai_config.get('voice_pitch', 50),
            voice_emotion=scene.ai_config.get('voice_emotion', 'Excited'),
        )
        
        return response.get('data', {}).get('video_id')
    
    def _generate_veo_scene_video(self, scene):
        """Genera video de escena con Gemini Veo"""
        from .ai_services.gemini_veo import GeminiVeoClient
        
        if not settings.GEMINI_API_KEY:
            raise ValidationException('GEMINI_API_KEY no está configurada')
        
        model_name = scene.ai_config.get('veo_model', 'veo-2.0-generate-001')
        client = GeminiVeoClient(api_key=settings.GEMINI_API_KEY, model_name=model_name)
        
        # Preparar storage URI
        storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/projects/{scene.project.id}/scenes/{scene.id}/"
        
        # Usar el script_text de la escena como prompt
        prompt = scene.script_text
        
        # Si hay B-roll, agregar contexto visual
        if scene.broll:
            prompt += f"\n\nVisual context: {', '.join(scene.broll[:3])}"
        
        params = {
            'prompt': prompt,
            'title': f"{scene.scene_id}",
            'duration': scene.ai_config.get('duration', 8),
            'aspect_ratio': scene.ai_config.get('aspect_ratio', '16:9'),
            'sample_count': scene.ai_config.get('sample_count', 1),
            'negative_prompt': scene.ai_config.get('negative_prompt'),
            'enhance_prompt': scene.ai_config.get('enhance_prompt', True),
            'person_generation': scene.ai_config.get('person_generation', 'allow_adult'),
            'compression_quality': scene.ai_config.get('compression_quality', 'optimized'),
            'seed': scene.ai_config.get('seed'),
            'storage_uri': storage_uri,
        }
        
        response = client.generate_video(**params)
        return response.get('video_id')
    
    def _generate_sora_scene_video(self, scene):
        """Genera video de escena con OpenAI Sora"""
        from .ai_services.sora import SoraClient
        
        if not settings.OPENAI_API_KEY:
            raise ValidationException('OPENAI_API_KEY no está configurada')
        
        client = SoraClient(api_key=settings.OPENAI_API_KEY)
        
        # Usar el script_text de la escena como prompt
        prompt = scene.script_text
        
        # Si hay B-roll, agregar contexto visual
        if scene.broll:
            prompt += f"\n\nVisual elements: {', '.join(scene.broll[:3])}"
        
        model = scene.ai_config.get('sora_model', 'sora-2')
        duration = int(scene.ai_config.get('duration', 8))
        size = scene.ai_config.get('size', '1280x720')
        
        response = client.generate_video(
            prompt=prompt,
            model=model,
            seconds=duration,
            size=size
        )
        
        return response.get('video_id')
    
    def check_scene_video_status(self, scene) -> Dict:
        """
        Consulta el estado del video de una escena en la API externa
        
        Args:
            scene: Scene a consultar
            
        Returns:
            Dict con estado actualizado
        """
        if not scene.external_id:
            raise ValidationException('La escena no tiene external_id')
        
        # Si ya está en estado final, no consultar
        if scene.video_status in ['completed', 'error']:
            return {
                'status': scene.video_status,
                'message': 'Video ya procesado'
            }
        
        try:
            if scene.ai_service == 'heygen':
                return self._check_heygen_scene_status(scene)
            elif scene.ai_service == 'gemini_veo':
                return self._check_veo_scene_status(scene)
            elif scene.ai_service == 'sora':
                return self._check_sora_scene_status(scene)
        except Exception as e:
            logger.error(f"Error al consultar estado de escena: {e}")
            raise ServiceException(str(e))
    
    def _check_heygen_scene_status(self, scene):
        """Consulta estado en HeyGen"""
        from .ai_services.heygen import HeyGenClient
        
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        status_data = client.get_video_status(scene.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            video_url = status_data.get('video_url')
            if video_url:
                gcs_path = f"projects/{scene.project.id}/scenes/{scene.id}/video.mp4"
                gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                
                metadata = {
                    'duration': status_data.get('duration'),
                    'video_url_original': video_url,
                    'thumbnail': status_data.get('thumbnail'),
                }
                
                scene.mark_video_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                logger.info(f"✓ Video de escena {scene.scene_id} completado: {gcs_full_path}")
        
        elif api_status == 'failed':
            error_msg = status_data.get('error', 'Video generation failed')
            scene.mark_video_as_error(error_msg)
        
        return status_data
    
    def _check_veo_scene_status(self, scene):
        """Consulta estado en Gemini Veo"""
        from .ai_services.gemini_veo import GeminiVeoClient
        
        client = GeminiVeoClient(api_key=settings.GEMINI_API_KEY)
        status_data = client.get_video_status(scene.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            all_video_urls = status_data.get('all_video_urls', [])
            if all_video_urls:
                # Usar el primer video generado
                video_data = all_video_urls[0]
                url = video_data['url']
                gcs_path = f"projects/{scene.project.id}/scenes/{scene.id}/video.mp4"
                
                if url.startswith('gs://'):
                    if url.startswith(f"gs://{settings.GCS_BUCKET_NAME}/"):
                        gcs_full_path = url
                    else:
                        gcs_full_path = gcs_storage.copy_from_gcs(url, gcs_path)
                elif url.startswith('http'):
                    gcs_full_path = gcs_storage.upload_from_url(url, gcs_path)
                else:
                    gcs_full_path = gcs_storage.upload_base64(url, gcs_path)
                
                metadata = {
                    'original_url': url,
                    'mime_type': video_data.get('mime_type', 'video/mp4'),
                    'operation_data': status_data.get('operation_data', {}),
                }
                
                scene.mark_video_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                logger.info(f"✓ Video de escena {scene.scene_id} completado: {gcs_full_path}")
        
        elif api_status in ['failed', 'error']:
            error_msg = status_data.get('error', 'Video generation failed')
            scene.mark_video_as_error(error_msg)
        
        return status_data
    
    def _check_sora_scene_status(self, scene):
        """Consulta estado en OpenAI Sora"""
        from .ai_services.sora import SoraClient
        
        client = SoraClient(api_key=settings.OPENAI_API_KEY)
        status_data = client.get_video_status(scene.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                success = client.download_video(scene.external_id, tmp_path)
                
                if success:
                    gcs_path = f"projects/{scene.project.id}/scenes/{scene.id}/video.mp4"
                    
                    with open(tmp_path, 'rb') as video_file:
                        gcs_full_path = gcs_storage.upload_from_bytes(
                            file_content=video_file.read(),
                            destination_path=gcs_path,
                            content_type='video/mp4'
                        )
                    
                    metadata = {
                        'model': status_data.get('model'),
                        'duration': status_data.get('seconds'),
                        'size': status_data.get('size'),
                    }
                    
                    scene.mark_video_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                    logger.info(f"✓ Video de escena {scene.scene_id} completado: {gcs_full_path}")
                else:
                    scene.mark_video_as_error("No se pudo descargar el video desde Sora")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif api_status == 'failed':
            error_msg = status_data.get('error', 'Video generation failed')
            scene.mark_video_as_error(error_msg)
        
        return status_data
    
    def get_scene_with_signed_urls(self, scene) -> Dict:
        """
        Obtiene una escena con todas sus URLs firmadas generadas
        
        Args:
            scene: Scene a procesar
            
        Returns:
            Dict con scene y URLs firmadas
        """
        result = {
            'scene': scene,
            'preview_image_url': None,
            'video_url': None
        }
        
        # URL firmada del preview image
        if scene.preview_image_status == 'completed' and scene.preview_image_gcs_path:
            try:
                result['preview_image_url'] = gcs_storage.get_signed_url(
                    scene.preview_image_gcs_path,
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada de preview: {e}")
        
        # URL firmada del video
        if scene.video_status == 'completed' and scene.video_gcs_path:
            try:
                result['video_url'] = gcs_storage.get_signed_url(
                    scene.video_gcs_path,
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada de video: {e}")
        
        return result


# ====================
# VIDEO COMPOSITION SERVICE
# ====================

class VideoCompositionService:
    """Servicio para combinar múltiples videos usando FFmpeg"""
    
    @staticmethod
    def combine_scene_videos(scenes, output_filename: str) -> str:
        """
        Combina videos de múltiples escenas usando FFmpeg
        
        Args:
            scenes: QuerySet o lista de Scene objects ordenados
            output_filename: Nombre base para el archivo de salida
            
        Returns:
            GCS path del video combinado
            
        Raises:
            ServiceException: Si falla la combinación
        """
        import tempfile
        import os
        import subprocess
        from django.conf import settings
        
        if not scenes or len(scenes) == 0:
            raise ValidationException("No hay escenas para combinar")
        
        # Verificar que todos tengan video
        for scene in scenes:
            if scene.video_status != 'completed' or not scene.video_gcs_path:
                raise ValidationException(f"La escena {scene.scene_id} no tiene video completado")
        
        temp_dir = None
        concat_file_path = None
        output_path = None
        
        try:
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp(prefix='atenea_combine_')
            logger.info(f"Directorio temporal creado: {temp_dir}")
            
            # Descargar todos los videos de GCS al directorio temporal
            video_paths = []
            for idx, scene in enumerate(scenes):
                # Extraer blob name del GCS path
                blob_name = scene.video_gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                blob = gcs_storage.bucket.blob(blob_name)
                
                # Descargar a archivo temporal
                temp_video_path = os.path.join(temp_dir, f"scene_{idx:03d}.mp4")
                blob.download_to_filename(temp_video_path)
                video_paths.append(temp_video_path)
                
                logger.info(f"Descargado: {scene.scene_id} -> {temp_video_path}")
            
            # Crear archivo de lista para FFmpeg concat
            concat_file_path = os.path.join(temp_dir, 'concat_list.txt')
            with open(concat_file_path, 'w', encoding='utf-8') as f:
                for video_path in video_paths:
                    # FFmpeg requiere rutas con formato específico
                    # Usar rutas absolutas y escapar caracteres especiales
                    escaped_path = video_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            logger.info(f"Archivo de concatenación creado: {concat_file_path}")
            
            # Path de salida temporal
            output_path = os.path.join(temp_dir, 'combined_output.mp4')
            
            # Ejecutar FFmpeg para combinar
            # Usar codec copy para no re-encodear (más rápido)
            ffmpeg_command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file_path,
                '-c', 'copy',  # Copy streams sin re-encodear
                '-y',  # Sobrescribir si existe
                output_path
            ]
            
            logger.info(f"Ejecutando FFmpeg: {' '.join(ffmpeg_command)}")
            
            result = subprocess.run(
                ffmpeg_command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo
            )
            
            if result.returncode != 0:
                error_msg = f"FFmpeg falló con código {result.returncode}\n"
                error_msg += f"STDOUT: {result.stdout}\n"
                error_msg += f"STDERR: {result.stderr}"
                logger.error(error_msg)
                raise ServiceException(f"Error al combinar videos con FFmpeg: {result.stderr[:500]}")
            
            logger.info("✓ Videos combinados exitosamente con FFmpeg")
            
            # Verificar que el archivo de salida existe
            if not os.path.exists(output_path):
                raise ServiceException("FFmpeg no generó el archivo de salida")
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Video combinado: {file_size} bytes")
            
            # Subir video combinado a GCS
            project_id = scenes[0].project.id if hasattr(scenes[0], 'project') else 'unknown'
            gcs_destination = f"projects/{project_id}/combined_videos/{output_filename}"
            
            with open(output_path, 'rb') as video_file:
                gcs_full_path = gcs_storage.upload_from_bytes(
                    file_content=video_file.read(),
                    destination_path=gcs_destination,
                    content_type='video/mp4'
                )
            
            logger.info(f"✓ Video combinado subido a GCS: {gcs_full_path}")
            
            return gcs_full_path
            
        except subprocess.TimeoutExpired:
            raise ServiceException("FFmpeg timeout: el proceso tardó más de 5 minutos")
        except Exception as e:
            logger.error(f"Error al combinar videos: {e}")
            raise ServiceException(f"Error al combinar videos: {str(e)}")
        finally:
            # Limpiar archivos temporales
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.info(f"✓ Directorio temporal eliminado: {temp_dir}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar directorio temporal {temp_dir}: {e}")
    
    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """
        Obtiene la duración de un video usando FFprobe
        
        Args:
            video_path: Path al archivo de video
            
        Returns:
            Duración en segundos
        """
        import subprocess
        
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logger.warning(f"No se pudo obtener duración del video: {result.stderr}")
                return 0.0
                
        except Exception as e:
            logger.warning(f"Error al obtener duración: {e}")
            return 0.0


# ====================
# N8N INTEGRATION SERVICE
# ====================

class N8nService:
    """Servicio para integrar con n8n para procesamiento de guiones"""
    
    def __init__(self):
        self.webhook_url = "https://n8n.nxhumans.com/webhook/6e03a7df-1812-446e-a776-9a5b4ab543c8"
    
    def send_script_for_processing(self, script):
        """Enviar guión a n8n para procesamiento"""
        try:
            import requests
            
            # Preparar datos para enviar (solo guión y duración)
            data = {
                'script_id': script.id,
                'guion': script.original_script,
                'duracion_minutos': script.desired_duration_min
            }
            
            # Marcar como procesando
            script.mark_as_processing()
            
            # Enviar a n8n
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Guión {script.id} enviado exitosamente a n8n")
                return True
            else:
                script.mark_as_error(f"Error HTTP {response.status_code}: {response.text}")
                logger.error(f"Error al enviar guión a n8n: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout as e:
            # Timeout no es un error fatal, n8n puede estar procesando
            logger.warning(f"Timeout al enviar guión a n8n (puede estar procesando): {e}")
            return True  # Consideramos que se envió correctamente
        except requests.exceptions.RequestException as e:
            script.mark_as_error(f"Error de conexión: {str(e)}")
            logger.error(f"Error de conexión al enviar guión a n8n: {e}")
            return False
        except Exception as e:
            script.mark_as_error(f"Error inesperado: {str(e)}")
            logger.error(f"Error inesperado al enviar guión a n8n: {e}")
            return False
    
    def process_webhook_response(self, data):
        """Procesar respuesta del webhook de n8n"""
        try:
            # Validar que tenemos la estructura esperada
            if 'status' not in data:
                raise ValidationException("Estructura de respuesta inválida del webhook")
            
            # Verificar que el procesamiento fue exitoso
            if data.get('status') != 'success':
                raise ValidationException(f"Error en n8n: {data.get('message', 'Error desconocido')}")
            
            # Obtener el script_id
            script_id = data.get('script_id')
            if not script_id:
                raise ValidationException("No se encontró script_id en la respuesta")
            
            try:
                script = Script.objects.get(id=script_id)
            except Script.DoesNotExist:
                raise ValidationException(f"Guión con ID {script_id} no encontrado")
            
            # Preparar datos procesados
            output_data = {}
            
            # Si viene con 'output' (estructura original)
            if 'output' in data:
                output_data = data.get('output')
                # Si output_data es un string (JSON stringificado), parsearlo
                if isinstance(output_data, str):
                    import json
                    output_data = json.loads(output_data)
            
            # Si viene con 'project' y 'scenes' directamente (estructura nueva)
            elif 'project' in data and 'scenes' in data:
                output_data = {
                    'project': data.get('project'),
                    'scenes': data.get('scenes')
                }
            
            # Validar estructura de datos procesados
            if 'project' not in output_data or 'scenes' not in output_data:
                raise ValidationException("Estructura de datos procesados inválida")
            
            # Marcar como completado con los datos procesados
            script.mark_as_completed(output_data)
            
            # Si es flujo del agente, crear objetos Scene en la BD
            if script.agent_flow:
                logger.info(f"Script {script_id} es del flujo del agente, creando escenas en BD...")
                scenes_data = output_data.get('scenes', [])
                
                if scenes_data:
                    # Crear escenas usando SceneService
                    created_scenes = SceneService.create_scenes_from_n8n_data(script, scenes_data)
                    
                    # Iniciar generación de preview images en background para cada escena
                    scene_service = SceneService()
                    for scene in created_scenes:
                        try:
                            # TODO: Idealmente esto debería ser async o con Celery
                            # Por ahora lo hacemos síncrono
                            scene_service.generate_preview_image(scene)
                        except Exception as e:
                            # No bloqueamos si falla una preview image
                            logger.error(f"Error al generar preview para escena {scene.scene_id}: {e}")
                    
                    logger.info(f"✓ {len(created_scenes)} escenas creadas para script {script_id}")
            
            logger.info(f"Guión {script_id} procesado exitosamente por n8n")
            return script
            
        except Exception as e:
            logger.error(f"Error al procesar respuesta del webhook: {e}")
            raise ServiceException(f"Error al procesar respuesta: {str(e)}")


class RedisService:
    """Servicio para manejar comunicación con Redis"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    def set_script_result(self, script_id: str, result_data: dict):
        """Guardar resultado de guión procesado en Redis"""
        try:
            key = f"script_result:{script_id}"
            value = json.dumps(result_data)
            
            # Guardar con expiración de 1 hora
            self.redis_client.setex(key, 3600, value)
            logger.info(f"Resultado del guión {script_id} guardado en Redis")
            
        except Exception as e:
            logger.error(f"Error al guardar resultado en Redis: {e}")
            raise ServiceException(f"Error al guardar en Redis: {str(e)}")
    
    def get_script_result(self, script_id: str):
        """Obtener resultado de un guión desde Redis"""
        try:
            key = f"script_result:{script_id}"
            result = self.redis_client.get(key)
            
            if result:
                data = json.loads(result)
                logger.info(f"Resultado encontrado en Redis para guión {script_id}")
                return data
            else:
                logger.info(f"No hay resultado aún en Redis para guión {script_id}")
                return None
            
        except Exception as e:
            logger.error(f"Error al obtener resultado de Redis: {e}")
            return None