"""
EJEMPLO: Django Forms - Mejores Prácticas
==========================================

Reemplaza la validación manual en views.py con Forms robustos
"""

from django import forms
from django.core.exceptions import ValidationError
from core.models import Project, Video


# ====================
# PROJECT FORMS
# ====================

class ProjectForm(forms.ModelForm):
    """Form para crear/editar proyectos"""
    
    class Meta:
        model = Project
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del proyecto',
                'required': True
            })
        }
    
    def clean_name(self):
        """Validación personalizada para el nombre"""
        name = self.cleaned_data.get('name')
        
        # Validar longitud mínima
        if len(name) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres')
        
        # Validar que no exista un proyecto con el mismo nombre (case insensitive)
        if Project.objects.filter(name__iexact=name).exists():
            if not self.instance.pk:  # Solo si es creación, no edición
                raise ValidationError('Ya existe un proyecto con este nombre')
        
        return name.strip()


# ====================
# VIDEO FORMS - BASE
# ====================

class VideoBaseForm(forms.ModelForm):
    """Form base para todos los tipos de videos"""
    
    class Meta:
        model = Video
        fields = ['title', 'script', 'type']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del video'
            }),
            'script': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Guión del video'
            }),
            'type': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def clean_title(self):
        """Validar título"""
        title = self.cleaned_data.get('title')
        if len(title) < 3:
            raise ValidationError('El título debe tener al menos 3 caracteres')
        if len(title) > 255:
            raise ValidationError('El título no puede exceder 255 caracteres')
        return title.strip()
    
    def clean_script(self):
        """Validar script"""
        script = self.cleaned_data.get('script')
        if len(script) < 10:
            raise ValidationError('El guión debe tener al menos 10 caracteres')
        if len(script) > 10000:
            raise ValidationError('El guión es demasiado largo (máximo 10,000 caracteres)')
        return script.strip()


# ====================
# HEYGEN AVATAR V2 FORM
# ====================

