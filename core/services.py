"""
Capa de servicios para manejar la lógica de negocio
"""

import logging
import json
import redis
import requests
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from datetime import datetime

from .models import Project, Video, Image, Audio, Script
from django.contrib.auth.models import User
from .ai_services.heygen import HeyGenClient
from .ai_services.gemini_veo import GeminiVeoClient
from .ai_services.gemini_image import GeminiImageClient
from .ai_services.seedream import SeaDreamImageClient
from .ai_services.sora import SoraClient
from .storage.gcs import gcs_storage
from core.utils.prompt_templates import apply_prompt_template

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


# Importar excepciones de créditos para uso en servicios
try:
    from .services.credits import InsufficientCreditsException, RateLimitExceededException
except ImportError:
    # Si el módulo no existe aún, definir excepciones básicas
    class InsufficientCreditsException(ServiceException):
        """Excepción cuando no hay suficientes créditos"""
        pass
    
    class RateLimitExceededException(ServiceException):
        """Excepción cuando se excede el límite mensual"""
        pass


# ====================
# PROJECT SERVICE
# ====================

class ProjectService:
    """Servicio para manejar lógica de proyectos"""
    
    @staticmethod
    def create_project(name: str, owner) -> Project:
        """
        Crea un nuevo proyecto
        
        Args:
            name: Nombre del proyecto
            owner: Usuario propietario (requerido)
        
        Returns:
            Project creado
        
        Raises:
            ValidationException: Si el nombre no es válido o el owner no es válido
        """
        if len(name.strip()) < 3:
            raise ValidationException('El nombre debe tener al menos 3 caracteres')
        
        if not owner or not owner.is_authenticated:
            raise ValidationException('Se requiere un usuario propietario válido')
        
        project = Project.objects.create(name=name.strip(), owner=owner)
        logger.info(f"Proyecto creado: {project.id} - {project.name} por {owner.username}")
        
        return project
    
    @staticmethod
    def get_user_projects(user) -> List[Project]:
        """
        Obtiene proyectos del usuario (propios y compartidos)
        
        Args:
            user: Usuario autenticado
        
        Returns:
            Lista de proyectos a los que el usuario tiene acceso
        """
        if not user or not user.is_authenticated:
            return Project.objects.none()
        
        # Proyectos propios
        owned = Project.objects.filter(owner=user)
        
        # Proyectos compartidos (a través de ProjectMember)
        from .models import ProjectMember
        shared_project_ids = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
        shared = Project.objects.filter(id__in=shared_project_ids)
        
        # Combinar y ordenar
        return (owned | shared).distinct().order_by('-created_at')
    
    @staticmethod
    def user_has_access(project: Project, user) -> bool:
        """
        Verifica si un usuario tiene acceso a un proyecto
        
        Args:
            project: Proyecto a verificar
            user: Usuario a verificar
        
        Returns:
            True si el usuario tiene acceso, False en caso contrario
        """
        if not user or not user.is_authenticated:
            return False
        
        return project.has_access(user)
    
    @staticmethod
    def user_can_edit(project: Project, user) -> bool:
        """
        Verifica si un usuario puede editar un proyecto
        
        Args:
            project: Proyecto a verificar
            user: Usuario a verificar
        
        Returns:
            True si el usuario puede editar (owner o editor), False en caso contrario
        """
        if not user or not user.is_authenticated:
            return False
        
        role = project.get_user_role(user)
        return role in ['owner', 'editor']
    
    @staticmethod
    def add_member(project: Project, user, role: str = 'editor') -> 'ProjectMember':
        """
        Agrega un miembro a un proyecto
        
        Args:
            project: Proyecto al que agregar el miembro
            user: Usuario a agregar
            role: Rol del usuario ('owner' o 'editor')
        
        Returns:
            ProjectMember creado
        
        Raises:
            ValidationException: Si el usuario ya es miembro o el rol no es válido
        """
        from .models import ProjectMember
        
        if project.owner == user:
            raise ValidationException('El propietario ya tiene acceso al proyecto')
        
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise ValidationException('El usuario ya es miembro del proyecto')
        
        if role not in ['owner', 'editor']:
            raise ValidationException('Rol inválido. Debe ser "owner" o "editor"')
        
        member = ProjectMember.objects.create(project=project, user=user, role=role)
        logger.info(f"Miembro agregado: {user.username} a proyecto {project.id} como {role}")
        
        return member
    
    @staticmethod
    def remove_member(project: Project, user) -> None:
        """
        Elimina un miembro de un proyecto
        
        Args:
            project: Proyecto del que eliminar el miembro
            user: Usuario a eliminar
        """
        from .models import ProjectMember
        
        if project.owner == user:
            raise ValidationException('No se puede eliminar al propietario del proyecto')
        
        ProjectMember.objects.filter(project=project, user=user).delete()
        logger.info(f"Miembro eliminado: {user.username} del proyecto {project.id}")
    
    @staticmethod
    def update_project_name(project: Project, new_name: str, user) -> Project:
        """
        Actualiza el nombre de un proyecto
        
        Args:
            project: Proyecto a actualizar
            new_name: Nuevo nombre del proyecto
            user: Usuario que realiza la actualización
        
        Returns:
            Project actualizado
        
        Raises:
            ValidationException: Si el nombre no es válido o el usuario no tiene permisos
        """
        if not ProjectService.user_can_edit(project, user):
            raise ValidationException('No tienes permisos para editar este proyecto')
        
        if len(new_name.strip()) < 3:
            raise ValidationException('El nombre debe tener al menos 3 caracteres')
        
        project.name = new_name.strip()
        project.save()
        logger.info(f"Nombre del proyecto {project.id} actualizado a '{project.name}' por {user.username}")
        
        return project
    
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
    def get_project_with_videos_by_uuid(project_uuid) -> Project:
        """Obtiene proyecto con sus videos optimizado usando UUID"""
        try:
            return Project.objects.prefetch_related(
                'videos'
            ).get(uuid=project_uuid)
        except Project.DoesNotExist:
            raise ValidationException(f'Proyecto {project_uuid} no encontrado')
    
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
# INVITATION SERVICE
# ====================

class InvitationService:
    """Servicio para manejar invitaciones a proyectos"""
    
    @staticmethod
    def create_invitation(
        project: Project,
        email: str,
        invited_by,
        role: str = 'editor',
        expires_in_days: int = 7
    ) -> 'ProjectInvitation':
        """
        Crea una invitación para unirse a un proyecto
        
        Args:
            project: Proyecto al que se invita
            email: Email del usuario invitado
            invited_by: Usuario que envía la invitación
            role: Rol que se asignará ('owner' o 'editor')
            expires_in_days: Días hasta que expire la invitación (default: 7)
        
        Returns:
            ProjectInvitation creada
        
        Raises:
            ValidationException: Si hay un error en la validación
        """
        from .models import ProjectInvitation, ProjectMember
        from django.utils import timezone
        from datetime import timedelta
        
        # Validaciones
        if not email or '@' not in email:
            raise ValidationException('Email inválido')
        
        if role not in ['owner', 'editor']:
            raise ValidationException('Rol inválido. Debe ser "owner" o "editor"')
        
        # Verificar que el usuario que invita tenga permisos
        if not ProjectService.user_can_edit(project, invited_by):
            raise ValidationException('No tienes permisos para invitar usuarios a este proyecto')
        
        # Verificar si ya existe una invitación pendiente para este email
        existing = ProjectInvitation.objects.filter(
            project=project,
            email=email,
            status='pending'
        ).first()
        
        if existing and not existing.is_expired():
            raise ValidationException('Ya existe una invitación pendiente para este email')
        
        # Si existe pero está expirada, cancelarla
        if existing and existing.is_expired():
            existing.status = 'expired'
            existing.save()
        
        # Verificar si el usuario ya es miembro
        try:
            user = User.objects.get(email=email)
            if project.owner == user or ProjectMember.objects.filter(project=project, user=user).exists():
                raise ValidationException('El usuario ya tiene acceso al proyecto')
        except User.DoesNotExist:
            pass  # Usuario no existe aún, está bien
        
        # Crear invitación
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        invitation = ProjectInvitation.objects.create(
            project=project,
            email=email,
            invited_by=invited_by,
            role=role,
            expires_at=expires_at
        )
        
        logger.info(f"Invitación creada: {email} para proyecto {project.id} por {invited_by.username}")
        
        return invitation
    
    @staticmethod
    def accept_invitation(token: str, user) -> 'ProjectMember':
        """
        Acepta una invitación y agrega al usuario al proyecto
        
        Args:
            token: Token de la invitación
            user: Usuario que acepta la invitación
        
        Returns:
            ProjectMember creado
        
        Raises:
            ValidationException: Si la invitación no es válida o no puede ser aceptada
        """
        from .models import ProjectInvitation
        
        try:
            invitation = ProjectInvitation.objects.get(token=token)
        except ProjectInvitation.DoesNotExist:
            raise ValidationException('Invitación no encontrada')
        
        # Validar que el email coincida
        if invitation.email.lower() != user.email.lower():
            raise ValidationException('Esta invitación es para otro usuario')
        
        # Validar que pueda ser aceptada
        if not invitation.can_be_accepted():
            if invitation.is_expired():
                invitation.status = 'expired'
                invitation.save()
                raise ValidationException('La invitación ha expirado')
            raise ValidationException('La invitación no puede ser aceptada')
        
        # Agregar usuario al proyecto
        member = ProjectService.add_member(invitation.project, user, invitation.role)
        
        # Marcar invitación como aceptada
        from django.utils import timezone
        invitation.status = 'accepted'
        invitation.accepted_at = timezone.now()
        invitation.save()
        
        logger.info(f"Invitación aceptada: {user.username} se unió al proyecto {invitation.project.id}")
        
        return member
    
    @staticmethod
    def cancel_invitation(invitation_id: int, user) -> None:
        """
        Cancela una invitación
        
        Args:
            invitation_id: ID de la invitación
            user: Usuario que cancela (debe ser el que la creó o owner del proyecto)
        
        Raises:
            ValidationException: Si no tiene permisos o la invitación no existe
        """
        from .models import ProjectInvitation
        
        try:
            invitation = ProjectInvitation.objects.get(id=invitation_id)
        except ProjectInvitation.DoesNotExist:
            raise ValidationException('Invitación no encontrada')
        
        # Verificar permisos
        if invitation.invited_by != user and invitation.project.owner != user:
            raise ValidationException('No tienes permisos para cancelar esta invitación')
        
        if invitation.status != 'pending':
            raise ValidationException('Solo se pueden cancelar invitaciones pendientes')
        
        invitation.status = 'cancelled'
        invitation.save()
        
        logger.info(f"Invitación cancelada: {invitation_id} por {user.username}")
    
    @staticmethod
    def get_project_invitations(project: Project, user) -> List['ProjectInvitation']:
        """
        Obtiene las invitaciones de un proyecto
        
        Args:
            project: Proyecto
            user: Usuario que solicita (debe tener permisos)
        
        Returns:
            Lista de invitaciones
        """
        from .models import ProjectInvitation
        
        if not ProjectService.user_can_edit(project, user):
            raise ValidationException('No tienes permisos para ver las invitaciones')
        
        return ProjectInvitation.objects.filter(project=project).order_by('-created_at')


# ====================
# VIDEO SERVICE
# ====================

