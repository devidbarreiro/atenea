from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Constantes para choices
VIDEO_TYPES = [
    ('heygen_avatar_v2', 'HeyGen Avatar V2'),
    ('heygen_avatar_iv', 'HeyGen Avatar IV'),
    ('gemini_veo', 'Gemini Veo'),
    ('sora', 'OpenAI Sora'),
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
]


class Project(models.Model):
    """Modelo para proyectos que agrupan videos"""
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
    type = models.CharField(max_length=20, choices=VIDEO_TYPES)
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
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.created_by:
            try:
                from core.services.credits import CreditService
                CreditService.deduct_credits_for_video(self.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para video {self.id}: {e}")
                # No fallar la operación si falla el cobro

    def mark_as_error(self, error_message):
        """Marca el video con error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Image(models.Model):
    """Modelo para imágenes generadas por IA (Gemini)"""
    
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
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.created_by:
            try:
                from core.services.credits import CreditService
                CreditService.deduct_credits_for_image(self.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para imagen {self.id}: {e}")
                # No fallar la operación si falla el cobro

    def mark_as_error(self, error_message):
        """Marca la imagen con error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Audio(models.Model):
    """Modelo para audios generados por ElevenLabs TTS"""
    
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
    
    # Contenido
    text = models.TextField(help_text='Texto para convertir a voz')
    
    # Configuración de voz
    voice_id = models.CharField(
        max_length=100,
        help_text='ID de la voz en ElevenLabs'
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
        self.save(update_fields=[
            'status', 'completed_at', 'gcs_path', 'duration', 
            'metadata', 'alignment', 'updated_at'
        ])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.created_by:
            try:
                from core.services.credits import CreditService
                CreditService.deduct_credits_for_audio(self.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para audio {self.id}: {e}")
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
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['video_status', 'completed_at', 'video_gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.script.created_by:
            try:
                from core.services.credits import CreditService
                CreditService.deduct_credits_for_scene_video(self.script.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para video de escena {self.id}: {e}")
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
        self.save(update_fields=['audio_status', 'audio_gcs_path', 'audio_duration', 'audio_voice_id', 'audio_voice_name', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.script.created_by:
            try:
                from core.services.credits import CreditService
                # Calcular costo basado en script_text de la escena
                cost = CreditService.estimate_audio_cost(self.script_text)
                if cost > 0:
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
            except Exception as e:
                logger.error(f"Error al cobrar créditos para audio de escena {self.id}: {e}")
                # No fallar la operación si falla el cobro
    
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


class Music(models.Model):
    """
    Modelo para almacenar pistas de música generadas con ElevenLabs Music
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='music_tracks',
        null=True,
        blank=True,
        help_text='Proyecto al que pertenece (opcional)'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='music_tracks',
        null=True,
        blank=True,
        help_text='Usuario que creó esta música'
    )
    name = models.CharField(
        max_length=255,
        help_text='Nombre descriptivo de la pista musical'
    )
    prompt = models.TextField(
        help_text='Prompt usado para generar la música'
    )
    duration_ms = models.IntegerField(
        help_text='Duración de la música en milisegundos'
    )
    
    # Composition Plan (opcional, si se usó)
    composition_plan = models.JSONField(
        null=True,
        blank=True,
        help_text='Plan de composición detallado (JSON) usado para generar la música'
    )
    
    # Metadata de la canción generada
    song_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text='Metadatos de la canción generada (tempo, key, mood, etc.)'
    )
    
    # Almacenamiento en GCS
    gcs_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Path en GCS donde está almacenada la música'
    )
    
    # Estado de generación
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('generating', 'Generando'),
        ('completed', 'Completado'),
        ('error', 'Error'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(
        null=True,
        blank=True
    )
    
    # Campos de ElevenLabs
    elevenlabs_track_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='ID del track en ElevenLabs (si aplica)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora en que se generó la música'
    )
    
    class Meta:
        db_table = 'music'
        ordering = ['-created_at']
        verbose_name = 'Música'
        verbose_name_plural = 'Músicas'
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"
    
    @property
    def duration_sec(self):
        """Retorna la duración en segundos"""
        if self.duration_ms:
            return self.duration_ms / 1000.0
        return None
    
    def mark_as_generating(self):
        """Marca la música como en proceso de generación"""
        self.status = 'generating'
        self.error_message = None
        self.save(update_fields=['status', 'error_message', 'updated_at'])
    
    def mark_as_completed(self, gcs_path: str, song_metadata: dict = None):
        """Marca la música como completada"""
        from django.utils import timezone
        self.status = 'completed'
        self.gcs_path = gcs_path
        if song_metadata:
            self.song_metadata = song_metadata
        self.generated_at = timezone.now()
        self.save(update_fields=['status', 'gcs_path', 'song_metadata', 'generated_at', 'updated_at'])
    
    def mark_as_error(self, error_message: str):
        """Marca la música como error"""
        self.status = 'error'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])
    
    def duration_seconds(self):
        """Retorna la duración en segundos de forma segura"""
        if self.duration_ms is None:
            return 0
        return round(self.duration_ms / 1000.0, 2)


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