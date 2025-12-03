from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from decimal import Decimal
import logging
import uuid

logger = logging.getLogger(__name__)

# Constantes para choices
VIDEO_TYPES = [
    ('heygen_avatar_v2', 'HeyGen Avatar V2'),
    ('heygen_avatar_iv', 'HeyGen Avatar IV'),
    ('gemini_veo', 'Gemini Veo'),
    ('sora', 'OpenAI Sora'),
    # Higgsfield
    ('higgsfield_dop_standard', 'Higgsfield DoP Standard'),
    ('higgsfield_dop_preview', 'Higgsfield DoP Preview'),
    ('higgsfield_seedance_v1_pro', 'Higgsfield Seedance V1 Pro'),
    ('higgsfield_kling_v2_1_pro', 'Higgsfield Kling V2.1 Pro'),
    # Kling
    ('kling_v1', 'Kling V1'),
    ('kling_v1_5', 'Kling V1.5'),
    ('kling_v1_6', 'Kling V1.6'),
    ('kling_v2_master', 'Kling V2 Master'),
    ('kling_v2_1', 'Kling V2.1'),
    ('kling_v2_5_turbo', 'Kling V2.5 Turbo'),
    # Manim
    ('manim_quote', 'Manim Quote'),
]

VIDEO_STATUS = [
    ('pending', 'Pendiente'),
    ('processing', 'Procesando'),
    ('completed', 'Completado'),
    ('error', 'Error'),
]

# Tipos de video para el flujo del agente
AGENT_VIDEO_TYPES = [
    ('ultra', 'Modo Ultra (Veo3 y Sora2)'),
    ('avatar', 'Con Avatares (HeyGen)'),
    ('general', 'Video General'),
]

# Orientaciones de video
VIDEO_ORIENTATIONS = [
    ('16:9', 'Horizontal (16:9)'),
    ('9:16', 'Vertical (9:16)'),
]

IMAGE_TYPES = [
    ('text_to_image', 'Texto a Imagen'),
    ('image_to_image', 'Imagen a Imagen (Edición)'),
    ('multi_image', 'Múltiples Imágenes (Composición)'),
]

IMAGE_STATUS = [
    ('pending', 'Pendiente'),
    ('processing', 'Procesando'),
    ('completed', 'Completado'),
    ('error', 'Error'),
]

AUDIO_STATUS = [
    ('pending', 'Pendiente'),
    ('processing', 'Procesando'),
    ('completed', 'Completado'),
    ('error', 'Error'),
]

SCRIPT_STATUS = [
    ('pending', 'Pendiente'),
    ('processing', 'Procesando'),
    ('completed', 'Completado'),
    ('error', 'Error'),
]

SCENE_STATUS = [
    ('pending', 'Pendiente'),
    ('processing', 'Procesando'),
    ('completed', 'Completado'),
    ('error', 'Error'),
]

SCENE_AI_SERVICES = [
    ('gemini_veo', 'Gemini Veo'),
    ('sora', 'OpenAI Sora'),
    ('heygen_v2', 'HeyGen Avatar V2'),
    ('heygen_avatar_iv', 'HeyGen Avatar IV'),
    ('vuela_ai', 'Vuela.ai'),
    # Higgsfield
    ('higgsfield_dop_standard', 'Higgsfield DoP Standard'),
    ('higgsfield_dop_preview', 'Higgsfield DoP Preview'),
    ('higgsfield_seedance_v1_pro', 'Higgsfield Seedance V1 Pro'),
    ('higgsfield_kling_v2_1_pro', 'Higgsfield Kling V2.1 Pro'),
    # Kling
    ('kling_v1', 'Kling V1'),
    ('kling_v1_5', 'Kling V1.5'),
    ('kling_v1_6', 'Kling V1.6'),
    ('kling_v2_master', 'Kling V2 Master'),
    ('kling_v2_1', 'Kling V2.1'),
    ('kling_v2_5_turbo', 'Kling V2.5 Turbo'),
]


