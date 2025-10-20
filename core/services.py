"""
Capa de servicios para manejar la lógica de negocio
"""

import logging
from typing import Dict, Optional, List
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from datetime import datetime

from .models import Project, Video
from .ai_services.heygen import HeyGenClient
from .ai_services.gemini_veo import GeminiVeoClient
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