class HeyGenAvatarV2Form(VideoBaseForm):
    """Form específico para videos HeyGen Avatar V2"""
    
    avatar_id = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Selecciona un avatar'
    )
    
    voice_id = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Selecciona una voz'
    )
    
    has_background = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    background_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/background.jpg'
        })
    )
    
    voice_speed = forms.FloatField(
        min_value=0.5,
        max_value=2.0,
        initial=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1'
        })
    )
    
    voice_pitch = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    
    voice_emotion = forms.ChoiceField(
        choices=[
            ('Excited', 'Excited'),
            ('Serious', 'Serious'),
            ('Friendly', 'Friendly'),
            ('Soothing', 'Soothing'),
        ],
        initial='Excited',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        """Validación cruzada de campos"""
        cleaned_data = super().clean()
        has_background = cleaned_data.get('has_background')
        background_url = cleaned_data.get('background_url')
        
        # Si tiene background, debe tener URL
        if has_background and not background_url:
            raise ValidationError({
                'background_url': 'Debes proporcionar una URL si activas el background'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Guardar con configuración en JSONField"""
        instance = super().save(commit=False)
        
        # Guardar configuración específica en el campo config
        instance.config = {
            'avatar_id': self.cleaned_data['avatar_id'],
            'voice_id': self.cleaned_data['voice_id'],
            'has_background': self.cleaned_data.get('has_background', False),
            'background_url': self.cleaned_data.get('background_url', ''),
            'voice_speed': self.cleaned_data.get('voice_speed', 1.0),
            'voice_pitch': self.cleaned_data.get('voice_pitch', 50),
            'voice_emotion': self.cleaned_data.get('voice_emotion', 'Excited'),
        }
        
        if commit:
            instance.save()
        
        return instance


# ====================
# HEYGEN AVATAR IV FORM
# ====================

class HeyGenAvatarIVForm(VideoBaseForm):
    """Form para Avatar IV (imagen personalizada)"""
    
    voice_id = forms.CharField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    image_source = forms.ChoiceField(
        choices=[
            ('upload', 'Subir nueva imagen'),
            ('existing', 'Usar imagen existente')
        ],
        initial='upload',
        widget=forms.RadioSelect()
    )
    
    avatar_image = forms.ImageField(
        required=False,
        help_text='Imagen del avatar (JPEG, PNG)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    existing_image_key = forms.CharField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    video_orientation = forms.ChoiceField(
        choices=[
            ('portrait', 'Vertical (9:16)'),
            ('landscape', 'Horizontal (16:9)')
        ],
        initial='portrait',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    fit = forms.ChoiceField(
        choices=[
            ('cover', 'Cubrir (recortar si es necesario)'),
            ('contain', 'Contener (mostrar todo)')
        ],
        initial='cover',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        """Validación según la fuente de imagen"""
        cleaned_data = super().clean()
        image_source = cleaned_data.get('image_source')
        avatar_image = cleaned_data.get('avatar_image')
        existing_image_key = cleaned_data.get('existing_image_key')
        
        if image_source == 'upload' and not avatar_image:
            raise ValidationError({
                'avatar_image': 'Debes subir una imagen'
            })
        
        if image_source == 'existing' and not existing_image_key:
            raise ValidationError({
                'existing_image_key': 'Debes seleccionar una imagen existente'
            })
        
        # Validar tamaño de imagen
        if avatar_image:
            if avatar_image.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError({
                    'avatar_image': 'La imagen no puede superar 10MB'
                })
        
        return cleaned_data


# ====================
# GEMINI VEO FORM
# ====================

class GeminiVeoForm(VideoBaseForm):
    """Form para Gemini Veo 2"""
    
    veo_model = forms.ChoiceField(
        choices=[
            ('veo-2.0-generate-001', 'Veo 2.0 Standard'),
            ('veo-2.0-generate-exp', 'Veo 2.0 Experimental'),
        ],
        initial='veo-2.0-generate-001',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    duration = forms.IntegerField(
        min_value=5,
        max_value=8,
        initial=8,
        help_text='Duración en segundos (5-8)',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    aspect_ratio = forms.ChoiceField(
        choices=[
            ('16:9', 'Horizontal (16:9)'),
            ('9:16', 'Vertical (9:16)'),
            ('1:1', 'Cuadrado (1:1)'),
        ],
        initial='16:9',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sample_count = forms.IntegerField(
        min_value=1,
        max_value=4,
        initial=1,
        help_text='Número de videos a generar (1-4)',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    negative_prompt = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Describe lo que NO quieres en el video'
        })
    )
    
    enhance_prompt = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Usar Gemini para mejorar el prompt',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    person_generation = forms.ChoiceField(
        choices=[
            ('allow_adult', 'Permitir personas adultas'),
            ('dont_allow', 'No permitir personas'),
        ],
        initial='allow_adult',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    compression_quality = forms.ChoiceField(
        choices=[
            ('optimized', 'Optimizado (recomendado)'),
            ('lossless', 'Sin pérdidas (mayor calidad)'),
        ],
        initial='optimized',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    seed = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=4294967295,
        help_text='Seed para reproducibilidad (opcional)',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    input_image = forms.ImageField(
        required=False,
        help_text='Imagen inicial para imagen-a-video (opcional)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )


# ====================
# FORM FACTORY
# ====================

def get_video_form_class(video_type: str):
    """Factory para obtener el Form correcto según el tipo de video"""
    form_classes = {
        'heygen_avatar_v2': HeyGenAvatarV2Form,
        'heygen_avatar_iv': HeyGenAvatarIVForm,
        'gemini_veo': GeminiVeoForm,
    }
    
    return form_classes.get(video_type, VideoBaseForm)


# ====================
# USO EN VIEWS
# ====================

"""
Ejemplo de uso en una vista:

from .forms import get_video_form_class

def video_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        video_type = request.POST.get('type')
        form_class = get_video_form_class(video_type)
        form = form_class(request.POST, request.FILES)
        
        if form.is_valid():
            video = form.save(commit=False)
            video.project = project
            video.save()
            
            messages.success(request, 'Video creado exitosamente')
            return redirect('core:video_detail', video_id=video.id)
        else:
            messages.error(request, 'Hay errores en el formulario')
    else:
        form = VideoBaseForm()
    
    return render(request, 'videos/create.html', {'form': form, 'project': project})
"""