class Project(models.Model):
    """Modelo para proyectos que agrupan videos"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_projects',
        null=True,
        blank=True,
        help_text='Usuario propietario del proyecto'
    )
    shared_with = models.ManyToManyField(
        User,
        through='ProjectMember',
        related_name='shared_projects',
        blank=True,
        help_text='Usuarios con acceso al proyecto'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'

    def __str__(self):
        return self.name
    
    def has_access(self, user):
        """Verifica si un usuario tiene acceso al proyecto"""
        return self.owner == user or self.members.filter(user=user).exists()
    
    def get_user_role(self, user):
        """Obtiene el rol del usuario en el proyecto"""
        if self.owner == user:
            return 'owner'
        try:
            member = self.members.get(user=user)
            return member.role
        except ProjectMember.DoesNotExist:
            return None

    @property
    def video_count(self):
        """Retorna el número de videos en el proyecto"""
        return self.videos.count()

    @property
    def completed_videos(self):
        """Retorna videos completados"""
        return self.videos.filter(status='completed').count()
    
    @property
    def image_count(self):
        """Retorna el número de imágenes en el proyecto"""
        return self.images.count()
    
    @property
    def completed_images(self):
        """Retorna imágenes completadas"""
        return self.images.filter(status='completed').count()
    
    @property
    def script_count(self):
        """Retorna el número de guiones en el proyecto"""
        return self.scripts.count()
    
    @property
    def completed_scripts(self):
        """Retorna guiones completados"""
        return self.scripts.filter(status='completed').count()
    
    @property
    def scene_count(self):
        """Retorna el número de escenas en el proyecto"""
        return self.scenes.count()
    
    @property
    def completed_scenes(self):
        """Retorna escenas completadas"""
        return self.scenes.filter(video_status='completed').count()


class Video(models.Model):
    """Modelo para videos generados por IA"""
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        help_text='UUID público para URLs y storage'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='videos',
        null=True,
        blank=True,
        help_text='Proyecto al que pertenece (opcional)'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='videos',
        null=True,
        blank=True,
        help_text='Usuario que creó este video'
    )
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=30, choices=VIDEO_TYPES)
    status = models.CharField(
        max_length=20,
        choices=VIDEO_STATUS,
        default='pending'
    )
    
    # Contenido y configuración
    script = models.TextField(help_text='Guión del video')
    config = models.JSONField(
        default=dict,
        help_text='Configuración específica (avatar_id, voice_id, background, etc.)'
    )
    
    # Almacenamiento
    gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta del video en Google Cloud Storage'
    )
    
    # Metadatos del video
    duration = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duración en segundos'
    )
    resolution = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Resolución del video (ej: 1280x720)'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Metadata adicional de la API'
    )
    
    # Control de errores
    error_message = models.TextField(blank=True, null=True)
    
    # API response tracking
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID del video en la plataforma externa (HeyGen, Gemini)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Video'
        verbose_name_plural = 'Videos'

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def mark_as_processing(self):
        """Marca el video como procesando"""
        self.status = 'processing'
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
        """Marca el video como completado y cobra créditos si es necesario"""
        # Inicializar metadata si no existe
        if not self.metadata:
            self.metadata = {}
        
        # Actualizar metadata PRIMERO (incluyendo duración) antes de calcular el costo
        if metadata:
            self.metadata.update(metadata)
        
        # Actualizar campo duration si está en metadata
        if 'duration' in self.metadata and self.metadata['duration']:
            try:
                duration_value = self.metadata['duration']
                # Convertir a int si es necesario
                if isinstance(duration_value, (int, float)):
                    self.duration = int(duration_value)
                elif isinstance(duration_value, str):
                    self.duration = int(float(duration_value))
            except (ValueError, TypeError) as e:
                logger.warning(f"No se pudo convertir duración para video {self.id}: {duration_value}, error: {e}")
        
        # Marcar como completado
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        
        # Guardar primero para tener la duración disponible
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'duration', 'metadata', 'updated_at'])
        
        # AHORA intentar cobrar créditos DESPUÉS de tener la metadata y duración guardadas
        if charge_credits:
            if not self.created_by:
                logger.warning(f"Video {self.id} no tiene created_by, no se pueden cobrar créditos")
            else:
                try:
                    from core.services.credits import CreditService, InsufficientCreditsException
                    # Refrescar desde BD para asegurar que tenemos el metadata más reciente
                    self.refresh_from_db()
                    
                    # Verificar si ya se cobraron créditos
                    if not self.metadata.get('credits_charged'):
                        logger.info(f"Cobrando créditos para video {self.id} (tipo: {self.type})")
                        CreditService.deduct_credits_for_video(self.created_by, self)
                    else:
                        logger.info(f"Créditos ya cobrados para video {self.id}")
                except InsufficientCreditsException as e:
                    logger.error(f"Créditos insuficientes para video {self.id}: {e}")
                    # Marcar en metadata que el cobro está pendiente
                    self.metadata['credits_charge_pending'] = True
                    self.metadata['credits_charge_error'] = str(e)
                    self.save(update_fields=['metadata'])
                    # El polling intentará cobrar de nuevo más tarde
                    logger.warning(f"Video {self.id} completado pero créditos pendientes. Se intentará cobrar durante el polling.")
                except Exception as e:
                    logger.error(f"Error al cobrar créditos para video {self.id}: {e}", exc_info=True)
                    # Marcar en metadata que hubo un error pero continuar
                    self.metadata['credits_charge_error'] = str(e)
                    self.save(update_fields=['metadata'])

    def mark_as_error(self, error_message):
        """Marca el video con error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Image(models.Model):
    """Modelo para imágenes generadas por IA (Gemini)"""
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        help_text='UUID público para URLs y storage'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        blank=True,
        help_text='Proyecto al que pertenece (opcional)'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        blank=True,
        help_text='Usuario que creó esta imagen'
    )
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=IMAGE_TYPES)
    status = models.CharField(
        max_length=20,
        choices=IMAGE_STATUS,
        default='pending'
    )
    
    # Contenido y configuración
    prompt = models.TextField(help_text='Prompt descriptivo para la imagen')
    config = models.JSONField(
        default=dict,
        help_text='Configuración específica (aspect_ratio, response_modalities, etc.)'
    )
    
    # Almacenamiento
    gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta de la imagen en Google Cloud Storage'
    )
    
    # Metadatos de la imagen
    width = models.IntegerField(
        null=True,
        blank=True,
        help_text='Ancho de la imagen en pixels'
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        help_text='Alto de la imagen en pixels'
    )
    aspect_ratio = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='Relación de aspecto (ej: 16:9, 1:1)'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Metadata adicional de la API'
    )
    
    # Control de errores
    error_message = models.TextField(blank=True, null=True)
    
    # API response tracking
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID de la generación en Gemini'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Imagen'
        verbose_name_plural = 'Imágenes'

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def mark_as_processing(self):
        """Marca la imagen como procesando"""
        self.status = 'processing'
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
        """Marca la imagen como completada y cobra créditos si es necesario"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        
        # Inicializar metadata si no existe
        if not self.metadata:
            self.metadata = {}
        
        # Actualizar metadata sin sobrescribir
        if metadata:
            self.metadata.update(metadata)
        
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits:
            if not self.created_by:
                logger.warning(f"Imagen {self.id} no tiene created_by, no se pueden cobrar créditos")
            else:
                try:
                    from core.services.credits import CreditService
                    # Refrescar desde BD para asegurar que tenemos el metadata más reciente
                    self.refresh_from_db()
                    
                    # Verificar si ya se cobraron créditos
                    if not self.metadata.get('credits_charged'):
                        logger.info(f"Cobrando créditos para imagen {self.id} (tipo: {self.type})")
                        CreditService.deduct_credits_for_image(self.created_by, self)
                    else:
                        logger.info(f"Créditos ya cobrados para imagen {self.id}")
                except Exception as e:
                    logger.error(f"Error al cobrar créditos para imagen {self.id}: {e}", exc_info=True)
                    # No fallar la operación si falla el cobro

    def mark_as_error(self, error_message):
        """Marca la imagen con error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Audio(models.Model):
    """Modelo unificado para audios (TTS y música generada)"""
    
    AUDIO_TYPE_CHOICES = [
        ('tts', 'Text-to-Speech'),
        ('music', 'Música Generada'),
    ]
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        help_text='UUID público para URLs y storage'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='audios',
        null=True,
        blank=True,
        help_text='Proyecto al que pertenece (opcional)'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='audios',
        null=True,
        blank=True,
        help_text='Usuario que creó este audio'
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=AUDIO_STATUS,
        default='pending'
    )
    
    # Tipo de audio (TTS o música)
    type = models.CharField(
        max_length=20,
        choices=AUDIO_TYPE_CHOICES,
        default='tts',
        db_index=True,
        help_text='Tipo de audio: TTS o música generada'
    )
    
    # Campos TTS (nullable si type='music')
    text = models.TextField(
        null=True,
        blank=True,
        help_text='Texto para convertir a voz (TTS)'
    )
    voice_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='ID de la voz en ElevenLabs (TTS)'
    )
    
    # Campos Music (nullable si type='tts')
    prompt = models.TextField(
        null=True,
        blank=True,
        help_text='Prompt usado para generar la música'
    )
    composition_plan = models.JSONField(
        null=True,
        blank=True,
        help_text='Plan de composición detallado (JSON)'
    )
    song_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text='Metadatos de la canción (tempo, key, mood, etc.)'
    )
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duración de la música en milisegundos'
    )
    elevenlabs_track_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='ID del track en ElevenLabs Music'
    )
    voice_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Nombre de la voz (para mostrar en UI)'
    )
    model_id = models.CharField(
        max_length=100,
        default='eleven_turbo_v2_5',
        help_text='Modelo de ElevenLabs (eleven_turbo_v2_5, eleven_multilingual_v2, etc.)'
    )
    language_code = models.CharField(
        max_length=10,
        default='es',
        help_text='Código de idioma (ISO 639-1)'
    )
    
    # Configuración de voice settings (guardados como JSONField para flexibilidad)
    voice_settings = models.JSONField(
        default=dict,
        help_text='Configuración de voz: stability, similarity_boost, style, speed'
    )
    
    # Almacenamiento
    gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta del audio en Google Cloud Storage'
    )
    
    # Metadatos del audio
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text='Duración del audio en segundos'
    )
    file_size = models.IntegerField(
        null=True,
        blank=True,
        help_text='Tamaño del archivo en bytes'
    )
    format = models.CharField(
        max_length=10,
        default='mp3',
        help_text='Formato del audio (mp3, wav, etc.)'
    )
    sample_rate = models.IntegerField(
        null=True,
        blank=True,
        help_text='Sample rate del audio (44100, 48000, etc.)'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Metadata adicional de la API'
    )
    
    # Alignment data (timestamps carácter por carácter)
    alignment = models.JSONField(
        default=dict,
        blank=True,
        help_text='Datos de sincronización carácter por carácter'
    )
    
    # Control de errores
    error_message = models.TextField(blank=True, null=True)
    
    # API response tracking
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID de la generación en ElevenLabs (si aplica)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audio'
        verbose_name_plural = 'Audios'

    def __str__(self):
        return f"{self.title} ({self.voice_name or self.voice_id})"

    def mark_as_processing(self):
        """Marca el audio como procesando"""
        self.status = 'processing'
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_completed(self, gcs_path=None, duration=None, metadata=None, alignment=None, charge_credits=True):
        """Marca el audio como completado y cobra créditos si es necesario"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if duration:
            self.duration = duration
        if metadata:
            self.metadata = metadata
        if alignment:
            self.alignment = alignment
        # Inicializar metadata si no existe
        if not self.metadata:
            self.metadata = {}
        
        # Actualizar metadata sin sobrescribir
        if metadata:
            self.metadata.update(metadata)
        
        self.save(update_fields=[
            'status', 'completed_at', 'gcs_path', 'duration', 
            'metadata', 'alignment', 'updated_at'
        ])
        
        # Cobrar créditos automáticamente
        if charge_credits:
            if not self.created_by:
                logger.warning(f"Audio {self.id} no tiene created_by, no se pueden cobrar créditos")
            else:
                try:
                    from core.services.credits import CreditService
                    # Refrescar desde BD para asegurar que tenemos el metadata más reciente
                    self.refresh_from_db()
                    
                    # Verificar si ya se cobraron créditos
                    if not self.metadata.get('credits_charged'):
                        logger.info(f"Cobrando créditos para audio {self.id} (caracteres: {len(self.text)})")
                        CreditService.deduct_credits_for_audio(self.created_by, self)
                    else:
                        logger.info(f"Créditos ya cobrados para audio {self.id}")
                except Exception as e:
                    logger.error(f"Error al cobrar créditos para audio {self.id}: {e}", exc_info=True)
                    # No fallar la operación si falla el cobro

    def mark_as_error(self, error_message):
        """Marca el audio con error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Script(models.Model):
    """Modelo para guiones procesados por n8n"""
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='scripts',
        null=True,
        blank=True,
        help_text='Proyecto al que pertenece (opcional)'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='scripts',
        null=True,
        blank=True,
        help_text='Usuario que creó este guión'
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=SCRIPT_STATUS,
        default='pending'
    )
    
    # Contenido del guión
    original_script = models.TextField(help_text='Guión original enviado')
    desired_duration_min = models.IntegerField(
        default=5,
        help_text='Duración deseada del video en minutos'
    )
    processed_data = models.JSONField(
        default=dict,
        help_text='Datos procesados por n8n (project, scenes, etc.)'
    )
    
    # Agent flow
    agent_flow = models.BooleanField(
        default=False,
        help_text='True si fue creado por el flujo del agente'
    )
    final_video = models.ForeignKey(
        'Video',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_script',
        help_text='Video final combinado generado por el agente'
    )
    
    # Configuración del agente (Paso 1)
    video_type = models.CharField(
        max_length=20,
        choices=AGENT_VIDEO_TYPES,
        blank=True,
        null=True,
        help_text='Tipo de video para el flujo del agente'
    )
    video_orientation = models.CharField(
        max_length=10,
        choices=VIDEO_ORIENTATIONS,
        default='16:9',
        help_text='Orientación del video (heredada a todas las escenas)'
    )
    generate_previews = models.BooleanField(
        default=True,
        help_text='Si se deben generar previews automáticamente'
    )
    
    # Metadatos del procesamiento
    platform_mode = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Modo de plataforma (mixto, etc.)'
    )
    num_scenes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Número de escenas'
    )
    language = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='Idioma del guión'
    )
    total_estimated_duration_min = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duración total estimada en minutos'
    )
    
    # Configuración de audio global (ElevenLabs)
    default_voice_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='ID de voz por defecto de ElevenLabs para todas las escenas'
    )
    default_voice_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Nombre de voz por defecto de ElevenLabs'
    )
    enable_audio = models.BooleanField(
        default=True,
        help_text='Si True, genera audio automáticamente para escenas Veo/Sora'
    )
    
    # Control de errores
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Guión'
        verbose_name_plural = 'Guiones'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def mark_as_processing(self):
        """Marca el guión como procesando"""
        self.status = 'processing'
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_completed(self, processed_data=None):
        """Marca el guión como completado"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if processed_data:
            self.processed_data = processed_data
            # Extraer metadatos del processed_data
            if 'project' in processed_data:
                project_data = processed_data['project']
                self.platform_mode = project_data.get('platform_mode')
                self.num_scenes = project_data.get('num_scenes')
                self.language = project_data.get('language')
                self.total_estimated_duration_min = project_data.get('total_estimated_duration_min')
        self.save(update_fields=['status', 'completed_at', 'processed_data', 'platform_mode', 'num_scenes', 'language', 'total_estimated_duration_min', 'updated_at'])

    def mark_as_error(self, error_message):
        """Marca el guión con error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])

    @property
    def scenes(self):
        """Retorna las escenas del guión procesado (desde processed_data JSON)"""
        return self.processed_data.get('scenes', [])

    @property
    def project_data(self):
        """Retorna los datos del proyecto del guión procesado"""
        return self.processed_data.get('project', {})


