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
            # Usar APIService que tiene caché en Redis
            from core.services import APIService
            api_service = APIService()
            
            # Obtener avatares y voces con caché (usa Redis automáticamente)
            avatars = api_service.list_avatars(use_cache=True)
            voices = api_service.list_voices(use_cache=True)
            
            logger.info(f"HeyGen V2: Cargados {len(avatars)} avatares y {len(voices)} voces (desde caché o API)")
            
            data['avatars'] = avatars
            data['voices'] = voices
            
            # Generar datos de avatares para el dropdown personalizado
            import uuid
            import json
            unique_id = str(uuid.uuid4())[:8]
            avatar_select_id = f'avatar_id_select_{unique_id}'
            avatar_preview_id = f'avatar_preview_container_{unique_id}'
            avatar_dropdown_id = f'avatar_dropdown_{unique_id}'
            
            # Preparar datos de avatares para JavaScript
            avatars_data = []
            for avatar in avatars:
                avatar_id = avatar.get("avatar_id") or avatar.get("id")
                avatar_name = avatar.get("avatar_name") or avatar.get("name") or avatar_id
                preview_image = avatar.get("preview_image_url") or avatar.get("avatar_image") or ''
                preview_video = avatar.get("preview_video_url") or ''
                avatars_data.append({
                    'id': avatar_id,
                    'name': avatar_name,
                    'preview_image': preview_image,
                    'preview_video': preview_video
                })
            
            # Convertir a JSON y escapar correctamente para usar en data attribute HTML
            # Usar comillas dobles en el JSON y escapar solo las comillas dobles
            avatars_json = json.dumps(avatars_data, ensure_ascii=False)
            # Escapar comillas dobles y backslashes para uso seguro en atributo HTML
            avatars_json_escaped = avatars_json.replace('\\', '\\\\').replace('"', '&quot;')
            
            fields.append({
                'name': 'avatar_id',
                'label': 'Avatar',
                'required': True,
                'html': f'''
                    <div class="mb-4" 
                         data-avatars="{avatars_json_escaped}"
                         x-data="{{
                            open: false,
                            selectedAvatar: null,
                            avatars: JSON.parse($el.dataset.avatars),
                            searchTerm: '',
                            visibleAvatars: 20,
                            get filteredAvatars() {{
                                if (!this.searchTerm) return this.avatars.slice(0, this.visibleAvatars);
                                const term = this.searchTerm.toLowerCase();
                                return this.avatars.filter(a => 
                                    a.name.toLowerCase().includes(term) || 
                                    a.id.toLowerCase().includes(term)
                                ).slice(0, this.visibleAvatars);
                            }},
                            selectAvatar(avatar) {{
                                this.selectedAvatar = avatar;
                                this.open = false;
                                const hiddenInput = document.getElementById('{avatar_select_id}');
                                if (hiddenInput) hiddenInput.value = avatar.id;
                            }},
                            loadMore() {{
                                this.visibleAvatars += 20;
                            }}
                         }}" 
                         x-init="
                            const dropdown = $el.querySelector('.avatar-dropdown-menu');
                            if (dropdown) {{
                                dropdown.addEventListener('scroll', function() {{
                                    if (this.scrollTop + this.clientHeight >= this.scrollHeight - 100) {{
                                        if (visibleAvatars < avatars.length) {{
                                            visibleAvatars += 20;
                                        }}
                                    }}
                                }});
                            }}
                         ">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            AVATAR <span class="text-red-500">*</span>
                        </label>
                        
                        <!-- Input hidden para el formulario -->
                        <input type="hidden" name="avatar_id" id="{avatar_select_id}" x-bind:value="selectedAvatar ? selectedAvatar.id : ''" required>
                        
                        <!-- Botón selector -->
                        <div class="relative">
                            <button type="button" 
                                    @click="open = !open"
                                    class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50 focus:ring-2 focus:ring-black focus:border-black transition-all text-left flex items-center justify-between">
                                <span x-text="selectedAvatar ? selectedAvatar.name : 'Selecciona un avatar'" 
                                      class="text-gray-700"></span>
                                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                </svg>
                            </button>
                            
                            <!-- Dropdown menu -->
                            <div x-show="open" 
                                 @click.away="open = false"
                                 x-transition:enter="transition ease-out duration-200"
                                 x-transition:enter-start="opacity-0 scale-95"
                                 x-transition:enter-end="opacity-100 scale-100"
                                 x-transition:leave="transition ease-in duration-150"
                                 x-transition:leave-start="opacity-100 scale-100"
                                 x-transition:leave-end="opacity-0 scale-95"
                                 class="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-96 overflow-hidden"
                                 style="display: none;">
                                
                                <!-- Search bar -->
                                <div class="p-2 border-b border-gray-200">
                                    <input type="text" 
                                           x-model="searchTerm"
                                           placeholder="Buscar avatar..."
                                           class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-black">
                                </div>
                                
                                <!-- Avatares grid -->
                                <div class="avatar-dropdown-menu overflow-y-auto max-h-80 p-2">
                                    <div class="grid grid-cols-2 gap-2">
                                        <template x-for="avatar in filteredAvatars" :key="avatar.id">
                                            <div @click="selectAvatar(avatar)"
                                                 class="avatar-item cursor-pointer rounded-lg border-2 transition-all hover:border-black p-1"
                                                 :class="selectedAvatar && selectedAvatar.id === avatar.id ? 'border-black bg-gray-50' : 'border-gray-200'">
                                                <!-- Preview thumbnail (lazy loading - solo imagen, no video) -->
                                                <div class="aspect-video bg-gray-100 rounded overflow-hidden mb-1 relative">
                                                    <img x-show="avatar.preview_image"
                                                         :src="avatar.preview_image"
                                                         :alt="avatar.name"
                                                         loading="lazy"
                                                         class="w-full h-full object-cover"
                                                         @error="$el.style.display = 'none'">
                                                    <!-- Indicador de video si tiene preview_video -->
                                                    <div x-show="avatar.preview_video && avatar.preview_image" 
                                                         class="absolute top-1 right-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded flex items-center gap-1">
                                                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                            <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"></path>
                                                        </svg>
                                                    </div>
                                                    <div x-show="!avatar.preview_image" class="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                                                        No preview
                                                    </div>
                                                </div>
                                                <!-- Nombre -->
                                                <p class="text-xs font-medium text-gray-700 truncate px-1" x-text="avatar.name"></p>
                                            </div>
                                        </template>
                                    </div>
                                    
                                    <!-- Load more button -->
                                    <div x-show="visibleAvatars < avatars.length && !searchTerm" class="mt-2 text-center">
                                        <button @click="loadMore()" 
                                                class="text-xs text-gray-600 hover:text-gray-900 px-3 py-1">
                                            Cargar más...
                                        </button>
                                    </div>
                                    
                                    <!-- No results -->
                                    <div x-show="filteredAvatars.length === 0" class="text-center py-4 text-gray-500 text-sm">
                                        No se encontraron avatares
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Preview grande del avatar seleccionado -->
                        <div x-show="selectedAvatar" 
                             x-transition
                             class="mt-3 rounded-lg overflow-hidden bg-gray-100 border border-gray-200 relative"
                             style="width: 100%; aspect-ratio: 16/9; max-width: 400px;">
                            <template x-if="selectedAvatar.preview_video">
                                <video :src="selectedAvatar.preview_video" 
                                       class="w-full h-full object-cover"
                                       muted 
                                       loop 
                                       playsinline 
                                       autoplay></video>
                            </template>
                            <template x-if="selectedAvatar.preview_image && !selectedAvatar.preview_video">
                                <img :src="selectedAvatar.preview_image" 
                                     :alt="selectedAvatar.name"
                                     class="w-full h-full object-cover">
                            </template>
                            <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
                                <p class="text-white font-semibold text-sm" x-text="selectedAvatar.name"></p>
                            </div>
                        </div>
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
            
            # Campos para background (opcional)
            fields.append({
                'name': 'has_background',
                'label': 'Incluir Fondo',
                'required': False,
                'html': '''
                    <div class="mb-4">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" name="has_background" value="true" class="w-4 h-4 text-black border-gray-300 rounded focus:ring-black">
                            <span class="text-xs font-semibold text-gray-700 uppercase">Incluir Imagen de Fondo</span>
                        </label>
                        <p class="mt-1 text-xs text-gray-500">Activa esta opción para agregar una imagen de fondo al video</p>
                    </div>
                '''
            })
            
            fields.append({
                'name': 'background_url',
                'label': 'URL del Fondo',
                'required': False,
                'html': '''
                    <div class="mb-4">
                        <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                            URL DEL FONDO
                        </label>
                        <input type="url" 
                               name="background_url" 
                               placeholder="https://ejemplo.com/imagen.jpg" 
                               class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                        <p class="mt-1 text-xs text-gray-500">URL de la imagen de fondo (solo si "Incluir Fondo" está activado)</p>
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
            # Usar APIService que tiene caché en Redis
            from core.services import APIService
            api_service = APIService()
            
            # Obtener image assets y voces con caché (usa Redis automáticamente)
            image_assets = api_service.list_image_assets(use_cache=True)
            voices = api_service.list_voices(use_cache=True)
            
            logger.info(f"HeyGen IV: Cargados {len(image_assets)} assets de imagen y {len(voices)} voces (desde caché o API)")
            
            data['image_assets'] = image_assets
            data['voices'] = voices
            
            # Generar HTML para avatar image select (solo si hay assets disponibles)
            # Si no hay assets, el usuario debe usar start_image para subir una imagen
            if image_assets:
                # Crear un diccionario de assets con sus previews para JavaScript
                assets_data = {}
                image_asset_options = '<option value="">Selecciona una imagen de avatar existente (opcional)</option>'
                for asset in image_assets:
                    asset_id = asset.get("asset_id") or asset.get("id")
                    asset_name = asset.get("asset_name") or asset.get("name") or asset_id
                    # Intentar obtener URL de preview de diferentes campos posibles
                    preview_url = (
                        asset.get("preview_url") or 
                        asset.get("thumbnail_url") or 
                        asset.get("url") or 
                        asset.get("image_url") or
                        asset.get("asset_url") or
                        ''
                    )
                    image_asset_options += f'<option value="{asset_id}" data-preview-url="{preview_url}">{asset_name}</option>'
                    if preview_url:
                        assets_data[asset_id] = {
                            'name': asset_name,
                            'preview_url': preview_url
                        }
                
                # Convertir assets_data a JSON para JavaScript
                import json
                assets_json = json.dumps(assets_data)
                
                fields.append({
                    'name': 'avatar_image_id',
                    'label': 'Imagen de Avatar Existente',
                    'required': False,
                    'html': f'''
                        <div class="mb-4" x-data="{{
                            selectedAssetId: '',
                            assetsData: {assets_json},
                            getPreviewUrl() {{
                                return this.selectedAssetId && this.assetsData[this.selectedAssetId] 
                                    ? this.assetsData[this.selectedAssetId].preview_url 
                                    : null;
                            }}
                        }}">
                            <label class="block text-xs font-semibold text-gray-700 uppercase mb-2">
                                IMAGEN DE AVATAR EXISTENTE (Opcional)
                            </label>
                            <select 
                                name="avatar_image_id" 
                                x-model="selectedAssetId"
                                @change="selectedAssetId = $event.target.value"
                                class="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-black focus:border-black transition-all">
                                {image_asset_options}
                            </select>
                            
                            <!-- Preview de la imagen seleccionada -->
                            <div x-show="getPreviewUrl()" class="mt-3 rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                                <div class="aspect-video bg-gray-100 relative">
                                    <img 
                                        :src="getPreviewUrl()" 
                                        :alt="selectedAssetId && assetsData[selectedAssetId] ? assetsData[selectedAssetId].name : 'Preview'"
                                        class="w-full h-full object-cover"
                                        @error="$el.style.display = 'none'">
                                    <div class="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent"></div>
                                    <div class="absolute bottom-2 left-2 right-2">
                                        <p class="text-white text-xs font-medium truncate" 
                                           x-text="selectedAssetId && assetsData[selectedAssetId] ? assetsData[selectedAssetId].name : ''"
                                           style="text-shadow: 0 1px 3px rgba(0,0,0,0.5);"></p>
                                    </div>
                                </div>
                            </div>
                            
                            <p class="mt-1 text-xs text-gray-500">O sube una nueva imagen usando el campo "Start Image" en Referencias</p>
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

