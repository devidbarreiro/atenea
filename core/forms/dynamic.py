"""
Sistema de formularios dinámicos basado en MODEL_CAPABILITIES
Genera formularios automáticamente según las capacidades del modelo
"""
import logging
from django import forms
from django.core.exceptions import ValidationError
from core.ai_services.model_config import MODEL_CAPABILITIES, get_model_capabilities

logger = logging.getLogger(__name__)


class DynamicVideoForm(forms.Form):
    """Formulario dinámico que se adapta según el modelo seleccionado"""
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Mi video generado con IA',
        }),
        label='Título',
        required=True
    )
    
    model_id = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'hx-get': '/videos/form-fields/',
            'hx-target': '#dynamic-fields',
            'hx-swap': 'innerHTML',
            'hx-trigger': 'change',
        }),
        label='Modelo',
        required=True
    )
    
    script = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none',
            'rows': 5,
            'placeholder': 'Describe el video que quieres generar...',
        }),
        label='Prompt / Guión',
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        item_type = kwargs.pop('item_type', 'video')
        super().__init__(*args, **kwargs)
        
        # Cargar modelos disponibles
        models = self._get_available_models(item_type)
        self.fields['model_id'].choices = models
        
        # Si hay un model_id inicial, generar campos dinámicos
        initial_model_id = self.initial.get('model_id') or (self.data.get('model_id') if self.data else None)
        if initial_model_id:
            self._add_dynamic_fields(initial_model_id)
            # Personalizar campo script según el modelo
            self._customize_script_field(initial_model_id)
    
    def _get_available_models(self, item_type):
        """Obtiene lista de modelos disponibles para el tipo especificado"""
        choices = [('', 'Selecciona un modelo')]
        
        for model_id, model_config in MODEL_CAPABILITIES.items():
            if model_config.get('type') == item_type:
                name = model_config.get('name', model_id)
                description = model_config.get('description', '')
                label = f"{name}"
                if description:
                    label += f" - {description}"
                choices.append((model_id, label))
        
        return choices
    
    def _add_dynamic_fields(self, model_id):
        """Añade campos dinámicos según las capacidades del modelo"""
        capabilities = get_model_capabilities(model_id)
        if not capabilities:
            return
        
        supports = capabilities.get('supports', {})
        
        # Duración
        if supports.get('duration'):
            duration_config = supports['duration']
            if duration_config.get('fixed'):
                self.fields['duration'] = forms.IntegerField(
                    initial=duration_config['fixed'],
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                        'readonly': True,
                    }),
                    label='Duración',
                    required=False
                )
            elif duration_config.get('options'):
                self.fields['duration'] = forms.ChoiceField(
                    choices=[(opt, f'{opt} segundos') for opt in duration_config['options']],
                    initial=duration_config['options'][0] if duration_config['options'] else None,
                    widget=forms.Select(attrs={
                        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                    }),
                    label='Duración',
                    required=True
                )
            elif duration_config.get('min') and duration_config.get('max'):
                choices = [(i, f'{i} segundos') for i in range(duration_config['min'], duration_config['max'] + 1)]
                self.fields['duration'] = forms.ChoiceField(
                    choices=choices,
                    initial=duration_config.get('min'),
                    widget=forms.Select(attrs={
                        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                    }),
                    label='Duración',
                    required=True
                )
        
        # Aspect Ratio
        if supports.get('aspect_ratio'):
            aspect_ratios = supports['aspect_ratio']
            labels = {
                '1:1': '1:1 (Cuadrado)',
                '16:9': '16:9 (Horizontal)',
                '9:16': '9:16 (Vertical)',
                '2:3': '2:3 (Vertical)',
                '3:2': '3:2 (Horizontal)',
                '3:4': '3:4 (Vertical)',
                '4:3': '4:3 (Horizontal)',
                '4:5': '4:5 (Vertical)',
                '5:4': '5:4 (Horizontal)',
                '21:9': '21:9 (Ultra Wide)',
            }
            choices = [(ar, labels.get(ar, ar)) for ar in aspect_ratios]
            self.fields['aspect_ratio'] = forms.ChoiceField(
                choices=choices,
                initial=aspect_ratios[0] if aspect_ratios else None,
                widget=forms.Select(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                }),
                label='Aspect Ratio',
                required=True
            )
        
        # Resolución
        if supports.get('resolution') and isinstance(supports['resolution'], list):
            choices = [(res, res.upper()) for res in supports['resolution']]
            self.fields['resolution'] = forms.ChoiceField(
                choices=choices,
                initial=supports['resolution'][0] if supports['resolution'] else None,
                widget=forms.Select(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                }),
                label='Resolución',
                required=False
            )
        
        # Audio
        if supports.get('audio'):
            self.fields['generate_audio'] = forms.BooleanField(
                required=False,
                widget=forms.CheckboxInput(attrs={
                    'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
                }),
                label='Generar audio',
            )
        
        # Referencias
        references = supports.get('references', {})
        if references.get('start_image'):
            self.fields['start_image'] = forms.ImageField(
                widget=forms.FileInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700',
                    'accept': 'image/*',
                }),
                label='Imagen de Inicio',
                required=False
            )
        
        if references.get('end_image'):
            self.fields['end_image'] = forms.ImageField(
                widget=forms.FileInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700',
                    'accept': 'image/*',
                }),
                label='Imagen Final',
                required=False
            )
        
        if references.get('style_image'):
            self.fields['style_image'] = forms.ImageField(
                widget=forms.FileInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700',
                    'accept': 'image/*',
                }),
                label='Imagen de Estilo',
                required=False
            )
        
        if references.get('asset_image'):
            self.fields['asset_image'] = forms.ImageField(
                widget=forms.FileInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700',
                    'accept': 'image/*',
                }),
                label='Imagen de Recurso (Asset)',
                required=False
            )
        
        # Negative Prompt
        if supports.get('negative_prompt'):
            self.fields['negative_prompt'] = forms.CharField(
                required=False,
                widget=forms.Textarea(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-none',
                    'rows': 3,
                    'placeholder': 'Elementos a evitar en el video...',
                }),
                label='Prompt Negativo',
            )
        
        # Seed
        if supports.get('seed'):
            self.fields['seed'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=4294967295,
                widget=forms.NumberInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                    'placeholder': 'Opcional: número para reproducibilidad',
                }),
                label='Seed (Semilla)',
            )
        
        # Modo (para Kling)
        if supports.get('modes'):
            choices = [(mode, mode.upper()) for mode in supports['modes']]
            self.fields['mode'] = forms.ChoiceField(
                choices=choices,
                initial=supports['modes'][0] if supports['modes'] else None,
                widget=forms.Select(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                }),
                label='Modo',
                required=False
            )
        
        # Autor (para Manim Quote)
        if supports.get('author'):
            self.fields['author'] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                    'placeholder': 'Nombre del autor (opcional)',
                }),
                label='Autor',
            )
        
        # Calidad (para Manim Quote)
        if supports.get('quality'):
            quality_labels = {
                'l': 'Baja (480p)',
                'm': 'Media (720p)',
                'h': 'Alta (1080p)',
                'k': '4K Máxima (2160p)',
            }
            choices = [(q, quality_labels.get(q, q.upper())) for q in supports['quality']]
            self.fields['quality'] = forms.ChoiceField(
                choices=choices,
                initial='k',
                widget=forms.Select(attrs={
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                }),
                label='Calidad',
                required=False
            )
    
    def _customize_script_field(self, model_id):
        """Personaliza el campo script según el modelo"""
        if model_id == 'manim-quote':
            # Para Manim Quote, cambiar label y placeholder
            self.fields['script'].label = 'Texto de la cita'
            self.fields['script'].widget.attrs['placeholder'] = 'Escribe el texto de la cita que quieres animar...'
            self.fields['script'].widget.attrs['rows'] = 4
    
    def clean(self):
        """
        Valida los campos según las capacidades del modelo seleccionado
        """
        cleaned_data = super().clean()
        model_id = cleaned_data.get('model_id')
        
        if not model_id:
            # Si no hay modelo seleccionado, no podemos validar campos dinámicos
            return cleaned_data
        
        # Obtener capacidades del modelo
        capabilities = get_model_capabilities(model_id)
        if not capabilities:
            logger.warning(f"No se encontraron capacidades para el modelo: {model_id}")
            return cleaned_data
        
        supports = capabilities.get('supports', {})
        
        # Validar duration según el modelo
        if 'duration' in cleaned_data and supports.get('duration'):
            duration_value = cleaned_data.get('duration')
            if duration_value:
                try:
                    # Convertir a int si viene como string desde ChoiceField
                    duration_int = int(duration_value) if isinstance(duration_value, str) else duration_value
                    duration_config = supports['duration']
                    
                    # Validar según tipo de configuración
                    if duration_config.get('fixed'):
                        if duration_int != duration_config['fixed']:
                            raise ValidationError(
                                f"La duración debe ser {duration_config['fixed']} segundos para este modelo"
                            )
                    elif duration_config.get('options'):
                        if duration_int not in duration_config['options']:
                            raise ValidationError(
                                f"La duración debe ser una de: {', '.join(map(str, duration_config['options']))} segundos"
                            )
                    elif duration_config.get('min') and duration_config.get('max'):
                        if not (duration_config['min'] <= duration_int <= duration_config['max']):
                            raise ValidationError(
                                f"La duración debe estar entre {duration_config['min']} y {duration_config['max']} segundos"
                            )
                    
                    cleaned_data['duration'] = duration_int
                except (ValueError, TypeError):
                    raise ValidationError("La duración debe ser un número válido")
        
        # Validar aspect_ratio según el modelo
        if 'aspect_ratio' in cleaned_data and supports.get('aspect_ratio'):
            aspect_ratio = cleaned_data.get('aspect_ratio')
            if aspect_ratio:
                supported_ratios = supports['aspect_ratio']
                if aspect_ratio not in supported_ratios:
                    raise ValidationError(
                        f"El aspect ratio '{aspect_ratio}' no está soportado. Opciones válidas: {', '.join(supported_ratios)}"
                    )
        
        # Validar resolution según el modelo
        if 'resolution' in cleaned_data and supports.get('resolution'):
            resolution = cleaned_data.get('resolution')
            if resolution:
                supported_resolutions = supports['resolution']
                if isinstance(supported_resolutions, list) and resolution not in supported_resolutions:
                    raise ValidationError(
                        f"La resolución '{resolution}' no está soportada. Opciones válidas: {', '.join(supported_resolutions)}"
                    )
        
        # Validar campos específicos de modelo (HeyGen)
        if model_id in ['heygen-avatar-v2', 'heygen-avatar-iv']:
            # Validar avatar_id (puede venir de select o input text)
            avatar_id = cleaned_data.get('avatar_id')
            if not avatar_id:
                # Solo requerir si el modelo lo necesita
                if model_id == 'heygen-avatar-v2':
                    raise ValidationError({
                        'avatar_id': 'El avatar es requerido para HeyGen Avatar V2'
                    })
                elif model_id == 'heygen-avatar-iv':
                    avatar_image_id = cleaned_data.get('avatar_image_id')
                    if not avatar_image_id:
                        raise ValidationError({
                            'avatar_image_id': 'La imagen de avatar es requerida para HeyGen Avatar IV'
                        })
            
            # Validar voice_id
            voice_id = cleaned_data.get('voice_id')
            if not voice_id:
                raise ValidationError({
                    'voice_id': 'La voz es requerida para HeyGen'
                })
            
            # Si tenemos los datos de HeyGen disponibles, validar que los IDs existan
            # Nota: Esto requiere acceso a los datos de get_model_specific_fields
            # Por ahora solo validamos que estén presentes
        
        # Validar seed si está presente
        if 'seed' in cleaned_data:
            seed = cleaned_data.get('seed')
            if seed is not None:
                try:
                    seed_int = int(seed) if not isinstance(seed, int) else seed
                    if seed_int < 0 or seed_int > 4294967295:
                        raise ValidationError({
                            'seed': 'El seed debe estar entre 0 y 4294967295'
                        })
                    cleaned_data['seed'] = seed_int
                except (ValueError, TypeError):
                    raise ValidationError({
                        'seed': 'El seed debe ser un número válido'
                    })
        
        # Validar mode si está presente (para Kling)
        if 'mode' in cleaned_data and supports.get('modes'):
            mode = cleaned_data.get('mode')
            if mode:
                supported_modes = supports['modes']
                if mode not in supported_modes:
                    raise ValidationError({
                        'mode': f"El modo '{mode}' no está soportado. Opciones válidas: {', '.join(supported_modes)}"
                    })
        
        return cleaned_data