class Scene(models.Model):
    """Modelo para escenas individuales del agente de video"""
    
    # Relaciones
    script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE,
        related_name='db_scenes',
        help_text='Guión del que forma parte esta escena'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='scenes',
        help_text='Proyecto al que pertenece (para consultas directas)'
    )
    
    # Datos de la escena (desde n8n)
    scene_id = models.CharField(
        max_length=50,
        help_text='ID de la escena (ej: "Escena 1")'
    )
    summary = models.TextField(
        help_text='Resumen breve del contenido de la escena'
    )
    script_text = models.TextField(
        help_text='Texto literal y completo del guión para narración (HeyGen + ElevenLabs)'
    )
    visual_prompt = models.TextField(
        blank=True,
        null=True,
        help_text='Prompt visual para generar el video (Veo/Sora/Vuela) - en inglés'
    )
    duration_sec = models.IntegerField(
        help_text='Duración de la escena en segundos'
    )
    avatar = models.CharField(
        max_length=10,
        help_text='Indica si tiene avatar visible (si/no)'
    )
    platform = models.CharField(
        max_length=50,
        help_text='Plataforma sugerida por n8n (gemini_veo, sora, heygen)'
    )
    broll = models.JSONField(
        default=list,
        help_text='Lista de elementos visuales sugeridos para B-roll'
    )
    transition = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Tipo de transición (corte, fundido, deslizamiento, etc.)'
    )
    text_on_screen = models.TextField(
        blank=True,
        null=True,
        help_text='Texto para mostrar en pantalla'
    )
    audio_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notas sobre tono, música y efectos de audio'
    )
    
    # Orden en el video final
    order = models.IntegerField(
        help_text='Orden de la escena en la secuencia del video (0, 1, 2...)'
    )
    
    # Indica si está incluida en el video final
    is_included = models.BooleanField(
        default=True,
        help_text='Si está marcada para incluir en el video final'
    )
    
    # Preview image (generada con Gemini)
    preview_image_gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta de la imagen preview en GCS'
    )
    preview_image_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendiente'),
            ('generating', 'Generando'),
            ('completed', 'Completada'),
            ('error', 'Error')
        ],
        default='pending',
        help_text='Estado de generación de la imagen preview'
    )
    preview_image_error = models.TextField(
        blank=True,
        null=True,
        help_text='Mensaje de error si falla la generación del preview'
    )
    
    # Fuente de la imagen preview/referencia
    image_source = models.CharField(
        max_length=20,
        choices=[
            ('ai_generated', 'Generada con IA'),
            ('freepik_stock', 'Freepik Stock'),
            ('user_upload', 'Subida por Usuario')
        ],
        default='ai_generated',
        help_text='Origen de la imagen preview/referencia'
    )
    freepik_resource_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID del recurso de Freepik si se usó stock'
    )
    
    # Configuración del servicio IA para generar video
    ai_service = models.CharField(
        max_length=50,
        choices=SCENE_AI_SERVICES,
        help_text='Servicio de IA seleccionado para generar el video'
    )
    ai_config = models.JSONField(
        default=dict,
        help_text='Configuración específica del servicio (avatar_id, voice_id, duration, etc.)'
    )
    
    # Video generado
    video_gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta del video generado en GCS'
    )
    video_status = models.CharField(
        max_length=20,
        choices=SCENE_STATUS,
        default='pending',
        help_text='Estado de generación del video'
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID del video en la plataforma externa (HeyGen, Gemini, Sora)'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text='Mensaje de error si falla la generación del video'
    )
    
    # Audio generado con ElevenLabs (para escenas Veo/Sora)
    audio_gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta del audio narrado en GCS (ElevenLabs TTS)'
    )
    audio_status = models.CharField(
        max_length=20,
        choices=SCENE_STATUS,
        default='pending',
        help_text='Estado de generación del audio'
    )
    audio_voice_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='ID de la voz de ElevenLabs usada'
    )
    audio_voice_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Nombre de la voz de ElevenLabs'
    )
    audio_duration = models.FloatField(
        null=True,
        blank=True,
        help_text='Duración del audio en segundos'
    )
    audio_error_message = models.TextField(
        blank=True,
        null=True,
        help_text='Mensaje de error si falla la generación del audio'
    )
    
    # Video final combinado (video + audio)
    final_video_gcs_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Ruta del video final con audio combinado en GCS'
    )
    final_video_status = models.CharField(
        max_length=20,
        choices=SCENE_STATUS,
        default='pending',
        help_text='Estado de combinación del video final'
    )
    
    # Historial de versiones (para regeneración)
    version = models.IntegerField(
        default=1,
        help_text='Versión de la escena (incrementa con cada regeneración)'
    )
    parent_scene = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='versions',
        help_text='Escena padre si es una versión regenerada'
    )
    
    # Metadatos adicionales
    metadata = models.JSONField(
        default=dict,
        help_text='Metadata adicional de la API o del proceso'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Escena'
        verbose_name_plural = 'Escenas'
        unique_together = ['script', 'scene_id']

    def __str__(self):
        return f"{self.scene_id} - {self.script.title}"
    
    def mark_preview_as_generating(self):
        """Marca el preview como generando"""
        self.preview_image_status = 'generating'
        self.save(update_fields=['preview_image_status', 'updated_at'])
    
    def mark_preview_as_completed(self, gcs_path, charge_credits=True):
        """Marca el preview como completado y cobra créditos si es necesario"""
        self.preview_image_status = 'completed'
        self.preview_image_gcs_path = gcs_path
        self.save(update_fields=['preview_image_status', 'preview_image_gcs_path', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.script.created_by:
            try:
                from core.services.credits import CreditService
                CreditService.deduct_credits_for_scene_preview(self.script.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para preview de escena {self.id}: {e}")
                # No fallar la operación si falla el cobro
    
    def mark_preview_as_error(self, error_message):
        """Marca el preview con error"""
        self.preview_image_status = 'error'
        self.preview_image_error = error_message
        self.save(update_fields=['preview_image_status', 'preview_image_error', 'updated_at'])
    
    def mark_video_as_processing(self):
        """Marca el video como procesando"""
        self.video_status = 'processing'
        self.save(update_fields=['video_status', 'updated_at'])

    def mark_video_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
        """Marca el video como completado y cobra créditos si es necesario"""
        self.video_status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.video_gcs_path = gcs_path
        
        # Inicializar metadata si no existe
        if not self.metadata:
            self.metadata = {}
        
        # Actualizar metadata sin sobrescribir
        if metadata:
            self.metadata.update(metadata)
        
        self.save(update_fields=['video_status', 'completed_at', 'video_gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits:
            if not self.script.created_by:
                logger.warning(f"Escena {self.id} no tiene script.created_by, no se pueden cobrar créditos")
            else:
                try:
                    from core.services.credits import CreditService
                    # Refrescar desde BD para asegurar que tenemos el metadata más reciente
                    self.refresh_from_db()
                    
                    # Verificar si ya se cobraron créditos
                    if not self.metadata.get('credits_charged'):
                        logger.info(f"Cobrando créditos para video de escena {self.scene_id} (ID: {self.id}, servicio: {self.ai_service})")
                        CreditService.deduct_credits_for_scene_video(self.script.created_by, self)
                    else:
                        logger.info(f"Créditos ya cobrados para video de escena {self.scene_id} (ID: {self.id})")
                except Exception as e:
                    logger.error(f"Error al cobrar créditos para video de escena {self.id}: {e}", exc_info=True)
                    # No fallar la operación si falla el cobro

    def mark_video_as_error(self, error_message):
        """Marca el video con error"""
        self.video_status = 'error'
        self.error_message = error_message
        self.save(update_fields=['video_status', 'error_message', 'updated_at'])
    
    def mark_audio_as_processing(self):
        """Marca el audio como procesando"""
        self.audio_status = 'processing'
        self.save(update_fields=['audio_status', 'updated_at'])
    
    def mark_audio_as_completed(self, gcs_path: str, duration: float = None, voice_id: str = None, voice_name: str = None, charge_credits=True):
        """Marca el audio como completado y cobra créditos si es necesario"""
        self.audio_status = 'completed'
        self.audio_gcs_path = gcs_path
        if duration:
            self.audio_duration = duration
        if voice_id:
            self.audio_voice_id = voice_id
        if voice_name:
            self.audio_voice_name = voice_name
        
        # Inicializar metadata si no existe
        if not self.metadata:
            self.metadata = {}
        
        # Cobrar créditos automáticamente
        if charge_credits:
            if not self.script.created_by:
                logger.warning(f"Escena {self.id} no tiene script.created_by, no se pueden cobrar créditos de audio")
            else:
                try:
                    from core.services.credits import CreditService
                    # Verificar si ya se cobraron créditos
                    if not self.metadata.get('audio_credits_charged'):
                        # Calcular costo basado en script_text de la escena
                        cost = CreditService.estimate_audio_cost(self.script_text)
                        if cost > 0:
                            logger.info(f"Cobrando {cost} créditos por audio de escena {self.scene_id} (ID: {self.id}, caracteres: {len(self.script_text)})")
                            CreditService.deduct_credits(
                                user=self.script.created_by,
                                amount=cost,
                                service_name='elevenlabs',
                                operation_type='audio_generation',
                                resource=self,
                                metadata={
                                    'character_count': len(self.script_text),
                                    'duration': duration,
                                    'voice_id': voice_id,
                                }
                            )
                            # Marcar como cobrado
                            self.metadata['audio_credits_charged'] = True
                            logger.info(f"✓ Créditos de audio cobrados y marcados en metadata para escena {self.scene_id} (ID: {self.id})")
                        else:
                            logger.warning(f"Costo de audio es 0 para escena {self.scene_id} (ID: {self.id})")
                    else:
                        logger.info(f"Créditos de audio ya cobrados para escena {self.scene_id} (ID: {self.id})")
                except Exception as e:
                    logger.error(f"Error al cobrar créditos para audio de escena {self.id}: {e}", exc_info=True)
                    # No fallar la operación si falla el cobro
        
        self.save(update_fields=['audio_status', 'audio_gcs_path', 'audio_duration', 'audio_voice_id', 'audio_voice_name', 'metadata', 'updated_at'])
    
    def mark_audio_as_error(self, error_message: str):
        """Marca el audio como error"""
        self.audio_status = 'error'
        self.audio_error_message = error_message
        self.save(update_fields=['audio_status', 'audio_error_message', 'updated_at'])
    
    def mark_final_video_as_processing(self):
        """Marca el video final como procesando"""
        self.final_video_status = 'processing'
        self.save(update_fields=['final_video_status', 'updated_at'])
    
    def mark_final_video_as_completed(self, gcs_path: str):
        """Marca el video final como completado"""
        self.final_video_status = 'completed'
        self.final_video_gcs_path = gcs_path
        self.completed_at = timezone.now()
        self.save(update_fields=['final_video_status', 'final_video_gcs_path', 'completed_at', 'updated_at'])
    
    def mark_final_video_as_error(self, error_message: str):
        """Marca el video final como error"""
        self.final_video_status = 'error'
        self.error_message = error_message
        self.save(update_fields=['final_video_status', 'error_message', 'updated_at'])
    
    def needs_audio(self) -> bool:
        """Determina si esta escena necesita audio (Veo/Sora sin avatar)"""
        return self.ai_service in ['gemini_veo', 'sora', 'vuela_ai'] and self.video_status == 'completed'
    
    def needs_combination(self) -> bool:
        """Determina si esta escena necesita combinar video+audio"""
        return (
            self.video_status == 'completed' and 
            self.audio_status == 'completed' and 
            self.final_video_status == 'pending' and
            self.needs_audio()
        )


# Constantes para roles de proyecto
PROJECT_ROLES = [
    ('owner', 'Propietario'),
    ('editor', 'Editor'),
]

INVITATION_STATUS = [
    ('pending', 'Pendiente'),
    ('accepted', 'Aceptada'),
    ('expired', 'Expirada'),
    ('cancelled', 'Cancelada'),
]


class ProjectMember(models.Model):
    """Usuarios que tienen acceso a un proyecto compartido"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='members',
        help_text='Proyecto al que pertenece el miembro'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        help_text='Usuario miembro del proyecto'
    )
    role = models.CharField(
        max_length=20,
        choices=PROJECT_ROLES,
        default='editor',
        help_text='Rol del usuario en el proyecto'
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha en que el usuario se unió al proyecto'
    )

    class Meta:
        unique_together = ['project', 'user']
        verbose_name = 'Miembro de Proyecto'
        verbose_name_plural = 'Miembros de Proyectos'
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_role_display()})"


class ProjectInvitation(models.Model):
    """Invitaciones pendientes para unirse a proyectos"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text='Proyecto al que se invita'
    )
    email = models.EmailField(
        help_text='Email del usuario invitado'
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        help_text='Usuario que envió la invitación'
    )
    role = models.CharField(
        max_length=20,
        choices=PROJECT_ROLES,
        default='editor',
        help_text='Rol que se asignará al usuario cuando acepte'
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        help_text='Token único para aceptar la invitación'
    )
    status = models.CharField(
        max_length=20,
        choices=INVITATION_STATUS,
        default='pending',
        help_text='Estado de la invitación'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha de creación de la invitación'
    )
    expires_at = models.DateTimeField(
        help_text='Fecha de expiración de la invitación'
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha en que se aceptó la invitación'
    )

    class Meta:
        verbose_name = 'Invitación de Proyecto'
        verbose_name_plural = 'Invitaciones de Proyectos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'status']),
        ]

    def __str__(self):
        return f"Invitación para {self.email} - {self.project.name}"

    def save(self, *args, **kwargs):
        """Genera token único si no existe"""
        if not self.token:
            self.token = get_random_string(length=64)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Verifica si la invitación ha expirado"""
        return timezone.now() > self.expires_at

    def can_be_accepted(self):
        """Verifica si la invitación puede ser aceptada"""
        return (
            self.status == 'pending' and
            not self.is_expired()
        )


# ====================
# CREDITOS Y RATE LIMITING
# ====================

class UserCredits(models.Model):
    """Saldo de créditos por usuario"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='credits'
    )
    credits = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Saldo actual de créditos'
    )
    total_purchased = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Total de créditos comprados históricamente'
    )
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Total de créditos gastados históricamente'
    )
    monthly_limit = models.IntegerField(
        default=1000,
        help_text='Límite mensual de créditos'
    )
    current_month_usage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Créditos usados en el mes actual'
    )
    last_reset_date = models.DateField(
        null=True,
        blank=True,
        help_text='Última fecha de reset mensual'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Créditos de Usuario'
        verbose_name_plural = 'Créditos de Usuarios'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.credits} créditos"
    
    def reset_monthly_usage(self):
        """Resetea el uso mensual"""
        self.current_month_usage = Decimal('0')
        self.last_reset_date = timezone.now().date()
        self.save(update_fields=['current_month_usage', 'last_reset_date'])
        logger.info(f"Uso mensual reseteado para usuario {self.user.username}")
    
    @property
    def credits_remaining(self):
        """Créditos restantes del mes"""
        # Si el límite es 0, es ilimitado
        if self.monthly_limit == 0:
            return Decimal('999999999')  # Valor muy alto para representar ilimitado
        return max(Decimal('0'), self.monthly_limit - self.current_month_usage)
    
    @property
    def usage_percentage(self):
        """Porcentaje de uso mensual"""
        if self.monthly_limit == 0:
            return 0
        return min(100, (self.current_month_usage / self.monthly_limit) * 100)


