"""
Formularios Django para validación de datos
"""

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Project, Video, VIDEO_TYPES


class ProjectForm(forms.ModelForm):
    """Formulario para crear/editar proyectos"""
    
    class Meta:
        model = Project
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del proyecto',
                'required': True,
            })
        }
        labels = {
            'name': 'Nombre del Proyecto'
        }
        help_texts = {
            'name': 'Ingresa un nombre descriptivo para tu proyecto'
        }


class VideoBaseForm(forms.Form):
    """Formulario base para todos los tipos de videos"""
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Título del video',
            'required': True,
        }),
        label='Título',
        help_text='Nombre descriptivo para identificar el video'
    )
    
    script = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Escribe el guión o prompt para tu video...',
            'rows': 5,
            'required': True,
        }),
        label='Guión / Prompt',
        help_text='El texto que se usará para generar el video'
    )
    
    type = forms.ChoiceField(
        choices=VIDEO_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        }),
        label='Tipo de Video',
        help_text='Selecciona la plataforma de generación'
    )


class HeyGenAvatarV2Form(VideoBaseForm):
    """Formulario para videos HeyGen Avatar V2"""
    
    avatar_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ID del avatar',
            'required': True,
        }),
        label='Avatar ID',
        help_text='Identificador del avatar de HeyGen'
    )
    
    voice_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ID de la voz',
            'required': True,
        }),
        label='Voice ID',
        help_text='Identificador de la voz de HeyGen'
    )
    
    has_background = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Incluir Fondo',
        help_text='Agregar imagen de fondo al video'
    )
    
    background_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://ejemplo.com/fondo.jpg',
        }),
        label='URL del Fondo',
        help_text='URL de la imagen de fondo (solo si "Incluir Fondo" está marcado)'
    )
    
    voice_speed = forms.FloatField(
        initial=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(2.0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0.5',
            'max': '2.0',
        }),
        label='Velocidad de Voz',
        help_text='Velocidad de la voz (0.5 = lento, 2.0 = rápido)'
    )
    
    voice_pitch = forms.IntegerField(
        initial=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
        }),
        label='Tono de Voz',
        help_text='Tono de la voz (0-100)'
    )
    
    voice_emotion = forms.ChoiceField(
        choices=[
            ('Excited', 'Emocionado'),
            ('Serious', 'Serio'),
            ('Friendly', 'Amigable'),
            ('Soothing', 'Calmado'),
            ('Broadcaster', 'Locutor'),
        ],
        initial='Excited',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Emoción de Voz',
        help_text='Emoción que transmitirá la voz'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        has_background = cleaned_data.get('has_background')
        background_url = cleaned_data.get('background_url')
        
        if has_background and not background_url:
            raise forms.ValidationError(
                'Debes proporcionar una URL de fondo si "Incluir Fondo" está marcado'
            )
        
        return cleaned_data


class HeyGenAvatarIVForm(VideoBaseForm):
    """Formulario para videos HeyGen Avatar IV (Image Video)"""
    
    voice_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ID de la voz',
            'required': True,
        }),
        label='Voice ID',
        help_text='Identificador de la voz de HeyGen'
    )
    
    image_source = forms.ChoiceField(
        choices=[
            ('upload', 'Subir Nueva Imagen'),
            ('existing', 'Usar Imagen Existente'),
        ],
        initial='upload',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        label='Fuente de Imagen',
        help_text='Selecciona si subirás una nueva imagen o usarás una existente'
    )
    
    avatar_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        label='Imagen del Avatar',
        help_text='Sube una imagen para crear el avatar (solo si seleccionaste "Subir Nueva Imagen")'
    )
    
    existing_image_key = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ID de la imagen existente',
        }),
        label='ID de Imagen Existente',
        help_text='ID de la imagen en HeyGen (solo si seleccionaste "Usar Imagen Existente")'
    )
    
    video_orientation = forms.ChoiceField(
        choices=[
            ('portrait', 'Vertical (Portrait)'),
            ('landscape', 'Horizontal (Landscape)'),
        ],
        initial='portrait',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Orientación del Video',
        help_text='Orientación del video resultante'
    )
    
    fit = forms.ChoiceField(
        choices=[
            ('cover', 'Cubrir (Cover)'),
            ('contain', 'Contener (Contain)'),
        ],
        initial='cover',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Ajuste de Imagen',
        help_text='Cómo se ajusta la imagen en el video'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        image_source = cleaned_data.get('image_source')
        avatar_image = cleaned_data.get('avatar_image')
        existing_image_key = cleaned_data.get('existing_image_key')
        
        if image_source == 'upload' and not avatar_image:
            raise forms.ValidationError(
                'Debes subir una imagen si seleccionaste "Subir Nueva Imagen"'
            )
        
        if image_source == 'existing' and not existing_image_key:
            raise forms.ValidationError(
                'Debes proporcionar el ID de una imagen existente'
            )
        
        return cleaned_data


class GeminiVeoVideoForm(VideoBaseForm):
    """Formulario para videos Gemini Veo 2"""
    
    veo_model = forms.ChoiceField(
        choices=[
            ('veo-2.0-generate-001', 'Veo 2.0'),
        ],
        initial='veo-2.0-generate-001',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Modelo Veo',
        help_text='Versión del modelo Gemini Veo'
    )
    
    duration = forms.IntegerField(
        initial=8,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '10',
        }),
        label='Duración (segundos)',
        help_text='Duración del video en segundos (1-10)'
    )
    
    aspect_ratio = forms.ChoiceField(
        choices=[
            ('16:9', '16:9 (Horizontal)'),
            ('9:16', '9:16 (Vertical)'),
            ('1:1', '1:1 (Cuadrado)'),
        ],
        initial='16:9',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Aspect Ratio',
        help_text='Relación de aspecto del video'
    )
    
    sample_count = forms.IntegerField(
        initial=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '4',
        }),
        label='Cantidad de Muestras',
        help_text='Número de variaciones a generar (1-4)'
    )
    
    negative_prompt = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Elementos a evitar en el video...',
            'rows': 3,
        }),
        label='Prompt Negativo',
        help_text='Opcional: Describe qué NO quieres ver en el video'
    )
    
    enhance_prompt = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Mejorar Prompt Automáticamente',
        help_text='Permite que Gemini mejore tu prompt para mejores resultados'
    )
    
    person_generation = forms.ChoiceField(
        choices=[
            ('allow_adult', 'Permitir Adultos'),
            ('dont_allow', 'No Permitir Personas'),
        ],
        initial='allow_adult',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Generación de Personas',
        help_text='Controla si se permiten personas en el video'
    )
    
    compression_quality = forms.ChoiceField(
        choices=[
            ('optimized', 'Optimizada'),
            ('high', 'Alta'),
        ],
        initial='optimized',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Calidad de Compresión',
        help_text='Calidad del video resultante'
    )
    
    seed = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Opcional: número semilla',
        }),
        label='Semilla (Seed)',
        help_text='Opcional: Número para reproducibilidad de resultados'
    )
    
    # Imagen inicial (imagen-a-video)
    input_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        label='Imagen Inicial',
        help_text='Opcional: Imagen de inicio para generación imagen-a-video'
    )
    
    # Imágenes de referencia
    reference_image_1 = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        label='Imagen de Referencia 1',
        help_text='Opcional: Primera imagen de referencia para estilo/personajes'
    )
    
    reference_type_1 = forms.ChoiceField(
        choices=[
            ('asset', 'Recurso/Asset'),
            ('style', 'Estilo'),
            ('character', 'Personaje'),
        ],
        initial='asset',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Tipo de Referencia 1'
    )
    
    reference_image_2 = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        label='Imagen de Referencia 2',
        help_text='Opcional: Segunda imagen de referencia'
    )
    
    reference_type_2 = forms.ChoiceField(
        choices=[
            ('asset', 'Recurso/Asset'),
            ('style', 'Estilo'),
            ('character', 'Personaje'),
        ],
        initial='asset',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Tipo de Referencia 2'
    )
    
    reference_image_3 = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        label='Imagen de Referencia 3',
        help_text='Opcional: Tercera imagen de referencia'
    )
    
    reference_type_3 = forms.ChoiceField(
        choices=[
            ('asset', 'Recurso/Asset'),
            ('style', 'Estilo'),
            ('character', 'Personaje'),
        ],
        initial='asset',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Tipo de Referencia 3'
    )