def get_model_specific_fields(model_id, service):
    """
    Retorna campos específicos del modelo que requieren datos externos
    (ej: avatares de HeyGen, voces, etc.)
    
    Returns:
        dict con estructura: {
            'fields': [lista de campos HTML],
            'data': {datos necesarios para poblar campos}
        }
    """
    from core.ai_services.heygen import HeyGenClient
    from core.ai_services.elevenlabs import ElevenLabsClient
    from django.conf import settings
    
    fields = []
    data = {}
    
    # HeyGen Avatar V2
    if model_id == 'heygen-avatar-v2':
        try:
            api_key = getattr(settings, 'HEYGEN_API_KEY', None)
            if not api_key:
                raise ValueError('HEYGEN_API_KEY no está configurada en settings')
            client = HeyGenClient(api_key=api_key)
            avatars = client.list_avatars()
            voices = client.list_voices()
            
            logger.info(f"HeyGen V2: Cargados {len(avatars)} avatares y {len(voices)} voces")
            
            data['avatars'] = avatars
            data['voices'] = voices
            
            # Generar HTML para avatar select
            avatar_options = '<option value="">Selecciona un avatar</option>'
            for avatar in avatars:
                avatar_id = avatar.get("avatar_id") or avatar.get("id")
                avatar_name = avatar.get("avatar_name") or avatar.get("name") or avatar_id
                avatar_options += f'<option value="{avatar_id}">{avatar_name}</option>'
            
            fields.append({
                'name': 'avatar_id',
                'label': 'Avatar',
                'required': True,
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            AVATAR <span class="text-red-500">*</span>
                        </label>
                        <select name="avatar_id" required class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                            {avatar_options}
                        </select>
                    </div>
                '''
            })
            
            # Generar HTML para voice select
            voice_options = '<option value="">Selecciona una voz</option>'
            for voice in voices:
                voice_id = voice.get('voice_id') or voice.get('id')
                voice_name = voice.get('name', voice_id)
                voice_lang = voice.get('language', '')
                label = f"{voice_name}"
                if voice_lang:
                    label += f" ({voice_lang})"
                voice_options += f'<option value="{voice_id}">{label}</option>'
            
            fields.append({
                'name': 'voice_id',
                'label': 'Voz',
                'required': True,
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            VOZ <span class="text-red-500">*</span>
                        </label>
                        <select name="voice_id" required class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                            {voice_options}
                        </select>
                    </div>
                '''
            })
        except Exception as e:
            logger.error(f"Error cargando datos de HeyGen V2: {e}", exc_info=True)
            # Mostrar advertencia y permitir entrada manual
            error_msg = str(e)
            if 'API_KEY' in error_msg:
                error_msg = 'API Key no configurada'
            elif 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                error_msg = 'Error de conexión con HeyGen API'
            else:
                error_msg = 'No se pudieron cargar opciones automáticamente'
            
            fields.append({
                'name': 'heygen_warning',
                'label': 'Advertencia',
                'required': False,
                'html': f'''
                    <div class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p class="text-sm text-yellow-800 font-semibold mb-2">
                            ⚠️ {error_msg}
                        </p>
                        <p class="text-xs text-yellow-700 mb-3">
                            Puedes ingresar los IDs manualmente si los conoces:
                        </p>
                    </div>
                '''
            })
            
            # Campos de entrada manual (opcionales cuando hay error)
            fields.append({
                'name': 'avatar_id',
                'label': 'Avatar ID',
                'required': False,  # Hacer opcional cuando hay error
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            AVATAR ID <span class="text-yellow-600">(manual)</span>
                        </label>
                        <input type="text" 
                               name="avatar_id" 
                               placeholder="Ej: avatar_123456" 
                               class="w-full px-3 py-2.5 text-sm border border-yellow-300 rounded-lg bg-white focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500 transition-all">
                        <p class="mt-1 text-xs text-gray-500">Ingresa el ID del avatar si lo conoces</p>
                    </div>
                '''
            })
            
            fields.append({
                'name': 'voice_id',
                'label': 'Voice ID',
                'required': False,  # Hacer opcional cuando hay error
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            VOZ ID <span class="text-yellow-600">(manual)</span>
                        </label>
                        <input type="text" 
                               name="voice_id" 
                               placeholder="Ej: voice_123456" 
                               class="w-full px-3 py-2.5 text-sm border border-yellow-300 rounded-lg bg-white focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500 transition-all">
                        <p class="mt-1 text-xs text-gray-500">Ingresa el ID de la voz si lo conoces</p>
                    </div>
                '''
            })
    
    # HeyGen Avatar IV
    elif model_id == 'heygen-avatar-iv':
        try:
            api_key = getattr(settings, 'HEYGEN_API_KEY', None)
            if not api_key:
                raise ValueError('HEYGEN_API_KEY no está configurada en settings')
            client = HeyGenClient(api_key=api_key)
            # Listar assets de imagen usando el parámetro file_type
            image_assets = client.list_assets(file_type='image')
            voices = client.list_voices()
            
            logger.info(f"HeyGen IV: Cargados {len(image_assets)} assets de imagen y {len(voices)} voces")
            
            data['image_assets'] = image_assets
            data['voices'] = voices
            
            # Generar HTML para avatar image select
            image_asset_options = '<option value="">Selecciona una imagen de avatar</option>'
            for asset in image_assets:
                asset_id = asset.get("asset_id") or asset.get("id")
                asset_name = asset.get("asset_name") or asset.get("name") or asset_id
                image_asset_options += f'<option value="{asset_id}">{asset_name}</option>'
            
            fields.append({
                'name': 'avatar_image_id',
                'label': 'Imagen de Avatar',
                'required': True,
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            IMAGEN DE AVATAR <span class="text-red-500">*</span>
                        </label>
                        <select name="avatar_image_id" required class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                            {image_asset_options}
                        </select>
                    </div>
                '''
            })
            
            voice_options = '<option value="">Selecciona una voz</option>'
            for voice in voices:
                voice_id = voice.get('voice_id') or voice.get('id')
                voice_name = voice.get('name', voice_id)
                voice_lang = voice.get('language', '')
                label = f"{voice_name}"
                if voice_lang:
                    label += f" ({voice_lang})"
                voice_options += f'<option value="{voice_id}">{label}</option>'
            
            fields.append({
                'name': 'voice_id',
                'label': 'Voz',
                'required': True,
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            VOZ <span class="text-red-500">*</span>
                        </label>
                        <select name="voice_id" required class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                            {voice_options}
                        </select>
                    </div>
                '''
            })
        except Exception as e:
            logger.error(f"Error cargando datos de HeyGen IV: {e}", exc_info=True)
            # Mostrar advertencia y permitir entrada manual
            error_msg = str(e)
            if 'API_KEY' in error_msg:
                error_msg = 'API Key no configurada'
            elif 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                error_msg = 'Error de conexión con HeyGen API'
            else:
                error_msg = 'No se pudieron cargar opciones automáticamente'
            
            fields.append({
                'name': 'heygen_warning',
                'label': 'Advertencia',
                'required': False,
                'html': f'''
                    <div class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p class="text-sm text-yellow-800 font-semibold mb-2">
                            ⚠️ {error_msg}
                        </p>
                        <p class="text-xs text-yellow-700 mb-3">
                            Puedes ingresar los IDs manualmente si los conoces:
                        </p>
                    </div>
                '''
            })
            
            # Campos de entrada manual (opcionales cuando hay error)
            fields.append({
                'name': 'avatar_image_id',
                'label': 'Avatar Image ID',
                'required': False,  # Hacer opcional cuando hay error
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            IMAGEN DE AVATAR ID <span class="text-yellow-600">(manual)</span>
                        </label>
                        <input type="text" 
                               name="avatar_image_id" 
                               placeholder="Ej: asset_123456" 
                               class="w-full px-3 py-2.5 text-sm border border-yellow-300 rounded-lg bg-white focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500 transition-all">
                        <p class="mt-1 text-xs text-gray-500">Ingresa el ID del asset de imagen si lo conoces</p>
                    </div>
                '''
            })
            
            fields.append({
                'name': 'voice_id',
                'label': 'Voice ID',
                'required': False,  # Hacer opcional cuando hay error
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            VOZ ID <span class="text-yellow-600">(manual)</span>
                        </label>
                        <input type="text" 
                               name="voice_id" 
                               placeholder="Ej: voice_123456" 
                               class="w-full px-3 py-2.5 text-sm border border-yellow-300 rounded-lg bg-white focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500 transition-all">
                        <p class="mt-1 text-xs text-gray-500">Ingresa el ID de la voz si lo conoces</p>
                    </div>
                '''
            })
    
    # ElevenLabs TTS (para audios)
    elif model_id == 'elevenlabs' or model_id == 'elevenlabs-tts':
        try:
            api_key = getattr(settings, 'ELEVENLABS_API_KEY', None)
            if not api_key:
                raise ValueError('ELEVENLABS_API_KEY no está configurada en settings')
            client = ElevenLabsClient(api_key=api_key)
            voices = client.list_voices()
            
            logger.info(f"ElevenLabs: Cargadas {len(voices)} voces")
            
            data['voices'] = voices
            
            # Generar HTML para voice select
            voice_options = '<option value="">Selecciona una voz</option>'
            for voice in voices:
                voice_id = voice.get('voice_id') or voice.get('id')
                voice_name = voice.get('name', voice_id)
                voice_category = voice.get('category', '')
                labels = voice.get('labels', {})
                accent = labels.get('accent', '')
                gender = labels.get('gender', '')
                
                label = f"{voice_name}"
                details = []
                if accent:
                    details.append(accent)
                if gender:
                    details.append(gender)
                if voice_category:
                    details.append(voice_category)
                if details:
                    label += f" ({', '.join(details)})"
                    
                voice_options += f'<option value="{voice_id}">{label}</option>'
            
            fields.append({
                'name': 'voice_id',
                'label': 'Voz',
                'required': True,
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            VOZ <span class="text-red-500">*</span>
                        </label>
                        <select name="voice_id" required class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                            {voice_options}
                        </select>
                        <p class="mt-1 text-xs text-gray-500">Selecciona la voz para el audio</p>
                    </div>
                '''
            })
        except Exception as e:
            logger.error(f"Error cargando voces de ElevenLabs: {e}", exc_info=True)
            # Mostrar advertencia y permitir entrada manual
            error_msg = str(e)
            if 'API_KEY' in error_msg:
                error_msg = 'API Key no configurada'
            elif 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                error_msg = 'Error de conexión con ElevenLabs API'
            else:
                error_msg = 'No se pudieron cargar las voces automáticamente'
            
            fields.append({
                'name': 'elevenlabs_warning',
                'label': 'Advertencia',
                'required': False,
                'html': f'''
                    <div class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p class="text-sm text-yellow-800 font-semibold mb-2">
                            ⚠️ {error_msg}
                        </p>
                        <p class="text-xs text-yellow-700 mb-3">
                            Se usará la voz por defecto o puedes ingresar un ID de voz manualmente:
                        </p>
                    </div>
                '''
            })
            
            fields.append({
                'name': 'voice_id',
                'label': 'Voice ID',
                'required': False,
                'html': f'''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            VOZ ID <span class="text-yellow-600">(opcional)</span>
                        </label>
                        <input type="text" 
                               name="voice_id" 
                               placeholder="Ej: 21m00Tcm4TlvDq8ikWAM" 
                               class="w-full px-3 py-2.5 text-sm border border-yellow-300 rounded-lg bg-white focus:ring-2 focus:ring-yellow-500 focus:border-yellow-500 transition-all">
                        <p class="mt-1 text-xs text-gray-500">Ingresa el ID de la voz si lo conoces, o deja vacío para usar la voz por defecto</p>
                    </div>
                '''
            })
    
    return {
        'fields': fields,
        'data': data
    }

