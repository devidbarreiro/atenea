# Documentación Completa de Modelos - Parámetros de API

Este documento lista todos los modelos disponibles en Atenea con sus parámetros exactos según las llamadas a las APIs.

---

## 📹 MODELOS DE VIDEO

### 1. GEMINI VEO

#### `veo-2.0-generate-001`
**Endpoint:** `POST https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/veo-2.0-generate-001:predictLongRunning`

**Parámetros:**
```json
{
  "instances": [{
    "prompt": "string (requerido)",
    "image": {
      "gcsUri": "string (opcional)",
      "bytesBase64Encoded": "string (opcional)",
      "mimeType": "image/jpeg|image/png|image/webp"
    },
    "lastFrame": {
      "gcsUri": "string (opcional)",
      "bytesBase64Encoded": "string (opcional)",
      "mimeType": "image/jpeg"
    },
    "video": {
      "gcsUri": "string (opcional)",
      "bytesBase64Encoded": "string (opcional)",
      "mimeType": "video/mp4"
    }
  }],
  "parameters": {
    "durationSeconds": 5|6|7|8,
    "aspectRatio": "16:9"|"9:16",
    "sampleCount": 1-4,
    "personGeneration": "allow_adult"|"dont_allow",
    "compressionQuality": "optimized"|"lossless",
    "enhancePrompt": true|false,
    "negativePrompt": "string (opcional)",
    "seed": 0-4294967295 (opcional),
    "storageUri": "gs://bucket/path/ (opcional)"
  }
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ✅ Last Frame (fill-in-the-blank)
- ✅ Video Extension
- ❌ No audio
- ❌ No reference images
- ❌ No máscaras

---

#### `veo-2.0-generate-exp`
**Endpoint:** `POST .../veo-2.0-generate-exp:predictLongRunning`

**Parámetros:**
```json
{
  "instances": [{
    "prompt": "string (requerido)",
    "image": {...},
    "referenceImages": [
      {
        "image": {
          "gcsUri": "string",
          "bytesBase64Encoded": "string",
          "mimeType": "image/jpeg"
        },
        "referenceType": "asset"|"style"
      }
    ]
  }],
  "parameters": {
    "durationSeconds": 8,  // ⚠️ DEBE ser 8 cuando hay reference images
    "aspectRatio": "16:9"|"9:16",
    "sampleCount": 1-4,
    "personGeneration": "allow_adult"|"dont_allow",
    "compressionQuality": "optimized"|"lossless",
    "enhancePrompt": true|false,
    "negativePrompt": "string (opcional)",
    "seed": 0-4294967295 (opcional)
  }
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ✅ Reference Images (asset Y style)
- ❌ No audio
- ❌ No lastFrame
- ❌ No video extension

---

#### `veo-2.0-generate-preview`
**Endpoint:** `POST .../veo-2.0-generate-preview:predictLongRunning`

**Parámetros:**
```json
{
  "instances": [{
    "prompt": "string (requerido)",
    "image": {...},
    "mask": {
      "gcsUri": "string",
      "bytesBase64Encoded": "string",
      "mimeType": "image/png",
      "maskMode": "background"|"foreground"
    }
  }],
  "parameters": {
    "durationSeconds": 5|6|7|8,
    "aspectRatio": "16:9"|"9:16",
    "sampleCount": 1-4,
    "personGeneration": "allow_adult"|"dont_allow",
    "compressionQuality": "optimized"|"lossless",
    "enhancePrompt": true|false,
    "negativePrompt": "string (opcional)",
    "seed": 0-4294967295 (opcional)
  }
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ✅ Mask Editing (añadir/quitar objetos)
- ❌ No audio
- ❌ No reference images

---

#### `veo-3.0-generate-001`
**Endpoint:** `POST .../veo-3.0-generate-001:predictLongRunning`

**Parámetros:**
```json
{
  "instances": [{
    "prompt": "string (requerido)",
    "image": {...}
  }],
  "parameters": {
    "durationSeconds": 4|6|8,
    "aspectRatio": "16:9"|"9:16",
    "sampleCount": 1-4,
    "personGeneration": "allow_adult"|"dont_allow",
    "compressionQuality": "optimized"|"lossless",
    "enhancePrompt": true|false,
    "generateAudio": true|false,  // ⚠️ Requerido para Veo 3
    "resolution": "720p"|"1080p",
    "resizeMode": "pad"|"crop",  // Solo para image-to-video
    "negativePrompt": "string (opcional)",
    "seed": 0-4294967295 (opcional),
    "storageUri": "gs://bucket/path/ (opcional)"
  }
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ✅ Audio generado
- ✅ Resolución 720p/1080p
- ✅ Resize mode (pad/crop)
- ❌ No reference images
- ❌ No lastFrame
- ❌ No video extension

---

#### `veo-3.0-fast-generate-001`
**Endpoint:** `POST .../veo-3.0-fast-generate-001:predictLongRunning`

**Parámetros:** Igual que `veo-3.0-generate-001`

**Características:** Igual que `veo-3.0-generate-001` pero más rápido

---

#### `veo-3.0-generate-preview`
**Endpoint:** `POST .../veo-3.0-generate-preview:predictLongRunning`

**Parámetros:**
```json
{
  "instances": [{
    "prompt": "string (requerido)",
    "image": {...},
    "lastFrame": {...},
    "video": {...}
  }],
  "parameters": {
    "durationSeconds": 4|6|8,
    "aspectRatio": "16:9"|"9:16",
    "sampleCount": 1-4,
    "personGeneration": "allow_adult"|"dont_allow",
    "compressionQuality": "optimized"|"lossless",
    "enhancePrompt": true|false,
    "generateAudio": true|false,
    "resolution": "720p"|"1080p",
    "resizeMode": "pad"|"crop",
    "negativePrompt": "string (opcional)",
    "seed": 0-4294967295 (opcional)
  }
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ✅ Audio generado
- ✅ Resolución 720p/1080p
- ✅ Last Frame
- ✅ Video Extension
- ❌ No reference images

---

#### `veo-3.1-generate-preview`
**Endpoint:** `POST .../veo-3.1-generate-preview:predictLongRunning`

**Parámetros:**
```json
{
  "instances": [{
    "prompt": "string (requerido)",
    "image": {...},
    "referenceImages": [
      {
        "image": {
          "gcsUri": "string",
          "bytesBase64Encoded": "string",
          "mimeType": "image/jpeg"
        },
        "referenceType": "asset"  // ⚠️ Solo "asset", NO "style"
      }
    ],
    "lastFrame": {...}
  }],
  "parameters": {
    "durationSeconds": 8,  // ⚠️ DEBE ser 8 cuando hay reference images
    "aspectRatio": "16:9"|"9:16",
    "sampleCount": 1-4,
    "personGeneration": "allow_adult"|"dont_allow",
    "compressionQuality": "optimized"|"lossless",
    "enhancePrompt": true|false,
    "generateAudio": true|false,
    "resolution": "720p"|"1080p",
    "resizeMode": "pad"|"crop",
    "negativePrompt": "string (opcional)",
    "seed": 0-4294967295 (opcional)
  }
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ✅ Audio generado
- ✅ Resolución 720p/1080p
- ✅ Reference Images (solo Asset, no Style)
- ✅ Last Frame
- ❌ No video extension

---

#### `veo-3.1-fast-generate-preview`
**Endpoint:** `POST .../veo-3.1-fast-generate-preview:predictLongRunning`

**Parámetros:** Igual que `veo-3.1-generate-preview`

**Características:** Igual que `veo-3.1-generate-preview` pero más rápido

---

### 2. OPENAI SORA

#### `sora-2`
**Endpoint:** `POST https://api.openai.com/v1/videos`

**Parámetros (text-to-video):**
```json
{
  "model": "sora-2",
  "prompt": "string (requerido)",
  "seconds": "4"|"8"|"12",  // ⚠️ String, no int
  "size": "1280x720"|"720x1280"|"1024x1024"
}
```

**Parámetros (image-to-video con multipart/form-data):**
```
POST /v1/videos
Content-Type: multipart/form-data

model: "sora-2"
prompt: "string"
seconds: "4"|"8"|"12"
size: "1280x720"|"720x1280"|"1024x1024"
input_reference: <file>  // ⚠️ Imagen debe tener exactamente las mismas dimensiones que size
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video (con input_reference usando multipart/form-data)
- ❌ No audio
- ❌ No negative prompt
- ❌ No seed

**Nota:** Sora sí soporta image-to-video mediante el método `generate_video_with_image()` que usa multipart/form-data.

---

#### `sora-2-pro`
**Endpoint:** `POST https://api.openai.com/v1/videos`

**Parámetros:** Igual que `sora-2`

**Características:** Igual que `sora-2` pero mayor calidad

---

### 3. HEYGEN AVATAR V2

**Endpoint:** `POST https://api.heygen.com/v2/video/generate`

**Parámetros:**
```json
{
  "video_inputs": [
    {
      "character": {
        "type": "avatar",
        "avatar_id": "string (requerido)",
        "avatar_style": "normal",
        "scale": 1.0
      },
      "voice": {
        "type": "text",
        "input_text": "string (requerido)",
        "voice_id": "string (requerido)",
        "speed": 0.5-2.0,
        "pitch": 0-100,
        "emotion": "Excited"|"Serious"|"Friendly"|"Soothing"|"Broadcaster"
      },
      "background": {
        "type": "image",
        "url": "string (opcional)"
      }
    }
  ],
  "dimension": {
    "width": 1280,
    "height": 720
  },
  "aspect_ratio": "16:9"|"9:16",
  "caption": true|false,
  "title": "string"
}
```

**Características:**
- ✅ Text-to-video con avatar
- ✅ Audio incluido
- ✅ Controles de voz avanzados
- ✅ Fondo opcional
- ❌ No image-to-video

---

### 4. HEYGEN AVATAR IV

**Endpoint:** `POST https://api.heygen.com/v2/video/av4/generate`

**Parámetros:**
```json
{
  "image_key": "string (requerido)",  // Obtenido de upload de asset
  "video_title": "string",
  "script": "string (requerido)",
  "voice_id": "string (requerido)",
  "video_orientation": "portrait"|"landscape",
  "fit": "cover"|"contain"
}
```

**Características:**
- ✅ Image-to-video con avatar desde imagen
- ✅ Audio incluido
- ❌ No text-to-video directo

---

### 5. KLING AI

#### `kling-v1`, `kling-v1-5`, `kling-v1-6`, `kling-v2-1`, `kling-v2-5-turbo`
**Endpoint:** `POST https://api.klingai.com/v1/video/generate`

**Parámetros:**
```json
{
  "model_name": "kling-v1"|"kling-v1-5"|"kling-v1-6"|"kling-v2-1"|"kling-v2-5-turbo",
  "mode": "std"|"pro",  // ⚠️ Requerido para estos modelos
  "duration": 5|10,
  "aspect_ratio": "16:9"|"9:16",
  "prompt": "string (requerido para text-to-video)",
  "image_url": "string (requerido para image-to-video)"
}
```

**Características por modelo:**
- `kling-v1`: ✅ Text-to-video, ✅ Image-to-video, Resolución: std=720p, pro=720p
- `kling-v1-5`: ❌ Text-to-video, ✅ Image-to-video, Resolución: std=720p, pro=1080p
- `kling-v1-6`: ✅ Text-to-video, ✅ Image-to-video, Resolución: std=720p, pro=1080p
- `kling-v2-1`: ❌ Text-to-video, ✅ Image-to-video, Resolución: std=720p, pro=1080p
- `kling-v2-5-turbo`: ✅ Text-to-video, ✅ Image-to-video, Resolución: std=1080p, pro=1080p

---

#### `kling-v2-master`
**Endpoint:** `POST https://api.klingai.com/v1/video/generate`

**Parámetros:**
```json
{
  "model_name": "kling-v2-master",
  "duration": 5|10,
  "aspect_ratio": "16:9"|"9:16",
  "prompt": "string (requerido para text-to-video)",
  "image_url": "string (requerido para image-to-video)"
}
```

**Características:**
- ✅ Text-to-video
- ✅ Image-to-video
- ❌ No modos STD/PRO
- Resolución: 720p

---

### 6. HIGGSFIELD

#### `higgsfield-ai/dop/standard`
**Endpoint:** `POST https://platform.higgsfield.ai/higgsfield-ai/dop/standard`

**Parámetros:**
```json
{
  "prompt": "string (requerido)",
  "image_url": "string (requerido)",  // ⚠️ Requerido para image-to-video
  "aspect_ratio": "16:9"|"9:16"|"1:1" (opcional),
  "resolution": "720p" (opcional),
  "duration": 3 (opcional)
}
```

**Características:**
- ❌ Text-to-video
- ✅ Image-to-video
- Duración fija: 3 segundos
- Resolución: 720p

---

#### `higgsfield-ai/dop/preview`
**Endpoint:** `POST https://platform.higgsfield.ai/higgsfield-ai/dop/preview`

**Parámetros:** Igual que `higgsfield-ai/dop/standard`

**Características:** Igual que `dop/standard` pero más rápido

---

#### `bytedance/seedance/v1/pro/image-to-video`
**Endpoint:** `POST https://platform.higgsfield.ai/bytedance/seedance/v1/pro/image-to-video`

**Parámetros:**
```json
{
  "prompt": "string (requerido)",
  "image_url": "string (requerido)",
  "aspect_ratio": "16:9"|"9:16"|"1:1" (opcional),
  "resolution": "1080p" (opcional),
  "duration": 5 (opcional)
}
```

**Características:**
- ❌ Text-to-video
- ✅ Image-to-video
- Duración fija: 5 segundos
- Resolución: 1080p

---

#### `kling-video/v2.1/pro/image-to-video`
**Endpoint:** `POST https://platform.higgsfield.ai/kling-video/v2.1/pro/image-to-video`

**Parámetros:** Igual que `bytedance/seedance/v1/pro/image-to-video`

**Características:** Igual que `seedance/v1/pro`

---

### 7. VUELA.AI

**Endpoint:** `POST https://api.vuela.ai/generate/video`

**Parámetros:**
```json
{
  "mode": "single_voice"|"scenes"|"avatar",
  "video_script": "string (requerido)",
  "aspect_ratio": "16:9"|"9:16",
  "animation_type": "moving_image"|"ai_video",
  "quality_tier": "basic"|"premium",
  "language": "es",
  "country": "ES",
  
  // Para single_voice y avatar:
  "voice_id": "string (requerido)",
  "voice_style": "narrative"|"expressive"|"dynamic",
  "voice_speed": "standard"|"fast"|"very_fast",
  
  // Para scenes:
  "voices": [
    {"character": "Personaje1", "voice_id": "ID1"},
    {"character": "Personaje2", "voice_id": "ID2"}
  ],
  
  // Para media (si mode != avatar o avatar_layout == 'combined'):
  "media_type": "ai_image"|"google_image"|"custom_image",
  "style": "photorealistic"|"custom",
  "style_id": "string (si style == 'custom')",
  "images_per_minute": 8-40,
  "custom_images_urls": ["url1", "url2"] (si media_type == 'custom_image'),
  
  // Para avatar:
  "avatar_id": "string (requerido)",
  "avatar_layout": "full_screen"|"combined",
  "avatar_layout_style": "string (si layout == 'combined')",
  "avatar_layout_options": {} (si layout_style == 'presentation'),
  
  // Subtítulos:
  "add_subtitles": true|false,
  "caption_font": "Roboto"|"custom",
  "caption_alignment": "bottom",
  "subtitle_highlight_color": "string (opcional)",
  "subtitle_stroke_width": 0,
  "subtitle_highlight_mode": "string (opcional)",
  "caption_font_url": "string (si caption_font == 'custom')",
  
  // Música:
  "add_background_music": true|false,
  "background_music_id": "string (si add_background_music == true)"
}
```

**Características:**
- ✅ Text-to-video con múltiples modos
- ✅ Audio incluido
- ✅ Subtítulos opcionales
- ✅ Música de fondo opcional
- ❌ No image-to-video directo

---

## 🖼️ MODELOS DE IMAGEN

### 1. GEMINI IMAGE

**Modelo:** `gemini-2.5-flash-image`

**Endpoint:** `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent`

**Parámetros (text-to-image):**
```json
{
  "contents": ["string (prompt)"],
  "generationConfig": {
    "imageConfig": {
      "aspectRatio": "1:1"|"2:3"|"3:2"|"3:4"|"4:3"|"4:5"|"5:4"|"9:16"|"16:9"|"21:9"
    },
    "responseModalities": ["Text", "Image"] | ["Image"]
  }
}
```

**Parámetros (image-to-image):**
```json
{
  "contents": [
    "string (instrucciones de edición)",
    <PIL.Image object>
  ],
  "generationConfig": {
    "imageConfig": {
      "aspectRatio": "1:1"|"2:3"|"3:2"|"3:4"|"4:3"|"4:5"|"5:4"|"9:16"|"16:9"|"21:9"
    },
    "responseModalities": ["Text", "Image"] | ["Image"]
  }
}
```

**Parámetros (multi-image):**
```json
{
  "contents": [
    "string (instrucciones de composición)",
    <PIL.Image object 1>,
    <PIL.Image object 2>,
    <PIL.Image object 3> (opcional)
  ],
  "generationConfig": {
    "imageConfig": {
      "aspectRatio": "1:1"|"2:3"|"3:2"|"3:4"|"4:3"|"4:5"|"5:4"|"9:16"|"16:9"|"21:9"
    },
    "responseModalities": ["Text", "Image"] | ["Image"]
  }
}
```

**Aspect Ratios y Dimensiones:**
- `1:1`: 1024×1024
- `2:3`: 832×1248
- `3:2`: 1248×832
- `3:4`: 864×1184
- `4:3`: 1184×864
- `4:5`: 896×1152
- `5:4`: 1152×896
- `9:16`: 768×1344
- `16:9`: 1344×768
- `21:9`: 1536×672

---

### 2. HIGGSFIELD IMAGE

#### `higgsfield-ai/soul/standard`
**Endpoint:** `POST https://platform.higgsfield.ai/higgsfield-ai/soul/standard`

**Parámetros:**
```json
{
  "prompt": "string (requerido)",
  "aspect_ratio": "1:1"|"16:9"|"9:16" (opcional)
}
```

**Características:**
- ✅ Text-to-image
- ❌ No image-to-image

---

#### `reve/text-to-image`
**Endpoint:** `POST https://platform.higgsfield.ai/reve/text-to-image`

**Parámetros:** Igual que `higgsfield-ai/soul/standard`

**Características:** Igual que `soul/standard`

---

## 🎵 MODELOS DE AUDIO

### 1. ELEVENLABS TTS

**Endpoint:** `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={format}`

**Parámetros:**
```json
{
  "text": "string (requerido)",
  "model_id": "eleven_turbo_v2_5"|"eleven_multilingual_v2"|...,
  "language_code": "es"|"en"|...,
  "voice_settings": {
    "stability": 0.0-1.0,
    "similarity_boost": 0.0-1.0,
    "style": 0.0-1.0,
    "speed": 0.25-4.0
  },
  "seed": 0-4294967295 (opcional),
  "previous_text": "string (opcional)",
  "next_text": "string (opcional)"
}
```

**Formatos de salida:**
- `mp3_44100_128`
- `mp3_44100_192`
- `mp3_44100_224`
- `mp3_44100_320`
- `pcm_16000`
- `pcm_22050`
- `pcm_24000`
- `pcm_44100`
- `ulaw_8000`

**Características:**
- ✅ Text-to-Speech
- ✅ Múltiples voces
- ✅ Controles avanzados de voz
- ✅ Timestamps opcionales

---

## 📊 RESUMEN DE CAPACIDADES

### Videos
| Modelo | Text-to-Video | Image-to-Video | Audio | Resolución | Referencias | Duración |
|--------|---------------|----------------|-------|------------|-------------|----------|
| Veo 2.0 | ✅ | ✅ | ❌ | Fija | ❌ | 5-8s |
| Veo 2.0-exp | ✅ | ✅ | ❌ | Fija | ✅ (asset/style) | 8s |
| Veo 2.0-preview | ✅ | ✅ | ❌ | Fija | ❌ | 5-8s |
| Veo 3.0 | ✅ | ✅ | ✅ | 720p/1080p | ❌ | 4/6/8s |
| Veo 3.0 Fast | ✅ | ✅ | ✅ | 720p/1080p | ❌ | 4/6/8s |
| Veo 3.0 Preview | ✅ | ✅ | ✅ | 720p/1080p | ❌ | 4/6/8s |
| Veo 3.1 Preview | ✅ | ✅ | ✅ | 720p/1080p | ✅ (asset) | 4/6/8s |
| Veo 3.1 Fast Preview | ✅ | ✅ | ✅ | 720p/1080p | ✅ (asset) | 4/6/8s |
| Sora 2 | ✅ | ✅ | ❌ | 720p/1080p | ❌ | 4/8/12s |
| Sora 2 Pro | ✅ | ✅ | ❌ | 720p/1080p | ❌ | 4/8/12s |
| HeyGen V2 | ✅ | ❌ | ✅ | Variable | ❌ | Variable |
| HeyGen IV | ✅ | ✅ | ✅ | Variable | ❌ | Variable |
| Kling V1 | ✅ | ✅ | ❌ | 720p | ❌ | 5/10s |
| Kling V1.5 | ❌ | ✅ | ❌ | 720p/1080p | ❌ | 5/10s |
| Kling V1.6 | ✅ | ✅ | ❌ | 720p/1080p | ❌ | 5/10s |
| Kling V2.1 | ❌ | ✅ | ❌ | 720p/1080p | ❌ | 5/10s |
| Kling V2.5 Turbo | ✅ | ✅ | ❌ | 1080p | ❌ | 5/10s |
| Kling V2 Master | ✅ | ✅ | ❌ | 720p | ❌ | 5/10s |
| Higgsfield DoP Standard | ❌ | ✅ | ❌ | 720p | ❌ | 3s |
| Higgsfield DoP Preview | ❌ | ✅ | ❌ | 720p | ❌ | 3s |
| Higgsfield Seedance V1 Pro | ❌ | ✅ | ❌ | 1080p | ❌ | 5s |
| Higgsfield Kling V2.1 Pro | ❌ | ✅ | ❌ | 1080p | ❌ | 5s |
| Vuela.ai | ✅ | ❌ | ✅ | Variable | ❌ | Variable |

### Imágenes
| Modelo | Text-to-Image | Image-to-Image | Multi-Image | Aspect Ratios |
|--------|---------------|----------------|-------------|---------------|
| Gemini 2.5 Flash | ✅ | ✅ | ✅ | 10 opciones |
| Higgsfield Soul | ✅ | ❌ | ❌ | 3 opciones |
| Reve | ✅ | ❌ | ❌ | 3 opciones |

### Audio
| Modelo | Text-to-Speech | Voces | Idiomas | Formatos |
|--------|----------------|-------|---------|-----------|
| ElevenLabs | ✅ | Múltiples | Múltiples | 9 formatos |