class CreditTransaction(models.Model):
    """Historial de transacciones de créditos"""
    TRANSACTION_TYPES = [
        ('purchase', 'Compra'),
        ('spend', 'Gasto'),
        ('refund', 'Reembolso'),
        ('adjustment', 'Ajuste'),
        ('monthly_reset', 'Reset Mensual'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Cantidad de créditos (positivo para compras, negativo para gastos)'
    )
    balance_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Saldo antes de la transacción'
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Saldo después de la transacción'
    )
    description = models.TextField(
        blank=True,
        help_text='Descripción de la transacción'
    )
    
    # Relación genérica al recurso relacionado
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    service_name = models.CharField(
        max_length=50,
        blank=True,
        help_text='Nombre del servicio usado (gemini_veo, sora, etc.)'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Información adicional (duración, tokens, etc.)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['service_name', '-created_at']),
        ]
        verbose_name = 'Transacción de Créditos'
        verbose_name_plural = 'Transacciones de Créditos'
    
    def __str__(self):
        return f"{self.user.username}: {self.transaction_type} {self.amount} créditos"


class ServiceUsage(models.Model):
    """Tracking detallado de uso por servicio"""
    SERVICE_CHOICES = [
        ('gemini_veo', 'Gemini Veo'),
        ('sora', 'OpenAI Sora'),
        ('heygen_avatar_v2', 'HeyGen Avatar V2'),
        ('heygen_avatar_iv', 'HeyGen Avatar IV'),
        ('vuela_ai', 'Vuela.ai'),
        ('gemini_image', 'Gemini Image'),
        ('elevenlabs', 'ElevenLabs TTS'),
        ('elevenlabs_music', 'ElevenLabs Music'),
    ]
    
    OPERATION_TYPES = [
        ('video_generation', 'Generación de Video'),
        ('image_generation', 'Generación de Imagen'),
        ('audio_generation', 'Generación de Audio'),
        ('music_generation', 'Generación de Música'),
        ('preview_generation', 'Generación de Preview'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='service_usage'
    )
    service_name = models.CharField(
        max_length=50,
        choices=SERVICE_CHOICES
    )
    operation_type = models.CharField(
        max_length=50,
        choices=OPERATION_TYPES
    )
    
    # Consumo
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text='Tokens consumidos (si aplica)'
    )
    credits_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Créditos gastados'
    )
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Costo real en USD'
    )
    
    # Recurso generado
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text='Info adicional (duración, resolución, caracteres, etc.)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'service_name']),
            models.Index(fields=['service_name', '-created_at']),
            models.Index(fields=['created_at']),  # Para reportes por fecha
        ]
        verbose_name = 'Uso de Servicio'
        verbose_name_plural = 'Usos de Servicios'
    
    def __str__(self):
        return f"{self.user.username}: {self.service_name} - {self.credits_spent} créditos"


