# Guía Completa de Modelos Veo en Atenea

Esta guía documenta todos los modelos de Google Veo disponibles en el proyecto Atenea y cómo usar sus características específicas.

## 📋 Tabla de Contenidos

- [Modelos Disponibles](#modelos-disponibles)
- [Características por Modelo](#características-por-modelo)
- [Uso Básico](#uso-básico)
- [Características Avanzadas](#características-avanzadas)
- [Ejemplos Prácticos](#ejemplos-prácticos)
- [Mejores Prácticas](#mejores-prácticas)

## 🎬 Modelos Disponibles

### Veo 2.0

#### `veo-2.0-generate-001` (Estable)
- **Versión**: 2.0
- **Duración**: 5-8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ Last Frame (fill-in-the-blank)
  - ✅ Video Extension
  - ❌ No audio
  - ❌ No reference images
  - ❌ No máscaras

**Uso recomendado**: Generación estable y confiable con funcionalidades de extensión.

#### `veo-2.0-generate-exp` (Experimental)
- **Versión**: 2.0
- **Duración**: 5-8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ Reference Images (asset **Y** style)
  - ❌ No audio
  - ❌ No lastFrame
  - ❌ No video extension

**Uso recomendado**: Cuando necesites transferencia de estilo o consistencia visual con imágenes de referencia.

#### `veo-2.0-generate-preview` (Preview)
- **Versión**: 2.0
- **Duración**: 5-8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ Mask Editing (añadir/quitar objetos)
  - ❌ No audio
  - ❌ No reference images

**Uso recomendado**: Edición de videos con máscaras para modificar escenas.

---

### Veo 3.0

#### `veo-3.0-generate-001` (Estable)
- **Versión**: 3.0
- **Duración**: 4, 6 u 8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ **Audio generado**
  - ✅ **Resolución 720p/1080p**
  - ✅ Resize mode (pad/crop)
  - ❌ No reference images
  - ❌ No lastFrame
  - ❌ No video extension

**Uso recomendado**: Generación con audio y alta resolución.

#### `veo-3.0-fast-generate-001` (Rápido)
- **Versión**: 3.0
- **Duración**: 4, 6 u 8 segundos
- **Características**: Igual que `veo-3.0-generate-001` pero más rápido

**Uso recomendado**: Cuando necesites resultados rápidos con audio.

#### `veo-3.0-generate-preview` (Preview con extensión)
- **Versión**: 3.0
- **Duración**: 4, 6 u 8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ **Audio generado**
  - ✅ **Resolución 720p/1080p**
  - ✅ Last Frame (fill-in-the-blank)
  - ✅ Video Extension
  - ✅ Resize mode
  - ❌ No reference images

**Uso recomendado**: Cuando necesites audio + extensión de video.

#### `veo-3.0-fast-generate-preview` (Rápido Preview)
- **Versión**: 3.0
- **Duración**: 4, 6 u 8 segundos
- **Características**: Similar a `veo-3.0-generate-preview` pero sin lastFrame ni video extension

---

### Veo 3.1 (Recomendado)

#### `veo-3.1-generate-preview` ⭐ (Última versión)
- **Versión**: 3.1
- **Duración**: 4, 6 u 8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ **Audio generado**
  - ✅ **Resolución 720p/1080p**
  - ✅ **Reference Images (solo asset)**
  - ✅ Last Frame (fill-in-the-blank)
  - ✅ Resize mode
  - ❌ No video extension
  - ❌ No style images (solo asset)

**Uso recomendado**: **Modelo principal para la mayoría de casos**. Combina audio, alta resolución y reference images.

#### `veo-3.1-fast-generate-preview` ⚡ (Rápido)
- **Versión**: 3.1
- **Duración**: 4, 6 u 8 segundos
- **Características**:
  - ✅ Text-to-video
  - ✅ Image-to-video
  - ✅ **Audio generado**
  - ✅ **Resolución 720p/1080p**
  - ✅ Last Frame (fill-in-the-blank)
  - ✅ Resize mode
  - ❌ **NO soporta Reference Images** (limitación de modelos "fast")
  - ❌ No video extension

**Uso recomendado**: Cuando necesites resultados rápidos con audio y alta resolución, pero sin reference images.

---

## 🎯 Características por Modelo

| Característica | Veo 2.0-001 | Veo 2.0-exp | Veo 2.0-prev | Veo 3.0-001 | Veo 3.0-prev | Veo 3.1 ⭐ |
|----------------|-------------|-------------|--------------|-------------|--------------|-----------|
| **Text-to-video** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Image-to-video** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Audio** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **1080p** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Reference Images** | ❌ | ✅ (asset+style) | ❌ | ❌ | ❌ | ✅ (solo asset) |
| **Last Frame** | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Video Extension** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Mask Editing** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Resize Mode** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |

---

## 🚀 Uso Básico

### 1. Text-to-Video Simple

```python
from core.ai_services.gemini_veo import GeminiVeoClient

client = GeminiVeoClient(model_name='veo-3.1-generate-preview')

result = client.generate_video(
    prompt="Un drone volando sobre una playa tropical al atardecer",
    title="Playa Tropical",
    duration=8,
    aspect_ratio="16:9"
)

print(f"Operation ID: {result['video_id']}")
```

### 2. Con Audio y Alta Resolución (Veo 3+)

```python
result = client.generate_video(
    prompt="Un músico tocando guitarra en un estudio",
    title="Músico",
    duration=8,
    generate_audio=True,      # Solo Veo 3+
    resolution="1080p",        # Solo Veo 3+
    aspect_ratio="16:9"
)
```

### 3. Image-to-Video

```python
import base64

# Leer imagen
with open('imagen.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

result = client.generate_video(
    prompt="La escena cobra vida con movimiento suave",
    title="Animación desde Imagen",
    duration=6,
    input_image_base64=image_data,
    input_image_mime_type="image/jpeg",
    resize_mode="pad",         # pad o crop (Veo 3+)
    generate_audio=True
)
```

---

## 🎨 Características Avanzadas

### Reference Images

#### Asset Images (Veo 2.0-exp y Veo 3.1)
Para mantener consistencia de personajes, objetos o escenas:

```python
client = GeminiVeoClient(model_name='veo-3.1-generate-preview')

# Hasta 3 imágenes de asset
reference_images = [
    {
        "base64": image1_base64,
        "mime_type": "image/jpeg",
        "reference_type": "asset"
    },
    {
        "base64": image2_base64,
        "mime_type": "image/jpeg",
        "reference_type": "asset"
    }
]

result = client.generate_video(
    prompt="El personaje camina por una ciudad futurista",
    duration=8,  # DEBE ser 8 segundos
    reference_images=reference_images,
    generate_audio=True
)
```

#### Style Images (Solo Veo 2.0-exp)
Para transferencia de estilo artístico:

```python
client = GeminiVeoClient(model_name='veo-2.0-generate-exp')

reference_images = [
    {
        "base64": style_image_base64,
        "mime_type": "image/jpeg",
        "reference_type": "style"  # Solo Veo 2.0-exp
    }
]

result = client.generate_video(
    prompt="Un paisaje de montañas con lago",
    duration=8,
    reference_images=reference_images
)
```

⚠️ **Importante**: 
- Veo 3.1 **NO** soporta `style`, solo `asset`
- Duración **DEBE** ser 8 segundos con reference images
- Máximo 3 imágenes de asset o 1 imagen de style

### Last Frame (Fill-in-the-blank)

Genera video entre dos frames (modelos: veo-2.0-generate-001, veo-3.0-generate-preview, veo-3.1-*):

```python
client = GeminiVeoClient(model_name='veo-3.1-generate-preview')

result = client.generate_video(
    prompt="Transición suave entre los dos momentos",
    duration=8,
    input_image_base64=first_frame_base64,
    last_frame_base64=last_frame_base64,
    last_frame_mime_type="image/jpeg",
    generate_audio=True
)
```

### Video Extension

Extiende la duración de un video (modelos: veo-2.0-generate-001, veo-3.0-generate-preview):

```python
client = GeminiVeoClient(model_name='veo-3.0-generate-preview')

result = client.generate_video(
    prompt="Continúa la acción de forma natural",
    duration=8,
    video_base64=video_base64,
    video_mime_type="video/mp4",
    generate_audio=True
)
```

### Mask Editing

Añade o quita objetos usando máscaras (solo veo-2.0-generate-preview):

```python
client = GeminiVeoClient(model_name='veo-2.0-generate-preview')

result = client.generate_video(
    prompt="Un objeto mágico aparece en la escena",
    duration=8,
    input_image_base64=image_base64,
    mask_base64=mask_base64,
    mask_mime_type="image/png",
    mask_mode="foreground"  # o "background"
)
```

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Video Profesional con Todo

```python
from core.ai_services.gemini_veo import GeminiVeoClient

client = GeminiVeoClient(model_name='veo-3.1-generate-preview')

result = client.generate_video(
    # Prompt detallado
    prompt=(
        "Un chef profesional prepara un plato gourmet en una cocina moderna, "
        "plano medio, iluminación natural suave, movimiento fluido, "
        "ambiente elegante y cinematográfico"
    ),
    title="Chef Gourmet",
    
    # Configuración
    duration=8,
    aspect_ratio="16:9",
    sample_count=2,  # 2 variaciones
    
    # Mejoras
    negative_prompt="iluminación dura, colores saturados, movimiento brusco",
    enhance_prompt=True,
    
    # Veo 3.1 features
    generate_audio=True,
    resolution="1080p",
    
    # Reproducibilidad
    seed=42,
    
    # Configuración adicional
    person_generation="allow_adult",
    compression_quality="optimized"
)
```

### Ejemplo 2: Animación desde Imagen con Personaje

```python
# Imagen del personaje
with open('personaje.jpg', 'rb') as f:
    char_image = base64.b64encode(f.read()).decode('utf-8')

# Imagen de referencia para consistencia
with open('referencia.jpg', 'rb') as f:
    ref_image = base64.b64encode(f.read()).decode('utf-8')

client = GeminiVeoClient(model_name='veo-3.1-generate-preview')

result = client.generate_video(
    prompt="El personaje sonríe y saluda con la mano",
    duration=8,
    
    # Image-to-video
    input_image_base64=char_image,
    input_image_mime_type="image/jpeg",
    resize_mode="pad",
    
    # Reference image para consistencia
    reference_images=[
        {
            "base64": ref_image,
            "mime_type": "image/jpeg",
            "reference_type": "asset"
        }
    ],
    
    generate_audio=True,
    resolution="720p"
)
```

### Ejemplo 3: Consultar Estado

```python
# Consultar estado del video
status = client.get_video_status(result['video_id'])

if status['status'] == 'completed':
    print(f"✅ Video listo!")
    print(f"URL: {status['video_url']}")
    
    # Si generaste múltiples variaciones
    for idx, video in enumerate(status['all_video_urls']):
        print(f"Video {idx + 1}: {video['url']}")
        
elif status['status'] == 'processing':
    print("⏳ Aún procesando...")
    
elif status['status'] == 'failed':
    print(f"❌ Error: {status['error']}")
```

---

## 📝 Mejores Prácticas

### 1. Selección de Modelo

**Usa `veo-3.1-generate-preview`** para:
- ✅ Nuevos proyectos
- ✅ Necesitas audio
- ✅ Necesitas alta resolución
- ✅ Necesitas reference images (asset)

**Usa `veo-3.1-fast-generate-preview`** para:
- ✅ Prototipado rápido
- ✅ Iteración rápida de ideas

**Usa `veo-2.0-generate-exp`** para:
- ✅ Transferencia de estilo artístico (style images)

**Usa `veo-3.0-generate-preview`** para:
- ✅ Extensión de videos existentes

### 2. Duraciones Recomendadas

- **Veo 2**: Usa 8 segundos (más estable)
- **Veo 3**: Usa 8 segundos para mejor calidad, 6s para balance, 4s para rapidez
- **Con reference images**: SIEMPRE 8 segundos

### 3. Prompts Efectivos

✅ **Buenos prompts**:
```
"Un drone volando sobre una playa tropical al atardecer, con olas suaves 
y palmeras, iluminación dorada, movimiento cinematográfico"
```

❌ **Malos prompts**:
```
"una playa"
```

**Tips**:
- Sé específico con movimientos de cámara
- Describe la iluminación
- Menciona el estilo visual deseado
- Usa términos cinematográficos

### 4. Negative Prompts

Usa negative prompts para evitar elementos no deseados:

```python
negative_prompt="iluminación cenital, colores vivos, personas adicionales, texto"
```

### 5. Reference Images

**Para mejores resultados**:
- Usa imágenes de 720p o superior
- Mantén aspect ratio 16:9 o 9:16
- Usa imágenes claras y bien iluminadas
- Para personajes: usa diferentes ángulos del mismo personaje

### 6. Audio (Veo 3+)

El audio es generado automáticamente basado en:
- El contenido visual
- Los sonidos ambientales esperados
- La atmósfera de la escena

### 7. Resolución

- **720p**: Más rápido, menor costo
- **1080p**: Mejor calidad, más lento

### 8. Sample Count

- `sample_count=1`: Una variación
- `sample_count=2-4`: Múltiples opciones para elegir

Nota: Más muestras = más tiempo de generación

---

## 🐛 Solución de Problemas

### Error: "Duración no válida"
- **Veo 2**: Solo acepta 5-8 segundos
- **Veo 3**: Solo acepta 4, 6 u 8 segundos
- **Con reference images**: DEBE ser 8 segundos

### Error: "Modelo no soporta reference images"
- Solo `veo-2.0-generate-exp` y `veo-3.1-*` soportan reference images

### Error: "Veo 3.1 no soporta style"
- Veo 3.1 solo soporta `reference_type="asset"`
- Para `style`, usa `veo-2.0-generate-exp`

### Error: "Contenido bloqueado por filtro"
- Evita nombres de personas famosas
- Evita marcas comerciales
- Evita contenido violento/sexual
- Usa prompts más descriptivos y menos específicos

---

## 📚 Recursos Adicionales

- **Ejemplos de código**: `examples/veo_all_models_example.py`
- **Documentación de la API**: `core/ai_services/gemini_veo.py`
- **Formularios**: `core/forms.py` - `GeminiVeoVideoForm`

---

## 🔗 Enlaces Útiles

- [Documentación oficial de Veo](https://cloud.google.com/vertex-ai/docs/generative-ai/video/generate-video)
- [Vertex AI Console](https://console.cloud.google.com/vertex-ai)
- [Model Garden](https://console.cloud.google.com/vertex-ai/model-garden)

---

## 📊 Comparación Rápida

**¿Qué modelo usar?**

| Necesidad | Modelo Recomendado |
|-----------|-------------------|
| **Uso general moderno** | `veo-3.1-generate-preview` ⭐ |
| **Generación rápida** | `veo-3.1-fast-generate-preview` ⚡ |
| **Transferencia de estilo** | `veo-2.0-generate-exp` |
| **Extensión de video** | `veo-3.0-generate-preview` |
| **Edición con máscaras** | `veo-2.0-generate-preview` |
| **Sin audio (legacy)** | `veo-2.0-generate-001` |

---

**Última actualización**: Octubre 2025
**Versión del documento**: 1.0

