# Puntos de Cobro de Créditos Atenea

Este documento lista **TODOS** los lugares donde se genera contenido audiovisual y se deben cobrar créditos Atenea.

## ⚠️ IMPORTANTE

- **NO se cobran** llamadas a LLM (OpenAI GPT, Google Gemini para texto)
- **SÍ se cobran** todas las generaciones de contenido audiovisual (videos, imágenes, audios, música)

---

## 1. Generación de Videos Directos

### 1.1 VideoService.generate_video()
**Archivo**: `core/services.py` línea 660

**Puntos de cobro**:
- ✅ `_generate_heygen_video()` - HeyGen Avatar V2 o IV
- ✅ `_generate_veo_video()` - Gemini Veo
- ✅ `_generate_sora_video()` - OpenAI Sora

**Cuándo cobrar**: Cuando se marca como `completed` en `check_video_status()`

**Cálculo**:
- HeyGen Avatar V2: duración × 5 créditos/segundo
- HeyGen Avatar IV: duración × 15 créditos/segundo
- Veo 2/3: duración × 50 créditos/segundo
- Veo 3 + Audio: duración × 75 créditos/segundo
- Sora-2: duración × 10 créditos/segundo
- Sora-2 Pro: duración × 50 créditos/segundo

---

### 1.2 VideoService.check_video_status()
**Archivo**: `core/services.py` línea 872

**Puntos de cobro**:
- ✅ `_check_heygen_status()` línea 923 - cuando `video.mark_as_completed()`
- ✅ `_check_veo_status()` línea 975 - cuando `video.mark_as_completed()`
- ✅ `_check_sora_status()` línea 1050 - cuando `video.mark_as_completed()`

**Cuándo cobrar**: Cuando el video se completa exitosamente (status = 'completed')

**Datos necesarios**:
- Tipo de video (heygen_avatar_v2, heygen_avatar_iv, gemini_veo, sora)
- Duración del video (de metadata o calcular desde archivo)
- Modelo usado (para Sora: sora-2 vs sora-2-pro, para Veo: si tiene audio)

---

## 2. Generación de Imágenes

### 2.1 ImageService.generate_image()
**Archivo**: `core/services.py` línea 1476

**Puntos de cobro**:
- ✅ `generate_image_from_text()` - Text-to-image
- ✅ `generate_image_from_image()` - Image-to-image (edición)
- ✅ `generate_image_from_multiple_images()` - Multi-image (composición)

**Cuándo cobrar**: Cuando se marca como `completed` línea 1568

**Cálculo**: 
- Precio fijo: **2 créditos por imagen** (usando Imagen 4 Fast)

**Nota**: Todos los tipos de generación de imagen tienen el mismo costo.

---

## 3. Generación de Audio

### 3.1 AudioService.generate_audio()
**Archivo**: `core/services.py` línea 1753

**Puntos de cobro**:
- ✅ `text_to_speech()` - Generación básica
- ✅ `text_to_speech_with_timestamps()` - Con timestamps carácter por carácter

**Cuándo cobrar**: Cuando se marca como `completed` línea 1839

**Cálculo**:
- Por carácter procesado: **0.017 créditos por carácter**
- Ejemplo: 500 caracteres = 500 × 0.017 = **8.5 créditos** (redondeado a 9)

**Datos necesarios**:
- Longitud del texto (`audio.text`)

---

## 4. Generación de Escenas (Agente de Video)

### 4.1 SceneService.generate_preview_image()
**Archivo**: `core/services.py` línea 2137

**Puntos de cobro**:
- ✅ `generate_preview_image_with_prompt()` línea 2187 - Genera imagen preview

**Cuándo cobrar**: Cuando se marca como `completed` línea 2205

**Cálculo**: 
- **2 créditos por imagen preview**

---

### 4.2 SceneService.generate_scene_video()
**Archivo**: `core/services.py` línea 2216

**Puntos de cobro**:
- ✅ `_generate_heygen_scene_video()` línea 2268 - HeyGen V2 o IV
- ✅ `_generate_veo_scene_video()` línea 2340 - Gemini Veo
- ✅ `_generate_sora_scene_video()` línea 2379 - OpenAI Sora
- ✅ `_generate_vuela_ai_scene_video()` línea 2421 - Vuela.ai

**Cuándo cobrar**: Cuando se marca como `completed` en `check_scene_video_status()`

**Cálculo**:
- HeyGen Avatar V2: duración × 5 créditos/segundo
- HeyGen Avatar IV: duración × 15 créditos/segundo
- Veo 2/3: duración × 50 créditos/segundo
- Veo 3 + Audio: duración × 75 créditos/segundo
- Sora-2: duración × 10 créditos/segundo
- Sora-2 Pro: duración × 50 créditos/segundo
- Vuela.ai: duración × 3 créditos/segundo (orientativo)

