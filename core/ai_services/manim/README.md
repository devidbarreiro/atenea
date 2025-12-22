# Arquitectura Manim - Sistema Escalable de Animaciones

Este módulo proporciona una arquitectura escalable para generar videos animados con Manim.

## Estructura

```
manim/
├── __init__.py              # Exporta clases principales
├── base.py                  # BaseManimAnimation - Clase base para todas las animaciones
├── registry.py              # Sistema de registro de animaciones
├── client.py                # ManimClient - Cliente principal
├── render_wrapper.py       # Wrapper para ejecutar animaciones
├── animations/              # Módulo de animaciones
│   ├── __init__.py         # Importa todas las animaciones
│   ├── quote.py            # Animación de citas
│   ├── EXAMPLE_NEW_ANIMATION.py  # Plantilla para nuevas animaciones
│   └── ...                 # Futuras animaciones
└── README.md               # Esta documentación
```

## Conceptos Clave

### 1. BaseManimAnimation
Clase base abstracta que todas las animaciones deben heredar. Proporciona:
- `_fix_encoding()`: Repara encoding de texto
- `_get_env_var()`: Obtiene variables de entorno con soporte para base64
- `_get_config()`: Obtiene toda la configuración como dict
- `setup_background()`: Configura el color de fondo
- `get_animation_type()`: Método abstracto que retorna el tipo único
- `construct()`: Método abstracto que define la animación

### 2. Sistema de Registro
Las animaciones se registran automáticamente usando el decorador `@register_animation()`:

```python
@register_animation('quote')
class QuoteAnimation(BaseManimAnimation):
    def get_animation_type(self) -> str:
        return 'quote'
    
    def construct(self):
        # Tu animación aquí
        pass
```

### 3. ManimClient
Cliente principal que puede generar cualquier tipo de animación registrada:

```python
from core.ai_services.manim import ManimClient

client = ManimClient()
result = client.generate_video(
    animation_type='quote',
    config={
        'text': 'Mi cita',
        'author': 'Autor',
        'container_color': '#0066CC',
    },
    quality='k'
)
```

## Cómo Añadir una Nueva Animación

### Paso 1: Crear el archivo de animación

Crea un nuevo archivo en `animations/` (ej: `histogram.py`):

```python
from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation

@register_animation('histogram')
class HistogramAnimation(BaseManimAnimation):
    def get_animation_type(self) -> str:
        return 'histogram'
    
    def construct(self):
        # Obtener datos desde variables de entorno
        data_str = self._get_env_var('HISTOGRAM_ANIMATION_DATA', '[]')
        title = self._get_env_var('HISTOGRAM_ANIMATION_TITLE', 'Histograma', decode_base64=True)
        
        # Tu lógica de animación
        self.setup_background("#FFFFFF")
        # ... crear histograma ...
```

### Paso 2: Registrar en __init__.py

Añade la importación en `animations/__init__.py`:

```python
from .histogram import HistogramAnimation  # noqa: F401
```

### Paso 3: Añadir mapeo de configuración (opcional)

Si quieres usar nombres más naturales en `config`, añade un mapeo en `client.py`:

```python
key_mapping = {
    'histogram': {
        'data': 'DATA',
        'title': 'TITLE',
        'bins': 'BINS',
    }
}
```

### Paso 4: Usar desde el código

```python
client = ManimClient()
result = client.generate_video(
    animation_type='histogram',
    config={
        'data': [1, 2, 3, 4, 5],
        'title': 'Mi Histograma',
        'bins': 10,
    },
    quality='k'
)
```

## Tipos de Animaciones Planificadas

### Gráficas y Visualizaciones
- ✅ Quotes (citas)
- ✅ Intro Slide (cortinillas de entrada)
- ⏳ Bar Chart (gráficas de barras)
- ⏳ Line Chart (gráficas de líneas)
- ⏳ Pie Chart (gráficas de pastel)
- ⏳ Histogram (histogramas)
- ⏳ Scatter Plot (gráficas de dispersión)
- ⏳ XY Chart (gráficas x-y)
- ⏳ Heatmap (mapas de calor)
- ⏳ Box Plot (gráficas de cajas)

### Matemáticas y Ecuaciones
- ⏳ LaTeX Equations (ecuaciones LaTeX animadas)
- ⏳ Math Transformations (transformaciones matemáticas)
- ⏳ Geometric Proofs (demostraciones geométricas)

### Texto y Tipografía
- ✅ Quotes (ya implementado)
- ✅ Intro Slide (cortinillas de entrada estilo presentación)
- ⏳ Animated Text (texto con efectos)
- ⏳ Titles and Credits (títulos y créditos)

## Convenciones

### Nombres de Variables de Entorno
Las variables de entorno siguen el patrón:
```
{TIPO}_ANIMATION_{PARAMETRO}
```

Ejemplo para 'histogram':
- `HISTOGRAM_ANIMATION_DATA`
- `HISTOGRAM_ANIMATION_TITLE`
- `HISTOGRAM_ANIMATION_BINS`

### Codificación Base64
Los strings con caracteres especiales se codifican automáticamente en base64:
- Variable: `QUOTE_ANIMATION_TEXT` = valor codificado
- Flag: `QUOTE_ANIMATION_TEXT_ENCODED` = '1'

### Rutas de Videos
Los videos se generan en:
```
media/videos/{script_name}/{quality}/{scene_name}.mp4
```

Donde:
- `script_name`: Nombre del script ejecutado (render_wrapper)
- `quality`: l/m/h/k (480p15/720p30/1080p60/2160p60)
- `scene_name`: Nombre de la clase de animación

## Testing

### Probar una animación directamente:
```bash
export MANIM_ANIMATION_TYPE=quote
export QUOTE_ANIMATION_TEXT="Mi cita"
python -m manim -nql core/ai_services/manim/render_wrapper.py QuoteAnimation
```

### Probar desde Python:
```python
from core.ai_services.manim import ManimClient

client = ManimClient()
result = client.generate_video(
    animation_type='quote',
    config={'text': 'Test'},
    quality='l'  # Calidad baja para pruebas rápidas
)
print(result['video_path'])
```

## Integración con VideoService

Para integrar nuevas animaciones con `VideoService`, añade el caso en `core/services.py`:

```python
elif video.type == 'manim_histogram':
    external_id = self._generate_manim_video(video, animation_type='histogram')
```

O crea un método genérico:

```python
def _generate_manim_video(self, video: Video, animation_type: str) -> str:
    from core.ai_services.manim import ManimClient
    
    client = ManimClient()
    result = client.generate_video(
        animation_type=animation_type,
        config=video.config,
        quality=video.config.get('quality', 'k')
    )
    # ... subir a GCS y marcar como completado ...
```

