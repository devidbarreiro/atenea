# Quick Start - API de Atenea

Comienza a usar la API de Atenea en 5 minutos.

## Paso 1: Autenticación

Todas las solicitudes a la API requieren autenticación mediante sesión de usuario (Django).

## Paso 2: Crear tu Primer Video

### Con Gemini Veo

```python
from core.services import VideoService
from core.models import Video, Project

# Crear video
video = Video.objects.create(
    title="Mi primer video",
    type="gemini_veo",
    script="Un hermoso atardecer sobre el océano",
    created_by=request.user,
    project=project  # Opcional
)

# Generar
service = VideoService()
service.generate_video(video)
```

### Con HeyGen Avatar

```python
video = Video.objects.create(
    title="Video con avatar",
    type="heygen_avatar_v2",
    script="Hola, este es mi primer video con avatar",
    config={
        "avatar_id": "your_avatar_id",
        "voice_id": "your_voice_id"
    },
    created_by=request.user
)

service = VideoService()
service.generate_video(video)
```

## Paso 3: Crear tu Primera Imagen

```python
from core.services import ImageService
from core.models import Image

image = Image.objects.create(
    title="Mi primera imagen",
    type="text_to_image",
    prompt="Un paisaje futurista con montañas y un cielo estrellado",
    created_by=request.user
)

service = ImageService()
service.generate_image(image)
```

## Paso 4: Crear tu Primer Audio

```python
from core.services import AudioService
from core.models import Audio

audio = Audio.objects.create(
    title="Mi primer audio",
    text="Este es el texto que quiero convertir a voz",
    voice_id="elevenlabs_voice_id",
    voice_name="Voice Name",
    created_by=request.user
)

service = AudioService()
service.generate_audio(audio)
```

## Paso 5: Verificar Estado

```python
# Para videos
if video.status == 'completed':
    print(f"Video listo: {video.gcs_path}")

# Para imágenes
if image.status == 'completed':
    print(f"Imagen lista: {image.gcs_path}")

# Para audios
if audio.status == 'completed':
    print(f"Audio listo: {audio.gcs_path}")
```

## Servicios Disponibles

### Video Generation
- **[Google Gemini Veo](../services/google/video/)** - Videos cinematográficos
- **[OpenAI Sora](../services/openai/video/)** - Videos con efectos
- **[HeyGen](../services/heygen/video/)** - Avatares hablantes
- **[Vuela.ai](../services/vuela/video/)** - Videos con scripts
- **[Manim](../services/manim/video/)** - Videos animados con citas

### Image Generation
- **[Google Gemini Image](../services/google/image/)** - Generación de imágenes

### Audio Generation
- **[ElevenLabs TTS](../services/elevenlabs/tts/)** - Texto a voz

## Próximos Pasos

- Explora la [documentación completa de servicios](../services/)
- Consulta el [sistema de créditos](../system/credits.md)
- Revisa ejemplos específicos en cada servicio

---

**¿Necesitas ayuda?** Consulta la [Guía de Usuario](../../app/GUIA_USUARIO.md) o la documentación específica de cada servicio.