class GenerationTask(models.Model):
    """Tracking de tareas de generación en cola"""
    
    TASK_STATUS = [
        ('queued', 'En Cola'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]
    
    TASK_TYPES = [
        ('video', 'Video'),
        ('image', 'Imagen'),
        ('audio', 'Audio'),
        ('scene', 'Escena'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='UUID único de la tarea'
    )
    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Celery task ID (puede ser null antes de que Celery procese la tarea)'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='generation_tasks',
        help_text='Usuario que creó la tarea'
    )
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPES,
        help_text='Tipo de generación'
    )
    item_uuid = models.UUIDField(
        db_index=True,
        help_text='UUID del item generado (no ID numérico)'
    )
    status = models.CharField(
        max_length=20,
        choices=TASK_STATUS,
        default='queued',
        db_index=True,
        help_text='Estado de la tarea'
    )
    queue_name = models.CharField(
        max_length=50,
        help_text='Nombre de la cola de Celery'
    )
    priority = models.IntegerField(
        default=5,
        help_text='Prioridad (1-10, mayor = más prioridad, por tipo de generación)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Mensaje de error o razón de cancelación'
    )
    retry_count = models.IntegerField(
        default=0,
        help_text='Número de reintentos realizados'
    )
    max_retries = models.IntegerField(
        default=3,
        help_text='Máximo número de reintentos permitidos'
    )
    
    # Metadata para regeneración y tracking
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadata adicional (prompt, parámetros, etc.)'
    )
    
    class Meta:
        db_table = 'generation_task'
        verbose_name = 'Tarea de Generación'
        verbose_name_plural = 'Tareas de Generación'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['task_type', 'item_uuid']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['queue_name', 'priority', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_type} task {self.uuid} - {self.status}"
    
    def mark_as_processing(self):
        """Marca la tarea como procesando"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
        # Disparar evento para actualizar UI
        self._dispatch_status_change()
    
    def _dispatch_status_change(self):
        """Dispara evento JavaScript para actualizar UI (solo si hay canales configurados)"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'user_{self.user.id}',
                    {
                        'type': 'task_status_changed',
                        'task_uuid': str(self.uuid),
                        'status': self.status,
                    }
                )
        except Exception:
            # Si no hay canales configurados o hay error, no hacer nada
            pass
    
    def mark_as_completed(self, gcs_path=None, duration=None, metadata=None, alignment=None):
        """Marca la tarea como completada"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        
        # Actualizar metadata si se proporciona
        if metadata:
            if not self.metadata:
                self.metadata = {}
            self.metadata.update(metadata)
        
        update_fields = ['status', 'completed_at']
        if metadata:
            update_fields.append('metadata')
        
        self.save(update_fields=update_fields)
        self._dispatch_status_change()
    
    def mark_as_failed(self, error_message=None):
        """Marca la tarea como fallida"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])
        self._dispatch_status_change()
    
    def mark_as_cancelled(self, reason=None):
        """Marca la tarea como cancelada"""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        if reason:
            self.error_message = reason
        self.save(update_fields=['status', 'completed_at', 'error_message'])
        self._dispatch_status_change()


