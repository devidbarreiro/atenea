# Generar Video de Cita

Genera un video animado con una cita usando Manim.

## Función

```python
ManimClient.generate_quote_video(
    quote: str,
    author: Optional[str] = None,
    duration: Optional[float] = None,
    quality: str = "k",
    container_color: Optional[str] = None,
    text_color: Optional[str] = None,
    font_family: Optional[str] = None
) -> Dict[str, str]
```

## Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `quote` | `str` | ✅ Sí | Texto de la cita |
| `author` | `str` | ❌ No | Nombre del autor (opcional) |
| `duration` | `float` | ❌ No | Duración en segundos (se calcula automáticamente si no se especifica) |
| `quality` | `str` | ❌ No | Calidad de renderizado: `l` (480p15), `m` (720p30), `h` (1080p60), `k` (2160p60). Default: `k` |
| `container_color` | `str` | ❌ No | Color del contenedor en formato hex (ej: `#0066CC`). Default: `#0066CC` |
| `text_color` | `str` | ❌ No | Color del texto en formato hex (ej: `#FFFFFF`). Default: `#FFFFFF` |
| `font_family` | `str` | ❌ No | Tipo de fuente: `normal`, `bold`, `italic`, `bold_italic`. Default: `normal` |

## Retorno

```python
{
    'video_path': str  # Ruta local del video generado
}
```

## Ejemplo de Uso

### Básico

```python
from core.ai_services.manim import ManimClient

client = ManimClient()

result = client.generate_quote_video(
    quote="La creatividad es la inteligencia divirtiéndose",
    author="Albert Einstein"
)

print(f"Video generado en: {result['video_path']}")
```

### Con Personalización

```python
result = client.generate_quote_video(
    quote="El único modo de hacer un gran trabajo es amar lo que haces",
    author="Steve Jobs",
    quality="h",  # 1080p60
    container_color="#1a1a1a",  # Fondo oscuro
    text_color="#ffffff",  # Texto blanco
    font_family="bold",  # Fuente en negrita
    duration=10.0  # 10 segundos
)
```

## Calidades Disponibles

| Calidad | Resolución | FPS | Uso Recomendado |
|---------|------------|-----|-----------------|
| `l` | 480p | 15 | Preview rápido, pruebas |
| `m` | 720p | 30 | Uso general, web |
| `h` | 1080p | 60 | Alta calidad, presentaciones |
| `k` | 2160p (4K) | 60 | Máxima calidad, producción |

## Colores

Los colores se especifican en formato hexadecimal:

- `#0066CC` - Azul (default contenedor)
- `#FFFFFF` - Blanco (default texto)
- `#000000` - Negro
- `#FF0000` - Rojo
- Cualquier color hex válido

## Fuentes

- `normal` - Fuente normal (default)
- `bold` - Fuente en negrita
- `italic` - Fuente en cursiva
- `bold_italic` - Fuente en negrita y cursiva

## Manejo de Errores

### ValueError

Se lanza si:
- El texto de la cita está vacío

```python
try:
    result = client.generate_quote_video(quote="")
except ValueError as e:
    print(f"Error: {e}")
```

### Exception

Se lanza si:
- Falla el renderizado de Manim
- El video generado no se encuentra

```python
try:
    result = client.generate_quote_video(quote="Mi cita")
except Exception as e:
    print(f"Error al generar video: {e}")
```

## Notas

- El tiempo de renderizado depende de la calidad seleccionada
- Calidad `k` (4K) puede tardar varios minutos
- El video se genera localmente y luego se sube a Google Cloud Storage
- La duración se calcula automáticamente basándose en la longitud del texto si no se especifica

## Costo

**~1 crédito por video** (independiente de la duración y calidad)

---

**Ubicación**: `core/ai_services/manim.py`

