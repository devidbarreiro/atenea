# Guía: Añadir Nuevos Modelos de IA

Esta guía explica cómo añadir un nuevo modelo o servicio de IA al sistema de formularios dinámicos de Atenea.

## Arquitectura Modular

El sistema está diseñado para ser **modular y fácil de extender**. Consta de tres capas principales:

1. **Backend**: Configuración de capacidades del modelo (`core/ai_services/model_config.py`)
2. **Frontend**: Sistema de field providers (`static/js/model-field-providers.js`)
3. **Templates**: Formularios dinámicos que se adaptan automáticamente

---

## Paso 1: Configurar el Modelo en el Backend

### 1.1 Añadir al diccionario de capacidades

Edita `core/ai_services/model_config.py` y añade tu modelo al diccionario `MODEL_CAPABILITIES`:

```python
MODEL_CAPABILITIES: Dict[str, Dict] = {
    # ... modelos existentes ...
    
    'mi-nuevo-modelo': {
        'service': 'mi_servicio',  # Nombre del servicio (ej: 'openai', 'gemini_veo')
        'name': 'Mi Nuevo Modelo',
        'description': 'Descripción breve del modelo',
        'type': 'video',  # 'video', 'image', o 'audio'
        'supports': {
            'text_to_video': True,
            'image_to_video': False,
            'duration': {
                'min': 5,
                'max': 10,
                'options': [5, 8, 10]  # Opciones específicas
            },
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': True,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
            'modes': ['fast', 'quality'],  # Opcional: modos específicos
        },
        'logo': '/static/img/logos/mi-servicio.png',
    },
}
```

### 1.2 Añadir mapeo de tipo (solo para videos)

Si es un modelo de video, añádelo al mapeo `VIDEO_TYPE_TO_MODEL_ID`:

```python
VIDEO_TYPE_TO_MODEL_ID = {
    # ... mapeos existentes ...
    'mi_tipo_video': 'mi-nuevo-modelo',
}
```

### 1.3 Añadir precios (opcional)

Si el modelo tiene un costo específico, añádelo a `core/services/credits.py`:

```python
PRICING = {
    # ... precios existentes ...
    'mi_tipo_video': {
        'video': 0.5,  # Por segundo
        'video_audio': 0.8,  # Si soporta audio
    },
}
```

Y actualiza el método `estimate_video_cost()` si es necesario:

```python
@staticmethod
def estimate_video_cost(video_type=None, duration=None, config=None, model_id=None):
    # ... código existente ...
    
    elif video_type == 'mi_tipo_video':
        duration = duration or 8
        has_audio = config and config.get('generate_audio', False)
        price_key = 'video_audio' if has_audio else 'video'
        return Decimal(str(duration * CreditService.PRICING['mi_tipo_video'][price_key]))
```

---

## Paso 2: Crear el Field Provider (Frontend)

### 2.1 Campos simples (automáticos)

Si tu modelo solo usa campos estándar (duración, aspect ratio, etc.), **no necesitas hacer nada**. El sistema los mostrará automáticamente basándose en la configuración del backend.

### 2.2 Campos específicos del modelo

Si tu modelo necesita campos personalizados (como selección de avatar, voz, etc.), crea un field provider.

Edita `static/js/model-field-providers.js` y añade tu provider:

```javascript
/**
 * Provider para Mi Nuevo Modelo
 */
modelFieldProviders.register('mi-nuevo-modelo', {
    /**
     * Renderiza los campos HTML específicos del modelo
     * @param {string} modelId - ID del modelo
     * @param {string} service - Nombre del servicio
     * @returns {Promise<string>} HTML de los campos
     */
    async renderFields(modelId, service) {
        return `
            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Campo Personalizado <span class="text-red-500">*</span>
                </label>
                <input 
                    type="text" 
                    name="campo_personalizado" 
                    required
                    placeholder="Valor del campo"
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
            </div>
            
            <div class="mb-6">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Selector
                </label>
                <select 
                    name="selector" 
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                    <option value="">Cargando opciones...</option>
                </select>
            </div>
        `;
    },
    
    /**
     * Carga datos necesarios para los campos (opcional)
     * Se ejecuta después de renderFields
     * @param {HTMLElement} container - Contenedor donde se renderizaron los campos
     * @param {HTMLElement} formElement - Elemento del formulario completo
     */
    async loadData(container, formElement) {
        // Ejemplo: cargar opciones desde una API
        const select = container.querySelector('[name="selector"]');
        if (select) {
            try {
                const response = await fetch('/api/mi-endpoint/');
                const data = await response.json();
                
                select.innerHTML = '<option value="">Selecciona una opción</option>';
                data.options.forEach(option => {
                    const opt = document.createElement('option');
                    opt.value = option.id;
                    opt.textContent = option.name;
                    select.appendChild(opt);
                });
            } catch (error) {
                console.error('Error cargando datos:', error);
                select.innerHTML = '<option value="">Error al cargar opciones</option>';
            }
        }
    },
    
    /**
     * Extrae los datos del formulario específicos del modelo (opcional)
     * @param {HTMLElement} formElement - Elemento del formulario
     * @returns {Object} Datos extraídos
     */
    getFormData(formElement) {
        return {
            campo_personalizado: formElement.querySelector('[name="campo_personalizado"]')?.value || '',
            selector: formElement.querySelector('[name="selector"]')?.value || ''
        };
    }
});
```