class Notification(models.Model):
    """Notificaciones del sistema"""
    
    NOTIFICATION_TYPES = [
        ('generation_completed', 'Generación Completada'),
        ('generation_failed', 'Generación Fallida'),
        ('generation_progress', 'Progreso de Generación'),
        ('credits_low', 'Créditos Bajos'),
        ('credits_insufficient', 'Créditos Insuficientes'),
        ('project_invitation', 'Invitación de Proyecto'),
        ('system_maintenance', 'Mantenimiento del Sistema'),
        ('info', 'Información'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='UUID único de la notificación'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='Usuario destinatario'
    )
    type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        help_text='Tipo de notificación'
    )
    title = models.CharField(
        max_length=255,
        help_text='Título de la notificación'
    )
    message = models.TextField(
        help_text='Mensaje de la notificación'
    )
    read = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Si la notificación ha sido leída'
    )
    
    # Enlace opcional a un recurso
    action_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='URL de acción (opcional)'
    )
    action_label = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Etiqueta del botón de acción'
    )
    
    # Metadata adicional (progreso, item_uuid, etc.)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadata adicional (progreso, item_uuid, etc.)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        indexes = [
            models.Index(fields=['user', 'read', 'created_at']),
            models.Index(fields=['user', 'type', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.type} - {self.title}"
    
    def mark_as_read(self):
        """Marca la notificación como leída"""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save(update_fields=['read', 'read_at'])
    
    @classmethod
    def create_notification(
        cls,
        user: User,
        type: str,
        title: str,
        message: str,
        action_url: str = None,
        action_label: str = None,
        metadata: dict = None
    ) -> 'Notification':
        """
        Crea una notificación y la envía vía WebSocket
        
        Args:
            user: Usuario destinatario
            type: Tipo de notificación
            title: Título
            message: Mensaje
            action_url: URL opcional de acción
            action_label: Etiqueta del botón de acción
            metadata: Metadata adicional
        
        Returns:
            Notification creada
        """
        notification = cls.objects.create(
            user=user,
            type=type,
            title=title,
            message=message,
            action_url=action_url,
            action_label=action_label,
            metadata=metadata or {}
        )
        
        # Enviar vía WebSocket (si está disponible)
        try:
            from core.consumers import NotificationConsumer
            NotificationConsumer.send_notification_to_user_sync(user.id, notification)
        except Exception as e:
            logger.warning(f"Error enviando notificación vía WebSocket: {e}")
        
        return notification


class PromptTemplate(models.Model):
    """Plantillas de prompts reutilizables para generación de contenido"""
    
    TEMPLATE_TYPES = [
        ('video', 'Video'),
        ('image', 'Imagen'),
        ('agent', 'Agente'),
    ]
    
    RECOMMENDED_SERVICES = [
        ('sora', 'Sora'),
        ('higgsfield', 'Higgsfield'),
        ('gemini_veo', 'Gemini Veo'),
        ('agent', 'Agente'),
    ]
    
    # Identificación
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='UUID único de la plantilla'
    )
    
    # Información básica
    name = models.CharField(
        max_length=200,
        help_text='Nombre de la plantilla (ej: "Raven Transition")'
    )
    description = models.TextField(
        blank=True,
        help_text='Descripción detallada de la plantilla'
    )
    
    # Tipo de contenido
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        default='video',
        help_text='Tipo de contenido que genera',
        db_index=True
    )
    
    # Contenido del prompt
    prompt_text = models.TextField(
        max_length=2000,
        help_text='Texto del prompt que se enviará al servicio de IA (máximo 2000 caracteres)'
    )
    
    # Servicio recomendado
    recommended_service = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=RECOMMENDED_SERVICES,
        help_text='Servicio recomendado para usar este template',
        db_index=True
    )
    
    # Preview
    preview_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='URL del video/imagen de ejemplo'
    )
    
    # Sistema de permisos
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_prompt_templates',
        help_text='Usuario que creó la plantilla (None para templates del sistema)',
        null=True,
        blank=True,
        db_index=True
    )
    is_public = models.BooleanField(
        default=False,
        help_text='Si la plantilla es visible para todos los usuarios',
        db_index=True
    )
    
    # Sistema de votación
    upvotes = models.PositiveIntegerField(
        default=0,
        help_text='Número de votos positivos'
    )
    downvotes = models.PositiveIntegerField(
        default=0,
        help_text='Número de votos negativos'
    )
    
    # Estadísticas
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text='Número de veces que se ha usado'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha de creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Fecha de última modificación'
    )
    
    # Control de estado
    is_active = models.BooleanField(
        default=True,
        help_text='Si la plantilla está activa y disponible',
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Plantilla de Prompt'
        verbose_name_plural = 'Plantillas de Prompts'
        ordering = ['-usage_count', '-created_at']
        # Permitir mismo nombre si created_by es diferente o None
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'created_by'],
                name='unique_template_per_user',
                condition=models.Q(created_by__isnull=False)
            ),
            # Para templates del sistema (created_by=None), único por nombre, tipo y servicio recomendado
            models.UniqueConstraint(
                fields=['name', 'template_type', 'recommended_service'],
                name='unique_system_template',
                condition=models.Q(created_by__isnull=True)
            ),
        ]
        indexes = [
            models.Index(fields=['template_type', 'is_public', 'is_active']),
            models.Index(fields=['recommended_service', 'is_public', 'is_active']),
            models.Index(fields=['created_by', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def get_rating(self):
        """Calcula el rating basado en upvotes/downvotes (0-5)"""
        total = self.upvotes + self.downvotes
        if total == 0:
            return 0.0
        return (self.upvotes / total) * 5.0
    
    def increment_usage(self):
        """Incrementa el contador de uso"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def is_accessible_by(self, user):
        """Verifica si un usuario puede acceder a esta plantilla"""
        return self.is_public or self.created_by == user


class UserPromptVote(models.Model):
    """Votos de usuarios sobre templates"""
    
    VOTE_TYPES = [
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prompt_votes',
        help_text='Usuario que vota'
    )
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text='Template votado'
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VOTE_TYPES,
        help_text='Tipo de voto'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha del voto'
    )
    
    class Meta:
        unique_together = [['user', 'template']]
        verbose_name = 'Voto de Template'
        verbose_name_plural = 'Votos de Templates'
        indexes = [
            models.Index(fields=['template', 'vote_type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name} ({self.get_vote_type_display()})"


class UserPromptFavorite(models.Model):
    """Favoritos de usuarios sobre templates"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_prompts',
        help_text='Usuario que marca como favorito'
    )
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        help_text='Template favorito'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha en que se marcó como favorito'
    )
    
    class Meta:
        unique_together = [['user', 'template']]
        verbose_name = 'Template Favorito'
        verbose_name_plural = 'Templates Favoritos'
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"