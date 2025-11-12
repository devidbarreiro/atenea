from django.db import models
from django.utils import timezone

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
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'

    def __str__(self):
        return self.name

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
        related_name='videos'
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

    def mark_as_completed(self, gcs_path=None, metadata=None):
        """Marca el video como completado"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])

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
        related_name='images'
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

    def mark_as_completed(self, gcs_path=None, metadata=None):
        """Marca la imagen como completada"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])

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
        related_name='audios'
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

    def mark_as_completed(self, gcs_path=None, duration=None, metadata=None, alignment=None):
        """Marca el audio como completado"""
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
        related_name='scripts'
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
    
    def mark_preview_as_completed(self, gcs_path):
        """Marca el preview como completado"""
        self.preview_image_status = 'completed'
        self.preview_image_gcs_path = gcs_path
        self.save(update_fields=['preview_image_status', 'preview_image_gcs_path', 'updated_at'])
    
    def mark_preview_as_error(self, error_message):
        """Marca el preview con error"""
        self.preview_image_status = 'error'
        self.preview_image_error = error_message
        self.save(update_fields=['preview_image_status', 'preview_image_error', 'updated_at'])
    
    def mark_video_as_processing(self):
        """Marca el video como procesando"""
        self.video_status = 'processing'
        self.save(update_fields=['video_status', 'updated_at'])

    def mark_video_as_completed(self, gcs_path=None, metadata=None):
        """Marca el video como completado"""
        self.video_status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.video_gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['video_status', 'completed_at', 'video_gcs_path', 'metadata', 'updated_at'])

    def mark_video_as_error(self, error_message):
        """Marca el video con error"""
        self.video_status = 'error'
        self.error_message = error_message
        self.save(update_fields=['video_status', 'error_message', 'updated_at'])
    
    def mark_audio_as_processing(self):
        """Marca el audio como procesando"""
        self.audio_status = 'processing'
        self.save(update_fields=['audio_status', 'updated_at'])
    
    def mark_audio_as_completed(self, gcs_path: str, duration: float = None, voice_id: str = None, voice_name: str = None):
        """Marca el audio como completado"""
        self.audio_status = 'completed'
        self.audio_gcs_path = gcs_path
        if duration:
            self.audio_duration = duration
        if voice_id:
            self.audio_voice_id = voice_id
        if voice_name:
            self.audio_voice_name = voice_name
        self.save(update_fields=['audio_status', 'audio_gcs_path', 'audio_duration', 'audio_voice_id', 'audio_voice_name', 'updated_at'])
    
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
        help_text='Proyecto al que pertenece esta música'
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