class VideoService:
    """Servicio principal para manejar videos"""
    
    def __init__(self):
        self.heygen_client = None
        self.veo_client = None
        self.sora_client = None
        self.higgsfield_client = None
        self.kling_client = None
    
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
    
    def _get_higgsfield_client(self):
        """Lazy initialization de Higgsfield client"""
        if not self.higgsfield_client:
            from .ai_services.higgsfield import HiggsfieldClient
            if not settings.HIGGSFIELD_API_KEY_ID or not settings.HIGGSFIELD_API_KEY:
                raise ValidationException('HIGGSFIELD_API_KEY_ID y HIGGSFIELD_API_KEY deben estar configuradas')
            self.higgsfield_client = HiggsfieldClient(
                api_key_id=settings.HIGGSFIELD_API_KEY_ID,
                api_key_secret=settings.HIGGSFIELD_API_KEY
            )
        return self.higgsfield_client
    
    def _get_kling_client(self):
        """Lazy initialization de Kling client"""
        if not self.kling_client:
            from .ai_services.kling import KlingClient
            if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
                raise ValidationException('KLING_ACCESS_KEY y KLING_SECRET_KEY deben estar configuradas')
            self.kling_client = KlingClient(
                access_key=settings.KLING_ACCESS_KEY,
                secret_key=settings.KLING_SECRET_KEY
            )
        return self.kling_client
    
    # ----------------
    # CREAR VIDEO
    # ----------------
    
    def create_video(
        self,
        created_by: User,
        project: Project = None,
        title: str = None,
        video_type: str = None,
        script: str = None,
        config: Dict = None
    ) -> Video:
        """
        Crea un nuevo video (sin generarlo)
        
        Args:
            created_by: Usuario que crea el video
            project: Proyecto al que pertenece (opcional)
            title: Título del video
            video_type: Tipo de video
            script: Guión
            config: Configuración específica del tipo
        
        Returns:
            Video creado
        """
        video = Video.objects.create(
            created_by=created_by,
            project=project,
            title=title,
            type=video_type,
            script=script,
            config=config
        )
        
        logger.info(f"Video creado: {video.id} - {video.title} ({video.type}) por {created_by.username}")
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
        project: Project = None
    ) -> List[Dict]:
        """
        Sube imágenes de referencia para Veo
        
        Args:
            images: Lista de archivos de imagen
            reference_types: Lista de tipos ('asset' o 'style')
            project: Proyecto relacionado (opcional)
        
        Returns:
            Lista de dicts con datos de las imágenes subidas
        """
        from PIL import Image
        import io
        
        reference_images = []
        
        # Formatos soportados por Veo
        SUPPORTED_FORMATS = ['JPEG', 'PNG']
        SUPPORTED_MIME_TYPES = ['image/jpeg', 'image/png']
        
        for i, (image, ref_type) in enumerate(zip(images, reference_types)):
            if image:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_filename = image.name.replace(' ', '_')
                    
                    # Leer la imagen
                    image_file = image.read()
                    image.seek(0)  # Resetear el puntero
                    
                    # Detectar formato y convertir si es necesario
                    pil_image = Image.open(io.BytesIO(image_file))
                    original_format = pil_image.format
                    mime_type = image.content_type or f'image/{original_format.lower()}' if original_format else 'image/jpeg'
                    
                    # Convertir a JPEG si el formato no es soportado
                    if original_format not in SUPPORTED_FORMATS or mime_type not in SUPPORTED_MIME_TYPES:
                        logger.warning(f"Formato {original_format} ({mime_type}) no soportado por Veo. Convirtiendo a JPEG...")
                        
                        # Convertir a RGB si tiene canal alpha (RGBA, LA, etc.)
                        if pil_image.mode in ('RGBA', 'LA', 'P'):
                            # Crear fondo blanco para imágenes con transparencia
                            rgb_image = Image.new('RGB', pil_image.size, (255, 255, 255))
                            if pil_image.mode == 'P':
                                pil_image = pil_image.convert('RGBA')
                            rgb_image.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode == 'RGBA' else None)
                            pil_image = rgb_image
                        elif pil_image.mode != 'RGB':
                            pil_image = pil_image.convert('RGB')
                        
                        # Convertir a bytes JPEG
                        output = io.BytesIO()
                        pil_image.save(output, format='JPEG', quality=95)
                        image_file = output.getvalue()
                        mime_type = 'image/jpeg'
                        safe_filename = safe_filename.rsplit('.', 1)[0] + '.jpg'
                        logger.info(f"✅ Imagen convertida a JPEG: {safe_filename}")
                    
                    # Manejar caso cuando project es None
                    if project:
                        gcs_destination = f"veo_reference_images/project_{project.id}/{timestamp}_{i+1}_{safe_filename}"
                    else:
                        gcs_destination = f"veo_reference_images/standalone/{timestamp}_{i+1}_{safe_filename}"
                    
                    logger.info(f"Subiendo imagen de referencia {i+1} ({ref_type}): {safe_filename} ({mime_type})")
                    
                    # Subir imagen convertida
                    gcs_path = gcs_storage.upload_from_bytes(
                        file_content=image_file,
                        destination_path=gcs_destination,
                        content_type=mime_type
                    )
                    
                    reference_images.append({
                        'gcs_uri': gcs_path,
                        'reference_type': ref_type,
                        'mime_type': mime_type
                    })
                    
                    logger.info(f"✅ Imagen de referencia {i+1} subida: {gcs_path}")
                except Exception as e:
                    logger.error(f"Error al subir imagen de referencia {i+1}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
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
            InsufficientCreditsException: Si no hay suficientes créditos
            RateLimitExceededException: Si se excede el límite mensual
        """
        # Validar estado
        if video.status in ['processing', 'completed']:
            raise ValidationException(f'El video ya está en estado: {video.get_status_display()}')
        
        # Validar créditos ANTES de generar
        if video.created_by:
            from core.services.credits import CreditService, InsufficientCreditsException, RateLimitExceededException
            
            estimated_cost = CreditService.estimate_video_cost(
                video_type=video.type,
                duration=video.config.get('duration', 8),
                config=video.config
            )
            
            if estimated_cost > 0:
                if not CreditService.has_enough_credits(video.created_by, estimated_cost):
                    raise InsufficientCreditsException(
                        f"No tienes suficientes créditos. Necesitas aproximadamente {estimated_cost} créditos. "
                        f"Créditos disponibles: {CreditService.get_or_create_user_credits(video.created_by).credits}"
                    )
                
                try:
                    CreditService.check_rate_limit(video.created_by, estimated_cost)
                except RateLimitExceededException as e:
                    raise ValidationException(str(e))
        
        # Marcar como procesando
        video.mark_as_processing()
        
        try:
            if video.type in ['heygen_avatar_v2', 'heygen_avatar_iv']:
                external_id = self._generate_heygen_video(video)
            elif video.type == 'gemini_veo':
                external_id = self._generate_veo_video(video)
            elif video.type == 'sora':
                external_id = self._generate_sora_video(video)
            elif video.type in ['higgsfield_dop_standard', 'higgsfield_dop_preview', 'higgsfield_seedance_v1_pro', 'higgsfield_kling_v2_1_pro']:
                external_id = self._generate_higgsfield_video(video)
            elif video.type.startswith('kling_'):
                external_id = self._generate_kling_video(video)
            elif video.type == 'manim_quote':
                external_id = self._generate_manim_quote_video(video)
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
    
    def generate_video_async(self, video: Video, metadata: Dict = None) -> 'GenerationTask':
        """
        Encola la generación de un video usando el sistema de colas
        
        Args:
            video: Objeto Video a generar
            metadata: Metadata adicional (prompt, parámetros, etc.)
        
        Returns:
            GenerationTask creada
        
        Raises:
            ValidationException: Si hay error de validación
            ValueError: Si se alcanza el límite de tareas simultáneas
        """
        from core.services.queue import QueueService
        
        # Validar estado
        if video.status in ['processing', 'completed']:
            raise ValidationException(f'El video ya está en estado: {video.get_status_display()}')
        
        # Validar créditos ANTES de encolar
        if video.created_by:
            from core.services.credits import CreditService, InsufficientCreditsException, RateLimitExceededException
            
            estimated_cost = CreditService.estimate_video_cost(
                video_type=video.type,
                duration=video.config.get('duration', 8),
                config=video.config
            )
            
            if estimated_cost > 0:
                if not CreditService.has_enough_credits(video.created_by, estimated_cost):
                    raise InsufficientCreditsException(
                        f"No tienes suficientes créditos. Necesitas aproximadamente {estimated_cost} créditos. "
                        f"Créditos disponibles: {CreditService.get_or_create_user_credits(video.created_by).credits}"
                    )
                
                try:
                    CreditService.check_rate_limit(video.created_by, estimated_cost)
                except RateLimitExceededException as e:
                    raise ValidationException(str(e))
        
        # Preparar metadata
        task_metadata = metadata or {}
        task_metadata.update({
            'prompt': video.script,
            'video_type': video.type,
            'title': video.title,
        })
        
        # Encolar tarea
        task = QueueService.enqueue_generation(
            item=video,
            user=video.created_by,
            task_type='video',
            metadata=task_metadata
        )
        
        # Marcar video como pending (no processing todavía)
        video.status = 'pending'
        video.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Video {video.id} encolado. Task UUID: {task.uuid}")
        return task
    
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
            # Buscar imagen en diferentes ubicaciones posibles
            # 1. gcs_avatar_path (formulario tradicional)
            # 2. start_image (formulario dinámico)
            gcs_path = video.config.get('gcs_avatar_path') or video.config.get('start_image')
            
            if not gcs_path:
                raise ValidationException('Imagen de avatar es requerida')
            
            # Obtener URL firmada y subir a HeyGen
            avatar_url = gcs_storage.get_signed_url(gcs_path, expiration=600)
            image_key = client.upload_asset_from_url(avatar_url)
            
            # Guardar image_key y normalizar gcs_avatar_path para futuro uso
            video.config['image_key'] = image_key
            if not video.config.get('gcs_avatar_path') and video.config.get('start_image'):
                video.config['gcs_avatar_path'] = video.config['start_image']
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
        # Obtener el modelo desde config, con fallback a model_id si existe
        model_name = video.config.get('veo_model') or video.config.get('model_id', 'veo-2.0-generate-001')
        
        # Validar que el modelo soporte imágenes de referencia si las hay
        if video.config.get('reference_images'):
            from .ai_services.gemini_veo import VEO_MODELS
            if model_name in VEO_MODELS:
                if not VEO_MODELS[model_name].get('supports_reference_images', False):
                    raise ValidationException(
                        f'El modelo {model_name} no soporta imágenes de referencia. '
                        f'Usa veo-2.0-generate-exp o veo-3.1-*'
                    )
        
        client = self._get_veo_client(model_name)
        
        # Preparar storage URI
        if video.project:
            storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/projects/{video.project.id}/videos/{video.uuid}/"
        elif video.created_by:
            storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/users/{video.created_by.id}/videos/{video.uuid}/"
        else:
            storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/standalone/videos/{video.uuid}/"
        
        # Parámetros
        # Asegurar que duration sea un int válido
        duration = video.config.get('duration')
        if duration is None:
            duration = 8
        else:
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                duration = 8
        
        # Aplicar template de prompt si existe
        from core.utils.prompt_templates import apply_prompt_template
        final_prompt = apply_prompt_template(
            video.script,
            video.config.get('prompt_template_id')
        )
        
        params = {
            'prompt': final_prompt,
            'title': video.title,
            'duration': duration,
            'aspect_ratio': video.config.get('aspect_ratio', '16:9'),
            'sample_count': video.config.get('sample_count', 1),
            'negative_prompt': video.config.get('negative_prompt'),
            'enhance_prompt': video.config.get('enhance_prompt', True),
            'person_generation': video.config.get('person_generation', 'allow_adult'),
            'compression_quality': video.config.get('compression_quality', 'optimized'),
            'seed': video.config.get('seed'),
            'storage_uri': storage_uri,
        }
        
        # Parámetros específicos de Veo 3/3.1
        if video.config.get('generate_audio') is not None:
            params['generate_audio'] = video.config.get('generate_audio', False)
        if video.config.get('resolution'):
            params['resolution'] = video.config.get('resolution')
        if video.config.get('resize_mode'):
            params['resize_mode'] = video.config.get('resize_mode')
        
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
        
        # Aplicar template de prompt si existe
        from core.utils.prompt_templates import apply_prompt_template
        final_prompt = apply_prompt_template(
            video.script,
            video.config.get('prompt_template_id')
        )
        
        # Obtener configuración
        model = video.config.get('sora_model', 'sora-2')
        duration = int(video.config.get('duration', 8))  # Asegurar que es int
        size = video.config.get('size', '1280x720')
        use_input_reference = video.config.get('use_input_reference', False)
        
        # Log de configuración antes de generar
        logger.info(f"🎬 Configuración de generación Sora:")
        logger.info(f"   Modelo: {model}")
        logger.info(f"   Duración: {duration}s")
        logger.info(f"   Tamaño: {size}")
        logger.info(f"   Usa imagen de referencia: {use_input_reference}")
        logger.info(f"   Longitud del prompt: {len(final_prompt)} caracteres")
        logger.info(f"   Prompt: {final_prompt[:200]}...")
        
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
                    prompt=final_prompt,
                    input_reference_path=tmp_path,
                    model=model,
                    seconds=duration,
                    size=size
                )
            except Exception as e:
                logger.error(f"❌ Error al generar video con imagen de referencia: {str(e)}")
                logger.error(f"   Config: model={model}, duration={duration}, size={size}")
                logger.error(f"   GCS path: {gcs_path}, MIME type: {mime_type}")
                raise
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    logger.info(f"Archivo temporal eliminado: {tmp_path}")
        else:
            # Generación text-to-video
            try:
                response = client.generate_video(
                    prompt=final_prompt,
                    model=model,
                    seconds=duration,
                    size=size
                )
            except Exception as e:
                logger.error(f"❌ Error al generar video: {str(e)}")
                logger.error(f"   Config: model={model}, duration={duration}, size={size}")
                logger.error(f"   Prompt length: {len(final_prompt)} caracteres")
                raise
        
        video_id = response.get('video_id')
        logger.info(f"✅ Video creado con ID: {video_id}")
        return video_id
    
    def _generate_higgsfield_video(self, video: Video) -> str:
        """Genera video con Higgsfield"""
        client = self._get_higgsfield_client()
        
        # Mapear tipo de video a model_id de Higgsfield
        model_map = {
            'higgsfield_dop_standard': 'higgsfield-ai/dop/standard',
            'higgsfield_dop_preview': 'higgsfield-ai/dop/preview',
            'higgsfield_seedance_v1_pro': 'bytedance/seedance/v1/pro/image-to-video',
            'higgsfield_kling_v2_1_pro': 'kling-video/v2.1/pro/image-to-video',
        }
        
        model_id = model_map.get(video.type)
        if not model_id:
            raise ValidationException(f'Tipo de video Higgsfield no válido: {video.type}')
        
        # Obtener configuración
        # Aplicar template de prompt si existe
        from core.utils.prompt_templates import apply_prompt_template
        prompt = apply_prompt_template(
            video.script,
            video.config.get('prompt_template_id')
        )
        
        # Obtener URL de imagen si existe (requerido para image-to-video)
        image_url = None
        if video.config.get('input_image_gcs_path'):
            # Obtener URL firmada de GCS
            gcs_path = video.config['input_image_gcs_path']
            image_url = gcs_storage.get_signed_url(gcs_path, expiration=3600)
            logger.info(f"Usando imagen de GCS: {gcs_path}")
        elif video.config.get('image_url'):
            image_url = video.config['image_url']
        
        if not image_url:
            raise ValidationException(f'El modelo {model_id} requiere una imagen de entrada (image_url o input_image_gcs_path)')
        
        # Preparar parámetros opcionales (solo si están en config)
        kwargs = {}
        if 'aspect_ratio' in video.config:
            kwargs['aspect_ratio'] = video.config['aspect_ratio']
        if 'resolution' in video.config:
            kwargs['resolution'] = video.config['resolution']
        if 'duration' in video.config:
            kwargs['duration'] = video.config['duration']
        
        # Generar video
        response = client.generate_video(
            model_id=model_id,
            prompt=prompt,
            image_url=image_url,
            **kwargs
        )
        
        return response.get('request_id')
    
    def _generate_kling_video(self, video: Video) -> str:
        """Genera video con Kling"""
        client = self._get_kling_client()
        
        # Mapear tipo de video a model_name de Kling
        model_map = {
            'kling_v1': 'kling-v1',
            'kling_v1_5': 'kling-v1-5',
            'kling_v1_6': 'kling-v1-6',
            'kling_v2_master': 'kling-v2-master',
            'kling_v2_1': 'kling-v2-1',
            'kling_v2_5_turbo': 'kling-v2-5-turbo',
        }
        
        model_name = model_map.get(video.type)
        if not model_name:
            raise ValidationException(f'Tipo de video Kling no válido: {video.type}')
        
        # Obtener configuración
        # Aplicar template de prompt si existe
        from core.utils.prompt_templates import apply_prompt_template
        prompt = apply_prompt_template(
            video.script,
            video.config.get('prompt_template_id')
        )
        
        mode = video.config.get('mode', 'std')  # 'std' o 'pro'
        duration = int(video.config.get('duration', 5))
        aspect_ratio = video.config.get('aspect_ratio', '16:9')
        
        # Validar duración (Kling solo soporta 5 o 10 segundos)
        if duration not in [5, 10]:
            logger.warning(f"Duración {duration}s ajustada a 5s (Kling solo soporta 5 o 10 segundos)")
            duration = 5
        
        # Obtener URL de imagen si existe (para image-to-video)
        image_url = None
        if video.config.get('input_image_gcs_path'):
            # Obtener URL firmada de GCS
            gcs_path = video.config['input_image_gcs_path']
            image_url = gcs_storage.get_signed_url(gcs_path, expiration=3600)
            logger.info(f"Usando imagen de GCS: {gcs_path}")
        elif video.config.get('image_url'):
            image_url = video.config['image_url']
        
        # Generar video
        response = client.generate_video(
            model_name=model_name,
            prompt=prompt,
            image_url=image_url,
            mode=mode,
            duration=duration,
            aspect_ratio=aspect_ratio
        )
        
        return response.get('task_id')
    
    def _generate_manim_quote_video(self, video: Video) -> str:
        """Genera video de cita con Manim"""
        from core.ai_services.manim import ManimClient
        
        client = ManimClient()
        
        # Obtener configuración
        quote = video.script  # El texto de la cita va en script
        author = video.config.get('author')
        duration = video.config.get('duration')
        quality = video.config.get('quality', 'k')  # Default: máxima calidad
        container_color = video.config.get('container_color')  # Color del contenedor
        text_color = video.config.get('text_color')  # Color del texto
        font_family = video.config.get('font_family')  # Tipo de fuente
        display_time = video.config.get('display_time')  # Tiempo de visualización en pantalla
        
        # Generar video localmente
        # Usar video.id como unique_id para evitar colisiones entre renders simultáneos
        result = client.generate_quote_video(
            quote=quote,
            author=author,
            duration=duration,
            quality=quality,
            container_color=container_color,
            text_color=text_color,
            font_family=font_family,
            display_time=display_time,
            unique_id=str(video.id)  # ID único por video para evitar colisiones
        )
        
        video_path = result['video_path']
        
        # Subir video a GCS
        if video.project:
            gcs_destination = f"projects/{video.project.id}/videos/{video.uuid}/manim_quote.mp4"
        elif video.created_by:
            gcs_destination = f"users/{video.created_by.id}/videos/{video.uuid}/manim_quote.mp4"
        else:
            gcs_destination = f"standalone/videos/{video.uuid}/manim_quote.mp4"
        
        logger.info(f"Subiendo video de Manim a GCS: {gcs_destination}")
        gcs_path = gcs_storage.upload_file(video_path, gcs_destination)
        
        # Marcar como completado inmediatamente (Manim genera síncronamente)
        metadata = {
            'duration': duration or video.config.get('estimated_duration'),
            'quality': quality,
            'author': author,
            'local_path': video_path,
        }
        
        video.mark_as_completed(gcs_path=gcs_path, metadata=metadata)
        
        # Limpiar archivos locales después de subir a GCS
        try:
            video_path_obj = Path(video_path)
            if video_path_obj.exists():
                video_path_obj.unlink()
                logger.info(f"✅ Archivo local eliminado: {video_path}")
            
            # También limpiar archivos parciales si existen
            partial_dir = video_path_obj.parent / "partial_movie_files" / "QuoteAnimation"
            if partial_dir.exists():
                import shutil
                shutil.rmtree(partial_dir)
                logger.info(f"✅ Archivos parciales eliminados: {partial_dir}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar archivo local {video_path}: {e}")
            # No fallar si no se puede eliminar
        
        # Usar el ID del video como external_id (Manim no tiene external_id)
        return f"manim_{video.id}"
    
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
        
        # Si ya está en estado final, verificar si se cobraron créditos
        if video.status in ['completed', 'error']:
            # Verificar y cobrar créditos si no se han cobrado aún
            if video.status == 'completed' and video.created_by:
                try:
                    from core.services.credits import CreditService
                    # Verificar si ya se cobraron créditos
                    if not video.metadata.get('credits_charged'):
                        logger.info(f"Video {video.id} completado pero sin créditos cobrados. Cobrando ahora...")
                        CreditService.deduct_credits_for_video(video.created_by, video)
                except Exception as e:
                    logger.error(f"Error al verificar/cobrar créditos para video {video.id}: {e}")
            
            return {
                'status': video.status,
                'message': 'Video ya procesado'
            }
        
        try:
            if video.type in ['heygen_avatar_v2', 'heygen_avatar_iv']:
                status_data = self._check_heygen_status(video)
            elif video.type == 'gemini_veo':
                status_data = self._check_veo_status(video)
            elif video.type == 'sora':
                status_data = self._check_sora_status(video)
            elif video.type in ['higgsfield_dop_standard', 'higgsfield_dop_preview', 'higgsfield_seedance_v1_pro', 'higgsfield_kling_v2_1_pro']:
                status_data = self._check_higgsfield_status(video)
            elif video.type.startswith('kling_'):
                status_data = self._check_kling_status(video)
            elif video.type == 'manim_quote':
                # Manim genera síncronamente, así que si está aquí es porque ya está completado
                status_data = {'status': video.status}
            else:
                status_data = {'status': video.status}
            
            # Si el video está completado pero tiene créditos pendientes, intentar cobrar de nuevo
            if video.status == 'completed' and video.created_by:
                video.refresh_from_db()
                if video.metadata.get('credits_charge_pending') and not video.metadata.get('credits_charged'):
                    logger.info(f"Video {video.id} tiene créditos pendientes. Intentando cobrar de nuevo.")
                    try:
                        from core.services.credits import CreditService
                        CreditService.deduct_credits_for_video(video.created_by, video)
                        # Si el cobro fue exitoso, limpiar el flag de pendiente
                        video.refresh_from_db()
                        if video.metadata.get('credits_charged'):
                            video.metadata.pop('credits_charge_pending', None)
                            video.metadata.pop('credits_charge_error', None)
                            video.save(update_fields=['metadata'])
                            logger.info(f"✓ Créditos cobrados exitosamente para video {video.id}")
                    except Exception as e:
                        logger.warning(f"No se pudieron cobrar créditos pendientes para video {video.id}: {e}")
            
            return status_data
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
                if video.project:
                    gcs_path = f"projects/{video.project.id}/videos/{video.uuid}/final_video.mp4"
                elif video.created_by:
                    gcs_path = f"users/{video.created_by.id}/videos/{video.uuid}/final_video.mp4"
                else:
                    gcs_path = f"standalone/videos/{video.uuid}/final_video.mp4"
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
        # Obtener el modelo correcto desde el config del video
        model_name = video.config.get('veo_model') or video.config.get('model_id', 'veo-2.0-generate-001')
        client = self._get_veo_client(model_name)
        status_data = client.get_video_status(video.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            all_video_urls = status_data.get('all_video_urls', [])
            rai_filtered_count = status_data.get('rai_filtered_count', 0)
            
            # Si todos los videos fueron filtrados por RAI, marcar como error
            if not all_video_urls and rai_filtered_count > 0:
                rai_reasons = status_data.get('rai_filtered_reasons', [])
                reason_text = rai_reasons[0] if rai_reasons else 'Violación de políticas de uso de Vertex AI'
                error_message = (
                    f"El video fue filtrado por las políticas de uso de Vertex AI. "
                    f"{rai_filtered_count} video(s) bloqueado(s). "
                    f"Razón: {reason_text}. "
                    f"Intenta reformular el prompt evitando contenido violento, sexual o controversial."
                )
                logger.warning(f"Video {video.id} filtrado por RAI: {error_message}")
                video.mark_as_error(error_message)
                return status_data
            
            # Si hay videos disponibles, procesarlos
            if all_video_urls:
                # Procesar todos los videos
                all_gcs_paths = []
                for idx, video_data in enumerate(all_video_urls):
                    url = video_data['url']
                    filename = f"video_{idx + 1}.mp4" if len(all_video_urls) > 1 else "video.mp4"
                    if video.project:
                        gcs_path = f"projects/{video.project.id}/videos/{video.uuid}/{filename}"
                    elif video.created_by:
                        gcs_path = f"users/{video.created_by.id}/videos/{video.uuid}/{filename}"
                    else:
                        gcs_path = f"standalone/videos/{video.uuid}/{filename}"
                    
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
                    'rai_filtered_count': rai_filtered_count,
                    'videos_raw': status_data.get('videos', []),
                    'operation_data': status_data.get('operation_data', {}),
                    # Agregar duración desde la configuración del video
                    'duration': video.config.get('duration', 8),
                }
                
                video.mark_as_completed(
                    gcs_path=all_gcs_paths[0]['gcs_path'],
                    metadata=metadata
                )
            elif not all_video_urls:
                # Caso edge: completed pero sin videos y sin filtros RAI (no debería pasar)
                error_message = "Video completado pero sin videos disponibles"
                logger.warning(f"Video {video.id}: {error_message}")
                video.mark_as_error(error_message)
        
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
                    if video.project:
                        gcs_path = f"projects/{video.project.id}/videos/{video.uuid}/video.mp4"
                    elif video.created_by:
                        gcs_path = f"users/{video.created_by.id}/videos/{video.uuid}/video.mp4"
                    else:
                        gcs_path = f"standalone/videos/{video.uuid}/video.mp4"
                    
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
                            if video.project:
                                thumb_gcs_path = f"projects/{video.project.id}/videos/{video.uuid}/thumbnail.webp"
                            elif video.created_by:
                                thumb_gcs_path = f"users/{video.created_by.id}/videos/{video.uuid}/thumbnail.webp"
                            else:
                                thumb_gcs_path = f"standalone/videos/{video.uuid}/thumbnail.webp"
                            
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
            error_obj = status_data.get('error')
            
            # El error puede ser un dict con 'code' y 'message' o un string
            if isinstance(error_obj, dict):
                error_code = error_obj.get('code', 'unknown_error')
                error_message = error_obj.get('message', 'Video generation failed')
                error_msg = f"[{error_code}] {error_message}"
                logger.error(f"❌ Video Sora {video.id} falló: {error_msg}")
                logger.error(f"   Error completo: {error_obj}")
            else:
                error_msg = str(error_obj) if error_obj else 'Video generation failed'
                logger.error(f"❌ Video Sora {video.id} falló: {error_msg}")
            
            video.mark_as_error(error_msg)
        
        return status_data
    
    def _check_higgsfield_status(self, video: Video) -> Dict:
        """Consulta estado en Higgsfield API"""
        client = self._get_higgsfield_client()
        status_data = client.get_request_status(video.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            video_url = status_data.get('video_url')
            if video_url:
                # Determinar ruta GCS según contexto
                if video.project:
                    gcs_path = f"projects/{video.project.id}/videos/{video.uuid}/video.mp4"
                elif video.created_by:
                    gcs_path = f"users/{video.created_by.id}/videos/{video.uuid}/video.mp4"
                else:
                    gcs_path = f"standalone/videos/{video.uuid}/video.mp4"
                
                try:
                    # Descargar video desde URL y subir a GCS
                    gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                    
                    # Preparar metadata
                    metadata = {
                        'video_url_original': video_url,
                        'request_id': video.external_id,
                        'image_urls': status_data.get('image_urls', []),
                        'raw_response': status_data.get('raw_response', {}),
                    }
                    
                    video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                    logger.info(f"Video Higgsfield {video.id} completado: {gcs_full_path}")
                except Exception as e:
                    logger.error(f"Error al descargar/subir video de Higgsfield {video.id}: {e}")
                    video.mark_as_error(f"Error al procesar video: {str(e)}")
            else:
                logger.warning(f"Video Higgsfield {video.id} completado pero sin URL de video")
                video.mark_as_error("Video completado pero sin URL disponible")
        
        elif api_status in ['failed', 'error', 'nsfw']:
            error_msg = status_data.get('error', 'Video generation failed')
            if api_status == 'nsfw':
                error_msg = 'Content failed moderation checks (NSFW)'
            video.mark_as_error(error_msg)
            logger.error(f"Video Higgsfield {video.id} falló: {error_msg}")
        
        return status_data
    
    def _check_kling_status(self, video: Video) -> Dict:
        """Consulta estado en Kling API"""
        client = self._get_kling_client()
        status_data = client.get_video_status(video.external_id)
        
        api_status = status_data.get('status')
        
        # Kling puede usar 'completed' o 'success' como estado de completado
        if api_status in ['completed', 'success']:
            video_url = status_data.get('video_url')
            if video_url:
                # Determinar ruta GCS según contexto
                if video.project:
                    gcs_path = f"projects/{video.project.id}/videos/{video.uuid}/video.mp4"
                elif video.created_by:
                    gcs_path = f"users/{video.created_by.id}/videos/{video.uuid}/video.mp4"
                else:
                    gcs_path = f"standalone/videos/{video.uuid}/video.mp4"
                
                try:
                    # Descargar video desde URL y subir a GCS
                    gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                    
                    # Preparar metadata
                    metadata = {
                        'video_url_original': video_url,
                        'task_id': video.external_id,
                        'raw_response': status_data.get('raw_response', {}),
                    }
                    
                    video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                    logger.info(f"Video Kling {video.id} completado: {gcs_full_path}")
                except Exception as e:
                    logger.error(f"Error al descargar/subir video de Kling {video.id}: {e}")
                    video.mark_as_error(f"Error al procesar video: {str(e)}")
            else:
                logger.warning(f"Video Kling {video.id} completado pero sin URL de video")
                video.mark_as_error("Video completado pero sin URL disponible")
        
        elif api_status in ['failed', 'error']:
            error_msg = status_data.get('error', 'Video generation failed')
            video.mark_as_error(error_msg)
            logger.error(f"Video Kling {video.id} falló: {error_msg}")
        
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
    """Servicio para endpoints de API externa con caché robusto"""
    
    # Duración del caché en segundos (1 hora)
    CACHE_TTL = 3600
    # Duración del caché obsoleto (stale) en segundos (24 horas)
    STALE_CACHE_TTL = 86400
    
    def __init__(self):
        self.heygen_client = None
    
    def _get_heygen_client(self) -> HeyGenClient:
        """Lazy initialization de HeyGen client"""
        if not self.heygen_client:
            if not settings.HEYGEN_API_KEY:
                raise ValidationException('HEYGEN_API_KEY no está configurada')
            self.heygen_client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        return self.heygen_client
    
    def _get_stale_cache(self, cache_key: str):
        """Obtiene datos obsoletos del caché (stale cache)"""
        try:
            from django.core.cache import cache
            stale_key = f"{cache_key}_stale"
            return cache.get(stale_key)
        except Exception as e:
            logger.debug(f"Error al obtener stale cache (continuando sin caché): {e}")
            return None
    
    def _set_stale_cache(self, cache_key: str, data: List[Dict]):
        """Guarda datos en el caché obsoleto (stale cache)"""
        try:
            from django.core.cache import cache
            stale_key = f"{cache_key}_stale"
            cache.set(stale_key, data, self.STALE_CACHE_TTL)
        except Exception as e:
            logger.debug(f"Error al guardar stale cache (continuando sin caché): {e}")
    
    def list_avatars(self, use_cache: bool = True) -> List[Dict]:
        """
        Lista avatares disponibles de HeyGen con caché robusto (stale-while-revalidate)
        
        Args:
            use_cache: Si True, intenta usar caché. Si False, fuerza petición a la API.
        
        Returns:
            Lista de avatares
            
        Raises:
            ServiceException: Si falla la petición después de todos los reintentos y no hay caché obsoleto
        """
        from django.core.cache import cache
        
        cache_key = 'heygen_avatars'
        
        # Intentar obtener del caché fresco si está habilitado
        if use_cache:
            try:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    logger.debug("Usando avatares desde caché fresco")
                    return cached_data
            except Exception as e:
                # Si hay error con el caché, continuar sin caché
                logger.debug(f"Error al obtener del caché (continuando sin caché): {e}")
        
        # Intentar obtener datos obsoletos como fallback antes de hacer la petición
        stale_data = self._get_stale_cache(cache_key)
        
        try:
            client = self._get_heygen_client()
            avatars = client.list_avatars()
            
            # Guardar en caché fresco y obsoleto
            try:
                cache.set(cache_key, avatars, self.CACHE_TTL)
                self._set_stale_cache(cache_key, avatars)
                logger.debug(f"Avatares guardados en caché (fresco: {self.CACHE_TTL}s, obsoleto: {self.STALE_CACHE_TTL}s)")
            except Exception as cache_error:
                logger.debug(f"Error al guardar en caché (continuando sin caché): {cache_error}")
            
            return avatars
        except Exception as e:
            logger.error(f"Error al listar avatares después de reintentos: {e}")
            
            # Si hay datos obsoletos disponibles, usarlos como fallback
            if stale_data is not None:
                logger.warning("⚠️ Usando avatares en caché obsoleto como fallback (API no disponible)")
                return stale_data
            
            # Si no hay caché obsoleto, intentar obtener del caché fresco (por si acaso)
            try:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    logger.warning("⚠️ Usando avatares en caché fresco como último recurso")
                    return cached_data
            except Exception:
                pass  # Ignorar errores de caché
            
            # No hay datos disponibles en ningún caché
            logger.error("❌ No hay datos de avatares disponibles (ni API ni caché)")
            raise ServiceException(str(e))
    
    def list_voices(self, use_cache: bool = True) -> List[Dict]:
        """
        Lista voces disponibles de HeyGen con caché robusto (stale-while-revalidate)
        
        Args:
            use_cache: Si True, intenta usar caché. Si False, fuerza petición a la API.
        
        Returns:
            Lista de voces
            
        Raises:
            ServiceException: Si falla la petición después de todos los reintentos y no hay caché obsoleto
        """
        from django.core.cache import cache
        
        cache_key = 'heygen_voices'
        
        # Intentar obtener del caché fresco si está habilitado
        if use_cache:
            try:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    logger.debug("Usando voces desde caché fresco")
                    return cached_data
            except Exception as e:
                logger.debug(f"Error al obtener del caché (continuando sin caché): {e}")
        
        # Intentar obtener datos obsoletos como fallback antes de hacer la petición
        stale_data = self._get_stale_cache(cache_key)
        
        try:
            client = self._get_heygen_client()
            voices = client.list_voices()
            
            # Guardar en caché fresco y obsoleto
            try:
                cache.set(cache_key, voices, self.CACHE_TTL)
                self._set_stale_cache(cache_key, voices)
                logger.debug(f"Voces guardadas en caché (fresco: {self.CACHE_TTL}s, obsoleto: {self.STALE_CACHE_TTL}s)")
            except Exception as cache_error:
                logger.debug(f"Error al guardar en caché (continuando sin caché): {cache_error}")
            
            return voices
        except Exception as e:
            logger.error(f"Error al listar voces después de reintentos: {e}")
            
            # Si hay datos obsoletos disponibles, usarlos como fallback
            if stale_data is not None:
                logger.warning("⚠️ Usando voces en caché obsoleto como fallback (API no disponible)")
                return stale_data
            
            # Si no hay caché obsoleto, intentar obtener del caché fresco (por si acaso)
            try:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    logger.warning("⚠️ Usando voces en caché fresco como último recurso")
                    return cached_data
            except Exception:
                pass  # Ignorar errores de caché
            
            # No hay datos disponibles en ningún caché
            logger.error("❌ No hay datos de voces disponibles (ni API ni caché)")
            raise ServiceException(str(e))
    
    def list_image_assets(self, use_cache: bool = True) -> List[Dict]:
        """
        Lista imágenes disponibles en HeyGen con caché robusto (stale-while-revalidate)
        
        Args:
            use_cache: Si True, intenta usar caché. Si False, fuerza petición a la API.
        
        Returns:
            Lista de image assets
            
        Raises:
            ServiceException: Si falla la petición después de todos los reintentos y no hay caché obsoleto
        """
        from django.core.cache import cache
        
        cache_key = 'heygen_image_assets'
        
        # Intentar obtener del caché fresco si está habilitado
        if use_cache:
            try:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    logger.debug("Usando image assets desde caché fresco")
                    return cached_data
            except Exception as e:
                logger.debug(f"Error al obtener del caché (continuando sin caché): {e}")
        
        # Intentar obtener datos obsoletos como fallback antes de hacer la petición
        stale_data = self._get_stale_cache(cache_key)
        
        try:
            client = self._get_heygen_client()
            image_assets = client.list_image_assets()
            
            # Guardar en caché fresco y obsoleto
            try:
                cache.set(cache_key, image_assets, self.CACHE_TTL)
                self._set_stale_cache(cache_key, image_assets)
                logger.debug(f"Image assets guardados en caché (fresco: {self.CACHE_TTL}s, obsoleto: {self.STALE_CACHE_TTL}s)")
            except Exception as cache_error:
                logger.debug(f"Error al guardar en caché (continuando sin caché): {cache_error}")
            
            return image_assets
        except Exception as e:
            logger.error(f"Error al listar image assets después de reintentos: {e}")
            
            # Si hay datos obsoletos disponibles, usarlos como fallback
            if stale_data is not None:
                logger.warning("⚠️ Usando image assets en caché obsoleto como fallback (API no disponible)")
                return stale_data
            
            # Si no hay caché obsoleto, intentar obtener del caché fresco (por si acaso)
            try:
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    logger.warning("⚠️ Usando image assets en caché fresco como último recurso")
                    return cached_data
            except Exception:
                pass  # Ignorar errores de caché
            
            # No hay datos disponibles en ningún caché
            logger.error("❌ No hay datos de image assets disponibles (ni API ni caché)")
            raise ServiceException(str(e))


# ====================
# IMAGE SERVICE
# ====================

class ImageService:
    """Servicio principal para manejar imágenes generadas por IA"""
    
    def __init__(self):
        self.gemini_client = None
        self.higgsfield_client = None
        self.seedream_client = None
    
    # ----------------
    # CLIENT GETTERS
    # ----------------
    
    def _get_gemini_client(self, model_name: Optional[str] = None) -> GeminiImageClient:
        """
        Lazy initialization de Gemini Image client.
        """
        model_to_use = model_name or "gemini-2.5-flash-image"
        
        if self.gemini_client and self.gemini_client.model == model_to_use:
            return self.gemini_client
            
        if not settings.GEMINI_API_KEY:
            raise ValidationException('GEMINI_API_KEY no está configurada')
            
        client = GeminiImageClient(api_key=settings.GEMINI_API_KEY, model_name=model_to_use)
        
        if model_name is None or model_to_use == "gemini-2.5-flash-image":
            self.gemini_client = client
            
        return client
    
    def _get_higgsfield_client(self):
        """Lazy initialization de Higgsfield client."""
        if not self.higgsfield_client:
            from .ai_services.higgsfield import HiggsfieldClient
            if not settings.HIGGSFIELD_API_KEY_ID or not settings.HIGGSFIELD_API_KEY:
                raise ValidationException('HIGGSFIELD_API_KEY_ID y HIGGSFIELD_API_KEY deben estar configuradas')
            self.higgsfield_client = HiggsfieldClient(
                api_key_id=settings.HIGGSFIELD_API_KEY_ID,
                api_key_secret=settings.HIGGSFIELD_API_KEY
            )
        return self.higgsfield_client

    def _get_seedream_client(self, model_name: Optional[str] = None) -> SeaDreamImageClient:
        """Inicialización perezosa del cliente Seedream."""
        model_to_use = model_name or "seedream-default-model"

        if self.seedream_client and self.seedream_client.model == model_to_use:
            return self.seedream_client

        if not settings.SEEDREAM_API_KEY:
            raise ValidationException('SEEDREAM_API_KEY no está configurada')
            
        client = SeaDreamImageClient(api_key=settings.SEEDREAM_API_KEY, model_name=model_to_use)
        
        if model_name is None or model_to_use == "seedream-default-model":
            self.seedream_client = client
        
        return client
    
    # ----------------
    # CREAR IMAGEN (se mantiene el original)
    # ----------------
    
    def create_image(
        self,
        title: str,
        image_type: str,
        prompt: str,
        config: Dict,
        created_by: User,
        project: Project = None
    ) -> Image:
        """
        Crea una nueva imagen (sin generarla)
        """
        image = Image.objects.create(
            project=project,
            title=title,
            type=image_type,
            prompt=prompt,
            config=config,
            created_by=created_by
        )
        
        logger.info(f"Imagen creada: {image.id} - {image.title} ({image.type})")
        return image
    
    # ----------------
    # SUBIR IMÁGENES DE ENTRADA (se mantienen los originales)
    # ----------------
    
    def upload_input_image(
        self,
        image_file: UploadedFile,
        project: Project
    ) -> Dict[str, str]:
        """Sube imagen de entrada para image-to-image"""
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
        """Sube múltiples imágenes de entrada para composición"""
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
    # GENERAR IMAGEN (Router)
    # ----------------
    
    def generate_image(self, image: Image, skip_status_check: bool = False) -> str:
        """
        Genera una imagen usando el servicio apropiado según model_id
        """
        # Validar estado (solo si no se omite)
        if not skip_status_check and image.status in ['processing', 'completed']:
            raise ValidationException(f'La imagen ya está en estado: {image.get_status_display()}')
        
        # Obtener model_id del config
        model_id = image.config.get('model_id')
        
        # Determinar qué servicio usar según model_id
        from core.ai_services.model_config import get_model_capabilities
        capabilities = get_model_capabilities(model_id) if model_id else None
        service = capabilities.get('service') if capabilities else None
        
        # Validar créditos ANTES de generar
        if image.created_by:
            from core.services.credits import CreditService
            
            # Calcular costo según el servicio
            if service == 'higgsfield':
                estimated_cost = CreditService.estimate_image_cost(model_id=model_id)
            else:
                estimated_cost = CreditService.estimate_image_cost()
            
            if not CreditService.has_enough_credits(image.created_by, estimated_cost):
                raise InsufficientCreditsException(
                    f"No tienes suficientes créditos. Necesitas aproximadamente {estimated_cost} créditos."
                )
            
            try:
                CreditService.check_rate_limit(image.created_by, estimated_cost)
            except RateLimitExceededException as e:
                raise ValidationException(str(e))
        
        # Marcar como procesando
        image.mark_as_processing()
        
        try:
            # Aplicar template de prompt
            final_prompt = apply_prompt_template(
                image.prompt,
                image.config.get('prompt_template_id')
            )
            
            # Obtener configuración
            aspect_ratio = image.config.get('aspect_ratio', '1:1')
            
            # --- Enrutamiento ---
            if service == 'higgsfield':
                result = self._generate_higgsfield_image(image, model_id, aspect_ratio, final_prompt)
                
            elif service == 'seedream':
                # Delegamos a la función específica de SeaDream
                result = self._generate_seedream_image(image, model_id, aspect_ratio, final_prompt)
            
            else:
                # Por defecto, usar Gemini
                result = self._generate_gemini_image(image, model_id, aspect_ratio, final_prompt)
                
            # Subir imagen generada a GCS
            gcs_path = self._save_generated_image(
                image_data=result['image_data'],
                project=image.project,
                image_uuid=str(image.uuid)
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

    # ----------------
    # GENERACIÓN ASÍNCRONA (AÑADIDO)
    # ----------------

    def generate_image_async(self, image: Image, metadata: Dict = None) -> 'GenerationTask':
        """
        Encola la generación de una imagen usando el sistema de colas
        """
        from core.services.queue import QueueService
        
        # Validar estado
        if image.status in ['processing', 'completed']:
            raise ValidationException(f'La imagen ya está en estado: {image.get_status_display()}')
        
        # Validar créditos ANTES de encolar
        if image.created_by:
            from core.services.credits import CreditService
            
            model_id = image.config.get('model_id')
            from core.ai_services.model_config import get_model_capabilities
            capabilities = get_model_capabilities(model_id) if model_id else None
            service = capabilities.get('service') if capabilities else None
            
            estimated_cost = CreditService.estimate_image_cost(model_id=model_id) if service == 'higgsfield' else CreditService.estimate_image_cost()
            
            # Solo verificar créditos si el costo es > 0 (algunos modelos son gratis)
            if estimated_cost > 0:
                if not CreditService.has_enough_credits(image.created_by, estimated_cost):
                    raise InsufficientCreditsException(f"Créditos insuficientes. Necesitas aproximadamente {estimated_cost} créditos.")
                
                try:
                    CreditService.check_rate_limit(image.created_by, estimated_cost)
                except RateLimitExceededException as e:
                    raise ValidationException(str(e))
        
        # Preparar metadata
        task_metadata = metadata or {}
        task_metadata.update({
            'prompt': image.prompt,
            'image_type': image.type,
            'model_id': image.config.get('model_id'),
            'title': image.title,
            'item_id': image.id,
        })
        
        # Encolar tarea
        task = QueueService.enqueue_generation(
            item=image,
            user=image.created_by,
            task_type='image',
            metadata=task_metadata
        )
        
        # Marcar imagen como pending
        image.status = 'pending'
        image.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Imagen {image.id} encolada. Task UUID: {task.uuid}")
        return task

    # ----------------
    # DELEGATED GENERATION METHODS
    # ----------------
    
    def _generate_gemini_image(self, image: Image, model_id: str, aspect_ratio: str, final_prompt: str) -> dict:
        """Genera imagen usando el cliente Gemini."""
        client = self._get_gemini_client(model_name=model_id)
        response_modalities = image.config.get('response_modalities')

        if image.type == 'text_to_image':
            return client.generate_image_from_text(
                prompt=final_prompt,
                aspect_ratio=aspect_ratio,
                response_modalities=response_modalities,
            )

        elif image.type == 'image_to_image':
            input_gcs_path = image.config.get('input_image_gcs_path')
            if not input_gcs_path: raise ValidationException('Imagen de entrada es requerida.')
            
            input_image_data = self._download_image_from_gcs(input_gcs_path)
            
            return client.generate_image_from_image(
                prompt=final_prompt,
                input_image_data=input_image_data,
                aspect_ratio=aspect_ratio,
                response_modalities=response_modalities,
            )

        elif image.type == 'multi_image':
            input_images_config = image.config.get('input_images', [])
            if not input_images_config: raise ValidationException('Imágenes de entrada son requeridas.')

            input_images_data = [self._download_image_from_gcs(img_config['gcs_path']) for img_config in input_images_config]
            
            return client.generate_image_from_multiple_images(
                prompt=final_prompt,
                input_images_data=input_images_data,
                aspect_ratio=aspect_ratio,
                response_modalities=response_modalities,
            )
        
        raise ValidationException(f'Tipo de imagen {image.type} no soportado por Gemini.')


    def _generate_seedream_image(self, image: Image, model_id: str, aspect_ratio: str, final_prompt: str) -> dict:
        """Genera imagen usando el cliente SeaDream (Síncrono)."""
        client = self._get_seedream_client(model_name=model_id)
        
        try:
            if image.type == 'text_to_image':
                return client.generate_image_from_text(
                    prompt=final_prompt,
                    aspect_ratio=aspect_ratio,
                )
            
            elif image.type == 'image_to_image':
                input_gcs_path = image.config.get('input_image_gcs_path')
                if not input_gcs_path: raise ValidationException('Imagen de entrada es requerida.')
                
                # Descargar imagen desde GCS a bytes
                input_image_data = self._download_image_from_gcs(input_gcs_path)
                
                return client.generate_image_from_image(
                    prompt=final_prompt,
                    input_image_data=input_image_data,
                    aspect_ratio=aspect_ratio,
                )
            
            elif image.type == 'multi_image':
                input_images_config = image.config.get('input_images', [])
                if not input_images_config: raise ValidationException('Imágenes de entrada son requeridas.')

                # Descargar imágenes desde GCS a lista de bytes
                input_images_data = [self._download_image_from_gcs(img_config['gcs_path']) for img_config in input_images_config]
                
                return client.generate_image_from_multiple_images(
                    prompt=final_prompt,
                    input_images_data=input_images_data,
                    aspect_ratio=aspect_ratio,
                )
                
            raise ValidationException(f'Tipo de imagen {image.type} no soportado por SeaDream.')

        except Exception as e:
            logger.error(f"[Seedream] Error al generar imagen: {e}")
            raise ImageGenerationException(f"Error de la API de SeaDream: {str(e)}")


    def _generate_higgsfield_image(self, image: Image, model_id: str, aspect_ratio: str, final_prompt: str) -> dict:
        """
        Genera una imagen usando Higgsfield API (Maneja el polling síncrono).
        """
        import requests
        import time
        
        client = self._get_higgsfield_client()
        
        logger.info(f"Generando imagen con Higgsfield: {model_id}")
        
        try:
            response = client.generate_video(
                model_id=model_id,
                prompt=final_prompt,
                image_url=None,  # T-t-I
                aspect_ratio=aspect_ratio,
                resolution=None,
                duration=None
            )
        except Exception as e:
            raise ImageGenerationException(f"Error al iniciar generación con Higgsfield: {str(e)}")

        request_id = response.get('request_id')
        if not request_id:
            raise ImageGenerationException("No se recibió request_id de Higgsfield")
        
        image.external_id = request_id
        image.save(update_fields=['external_id'])

        # Polling síncrono
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(5)
            attempt += 1
            
            status_data = client.get_request_status(request_id)
            status = status_data.get('status')
            
            if status == 'completed':
                image_url = None
                if 'images' in status_data.get('raw_response', {}) and status_data['raw_response']['images']:
                    image_url = status_data['raw_response']['images'][0].get('url')
                
                if not image_url:
                    raise ImageGenerationException("No se encontró URL de imagen en la respuesta de Higgsfield")
                
                # Descargar imagen desde la URL
                try:
                    img_response = requests.get(image_url, timeout=30)
                    img_response.raise_for_status()
                    image_data = img_response.content
                except Exception as e:
                    raise StorageException(f"Error al descargar imagen generada desde Higgsfield: {str(e)}")

                # Determinar dimensiones (usando auxiliar)
                width, height = self._get_dimensions_from_aspect_ratio(aspect_ratio)
                
                return {
                    'image_data': image_data,
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'text_response': final_prompt
                }
            
            elif status in ['failed', 'error', 'cancelled', 'nsfw']:
                error_msg = status_data.get('error', 'Error desconocido')
                raise ImageGenerationException(f"Error al generar imagen con Higgsfield: {error_msg}")
        
        raise ImageGenerationException("Timeout esperando respuesta de Higgsfield")

    # ----------------
    # AUXILIAR METHODS
    # ----------------
    
    def _get_dimensions_from_aspect_ratio(self, aspect_ratio: str) -> tuple:
        """Obtiene dimensiones aproximadas según aspect_ratio"""
        ratios = {
            '1:1': (1024, 1024),
            '16:9': (1344, 768),
            '9:16': (768, 1344),
            '4:3': (1184, 864),
            '3:4': (864, 1184),
        }
        return ratios.get(aspect_ratio, (1024, 1024))
    
    def _download_image_from_gcs(self, gcs_path: str) -> bytes:
        """Descarga imagen desde GCS y retorna bytes"""
        try:
            # Necesario para el cliente Gemini y SeaDream (Image-to-Image)
            blob_name = gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
            blob = gcs_storage.bucket.blob(blob_name)
            image_data = blob.download_as_bytes()
            logger.info(f"Imagen descargada desde GCS: {len(image_data)} bytes")
            return image_data
        except Exception as e:
            logger.error(f"Error al descargar imagen desde GCS: {e}")
            raise StorageException(f"Error al descargar imagen: {str(e)}")
    
    def _save_generated_image(
        self,
        image_data: bytes,
        project: Optional[Project] = None,
        image_uuid: Optional[str] = None
    ) -> str:
        """Guarda imagen generada en GCS"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if project:
                gcs_destination = f"projects/{project.id}/images/{image_uuid}/{timestamp}_generated.png"
            else:
                gcs_destination = f"images/{image_uuid}/{timestamp}_generated.png"
            
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
# AUDIO SERVICE
# ====================

class AudioService:
    """Servicio para manejar audios generados por ElevenLabs TTS"""
    
    @staticmethod
    def _get_elevenlabs_client():
        """Obtiene cliente de ElevenLabs"""
        from .ai_services import ElevenLabsClient
        from django.conf import settings
        
        api_key = settings.ELEVENLABS_API_KEY
        if not api_key:
            raise ServiceException('ELEVENLABS_API_KEY no configurada')
        
        return ElevenLabsClient(api_key=api_key)
    
    @staticmethod
    def _get_default_voice_settings():
        """Obtiene configuración de voz por defecto desde settings"""
        from django.conf import settings
        from decouple import config
        
        return {
            'stability': float(config('ELEVENLABS_DEFAULT_STABILITY', default=0.5)),
            'similarity_boost': float(config('ELEVENLABS_DEFAULT_SIMILARITY_BOOST', default=0.75)),
            'style': float(config('ELEVENLABS_DEFAULT_STYLE', default=0.0)),
            'speed': float(config('ELEVENLABS_DEFAULT_SPEED', default=1.0)),
        }
    
    @staticmethod
    def create_audio(title: str, text: str, voice_id: str, created_by, voice_name: str = None, 
                     voice_settings: Dict = None, project = None):
        """
        Crea un nuevo audio (sin generarlo aún)
        
        Args:
            title: Título del audio
            text: Texto a convertir a voz
            voice_id: ID de la voz en ElevenLabs
            created_by: Usuario que crea el audio
            voice_name: Nombre de la voz (opcional)
            voice_settings: Configuración de voz (opcional, usa defaults si no se proporciona)
            project: Proyecto al que pertenece (opcional)
            
        Returns:
            Objeto Audio creado
        """
        from .models import Audio
        from django.conf import settings
        from decouple import config
        
        # Usar configuración por defecto si no se proporciona
        if voice_settings is None:
            voice_settings = AudioService._get_default_voice_settings()
        
        # Crear audio
        audio = Audio.objects.create(
            project=project,
            title=title,
            text=text,
            voice_id=voice_id,
            voice_name=voice_name or config('ELEVENLABS_DEFAULT_VOICE_NAME', default='Unknown'),
            model_id=config('ELEVENLABS_DEFAULT_MODEL', default='eleven_turbo_v2_5'),
            language_code=config('ELEVENLABS_DEFAULT_LANGUAGE', default='es'),
            voice_settings=voice_settings,
            status='pending',
            created_by=created_by
        )
        
        logger.info(f"Audio creado: {audio.id} - {audio.title}")
        return audio
    
    @staticmethod
    def generate_audio(audio, with_timestamps: bool = False):
        """
        Genera el audio usando ElevenLabs API
        
        Args:
            audio: Objeto Audio a generar (tipo 'tts' o 'music')
            with_timestamps: Si True, genera con timestamps carácter por carácter (solo TTS)
            
        Returns:
            GCS path del audio generado
            
        Raises:
            ServiceException: Si falla la generación
        """
        from .storage.gcs import gcs_storage
        import tempfile
        import os
        import base64
        
        # Validar estado
        if audio.status in ['processing', 'completed']:
            raise ValidationException(f'El audio ya está en estado: {audio.get_status_display()}')
        
        # Verificar tipo de audio
        audio_type = getattr(audio, 'type', 'tts') or 'tts'
        
        if audio_type == 'music':
            # La generación de música requiere implementación separada
            raise ValidationException('La generación de música aún no está implementada en este flujo')
        
        # Para TTS, validar campos requeridos
        if not audio.text:
            raise ValidationException('El texto es requerido para audio TTS')
        if not audio.voice_id:
            raise ValidationException('La voz es requerida para audio TTS')
        
        # Marcar como procesando
        audio.mark_as_processing()
        
        try:
            client = AudioService._get_elevenlabs_client()
            
            # Obtener configuración de voz
            voice_settings = audio.voice_settings or AudioService._get_default_voice_settings()
            
            logger.info(f"Generando audio TTS para: {audio.title}")
            logger.info(f"  Voz: {audio.voice_name} ({audio.voice_id})")
            logger.info(f"  Modelo: {audio.model_id}")
            text_preview = audio.text[:100] if audio.text else ''
            logger.info(f"  Texto: {text_preview}{'...' if len(audio.text or '') > 100 else ''}")
            
            # Procesar texto con tags de voz si los tiene
            from .services.voice_script_processor import VoiceScriptProcessor
            processor = VoiceScriptProcessor()
            processed_result = processor.process_script(audio.text, use_ssml=False)
            processed_text = processed_result['processed_text']
            
            # Log si se procesaron tags
            if processed_result['has_emotions'] or processed_result['has_pauses']:
                logger.info(f"Procesados tags de voz: {len(processed_result['metadata']['emotions_found'])} emociones, "
                          f"{len(processed_result['metadata']['pauses_found'])} pausas")
            
            if with_timestamps:
                # Generar con timestamps
                result = client.text_to_speech_with_timestamps(
                    text=processed_text,
                    voice_id=audio.voice_id,
                    model_id=audio.model_id,
                    language_code=audio.language_code,
                    **voice_settings
                )
                
                # El audio viene en base64
                audio_base64 = result.get('audio_base64')
                audio_bytes = base64.b64decode(audio_base64)
                alignment = result.get('alignment', {})
                
            else:
                # Generar sin timestamps
                audio_bytes = client.text_to_speech(
                    text=processed_text,
                    voice_id=audio.voice_id,
                    model_id=audio.model_id,
                    language_code=audio.language_code,
                    **voice_settings
                )
                alignment = {}
            
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Subir a GCS
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_title = audio.title.replace(' ', '_').replace('/', '_')
                if audio.project:
                    gcs_path = f"projects/{audio.project.id}/audios/{audio.uuid}/{timestamp}_{safe_title}.mp3"
                else:
                    gcs_path = f"audios/{audio.uuid}/{timestamp}_{safe_title}.mp3"
                
                with open(tmp_path, 'rb') as f:
                    gcs_full_path = gcs_storage.upload_from_bytes(
                        file_content=f.read(),
                        destination_path=gcs_path,
                        content_type='audio/mpeg'
                    )
                
                # Obtener duración del audio usando ffprobe
                duration = AudioService._get_audio_duration(tmp_path)
                file_size = os.path.getsize(tmp_path)
                
                # Marcar como completado
                audio.mark_as_completed(
                    gcs_path=gcs_full_path,
                    duration=duration,
                    metadata={
                        'model_id': audio.model_id,
                        'language_code': audio.language_code,
                        'voice_settings': voice_settings,
                        'file_size': file_size,
                    },
                    alignment=alignment if alignment else None
                )
                
                audio.file_size = file_size
                audio.save(update_fields=['file_size'])
                
                logger.info(f"✓ Audio generado: {gcs_full_path}")
                logger.info(f"  Duración: {duration}s, Tamaño: {file_size} bytes")
                
                return gcs_full_path
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error al generar audio: {e}")
            audio.mark_as_error(str(e))
            raise ServiceException(f"Error al generar audio: {str(e)}")
    
    @staticmethod
    def generate_audio_async(audio, metadata: Dict = None, with_timestamps: bool = False) -> 'GenerationTask':
        """
        Encola la generación de un audio usando el sistema de colas
        
        Args:
            audio: Objeto Audio a generar
            metadata: Metadata adicional (prompt, parámetros, etc.)
            with_timestamps: Si True, genera con timestamps carácter por carácter
        
        Returns:
            GenerationTask creada
        
        Raises:
            ValidationException: Si hay error de validación
            ValueError: Si se alcanza el límite de tareas simultáneas
        """
        from core.services.queue import QueueService
        
        # Validar estado
        if audio.status in ['processing', 'completed']:
            raise ValidationException(f'El audio ya está en estado: {audio.get_status_display()}')
        
        # Preparar metadata según tipo de audio
        task_metadata = metadata or {}
        audio_type = getattr(audio, 'type', 'tts') or 'tts'
        
        task_metadata.update({
            'title': audio.title,
            'audio_type': audio_type,
            'with_timestamps': with_timestamps,
        })
        
        # Campos específicos según tipo
        if audio_type == 'tts':
            task_metadata.update({
                'text': audio.text,
                'voice_id': audio.voice_id,
                'voice_name': audio.voice_name,
                'model_id': audio.model_id,
            })
        elif audio_type == 'music':
            task_metadata.update({
                'prompt': audio.prompt,
                'duration_ms': audio.duration_ms,
            })
        
        # Encolar tarea
        task = QueueService.enqueue_generation(
            item=audio,
            user=audio.created_by,
            task_type='audio',
            metadata=task_metadata
        )
        
        # Marcar audio como pending
        audio.status = 'pending'
        audio.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Audio {audio.id} encolado. Task UUID: {task.uuid}")
        return task
    
    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        """
        Obtiene la duración de un archivo de audio usando ffprobe
        
        Args:
            audio_path: Path al archivo de audio
            
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
                    audio_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logger.warning(f"No se pudo obtener duración del audio: {result.stderr}")
                return 0.0
                
        except FileNotFoundError:
            logger.warning("ffprobe no está instalado. No se puede obtener la duración del audio.")
            return 0.0
        except Exception as e:
            logger.warning(f"Error al obtener duración del audio: {e}")
            return 0.0
    
    @staticmethod
    def list_voices():
        """
        Lista todas las voces disponibles en ElevenLabs
        
        Returns:
            Lista de voces
        """
        try:
            client = AudioService._get_elevenlabs_client()
            voices = client.list_voices()
            return voices
        except Exception as e:
            logger.error(f"Error al listar voces: {e}")
            raise ServiceException(f"Error al listar voces: {str(e)}")
    
    def get_audio_with_signed_url(self, audio) -> Dict:
        """
        Obtiene un audio con su URL firmada para reproducción
        
        Args:
            audio: Objeto Audio
            
        Returns:
            Dict con audio y signed_url
        """
        result = {
            'audio': audio,
            'signed_url': None
        }
        
        if audio.status == 'completed' and audio.gcs_path:
            try:
                from .storage.gcs import gcs_storage
                result['signed_url'] = gcs_storage.get_signed_url(
                    audio.gcs_path,
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada de audio: {e}")
        
        return result


# ====================
# SCENE SERVICE
# ====================

class SceneService:
    @staticmethod
    def _get_project_id_for_path(scene):
        """Obtiene el ID del proyecto para rutas de almacenamiento"""
        if scene.project:
            return f"projects/{scene.project.id}"
        elif scene.script and scene.script.project:
            return f"projects/{scene.script.project.id}"
        elif scene.script and scene.script.created_by:
            return f"users/{scene.script.created_by.id}"
        else:
            return "standalone"
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
        
        # Obtener configuración heredada del script
        video_orientation = getattr(script, 'video_orientation', '16:9')
        video_type = getattr(script, 'video_type', 'general')
        
        # Obtener preferencias de modelos del script
        from .services.model_defaults import ModelDefaults
        model_preferences = ModelDefaults.apply_defaults(script)
        
        logger.info(f"Creando escenas con orientación heredada: {video_orientation}, tipo: {video_type}")
        logger.info(f"Preferencias de modelos aplicadas: {model_preferences}")
        
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
                # Convertir heygen antiguo a heygen_v2
                if ai_service == 'heygen':
                    ai_service = 'heygen_v2'
                if ai_service not in ['gemini_veo', 'sora', 'heygen_v2', 'heygen_avatar_iv', 'vuela_ai']:
                    ai_service = 'gemini_veo'  # Default
                
                # Aplicar preferencia de servicio HeyGen si está configurada
                if ai_service in ['heygen_v2', 'heygen_avatar_iv']:
                    heygen_preference = model_preferences.get('heygen')
                    if heygen_preference:
                        ai_service = heygen_preference
                        logger.info(f"Escena {scene_data.get('id')}: Usando servicio HeyGen {heygen_preference} (preferencia del script)")
                
                # Validar servicio según tipo de video
                if video_type == 'ultra':
                    # Modo Ultra: Solo Veo3 y Sora2
                    if ai_service in ['heygen_v2', 'heygen_avatar_iv']:
                        logger.info(f"Video tipo Ultra: Cambiando {ai_service} a gemini_veo")
                        ai_service = 'gemini_veo'
                elif video_type == 'avatar':
                    # Con Avatares: Principalmente HeyGen, pero permitir otros
                    if ai_service not in ['heygen_v2', 'heygen_avatar_iv', 'gemini_veo', 'sora']:
                        ai_service = 'heygen_v2'  # Default para avatares
                
                # Obtener continuity_context si existe
                continuity_context = scene_data.get('continuity_context', {})
                
                # Preparar config básica según el servicio CON ORIENTACIÓN HEREDADA
                ai_config = {}
                if ai_service in ['heygen_v2', 'heygen_avatar_iv'] and scene_data.get('avatar') == 'si':
                    # Config por defecto para HeyGen V2 o Avatar IV
                    # Prioridad: 1) model_preferences del script, 2) settings, 3) vacío
                    from django.conf import settings
                    
                    # Obtener avatar y voz por defecto desde model_preferences
                    default_avatar_id = model_preferences.get('default_heygen_avatar_id') or getattr(settings, 'HEYGEN_DEFAULT_AVATAR_ID', '')
                    default_voice_id = model_preferences.get('default_heygen_voice_id') or getattr(settings, 'HEYGEN_DEFAULT_VOICE_ID', '')
                    
                    ai_config = {
                        'avatar_id': default_avatar_id,
                        'voice_id': default_voice_id,
                        'video_orientation': video_orientation,  # Heredado del script
                        'voice_speed': 1.0,
                        'voice_pitch': 50,
                        'voice_emotion': 'Excited'
                    }
                    
                    # Log si se usan valores por defecto del script
                    if default_avatar_id:
                        logger.info(f"Escena {scene_data.get('id')}: Usando avatar por defecto del script: {default_avatar_id}")
                    if default_voice_id:
                        logger.info(f"Escena {scene_data.get('id')}: Usando voz por defecto del script: {default_voice_id}")
                    
                    # Para Avatar IV, agregar campo específico para image_key (si hay preview)
                    if ai_service == 'heygen_avatar_iv':
                        ai_config['image_key'] = ''  # Se llenará si hay imagen de preview
                elif ai_service == 'gemini_veo':
                    # Convertir duration_sec a int (viene como string desde n8n)
                    duration = int(scene_data.get('duration_sec', 8))
                    # Aplicar preferencia de modelo Veo si está configurada
                    veo_model = model_preferences.get('gemini_veo', 'veo-3.1-generate-preview')
                    ai_config = {
                        'veo_model': veo_model,
                        'duration': min(8, duration),  # Max 8s para Gemini Veo
                        'aspect_ratio': video_orientation,  # Heredado del script
                        'sample_count': 1,
                        'enhance_prompt': True,
                        'person_generation': 'allow_adult',
                        'compression_quality': 'optimized'
                    }
                    logger.info(f"Escena {scene_data.get('id')}: Usando modelo Veo {veo_model} (preferencia del script)")
                elif ai_service == 'sora':
                    # Mapear orientación a tamaño para Sora
                    if video_orientation == '9:16':
                        sora_size = '720x1280'  # Vertical
                    else:
                        sora_size = '1280x720'  # Horizontal (default)
                    
                    # Convertir duration_sec a int (viene como string desde n8n)
                    duration = int(scene_data.get('duration_sec', 8))
                    # Aplicar preferencia de modelo Sora si está configurada
                    sora_model = model_preferences.get('sora', 'sora-2')
                    ai_config = {
                        'sora_model': sora_model,
                        'duration': min(12, duration),  # Max 12s para Sora
                        'size': sora_size  # Heredado del script
                    }
                    logger.info(f"Escena {scene_data.get('id')}: Usando modelo Sora {sora_model} (preferencia del script)")
                elif ai_service == 'vuela_ai':
                    # Configuración para Vuela.ai
                    ai_config = {
                        'mode': 'single_voice',  # Default mode
                        'aspect_ratio': video_orientation,  # Heredado del script
                        'animation_type': 'moving_image',  # Efecto Ken Burns
                        'quality_tier': 'premium',
                        'voice_id': '',  # El usuario lo configurará
                        'voice_style': 'expressive',
                        'voice_speed': 'standard',
                        'media_type': 'ai_image',
                        'style': 'photorealistic',
                        'images_per_minute': 8,
                        'add_subtitles': False,
                        'add_background_music': False
                    }
                
                # Procesar visual_prompt: puede venir como objeto o string
                visual_prompt_data = scene_data.get('visual_prompt', '')
                visual_prompt_str = ''
                
                if isinstance(visual_prompt_data, dict):
                    # Si es objeto, construir prompt completo combinando todos los campos
                    prompt_parts = []
                    if visual_prompt_data.get('description'):
                        prompt_parts.append(visual_prompt_data['description'])
                    if visual_prompt_data.get('camera'):
                        prompt_parts.append(f"Camera: {visual_prompt_data['camera']}")
                    if visual_prompt_data.get('lighting'):
                        prompt_parts.append(f"Lighting: {visual_prompt_data['lighting']}")
                    if visual_prompt_data.get('composition'):
                        prompt_parts.append(f"Composition: {visual_prompt_data['composition']}")
                    if visual_prompt_data.get('atmosphere'):
                        prompt_parts.append(f"Atmosphere: {visual_prompt_data['atmosphere']}")
                    if visual_prompt_data.get('style_reference'):
                        prompt_parts.append(f"Style: {visual_prompt_data['style_reference']}")
                    if visual_prompt_data.get('continuity_notes'):
                        prompt_parts.append(f"Continuity: {visual_prompt_data['continuity_notes']}")
                    
                    visual_prompt_str = '. '.join(prompt_parts)
                    # Guardar también el objeto completo en ai_config para referencia
                    ai_config['visual_prompt_object'] = visual_prompt_data
                elif isinstance(visual_prompt_data, str):
                    visual_prompt_str = visual_prompt_data
                
                # Crear escena
                scene = Scene.objects.create(
                    script=script,
                    project=script.project,
                    scene_id=scene_data.get('id'),
                    summary=scene_data.get('summary', ''),
                    script_text=scene_data.get('script_text', ''),
                    visual_prompt=visual_prompt_str,
                    duration_sec=int(scene_data.get('duration_sec', 0)),  # Convertir a int
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
                    continuity_context=continuity_context,  # Guardar contexto de continuidad
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
        # Construir prompt optimizado para el preview
        prompt = f"""
Create a cinematic preview image for a video scene.

Scene summary: {scene.summary}
Scene content: {scene.script_text[:200]}...

Visual elements to include: {', '.join(scene.broll[:3]) if scene.broll else 'general scene'}

Style: Photorealistic, professional video production, cinematic lighting, high quality, 16:9 aspect ratio.
This is a preview thumbnail for a video, make it visually engaging and representative of the content.
"""
        return self.generate_preview_image_with_prompt(scene, prompt)
    
    def generate_preview_image_with_prompt(self, scene, custom_prompt: str):
        """
        Genera imagen preview para una escena usando un prompt personalizado
        
        Args:
            scene: Objeto Scene
            custom_prompt: Prompt personalizado para generar la imagen
            
        Returns:
            GCS path de la imagen generada
            
        Raises:
            ImageGenerationException: Si falla la generación
            InsufficientCreditsException: Si no hay suficientes créditos
            RateLimitExceededException: Si se excede el límite mensual
        """
        from .models import Scene
        
        # Validar créditos ANTES de generar
        if scene.script.created_by:
            from core.services.credits import CreditService, InsufficientCreditsException, RateLimitExceededException
            
            estimated_cost = CreditService.estimate_image_cost()
            
            if not CreditService.has_enough_credits(scene.script.created_by, estimated_cost):
                raise InsufficientCreditsException(
                    f"No tienes suficientes créditos. Necesitas aproximadamente {estimated_cost} créditos. "
                    f"Créditos disponibles: {CreditService.get_or_create_user_credits(scene.script.created_by).credits}"
                )
            
            try:
                CreditService.check_rate_limit(scene.script.created_by, estimated_cost)
            except RateLimitExceededException as e:
                raise ValidationException(str(e))
        
        try:
            # Marcar como generando
            scene.mark_preview_as_generating()
            
            # Usar ImageService con Gemini
            client = GeminiImageClient(api_key=settings.GEMINI_API_KEY)
            
            result = client.generate_image_from_text(
                prompt=custom_prompt,
                aspect_ratio='16:9',
                response_modalities=['Image']
            )
            
            # Subir a GCS
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_prefix = SceneService._get_project_id_for_path(scene).replace('projects/', '').replace('users/', 'user_').replace('standalone', 'standalone')
            gcs_destination = f"scene_previews/{project_prefix}/scene_{scene.id}/{timestamp}_preview.png"
            
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
            InsufficientCreditsException: Si no hay suficientes créditos
            RateLimitExceededException: Si se excede el límite mensual
        """
        # Validar créditos ANTES de generar
        if scene.script.created_by:
            from core.services.credits import CreditService, InsufficientCreditsException, RateLimitExceededException
            
            estimated_cost = CreditService.calculate_scene_video_cost(scene)
            
            if estimated_cost > 0:
                if not CreditService.has_enough_credits(scene.script.created_by, estimated_cost):
                    raise InsufficientCreditsException(
                        f"No tienes suficientes créditos. Necesitas aproximadamente {estimated_cost} créditos "
                        f"({scene.duration_sec}s de {scene.ai_service}). "
                        f"Créditos disponibles: {CreditService.get_or_create_user_credits(scene.script.created_by).credits}"
                    )
                
                try:
                    CreditService.check_rate_limit(scene.script.created_by, estimated_cost)
                except RateLimitExceededException as e:
                    raise ValidationException(str(e))
        
        try:
            # Validar que la configuración esté completa
            if not scene.ai_service:
                raise ValidationException("La escena no tiene servicio de IA configurado")
            
            # Convertir valores antiguos de heygen a heygen_v2 (backward compatibility)
            if scene.ai_service == 'heygen':
                logger.info(f"Convirtiendo ai_service 'heygen' a 'heygen_v2' para escena {scene.scene_id}")
                scene.ai_service = 'heygen_v2'
                scene.save(update_fields=['ai_service'])
            
            # Marcar como procesando
            scene.mark_video_as_processing()
            
            # Generar según el servicio
            if scene.ai_service in ['heygen_v2', 'heygen_avatar_iv']:
                external_id = self._generate_heygen_scene_video(scene)
            elif scene.ai_service == 'gemini_veo':
                external_id = self._generate_veo_scene_video(scene)
            elif scene.ai_service == 'sora':
                external_id = self._generate_sora_scene_video(scene)
            elif scene.ai_service == 'vuela_ai':
                external_id = self._generate_vuela_ai_scene_video(scene)
            elif scene.ai_service in ['higgsfield_dop_standard', 'higgsfield_dop_preview', 'higgsfield_seedance_v1_pro', 'higgsfield_kling_v2_1_pro']:
                external_id = self._generate_higgsfield_scene_video(scene)
            elif scene.ai_service.startswith('kling_'):
                external_id = self._generate_kling_scene_video(scene)
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
        """Genera video de escena con HeyGen (V2 o Avatar IV)"""
        from .ai_services.heygen import HeyGenClient
        from .storage.gcs import gcs_storage
        from .services.voice_validator import VoiceValidator
        
        if not settings.HEYGEN_API_KEY:
            raise ValidationException('HEYGEN_API_KEY no está configurada')
        
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        
        # Avatar IV: requiere image_key y voice_id
        if scene.ai_service == 'heygen_avatar_iv':
            voice_id = scene.ai_config.get('voice_id')
            if not voice_id:
                raise ValidationException('Voice ID es requerido para HeyGen Avatar IV')
            
            # Validar voz antes de generar
            script_default_voice_id = scene.script.default_voice_id if scene.script else None
            valid_voice = VoiceValidator.get_valid_voice(
                voice_id=voice_id,
                script_default_voice_id=script_default_voice_id,
                force_refresh=False
            )
            
            # Usar voz válida (puede ser la original o un fallback)
            actual_voice_id = valid_voice['voice_id']
            actual_voice_name = valid_voice['voice_name']
            
            # Guardar información de fallback si se usó
            if valid_voice['used_fallback']:
                if not scene.metadata:
                    scene.metadata = {}
                scene.metadata['voice_fallback'] = {
                    'original_voice_id': voice_id,
                    'used_voice_id': actual_voice_id,
                    'used_voice_name': actual_voice_name,
                    'fallback_reason': valid_voice['fallback_reason']
                }
                scene.save(update_fields=['metadata', 'updated_at'])
                logger.warning(
                    f"⚠ Escena {scene.scene_id}: Voz {voice_id} no válida. "
                    f"Usando fallback: {actual_voice_name} ({actual_voice_id})"
                )
            else:
                logger.info(f"✓ Escena {scene.scene_id}: Voz {voice_id} validada correctamente")
            
            # Obtener o subir imagen de preview como asset de HeyGen
            image_key = scene.ai_config.get('image_key')
            
            if not image_key and scene.preview_image_gcs_path:
                # Descargar la imagen de preview desde GCS
                logger.info(f"Descargando imagen de preview para Avatar IV desde GCS: {scene.preview_image_gcs_path}")
                image_data = gcs_storage.download_as_bytes(scene.preview_image_gcs_path)
                
                # Subir a HeyGen y obtener image_key
                logger.info(f"Subiendo imagen a HeyGen como asset para Avatar IV")
                image_key = client.upload_asset_from_bytes(image_data, content_type='image/jpeg')
                
                # Guardar image_key en la configuración para futuras regeneraciones
                scene.ai_config['image_key'] = image_key
                scene.save(update_fields=['ai_config', 'updated_at'])
                
                logger.info(f"✓ Imagen subida a HeyGen. Image Key: {image_key}")
            
            if not image_key:
                raise ValidationException('Se requiere una imagen de preview para HeyGen Avatar IV. Por favor, añade una imagen en el paso de configuración.')
            
            # Generar video Avatar IV
            video_orientation = scene.ai_config.get('video_orientation', '16:9')
            # Convertir formato de orientación a portrait/landscape
            orientation_map = {'9:16': 'portrait', '16:9': 'landscape'}
            orientation_str = orientation_map.get(video_orientation, 'landscape')
            
            response = client.generate_avatar_iv_video(
                script=scene.script_text,
                image_key=image_key,
                voice_id=actual_voice_id,  # Usar voz validada
                title=f"{scene.scene_id} - {scene.script.title}",
                video_orientation=orientation_str,
                fit=scene.ai_config.get('fit', 'cover')
            )
            
            return response.get('data', {}).get('video_id')
        
        # Avatar V2: requiere avatar_id y voice_id
        else:  # heygen_v2
            avatar_id = scene.ai_config.get('avatar_id')
            voice_id = scene.ai_config.get('voice_id')
            
            if not avatar_id or not voice_id:
                raise ValidationException('Avatar ID y Voice ID son requeridos para HeyGen Avatar V2')
            
            # Validar avatar antes de generar
            avatar_validation = VoiceValidator.validate_avatar(avatar_id, force_refresh=False)
            if not avatar_validation['valid']:
                if avatar_validation.get('fallback_avatar_id'):
                    avatar_id = avatar_validation['fallback_avatar_id']
                    if not scene.metadata:
                        scene.metadata = {}
                    scene.metadata['avatar_fallback'] = {
                        'original_avatar_id': scene.ai_config.get('avatar_id'),
                        'used_avatar_id': avatar_id,
                        'used_avatar_name': avatar_validation.get('fallback_avatar_name', 'Avatar por defecto')
                    }
                    scene.save(update_fields=['metadata', 'updated_at'])
                    logger.warning(
                        f"⚠ Escena {scene.scene_id}: Avatar {scene.ai_config.get('avatar_id')} no válido. "
                        f"Usando fallback: {avatar_id}"
                    )
                else:
                    raise ValidationException(
                        f"Avatar {avatar_id} no válido y no se encontró fallback disponible"
                    )
            
            # Validar voz antes de generar
            script_default_voice_id = scene.script.default_voice_id if scene.script else None
            valid_voice = VoiceValidator.get_valid_voice(
                voice_id=voice_id,
                script_default_voice_id=script_default_voice_id,
                force_refresh=False
            )
            
            # Usar voz válida (puede ser la original o un fallback)
            actual_voice_id = valid_voice['voice_id']
            actual_voice_name = valid_voice['voice_name']
            
            # Guardar información de fallback si se usó
            if valid_voice['used_fallback']:
                if not scene.metadata:
                    scene.metadata = {}
                if 'voice_fallback' not in scene.metadata:
                    scene.metadata['voice_fallback'] = {}
                scene.metadata['voice_fallback'].update({
                    'original_voice_id': voice_id,
                    'used_voice_id': actual_voice_id,
                    'used_voice_name': actual_voice_name,
                    'fallback_reason': valid_voice['fallback_reason']
                })
                scene.save(update_fields=['metadata', 'updated_at'])
                logger.warning(
                    f"⚠ Escena {scene.scene_id}: Voz {voice_id} no válida. "
                    f"Usando fallback: {actual_voice_name} ({actual_voice_id})"
                )
            else:
                logger.info(f"✓ Escena {scene.scene_id}: Voz {voice_id} validada correctamente")
            
            response = client.generate_video(
                script=scene.script_text,
                title=f"{scene.scene_id} - {scene.script.title}",
                avatar_id=avatar_id,  # Usar avatar validado
                voice_id=actual_voice_id,  # Usar voz validada
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
        project_prefix = SceneService._get_project_id_for_path(scene)
        storage_uri = f"gs://{settings.GCS_BUCKET_NAME}/{project_prefix}/scenes/{scene.id}/"
        
        # Usar visual_prompt si existe, sino fallback a script_text + broll
        if scene.visual_prompt:
            prompt = scene.visual_prompt
        else:
            # Fallback: usar script_text + broll
            prompt = scene.script_text
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
        from .ai_services.sora import SoraClient, SORA_DURATIONS
        
        if not settings.OPENAI_API_KEY:
            raise ValidationException('OPENAI_API_KEY no está configurada')
        
        client = SoraClient(api_key=settings.OPENAI_API_KEY)
        
        # Usar visual_prompt si existe, sino fallback a script_text + broll
        if scene.visual_prompt:
            prompt = scene.visual_prompt
        else:
            # Fallback: usar script_text + broll
            prompt = scene.script_text
            if scene.broll:
                prompt += f"\n\nVisual elements: {', '.join(scene.broll[:3])}"
        
        model = scene.ai_config.get('sora_model', 'sora-2')
        duration = int(scene.ai_config.get('duration', 8))
        size = scene.ai_config.get('size', '1280x720')
        
        # Validar y ajustar duración para Sora (solo 4, 8, 12 segundos)
        if duration not in SORA_DURATIONS:
            # Encontrar la duración más cercana
            closest_duration = min(SORA_DURATIONS, key=lambda x: abs(x - duration))
            logger.warning(f"Duración {duration}s no válida para Sora. Ajustando a {closest_duration}s")
            duration = closest_duration
            
            # Actualizar la configuración de la escena
            scene.ai_config['duration'] = duration
            scene.save(update_fields=['ai_config', 'updated_at'])
        
        response = client.generate_video(
            prompt=prompt,
            model=model,
            seconds=duration,
            size=size
        )
        
        return response.get('video_id')
    
    def _generate_vuela_ai_scene_video(self, scene):
        """Genera video de escena con Vuela.ai"""
        from .ai_services.vuela_ai import VuelaAIClient, VuelaMode, VuelaAnimationType, VuelaQualityTier, VuelaMediaType, VuelaVoiceStyle
        
        if not settings.VUELA_AI_API_KEY:
            raise ValidationException('VUELA_AI_API_KEY no está configurada')
        
        client = VuelaAIClient(api_key=settings.VUELA_AI_API_KEY)
        
        # Obtener configuración de la escena
        config = scene.ai_config
        voice_id = config.get('voice_id', '')
        
        if not voice_id:
            raise ValidationException('Debe configurar un voice_id para Vuela.ai')
        
        # Construir script (usar script_text para narración)
        # Vuela.ai usa script_text para la voz/narración del video
        video_script = scene.script_text.replace('\n', '\\n')
        
        # Mapear valores de configuración
        mode_str = config.get('mode', 'single_voice')
        mode = VuelaMode(mode_str)
        
        aspect_ratio = config.get('aspect_ratio', '16:9')
        
        animation_type_str = config.get('animation_type', 'moving_image')
        animation_type = VuelaAnimationType(animation_type_str)
        
        quality_tier_str = config.get('quality_tier', 'premium')
        quality_tier = VuelaQualityTier(quality_tier_str)
        
        voice_style_str = config.get('voice_style', 'expressive')
        voice_style = VuelaVoiceStyle(voice_style_str)
        
        voice_speed = config.get('voice_speed', 'standard')
        
        media_type_str = config.get('media_type', 'ai_image')
        media_type = VuelaMediaType(media_type_str)
        
        style = config.get('style', 'photorealistic')
        images_per_minute = int(config.get('images_per_minute', 8))
        
        add_subtitles = config.get('add_subtitles', False)
        add_background_music = config.get('add_background_music', False)
        
        # Generar video
        response = client.generate_video(
            mode=mode,
            video_script=video_script,
            aspect_ratio=aspect_ratio,
            animation_type=animation_type,
            quality_tier=quality_tier,
            language='es',  # TODO: Heredar del script
            country='ES',
            voice_id=voice_id,
            voice_style=voice_style,
            voice_speed=voice_speed,
            media_type=media_type,
            style=style,
            images_per_minute=images_per_minute,
            add_subtitles=add_subtitles,
            add_background_music=add_background_music
        )
        
        # Vuela.ai devuelve video_id en la respuesta
        video_id = response.get('video_id')
        if not video_id:
            raise ValidationException('Vuela.ai no devolvió video_id')
        
        return video_id
    
    def _generate_higgsfield_scene_video(self, scene):
        """Genera video de escena con Higgsfield"""
        from .ai_services.higgsfield import HiggsfieldClient
        
        if not settings.HIGGSFIELD_API_KEY_ID or not settings.HIGGSFIELD_API_KEY:
            raise ValidationException('HIGGSFIELD_API_KEY_ID y HIGGSFIELD_API_KEY deben estar configuradas')
        
        client = HiggsfieldClient(
            api_key_id=settings.HIGGSFIELD_API_KEY_ID,
            api_key_secret=settings.HIGGSFIELD_API_KEY
        )
        
        # Mapear ai_service a model_id
        model_map = {
            'higgsfield_dop_standard': 'higgsfield-ai/dop/standard',
            'higgsfield_dop_preview': 'higgsfield-ai/dop/preview',
            'higgsfield_seedance_v1_pro': 'bytedance/seedance/v1/pro/image-to-video',
            'higgsfield_kling_v2_1_pro': 'kling-video/v2.1/pro/image-to-video',
        }
        
        model_id = model_map.get(scene.ai_service)
        if not model_id:
            raise ValidationException(f'Servicio de IA Higgsfield no válido: {scene.ai_service}')
        
        # Usar visual_prompt si existe, sino fallback a script_text + broll
        if scene.visual_prompt:
            prompt = scene.visual_prompt
        else:
            prompt = scene.script_text
            if scene.broll:
                prompt += f"\n\nVisual elements: {', '.join(scene.broll[:3])}"
        
        # Obtener configuración
        config = scene.ai_config
        
        # Obtener URL de imagen (requerido para image-to-video)
        image_url = None
        if scene.preview_image_gcs_path:
            # Obtener URL firmada de GCS
            image_url = gcs_storage.get_signed_url(scene.preview_image_gcs_path, expiration=3600)
            logger.info(f"Usando imagen de preview desde GCS: {scene.preview_image_gcs_path}")
        elif config.get('image_url'):
            image_url = config['image_url']
        
        if not image_url:
            raise ValidationException(f'El modelo {model_id} requiere una imagen de entrada (preview_image_gcs_path o image_url en ai_config)')
        
        # Preparar parámetros opcionales (solo si están en config)
        kwargs = {}
        if 'aspect_ratio' in config:
            kwargs['aspect_ratio'] = config['aspect_ratio']
        if 'resolution' in config:
            kwargs['resolution'] = config['resolution']
        if 'duration' in config:
            kwargs['duration'] = config['duration']
        elif scene.duration_sec:
            kwargs['duration'] = scene.duration_sec
        
        # Generar video
        response = client.generate_video(
            model_id=model_id,
            prompt=prompt,
            image_url=image_url,
            **kwargs
        )
        
        return response.get('request_id')
    
    def _generate_kling_scene_video(self, scene):
        """Genera video de escena con Kling"""
        from .ai_services.kling import KlingClient
        
        if not settings.KLING_ACCESS_KEY or not settings.KLING_SECRET_KEY:
            raise ValidationException('KLING_ACCESS_KEY y KLING_SECRET_KEY deben estar configuradas')
        
        client = KlingClient(
            access_key=settings.KLING_ACCESS_KEY,
            secret_key=settings.KLING_SECRET_KEY
        )
        
        # Mapear ai_service a model_name
        model_map = {
            'kling_v1': 'kling-v1',
            'kling_v1_5': 'kling-v1-5',
            'kling_v1_6': 'kling-v1-6',
            'kling_v2_master': 'kling-v2-master',
            'kling_v2_1': 'kling-v2-1',
            'kling_v2_5_turbo': 'kling-v2-5-turbo',
        }
        
        model_name = model_map.get(scene.ai_service)
        if not model_name:
            raise ValidationException(f'Servicio de IA Kling no válido: {scene.ai_service}')
        
        # Usar visual_prompt si existe, sino fallback a script_text + broll
        if scene.visual_prompt:
            prompt = scene.visual_prompt
        else:
            prompt = scene.script_text
            if scene.broll:
                prompt += f"\n\nVisual elements: {', '.join(scene.broll[:3])}"
        
        # Obtener configuración
        config = scene.ai_config
        mode = config.get('mode', 'std')  # 'std' o 'pro'
        duration = int(config.get('duration', scene.duration_sec or 5))
        aspect_ratio = config.get('aspect_ratio', '16:9')
        
        # Validar duración (Kling solo soporta 5 o 10 segundos)
        if duration not in [5, 10]:
            logger.warning(f"Duración {duration}s ajustada a 5s (Kling solo soporta 5 o 10 segundos)")
            duration = 5
        
        # Obtener URL de imagen si existe (para image-to-video)
        image_url = None
        if scene.preview_image_gcs_path:
            # Obtener URL firmada de GCS
            image_url = gcs_storage.get_signed_url(scene.preview_image_gcs_path, expiration=3600)
            logger.info(f"Usando imagen de preview desde GCS: {scene.preview_image_gcs_path}")
        elif config.get('image_url'):
            image_url = config['image_url']
        
        # Generar video
        response = client.generate_video(
            model_name=model_name,
            prompt=prompt,
            image_url=image_url,
            mode=mode,
            duration=duration,
            aspect_ratio=aspect_ratio
        )
        
        return response.get('task_id')
    
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
        
        # Si ya está en estado final, verificar si se cobraron créditos
        if scene.video_status in ['completed', 'error']:
            # Verificar y cobrar créditos si no se han cobrado aún
            if scene.video_status == 'completed' and scene.script.created_by:
                try:
                    from core.services.credits import CreditService
                    # Verificar si ya se cobraron créditos
                    if not scene.metadata.get('credits_charged'):
                        logger.info(f"Escena {scene.scene_id} completada pero sin créditos cobrados. Cobrando ahora...")
                        CreditService.deduct_credits_for_scene_video(scene.script.created_by, scene)
                except Exception as e:
                    logger.error(f"Error al verificar/cobrar créditos para escena {scene.scene_id}: {e}")
            
            return {
                'status': scene.video_status,
                'message': 'Video ya procesado'
            }
        
        # Convertir valores antiguos de heygen a heygen_v2 (backward compatibility)
        if scene.ai_service == 'heygen':
            logger.info(f"Convirtiendo ai_service 'heygen' a 'heygen_v2' para escena {scene.scene_id}")
            scene.ai_service = 'heygen_v2'
            scene.save(update_fields=['ai_service'])
        
        try:
            if scene.ai_service in ['heygen_v2', 'heygen_avatar_iv']:
                return self._check_heygen_scene_status(scene)
            elif scene.ai_service == 'gemini_veo':
                return self._check_veo_scene_status(scene)
            elif scene.ai_service == 'sora':
                return self._check_sora_scene_status(scene)
            elif scene.ai_service == 'vuela_ai':
                return self._check_vuela_ai_scene_status(scene)
            else:
                raise ValidationException(f"Servicio de IA no soportado para check status: {scene.ai_service}")
        except Exception as e:
            logger.error(f"Error al consultar estado de escena: {e}")
            raise ServiceException(str(e))
    
    def _check_heygen_scene_status(self, scene):
        """Consulta estado en HeyGen con manejo mejorado de errores"""
        from .ai_services.heygen import HeyGenClient
        from .services.voice_validator import VoiceValidator
        
        client = HeyGenClient(api_key=settings.HEYGEN_API_KEY)
        status_data = client.get_video_status(scene.external_id)
        
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            video_url = status_data.get('video_url')
            if video_url:
                project_prefix = SceneService._get_project_id_for_path(scene)
                gcs_path = f"{project_prefix}/scenes/{scene.id}/video.mp4"
                gcs_full_path = gcs_storage.upload_from_url(video_url, gcs_path)
                
                metadata = {
                    'duration': status_data.get('duration'),
                    'video_url_original': video_url,
                    'thumbnail': status_data.get('thumbnail'),
                }
                
                scene.mark_video_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                logger.info(f"✓ Video de escena {scene.scene_id} completado: {gcs_full_path}")
                
                # Auto-generar audio si está habilitado
                self._auto_generate_audio_if_needed(scene)
        
        elif api_status == 'failed':
            error_obj = status_data.get('error', {})
            error_msg = 'Video generation failed'
            
            # Detectar errores específicos de voz/avatar no encontrados
            if isinstance(error_obj, dict):
                error_detail = error_obj.get('detail', '')
                error_code = error_obj.get('code', '')
                
                # Detectar error de voz no encontrada
                if 'VOICE' in error_detail and 'not found' in error_detail.lower():
                    logger.error(f"❌ Escena {scene.scene_id}: Voz no encontrada en HeyGen")
                    logger.error(f"   Error: {error_detail}")
                    
                    # Intentar regenerar con voz válida
                    try:
                        voice_id = scene.ai_config.get('voice_id')
                        if voice_id:
                            script_default_voice_id = scene.script.default_voice_id if scene.script else None
                            valid_voice = VoiceValidator.get_valid_voice(
                                voice_id=voice_id,
                                script_default_voice_id=script_default_voice_id,
                                force_refresh=True  # Forzar refresh después de error
                            )
                            
                            if valid_voice['used_fallback']:
                                # Actualizar configuración con voz válida
                                scene.ai_config['voice_id'] = valid_voice['voice_id']
                                if not scene.metadata:
                                    scene.metadata = {}
                                scene.metadata['voice_fallback'] = {
                                    'original_voice_id': voice_id,
                                    'used_voice_id': valid_voice['voice_id'],
                                    'used_voice_name': valid_voice['voice_name'],
                                    'fallback_reason': 'Error en generación - voz no encontrada',
                                    'regenerated': True
                                }
                                scene.save(update_fields=['ai_config', 'metadata', 'updated_at'])
                                
                                logger.info(
                                    f"🔄 Regenerando escena {scene.scene_id} con voz válida: "
                                    f"{valid_voice['voice_name']} ({valid_voice['voice_id']})"
                                )
                                
                                # Regenerar video con voz válida
                                scene.mark_video_as_pending()  # Resetear estado
                                external_id = self._generate_heygen_scene_video(scene)
                                scene.external_id = external_id
                                scene.save(update_fields=['external_id', 'updated_at'])
                                
                                return status_data  # Retornar sin marcar error, se regeneró
                            
                    except Exception as e:
                        logger.error(f"Error al intentar regenerar con voz válida: {e}")
                    
                    error_msg = f"Voz no encontrada: {error_detail}"
                
                # Detectar error de avatar no encontrado
                elif 'AVATAR' in error_detail and 'not found' in error_detail.lower():
                    logger.error(f"❌ Escena {scene.scene_id}: Avatar no encontrado en HeyGen")
                    logger.error(f"   Error: {error_detail}")
                    error_msg = f"Avatar no encontrado: {error_detail}"
                
                else:
                    error_msg = error_obj.get('message', str(error_obj))
            else:
                error_msg = str(error_obj) if error_obj else 'Video generation failed'
            
            scene.mark_video_as_error(error_msg)
            logger.error(f"❌ Escena {scene.scene_id} falló: {error_msg}")
        
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
                project_prefix = SceneService._get_project_id_for_path(scene)
                gcs_path = f"{project_prefix}/scenes/{scene.id}/video.mp4"
                
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
                
                # Auto-generar audio si está habilitado
                self._auto_generate_audio_if_needed(scene)
        
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
                    project_prefix = SceneService._get_project_id_for_path(scene)
                    gcs_path = f"{project_prefix}/scenes/{scene.id}/video.mp4"
                    
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
                    
                    # Auto-generar audio si está habilitado
                    self._auto_generate_audio_if_needed(scene)
                else:
                    scene.mark_video_as_error("No se pudo descargar el video desde Sora")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif api_status == 'failed':
            error_obj = status_data.get('error')
            
            # El error puede ser un dict con 'code' y 'message' o un string
            if isinstance(error_obj, dict):
                error_code = error_obj.get('code', 'unknown_error')
                error_message = error_obj.get('message', 'Video generation failed')
                error_msg = f"[{error_code}] {error_message}"
                logger.error(f"❌ Escena Sora {scene.id} falló: {error_msg}")
                logger.error(f"   Error completo: {error_obj}")
            else:
                error_msg = str(error_obj) if error_obj else 'Video generation failed'
                logger.error(f"❌ Escena Sora {scene.id} falló: {error_msg}")
            
            scene.mark_video_as_error(error_msg)
        
        return status_data
    
    def _download_freepik_video(self, scene, resource_id: str):
        """Descarga video de Freepik y lo sube a GCS"""
        from .ai_services.freepik import FreepikClient
        from .storage.gcs import gcs_storage
        
        if not settings.FREEPIK_API_KEY:
            raise ValidationException('FREEPIK_API_KEY no está configurada')
        
        client = FreepikClient(api_key=settings.FREEPIK_API_KEY)
        
        try:
            # Obtener URL de descarga
            download_url = client.get_download_url(resource_id, file_type='original')
            
            if not download_url:
                raise ValidationException('No se pudo obtener URL de descarga de Freepik')
            
            # Preparar ruta en GCS
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_prefix = SceneService._get_project_id_for_path(scene)
            gcs_path = f"{project_prefix}/scenes/{scene.id}/freepik_video_{timestamp}.mp4"
            
            # Descargar y subir a GCS
            logger.info(f"Descargando video de Freepik: {download_url}")
            gcs_full_path = gcs_storage.upload_from_url(download_url, gcs_path)
            
            # Actualizar escena usando mark_video_as_completed para cobrar créditos
            metadata = {
                'freepik_resource_id': resource_id,
                'image_source': 'freepik_stock',
            }
            scene.freepik_resource_id = resource_id
            scene.image_source = 'freepik_stock'
            scene.mark_video_as_completed(gcs_path=gcs_full_path, metadata=metadata)
            
            logger.info(f"✓ Video de Freepik subido para escena {scene.id}: {gcs_full_path}")
            return gcs_full_path
            
        except Exception as e:
            error_msg = f"Error al descargar video de Freepik: {str(e)}"
            logger.error(error_msg)
            scene.mark_video_as_error(error_msg)
            raise
    
    def _check_vuela_ai_scene_status(self, scene):
        """Consulta estado en Vuela.ai"""
        from .ai_services.vuela_ai import VuelaAIClient
        
        client = VuelaAIClient(api_key=settings.VUELA_AI_API_KEY)
        status_data = client.get_video_details(scene.external_id)
        
        # Vuela.ai devuelve: 'creating', 'completed', 'failed'
        api_status = status_data.get('status')
        
        if api_status == 'completed':
            # Descargar video desde Vuela.ai
            video_url = status_data.get('video_url')
            if not video_url:
                raise ValidationException('Vuela.ai no devolvió video_url')
            
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Descargar video
                logger.info(f"Descargando video de Vuela.ai: {video_url}")
                response = requests.get(video_url, timeout=300, stream=True)
                response.raise_for_status()
                
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Subir a GCS
                project_prefix = SceneService._get_project_id_for_path(scene)
                gcs_path = f"{project_prefix}/scenes/{scene.id}/video.mp4"
                
                with open(tmp_path, 'rb') as video_file:
                    gcs_full_path = gcs_storage.upload_from_bytes(
                        file_content=video_file.read(),
                        destination_path=gcs_path,
                        content_type='video/mp4'
                    )
                
                metadata = {
                    'mode': status_data.get('mode'),
                    'aspect_ratio': status_data.get('aspect_ratio'),
                    'animation_type': status_data.get('animation_type'),
                }
                
                scene.mark_video_as_completed(gcs_path=gcs_full_path, metadata=metadata)
                logger.info(f"✓ Video de escena {scene.scene_id} completado desde Vuela.ai: {gcs_full_path}")
                
                # Auto-generar audio si está habilitado
                self._auto_generate_audio_if_needed(scene)
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif api_status == 'failed':
            error_msg = status_data.get('error_message', 'Video generation failed')
            scene.mark_video_as_error(error_msg)
        
        return status_data
    
    def _auto_generate_audio_if_needed(self, scene):
        """
        Genera audio automáticamente si la escena lo necesita (Veo/Sora)
        y luego combina video+audio
        
        Args:
            scene: Scene que acaba de completar su video
        """
        try:
            # Verificar si debe generar audio
            if not scene.needs_audio():
                logger.info(f"Escena {scene.scene_id} no necesita audio (ai_service={scene.ai_service})")
                return
            
            # Verificar si el script tiene audio habilitado
            if not scene.script.enable_audio:
                logger.info(f"Audio deshabilitado para script {scene.script.id}")
                return
            
            # Obtener configuración de voz (priorizar voz de escena sobre voz por defecto)
            voice_id = scene.audio_voice_id or scene.script.default_voice_id
            voice_name = scene.audio_voice_name or scene.script.default_voice_name
            
            if not voice_id:
                logger.warning(f"No hay voice_id configurado para escena {scene.scene_id}, usando voz por defecto")
                from decouple import config
                voice_id = config('ELEVENLABS_DEFAULT_VOICE_ID', default='pFZP5JQG7iQjIQuC4Bku')
                voice_name = config('ELEVENLABS_DEFAULT_VOICE_NAME', default='Aria')
            
            logger.info(f"=== GENERANDO AUDIO AUTOMÁTICO PARA ESCENA {scene.scene_id} ===")
            logger.info(f"  Texto: {scene.script_text[:100]}...")
            logger.info(f"  Voz: {voice_name} ({voice_id})")
            
            # Generar audio
            self._generate_scene_audio(scene, voice_id, voice_name)
            
        except Exception as e:
            logger.error(f"Error al auto-generar audio para escena {scene.scene_id}: {e}")
            scene.mark_audio_as_error(str(e))
    
    def _generate_scene_audio(self, scene, voice_id: str, voice_name: str):
        """Genera audio para una escena usando ElevenLabs con validación y ajuste automático"""
        from .ai_services.elevenlabs import ElevenLabsClient
        from .storage.gcs import gcs_storage
        from .services.audio_duration_calculator import AudioDurationCalculator
        from decouple import config
        import tempfile
        import os
        
        scene.mark_audio_as_processing()
        
        try:
            # Obtener cliente
            client = ElevenLabsClient(api_key=settings.ELEVENLABS_API_KEY)
            
            # Configuración de voz inicial
            base_speed = float(config('ELEVENLABS_DEFAULT_SPEED', default=1.0))
            voice_settings = {
                'stability': float(config('ELEVENLABS_DEFAULT_STABILITY', default=0.5)),
                'similarity_boost': float(config('ELEVENLABS_DEFAULT_SIMILARITY_BOOST', default=0.75)),
                'style': float(config('ELEVENLABS_DEFAULT_STYLE', default=0.0)),
                'speed': base_speed,
            }
            
            # Obtener idioma del script o usar default
            language = scene.script.language if scene.script and scene.script.language else 'es'
            
            # Validar duración estimada antes de generar
            video_duration = scene.duration_sec
            validation = AudioDurationCalculator.validate_text_length(
                text=scene.script_text,
                duration_sec=video_duration,
                language=language,
                speed=base_speed
            )
            
            logger.info(
                f"Validación audio escena {scene.scene_id}: "
                f"estimado={validation['estimated_duration']:.2f}s, "
                f"target={video_duration}s, "
                f"diferencia={validation['difference_percent']:.1f}%"
            )
            
            # Si el texto es demasiado largo, ajustar velocidad
            speed_adjustment = None
            if validation['estimated_duration'] > video_duration:
                excess_percent = validation['difference_percent']
                
                if excess_percent <= 20:  # Máximo 20% de exceso
                    # Calcular factor de velocidad necesario
                    speed_factor = validation['estimated_duration'] / video_duration
                    # Limitar a máximo 1.2x (20% más rápido)
                    speed_factor = min(speed_factor, 1.2)
                    
                    # Ajustar velocidad en voice_settings
                    voice_settings['speed'] = base_speed * speed_factor
                    speed_adjustment = speed_factor
                    
                    logger.info(
                        f"Ajustando velocidad de audio: {base_speed}x → {voice_settings['speed']:.2f}x "
                        f"(factor: {speed_factor:.2f})"
                    )
                else:
                    # Texto demasiado largo (>20% de exceso)
                    logger.warning(
                        f"⚠ Audio excede video en {excess_percent:.1f}% "
                        f"({validation['estimated_duration']:.2f}s vs {video_duration}s). "
                        f"Se generará con velocidad ajustada pero puede requerir edición manual."
                    )
                    # Intentar ajuste máximo de velocidad
                    speed_factor = min(validation['estimated_duration'] / video_duration, 1.2)
                    voice_settings['speed'] = base_speed * speed_factor
                    speed_adjustment = speed_factor
            
            # Procesar texto con tags de voz si los tiene
            from .services.voice_script_processor import VoiceScriptProcessor
            processor = VoiceScriptProcessor()
            processed_result = processor.process_script(scene.script_text, use_ssml=False)
            processed_text = processed_result['processed_text']
            
            # Log si se procesaron tags
            if processed_result['has_emotions'] or processed_result['has_pauses']:
                logger.info(f"Procesados tags de voz en escena {scene.scene_id}: "
                          f"{len(processed_result['metadata']['emotions_found'])} emociones, "
                          f"{len(processed_result['metadata']['pauses_found'])} pausas")
            
            # Generar audio (con velocidad ajustada si es necesario)
            audio_bytes = client.text_to_speech(
                text=processed_text,
                voice_id=voice_id,
                model_id=config('ELEVENLABS_DEFAULT_MODEL', default='eleven_turbo_v2_5'),
                language_code=config('ELEVENLABS_DEFAULT_LANGUAGE', default='es'),
                **voice_settings
            )
            
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Obtener duración real del audio generado
                actual_duration = AudioService._get_audio_duration(tmp_path)
                
                # Verificar si aún excede después del ajuste
                if actual_duration > video_duration:
                    excess_percent = ((actual_duration - video_duration) / video_duration) * 100
                    logger.warning(
                        f"⚠ Audio generado aún excede video: {actual_duration:.2f}s vs {video_duration}s "
                        f"({excess_percent:.1f}% de exceso)"
                    )
                else:
                    logger.info(
                        f"✓ Audio ajustado correctamente: {actual_duration:.2f}s (target: {video_duration}s)"
                    )
                
                # Guardar información de ajuste en ai_config
                if speed_adjustment:
                    if not scene.ai_config:
                        scene.ai_config = {}
                    scene.ai_config['audio_speed_adjustment'] = speed_adjustment
                    scene.ai_config['audio_original_speed'] = base_speed
                    scene.ai_config['audio_estimated_duration'] = validation['estimated_duration']
                    scene.ai_config['audio_actual_duration'] = actual_duration
                    scene.save(update_fields=['ai_config', 'updated_at'])
                
                # Subir a GCS
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                project_prefix = SceneService._get_project_id_for_path(scene)
                gcs_path = f"{project_prefix}/scenes/{scene.id}/audio_{timestamp}.mp3"
                
                with open(tmp_path, 'rb') as f:
                    gcs_full_path = gcs_storage.upload_from_bytes(
                        file_content=f.read(),
                        destination_path=gcs_path,
                        content_type='audio/mpeg'
                    )
                
                # Marcar como completado (usar duración real)
                scene.mark_audio_as_completed(
                    gcs_path=gcs_full_path,
                    duration=actual_duration,
                    voice_id=voice_id,
                    voice_name=voice_name
                )
                
                logger.info(
                    f"✓ Audio generado para escena {scene.scene_id}: {gcs_full_path} "
                    f"(duración: {actual_duration:.2f}s, velocidad: {voice_settings['speed']:.2f}x)"
                )
                
                # Combinar video+audio automáticamente
                self._auto_combine_video_audio_if_ready(scene)
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error al generar audio para escena {scene.scene_id}: {e}")
            scene.mark_audio_as_error(str(e))
            raise
    
    def _auto_combine_video_audio_if_ready(self, scene):
        """
        Combina video+audio automáticamente si ambos están listos
        
        Args:
            scene: Scene a combinar
        """
        try:
            # Refrescar el objeto desde la base de datos para tener el estado más reciente
            scene.refresh_from_db()
            
            logger.info(f"=== VERIFICANDO COMBINACIÓN PARA ESCENA {scene.scene_id} ===")
            logger.info(f"  video_status: {scene.video_status}")
            logger.info(f"  audio_status: {scene.audio_status}")
            logger.info(f"  final_video_status: {scene.final_video_status}")
            logger.info(f"  ai_service: {scene.ai_service}")
            logger.info(f"  needs_audio(): {scene.needs_audio()}")
            logger.info(f"  needs_combination(): {scene.needs_combination()}")
            
            if not scene.needs_combination():
                logger.info(f"Escena {scene.scene_id} no necesita combinación aún")
                return
            
            logger.info(f"=== ✓ COMBINANDO VIDEO+AUDIO PARA ESCENA {scene.scene_id} ===")
            
            scene.mark_final_video_as_processing()
            
            # Combinar con FFmpeg
            # Obtener project_id de manera segura
            project_id = None
            if scene.project:
                project_id = scene.project.id
            elif scene.script and scene.script.project:
                project_id = scene.script.project.id
            
            final_gcs_path = self._combine_video_and_audio(
                scene.video_gcs_path,
                scene.audio_gcs_path,
                project_id,
                scene.id
            )
            
            scene.mark_final_video_as_completed(final_gcs_path)
            logger.info(f"✓ Video final combinado para escena {scene.scene_id}: {final_gcs_path}")
            
        except Exception as e:
            logger.error(f"Error al combinar video+audio para escena {scene.scene_id}: {e}")
            scene.mark_final_video_as_error(str(e))
    
    def _combine_video_and_audio(self, video_gcs_path: str, audio_gcs_path: str, project_id: int, scene_id: int) -> str:
        """
        Combina un video con un audio usando FFmpeg
        
        Args:
            video_gcs_path: Path GCS del video
            audio_gcs_path: Path GCS del audio
            project_id: ID del proyecto
            scene_id: ID de la escena
            
        Returns:
            GCS path del video combinado
        """
        import tempfile
        import subprocess
        import os
        from .storage.gcs import gcs_storage
        from datetime import datetime
        
        temp_dir = None
        video_path = None
        audio_path = None
        output_path = None
        
        try:
            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp(prefix='atenea_combine_audio_')
            
            # Descargar video
            video_blob = gcs_storage.bucket.blob(video_gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", ""))
            video_path = os.path.join(temp_dir, 'video.mp4')
            video_blob.download_to_filename(video_path)
            
            # Descargar audio
            audio_blob = gcs_storage.bucket.blob(audio_gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", ""))
            audio_path = os.path.join(temp_dir, 'audio.mp3')
            audio_blob.download_to_filename(audio_path)
            
            # Path de salida
            output_path = os.path.join(temp_dir, 'combined.mp4')
            
            # Detectar si el video tiene audio original
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            try:
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                has_original_audio = probe_result.stdout.strip() == 'audio'
                logger.info(f"Video original tiene audio: {has_original_audio}")
            except FileNotFoundError:
                logger.warning("ffprobe no está instalado. Asumiendo que el video no tiene audio.")
                has_original_audio = False
            except Exception as e:
                logger.warning(f"Error al verificar audio del video: {e}")
                has_original_audio = False
            
            # Obtener duraciones para decidir la estrategia
            video_duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            audio_duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            
            try:
                video_duration_result = subprocess.run(video_duration_cmd, capture_output=True, text=True)
                video_duration = float(video_duration_result.stdout.strip()) if video_duration_result.returncode == 0 else None
            except FileNotFoundError:
                logger.warning("ffprobe no está instalado. No se puede obtener duración del video.")
                video_duration = None
            except Exception as e:
                logger.warning(f"Error al obtener duración del video: {e}")
                video_duration = None
            
            try:
                audio_duration_result = subprocess.run(audio_duration_cmd, capture_output=True, text=True)
                audio_duration = float(audio_duration_result.stdout.strip()) if audio_duration_result.returncode == 0 else None
            except FileNotFoundError:
                logger.warning("ffprobe no está instalado. No se puede obtener duración del audio.")
                audio_duration = None
            except Exception as e:
                logger.warning(f"Error al obtener duración del audio: {e}")
                audio_duration = None
            
            logger.info(f"Duración video: {video_duration}s, Duración audio: {audio_duration}s")
            
            # Combinar con FFmpeg
            # Estrategia: ELIMINAR completamente el audio del video y REEMPLAZAR con ElevenLabs TTS
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_path,      # Input 0: video (puede tener audio o no)
                '-i', audio_path,      # Input 1: audio de ElevenLabs
                '-map', '0:v:0',       # Tomar SOLO el stream de video del input 0
                '-map', '1:a:0',       # Tomar el stream de audio del input 1 (ElevenLabs)
                '-c:v', 'copy',        # Copiar video sin re-encodear (mantener calidad)
                '-c:a', 'aac',         # Encodear audio a AAC
                '-b:a', '192k',        # Bitrate de audio 192kbps
                '-ar', '44100',        # Sample rate 44.1kHz
            ]
            
            # Solo usar -shortest si el audio es más largo que el video
            # Si el video es más largo, extender el audio con silencio para que coincida
            if video_duration and audio_duration:
                if audio_duration > video_duration:
                    # Audio más largo: cortar al video
                    ffmpeg_cmd.append('-shortest')
                    logger.info("Audio más largo que video: usando -shortest para cortar audio")
                elif video_duration > audio_duration:
                    # Video más largo: extender audio con silencio
                    pad_duration = video_duration - audio_duration
                    ffmpeg_cmd.extend(['-af', f'apad=pad_dur={pad_duration}'])
                    logger.info(f"Video más largo que audio: extendiendo audio con {pad_duration}s de silencio")
                # Si son iguales, no hacer nada especial
            
            ffmpeg_cmd.extend(['-y', output_path])
            
            logger.info(f"Ejecutando FFmpeg para REEMPLAZAR audio del video con ElevenLabs TTS")
            logger.info(f"Comando: {' '.join(ffmpeg_cmd)}")
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg stderr: {result.stderr}")
                raise ServiceException(f"FFmpeg falló: {result.stderr[:500]}")
            
            # Subir a GCS
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if project_id:
                gcs_destination = f"projects/{project_id}/scenes/{scene_id}/final_{timestamp}.mp4"
            else:
                # Si no hay proyecto, usar una ruta alternativa
                gcs_destination = f"standalone/scenes/{scene_id}/final_{timestamp}.mp4"
            
            with open(output_path, 'rb') as f:
                gcs_full_path = gcs_storage.upload_from_bytes(
                    file_content=f.read(),
                    destination_path=gcs_destination,
                    content_type='video/mp4'
                )
            
            return gcs_full_path
            
        finally:
            # Limpiar archivos temporales
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
    
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
            'video_url': None,
            'audio_url': None,
            'final_video_url': None
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
        
        # URL firmada del video original
        if scene.video_status == 'completed' and scene.video_gcs_path:
            try:
                result['video_url'] = gcs_storage.get_signed_url(
                    scene.video_gcs_path,
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada de video: {e}")
        
        # URL firmada del audio
        if scene.audio_status == 'completed' and scene.audio_gcs_path:
            try:
                result['audio_url'] = gcs_storage.get_signed_url(
                    scene.audio_gcs_path,
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada de audio: {e}")
        
        # URL firmada del video final (video+audio combinados)
        if scene.final_video_status == 'completed' and scene.final_video_gcs_path:
            try:
                result['final_video_url'] = gcs_storage.get_signed_url(
                    scene.final_video_gcs_path,
                    expiration=3600
                )
            except Exception as e:
                logger.error(f"Error al generar URL firmada de video final: {e}")
        
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
        
        # Verificar que todos tengan video (original o final combinado)
        for scene in scenes:
            has_original_video = scene.video_status == 'completed' and scene.video_gcs_path
            has_final_video = scene.final_video_status == 'completed' and scene.final_video_gcs_path
            
            if not (has_original_video or has_final_video):
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
            logger.info(f"=== ORDEN DE ESCENAS PARA CONCATENACIÓN ===")
            
            for idx, scene in enumerate(scenes):
                logger.info(f"  [{idx}] Escena {scene.scene_id} (order={scene.order}, service={scene.ai_service})")
                
                # PRIORIZAR el video final (con audio ElevenLabs) si existe, sino usar el original
                if scene.final_video_status == 'completed' and scene.final_video_gcs_path:
                    video_gcs_path = scene.final_video_gcs_path
                    logger.info(f"    → Usando video FINAL (con audio ElevenLabs TTS)")
                else:
                    video_gcs_path = scene.video_gcs_path
                    if scene.needs_audio():
                        logger.warning(f"    ⚠️ Video sin audio ElevenLabs (final_video_status={scene.final_video_status})")
                    else:
                        logger.info(f"    → Usando video original (servicio={scene.ai_service})")
                
                # Extraer blob name del GCS path
                blob_name = video_gcs_path.replace(f"gs://{settings.GCS_BUCKET_NAME}/", "")
                blob = gcs_storage.bucket.blob(blob_name)
                
                # Descargar a archivo temporal con orden explícito
                temp_video_path = os.path.join(temp_dir, f"scene_{scene.order:03d}_{scene.scene_id.replace(' ', '_')}.mp4")
                blob.download_to_filename(temp_video_path)
                video_paths.append(temp_video_path)
                
                logger.info(f"    ✓ Descargado: {temp_video_path} ({os.path.getsize(temp_video_path)} bytes)")
            
            logger.info(f"=== {len(video_paths)} VIDEOS DESCARGADOS ===")
            
            # Verificar resoluciones y audio de cada video
            logger.info("=== VERIFICANDO RESOLUCIONES Y AUDIO ===")
            videos_with_audio = []
            video_resolutions = []
            
            for video_path in video_paths:
                has_audio = VideoCompositionService._check_audio_stream(video_path)
                videos_with_audio.append(has_audio)
                
                # Obtener resolución
                resolution = VideoCompositionService._get_video_resolution(video_path)
                video_resolutions.append(resolution)
                
                logger.info(f"  {os.path.basename(video_path)}: {resolution[0]}x{resolution[1]} | {'✓ Audio' if has_audio else '⚠️ Sin audio'}")
            
            # Verificar si todas las resoluciones son iguales
            all_same_resolution = all(r == video_resolutions[0] for r in video_resolutions)
            
            if not all_same_resolution:
                # Listar todas las resoluciones diferentes
                unique_resolutions = list(set(video_resolutions))
                error_msg = (
                    f"❌ ERROR: Las escenas tienen resoluciones diferentes y no se pueden combinar.\n"
                    f"Resoluciones detectadas: {', '.join([f'{w}x{h}' for w, h in unique_resolutions])}\n\n"
                    f"SOLUCIÓN: Debes regenerar todas las escenas con la MISMA orientación (16:9 o 9:16).\n"
                    f"Ve al Paso 2 y asegúrate de que todas las escenas usen el mismo formato de video."
                )
                logger.error(error_msg)
                raise ValidationException(error_msg)
            
            # Si algún video no tiene audio, usar estrategia especial
            all_have_audio = all(videos_with_audio)
            if not all_have_audio:
                logger.warning("⚠️ Algunos videos no tienen audio - ajustando estrategia de concatenación")
            
            # Path de salida temporal
            output_path = os.path.join(temp_dir, 'combined_output.mp4')
            
            # Estrategia: Usar filtro concat de FFmpeg en lugar de demuxer concat
            # Esto es más robusto para videos de diferentes fuentes y evita desfases de audio
            
            # Construir comando FFmpeg con inputs individuales
            ffmpeg_command = ['ffmpeg']
            
            # Añadir todos los videos como inputs
            for video_path in video_paths:
                ffmpeg_command.extend(['-i', video_path])
            
            # Construir filter_complex para concatenación
            # Si todos tienen audio: [0:v][0:a][1:v][1:a]...[n:v][n:a]concat=n=N:v=1:a=1[outv][outa]
            # Si algunos no tienen audio: añadir anullsrc (audio silencioso) para los que no tienen
            
            if all_have_audio:
                # Todos tienen audio - estrategia simple
                filter_parts = []
                for i in range(len(video_paths)):
                    filter_parts.append(f"[{i}:v][{i}:a]")
                
                filter_complex = f"{''.join(filter_parts)}concat=n={len(video_paths)}:v=1:a=1[outv][outa]"
            else:
                # Algunos no tienen audio - añadir audio silencioso donde falte
                # Necesitamos obtener la duración de cada video sin audio
                filter_lines = []
                concat_inputs = []
                
                for i, has_audio in enumerate(videos_with_audio):
                    if has_audio:
                        concat_inputs.append(f"[{i}:v][{i}:a]")
                    else:
                        # Obtener duración del video sin audio
                        duration = VideoCompositionService.get_video_duration(video_paths[i])
                        
                        # Si no se pudo obtener duración, usar valor por defecto
                        if duration <= 0:
                            duration = 8.0  # 8 segundos por defecto
                        
                        # Generar audio silencioso con la duración del video
                        # anullsrc no acepta inputs, genera audio sintético directamente
                        audio_label = f"a{i}"
                        filter_lines.append(f"anullsrc=channel_layout=stereo:sample_rate=48000:duration={duration}[{audio_label}]")
                        concat_inputs.append(f"[{i}:v][{audio_label}]")
                
                if filter_lines:
                    filter_complex = ';'.join(filter_lines) + ';' + ''.join(concat_inputs) + f"concat=n={len(video_paths)}:v=1:a=1[outv][outa]"
                else:
                    filter_complex = ''.join(concat_inputs) + f"concat=n={len(video_paths)}:v=1:a=1[outv][outa]"
            
            ffmpeg_command.extend([
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',  # Re-encodear video con H.264
                '-preset', 'medium',  # Balance entre velocidad y calidad
                '-crf', '23',  # Calidad constante (18-28, menor=mejor)
                '-c:a', 'aac',  # Re-encodear audio con AAC
                '-b:a', '192k',  # Bitrate de audio
                '-ar', '48000',  # Sample rate consistente
                '-movflags', '+faststart',  # Optimizar para streaming
                '-y',  # Sobrescribir si existe
                output_path
            ])
            
            logger.info(f"Ejecutando FFmpeg con filter_complex concat:")
            logger.info(f"  Número de videos: {len(video_paths)}")
            logger.info(f"  Filter: {filter_complex}")
            logger.info(f"  Comando: {' '.join(ffmpeg_command[:10])}... (truncado)")
            
            result = subprocess.run(
                ffmpeg_command,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos máximo (re-encoding toma más tiempo)
            )
            
            if result.returncode != 0:
                error_msg = f"FFmpeg falló con código {result.returncode}\n"
                error_msg += f"=== STDOUT ===\n{result.stdout}\n"
                error_msg += f"=== STDERR ===\n{result.stderr}"
                logger.error(error_msg)
                
                # Detectar problemas específicos de audio
                stderr_lower = result.stderr.lower()
                if 'audio' in stderr_lower or 'stream' in stderr_lower:
                    logger.error("⚠️ Posible problema de audio detectado")
                    logger.error("Verificar que todos los videos tienen stream de audio")
                
                raise ServiceException(f"Error al combinar videos con FFmpeg: {result.stderr[:500]}")
            
            logger.info("✓ Videos combinados exitosamente con FFmpeg")
            
            # Verificar que el archivo de salida existe
            if not os.path.exists(output_path):
                raise ServiceException("FFmpeg no generó el archivo de salida")
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Video combinado: {file_size} bytes")
            
            # Subir video combinado a GCS
            project_id = None
            if scenes[0].project:
                project_id = scenes[0].project.id
            elif scenes[0].script and scenes[0].script.project:
                project_id = scenes[0].script.project.id
            
            if project_id:
                gcs_destination = f"projects/{project_id}/combined_videos/{output_filename}"
            else:
                gcs_destination = f"standalone/combined_videos/{output_filename}"
            
            with open(output_path, 'rb') as video_file:
                gcs_full_path = gcs_storage.upload_from_bytes(
                    file_content=video_file.read(),
                    destination_path=gcs_destination,
                    content_type='video/mp4'
                )
            
            logger.info(f"✓ Video combinado subido a GCS: {gcs_full_path}")
            
            return gcs_full_path
            
        except subprocess.TimeoutExpired:
            raise ServiceException("FFmpeg timeout: el proceso tardó más de 10 minutos")
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
                
        except FileNotFoundError:
            logger.warning("ffprobe no está instalado. No se puede obtener la duración del video.")
            return 0.0
        except Exception as e:
            logger.warning(f"Error al obtener duración: {e}")
            return 0.0
    
    @staticmethod
    def _check_audio_stream(video_path: str) -> bool:
        """
        Verifica si un video tiene stream de audio usando FFprobe
        
        Args:
            video_path: Path al archivo de video
            
        Returns:
            True si tiene audio, False si no
        """
        import subprocess
        
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-select_streams', 'a:0',
                    '-show_entries', 'stream=codec_name',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Si hay output, significa que encontró un stream de audio
            has_audio = result.returncode == 0 and result.stdout.strip() != ''
            
            if has_audio:
                codec = result.stdout.strip()
                logger.debug(f"  Audio codec: {codec}")
            
            return has_audio
                
        except FileNotFoundError:
            logger.warning("ffprobe no está instalado. Asumiendo que el video tiene audio.")
            return True
        except Exception as e:
            logger.warning(f"Error al verificar audio stream: {e}")
            # Por defecto, asumir que tiene audio si no se puede verificar
            return True
    
    @staticmethod
    def _get_video_resolution(video_path: str) -> tuple:
        """
        Obtiene la resolución de un video usando FFprobe
        
        Args:
            video_path: Path al archivo de video
            
        Returns:
            Tupla (width, height)
        """
        import subprocess
        
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height',
                    '-of', 'csv=s=x:p=0',
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                width, height = map(int, result.stdout.strip().split('x'))
                return (width, height)
            else:
                logger.warning(f"No se pudo obtener resolución del video: {result.stderr}")
                return (1280, 720)  # Default
                
        except FileNotFoundError:
            logger.warning("ffprobe no está instalado. Usando resolución por defecto (1280x720).")
            return (1280, 720)  # Default
        except Exception as e:
            logger.warning(f"Error al obtener resolución: {e}")
            return (1280, 720)  # Default


# ====================
# N8N INTEGRATION SERVICE
# ====================
# Este servicio se usa cuando USE_LANGCHAIN_AGENT=False (comportamiento legacy)
# Cuando USE_LANGCHAIN_AGENT=True, se usa ScriptAgentService en su lugar

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
                # Incluir characters si viene en la respuesta
                if 'characters' in data:
                    output_data['characters'] = data.get('characters')
                    logger.info(f"Script {script_id}: {len(data['characters'])} personajes recibidos")
                else:
                    logger.warning(f"Script {script_id}: No se recibieron 'characters' en la respuesta de n8n")
            
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
                    
                    # Iniciar generación de preview images solo si está habilitado
                    if script.generate_previews:
                        scene_service = SceneService()
                        for scene in created_scenes:
                            try:
                                # TODO: Idealmente esto debería ser async o con Celery
                                # Por ahora lo hacemos síncrono
                                scene_service.generate_preview_image(scene)
                            except Exception as e:
                                # No bloqueamos si falla una preview image
                                logger.error(f"Error al generar preview para escena {scene.scene_id}: {e}")
                    else:
                        logger.info(f"✓ Generación de previews deshabilitada (script.generate_previews=False)")
                    
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


# ====================
# OPENAI SCRIPT ASSISTANT SERVICE
# ====================

class OpenAIScriptAssistantService:
    """Servicio para asistencia de escritura de guiones con OpenAI GPT-4"""
    
    def __init__(self):
        """Inicializa el cliente de OpenAI"""
        if not settings.OPENAI_API_KEY:
            raise ValidationException('OPENAI_API_KEY no está configurada')
        
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4"
        
        # Prompt del sistema para guiar al asistente
        self.system_prompt = """Eres un asistente experto en redacción de guiones para videos. Tu objetivo es ayudar al usuario a crear un guión efectivo y bien estructurado mediante una conversación natural.

Tu proceso debe ser:
1. Hacer preguntas específicas sobre el contenido del video (tema, objetivo, audiencia, duración, tono, etc.)
2. A medida que el usuario responda, ir construyendo el guión progresivamente
3. Mostrar siempre el guión completo actualizado después de cada iteración
4. El usuario puede editar el guión directamente, y tú debes adaptar tus siguientes sugerencias basándote en esos cambios

IMPORTANTE: 
- Cuando actualices el guión, debes mostrar TODO el guión completo, no solo la parte que cambió
- El guión debe estar listo para ser leído/narrado directamente
- Sé conciso en tus preguntas y explicaciones
- Adapta el tono y estilo del guión según las preferencias del usuario
- Si el usuario hace cambios manuales al guión, reconócelos y adapta tus siguientes sugerencias

Formato de respuesta:
Tu respuesta debe tener DOS partes separadas por "---SCRIPT---":
1. ANTES del separador: Tu mensaje conversacional (pregunta o comentario)
2. DESPUÉS del separador: El guión completo actualizado (solo el texto del guión, sin formato especial)

Ejemplo:
Entiendo que quieres hacer un video sobre marketing digital. ¿Cuál es la duración aproximada que tienes en mente?
---SCRIPT---
Bienvenidos al mundo del marketing digital. Hoy vamos a explorar las estrategias más efectivas para hacer crecer tu negocio en línea."""
    
    def create_chat_session(self) -> Dict:
        """
        Crea una nueva sesión de chat
        
        Returns:
            Dict con 'session_id' y 'messages' iniciales
        """
        import uuid
        session_id = str(uuid.uuid4())
        
        # Mensaje inicial del asistente
        initial_messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "assistant",
                "content": "¡Hola! Soy tu asistente para escribir guiones. Voy a ayudarte a crear un guión profesional para tu video.\n\nPara empezar, cuéntame: ¿De qué va a tratar tu video?\n---SCRIPT---\n"
            }
        ]
        
        return {
            "session_id": session_id,
            "messages": initial_messages,
            "script": ""
        }
    
    def send_message(self, session_data: Dict, user_message: str, current_script: str = None) -> Dict:
        """
        Envía un mensaje al asistente y obtiene respuesta
        
        Args:
            session_data: Datos de la sesión (con historial de mensajes)
            user_message: Mensaje del usuario
            current_script: Guión actual (si el usuario lo editó manualmente)
        
        Returns:
            Dict con:
                - assistant_message: Mensaje del asistente
                - updated_script: Guión actualizado
                - messages: Historial completo actualizado
        """
        try:
            messages = session_data.get("messages", [])
            
            # Si el usuario editó el guión manualmente, informar al asistente
            if current_script and current_script != session_data.get("script", ""):
                user_message = f"[El usuario ha editado el guión manualmente. Nuevo contenido del guión:\n{current_script}\n]\n\n{user_message}"
            
            # Agregar mensaje del usuario
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Llamar a OpenAI
            logger.info(f"Enviando mensaje a OpenAI GPT-4 (historial: {len(messages)} mensajes)")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_reply = response.choices[0].message.content
            
            # Agregar respuesta del asistente al historial
            messages.append({
                "role": "assistant",
                "content": assistant_reply
            })
            
            # Separar el mensaje del guión
            if "---SCRIPT---" in assistant_reply:
                parts = assistant_reply.split("---SCRIPT---")
                assistant_message = parts[0].strip()
                updated_script = parts[1].strip() if len(parts) > 1 else ""
            else:
                # Si no hay separador, todo es mensaje
                assistant_message = assistant_reply
                updated_script = current_script or ""
            
            logger.info(f"✓ Respuesta recibida de OpenAI (script length: {len(updated_script)})")
            
            return {
                "assistant_message": assistant_message,
                "updated_script": updated_script,
                "messages": messages,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error al comunicar con OpenAI: {e}")
            raise ServiceException(f"Error al procesar mensaje: {str(e)}")


# ====================
# ELEVENLABS MUSIC SERVICE - ELIMINADO
# La funcionalidad de música ahora está integrada en el modelo Audio con type='music'
# ====================