### 2.3 Provider por servicio (opcional)

Si varios modelos del mismo servicio comparten campos, puedes registrar un provider por servicio:

```javascript
modelFieldProviders.register('mi_servicio', {
    async renderFields(modelId, service) {
        // Renderizar campos comunes para todos los modelos del servicio
        // Puedes usar modelId para personalizar según el modelo específico
        if (modelId === 'modelo-a') {
            return '... campos específicos de modelo-a ...';
        } else {
            return '... campos comunes ...';
        }
    },
    // ...
});
```

---

## Paso 3: Crear el Servicio de IA (Backend)

Crea el cliente del servicio en `core/ai_services/mi_servicio.py`:

```python
from .base import BaseAIClient
import logging

logger = logging.getLogger(__name__)

class MiServicioClient(BaseAIClient):
    """Cliente para Mi Servicio de IA"""
    
    def __init__(self, api_key=None):
        super().__init__()
        self.api_key = api_key or settings.MI_SERVICIO_API_KEY
        self.base_url = "https://api.mi-servicio.com"
    
    def generate_video(self, prompt, duration=8, **kwargs):
        """Genera un video"""
        # Implementar lógica de generación
        pass
```

---

## Paso 4: Integrar en las Vistas

### 4.1 Actualizar la vista de creación

En `core/views.py`, actualiza la vista de creación para manejar tu nuevo modelo:

```python
class VideoGenerateView(LoginRequiredMixin, View):
    def post(self, request, video_id):
        video = get_object_or_404(Video, id=video_id, user=request.user)
        
        model_id = request.POST.get('model_id')
        
        if model_id == 'mi-nuevo-modelo':
            # Lógica específica para tu modelo
            client = MiServicioClient()
            result = client.generate_video(
                prompt=video.script,
                duration=int(request.POST.get('duration', 8)),
                campo_personalizado=request.POST.get('campo_personalizado'),
                # ...
            )
            # Procesar resultado...
```

---

## Ejemplo Completo: HeyGen Avatar V2

### Backend (`model_config.py`)

```python
'heygen-avatar-v2': {
    'service': 'heygen',
    'name': 'HeyGen Avatar V2',
    'description': 'Avatar con controles avanzados',
    'type': 'video',
    'supports': {
        'text_to_video': True,
        'image_to_video': False,
        'duration': {'min': 1, 'max': 300},
        'audio': True,  # Requiere voz
        # ... más configuraciones
    },
}
```

### Frontend (`model-field-providers.js`)

```javascript
modelFieldProviders.register('heygen-avatar-v2', {
    async renderFields(modelId, service) {
        return `
            <div class="mb-6">
                <label>Avatar <span class="text-red-500">*</span></label>
                <select name="avatar_id" id="heygen-avatar-select" required>
                    <option value="">Cargando avatares...</option>
                </select>
            </div>
            <div class="mb-6">
                <label>Voz <span class="text-red-500">*</span></label>
                <select name="voice_id" id="heygen-voice-select" required>
                    <option value="">Cargando voces...</option>
                </select>
            </div>
        `;
    },
    
    async loadData(container, formElement) {
        // Cargar avatares y voces desde API
        const avatarSelect = container.querySelector('#heygen-avatar-select');
        const response = await fetch('/api/avatars/');
        const data = await response.json();
        // Poblar select...
    },
    
    getFormData(formElement) {
        return {
            avatar_id: formElement.querySelector('[name="avatar_id"]')?.value,
            voice_id: formElement.querySelector('[name="voice_id"]')?.value
        };
    }
});
```

---

## Buenas Prácticas

1. **Nombres consistentes**: Usa nombres consistentes entre backend y frontend
2. **Validación**: Valida los datos tanto en frontend como backend
3. **Manejo de errores**: Maneja errores de carga de datos gracefully
4. **Documentación**: Documenta campos personalizados y sus propósitos
5. **Testing**: Prueba con diferentes configuraciones del modelo

---

## Estructura de Archivos

```
core/
├── ai_services/
│   ├── model_config.py          # Configuración de capacidades
│   └── mi_servicio.py          # Cliente del servicio
├── services/
│   └── credits.py              # Precios y cálculo de costos
└── views.py                    # Vistas de creación/generación

static/js/
├── dynamic-form.js             # Lógica del formulario dinámico
└── model-field-providers.js    # Providers de campos específicos

templates/
└── videos/
    ├── create.html             # Template principal
    └── _form.html              # Formulario dinámico
```

---

## Preguntas Frecuentes

**P: ¿Necesito crear un provider si mi modelo solo usa campos estándar?**  
R: No, el sistema mostrará automáticamente los campos basándose en `MODEL_CAPABILITIES`.

**P: ¿Cómo manejo campos que dependen de otros campos?**  
R: Usa eventos en `loadData()` para escuchar cambios y actualizar campos dependientes.

**P: ¿Puedo tener múltiples providers para el mismo modelo?**  
R: No directamente, pero puedes usar un provider por servicio y personalizar según `modelId`.

**P: ¿Cómo actualizo el costo estimado para mi modelo?**  
R: Añade la lógica en `CreditService.estimate_video_cost()` y actualiza `PRICING`.

---

## Recursos Adicionales

- [Documentación de Modelos API](../MODELOS_API_COMPLETA.md)
- [Arquitectura del Sistema](../architecture/README.md)
- [Guía de Estilos Frontend](../guides/frontend-styles.md)