**Datos necesarios**:
- `scene.duration_sec` - Duración de la escena
- `scene.ai_service` - Tipo de servicio usado
- `scene.ai_config` - Configuración (modelo, si tiene audio, etc.)

---

### 4.3 SceneService.generate_scene_audio()
**Archivo**: `core/services.py` (buscar método)

**Puntos de cobro**:
- ✅ Generación de audio para escenas Veo/Sora

**Cuándo cobrar**: Cuando se marca como `completed`

**Cálculo**:
- Por carácter: **0.017 créditos por carácter**
- Usar `scene.script_text` para contar caracteres

---

### 4.4 SceneService.check_scene_video_status()
**Archivo**: `core/services.py` (buscar método)

**Puntos de cobro**:
- ✅ Cuando `scene.mark_video_as_completed()` se llama

**Cuándo cobrar**: Cuando el video de escena se completa exitosamente

**Datos necesarios**:
- Duración real del video generado
- Tipo de servicio usado

---

## 5. Generación de Música

### 5.1 Music Generation (ElevenLabs Music)
**Archivo**: `core/services.py` (buscar método de música)

**Puntos de cobro**:
- ✅ Cuando se genera música con ElevenLabs Music API

**Cuándo cobrar**: Cuando se marca como `completed` línea 3916

**Cálculo**: 
- ⚠️ **PENDIENTE**: Verificar pricing de ElevenLabs Music API
- Por ahora: usar estimación basada en duración

---

## 6. Views que Llaman Generación

### 6.1 VideoGenerateView
**Archivo**: `core/views.py` línea 1120, 1332, 1509

**Flujo**:
1. Usuario hace clic en "Generar"
2. Se llama `video_service.generate_video(video)`
3. Se inicia generación (no cobrar aquí)
4. Se hace polling con `check_video_status()`
5. **COBRAR cuando se completa** en `check_video_status()`

---

### 6.2 ImageGenerateView
**Archivo**: `core/views.py` línea 1739, 1841, 1946

**Flujo**:
1. Usuario hace clic en "Generar"
2. Se llama `image_service.generate_image(image)`
3. **COBRAR cuando se completa** en `generate_image()` línea 1568

---

### 6.3 AudioGenerateView
**Archivo**: `core/views.py` línea 2083

**Flujo**:
1. Usuario hace clic en "Generar"
2. Se llama `AudioService.generate_audio(audio)`
3. **COBRAR cuando se completa** en `generate_audio()` línea 1839

---

## Resumen de Puntos de Cobro

| Servicio | Método | Línea | Cuándo Cobrar |
|----------|--------|-------|---------------|
| **Video HeyGen V2** | `VideoService._check_heygen_status()` | 923 | Al completar |
| **Video HeyGen IV** | `VideoService._check_heygen_status()` | 923 | Al completar |
| **Video Veo** | `VideoService._check_veo_status()` | 975 | Al completar |
| **Video Sora** | `VideoService._check_sora_status()` | 1050 | Al completar |
| **Imagen Gemini** | `ImageService.generate_image()` | 1568 | Al completar |
| **Audio ElevenLabs** | `AudioService.generate_audio()` | 1839 | Al completar |
| **Preview Escena** | `SceneService.generate_preview_image_with_prompt()` | 2205 | Al completar |
| **Video Escena HeyGen** | `SceneService.check_scene_video_status()` | - | Al completar |
| **Video Escena Veo** | `SceneService.check_scene_video_status()` | - | Al completar |
| **Video Escena Sora** | `SceneService.check_scene_video_status()` | - | Al completar |
| **Video Escena Vuela** | `SceneService.check_scene_video_status()` | - | Al completar |
| **Audio Escena** | `SceneService.generate_scene_audio()` | - | Al completar |
| **Música** | `MusicService.generate_music()` | 3916 | Al completar |

---

## Estrategia de Implementación

### Opción 1: Decorador/Middleware
Crear un decorador que envuelva los métodos `mark_as_completed()` para cobrar automáticamente.

### Opción 2: Servicio de Créditos
Crear `CreditService.deduct_credits()` y llamarlo explícitamente en cada punto de cobro.

### Opción 3: Signal de Django
Usar signals de Django para detectar cuando un modelo se marca como `completed` y cobrar automáticamente.

**Recomendación**: **Opción 2** (Servicio explícito) para mayor control y claridad.

---

## Próximos Pasos

1. ✅ **Completado**: Identificar todos los puntos de cobro
2. ⏳ **Pendiente**: Crear `CreditService` con métodos de cálculo
3. ⏳ **Pendiente**: Integrar cobro en cada punto identificado
4. ⏳ **Pendiente**: Crear sistema de tracking de uso
5. ⏳ **Pendiente**: Implementar rate limiting mensual



