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

SCRIPT_STATUS = [
    ('pending', 'Pendiente'),
    ('processing', 'Procesando'),
    ('completed', 'Completado'),
    ('error', 'Error'),
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
        """Retorna las escenas del guión procesado"""
        return self.processed_data.get('scenes', [])

    @property
    def project_data(self):
        """Retorna los datos del proyecto del guión procesado"""
        return self.processed_data.get('project', {})
