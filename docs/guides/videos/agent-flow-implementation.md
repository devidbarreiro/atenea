# Implementación del Flujo de Agente de Video

## 📋 Resumen Ejecutivo

El **Flujo de Agente de Video** es un sistema completo de 4 pasos que permite crear videos profesionales multi-escena usando IA. El sistema:

1. ✅ Analiza un guión con IA (n8n)
2. ✅ Divide automáticamente en escenas optimizadas
3. ✅ Genera preview images con Gemini
4. ✅ Genera videos para cada escena (HeyGen/Veo/Sora)
5. ✅ Combina todos los videos con FFmpeg

---

## 🎯 Flujo de Usuario

### Paso 1: Contenido (`/projects/{id}/agent/create/`)
- Usuario escribe o pega su guión
- Selecciona duración deseada
- **Próximamente:** Subir PDF

### Paso 2: Configurar (`/projects/{id}/agent/configure/`)
- Sistema envía guión a n8n para análisis
- n8n procesa con IA y retorna escenas
- Sistema crea objetos `Scene` en BD
- Genera preview images con Gemini (automático)
- Usuario revisa escenas y puede ajustar:
  - Servicio de IA (Veo/Sora/HeyGen)
  - Configuración específica (duración, aspecto, avatar, voz)
  - **Próximamente:** Editar texto del guión

### Paso 3: Escenas (`/projects/{id}/agent/scenes/`)
- Sistema genera automáticamente video para cada escena
- Polling cada 5s para actualizar estados
- Muestra videos cuando están listos
- **Próximamente:** Regenerar escenas individuales
- Continuar cuando todas están completadas

### Paso 4: Final (`/projects/{id}/agent/final/`)
- Muestra preview de todas las escenas
- Usuario ingresa título del video final
- Click "Combinar con FFmpeg"
- Sistema:
  1. Descarga videos de GCS
  2. Combina con FFmpeg
  3. Sube resultado a GCS
  4. Crea objeto `Video`
  5. Asocia con `Script`
- Redirige a detalle del video

---

## 🗂️ Modelos de Datos

### Script (Actualizado)
```python
class Script(models.Model):
    # ... campos existentes ...
    agent_flow = BooleanField(default=False)  # Identifica scripts del agente
    final_video = ForeignKey(Video, ...)      # Video final combinado
```

### Scene (Nuevo)
```python
class Scene(models.Model):
    # Relaciones
    script = ForeignKey(Script, related_name='db_scenes')
    project = ForeignKey(Project, related_name='scenes')
    
    # Datos de la escena (desde n8n)
    scene_id, summary, script_text, duration_sec, avatar, platform
    broll, transition, text_on_screen, audio_notes
    order, is_included
    
    # Preview image
    preview_image_gcs_path, preview_image_status, preview_image_error
    
    # Configuración IA
    ai_service, ai_config
    
    # Video generado
    video_gcs_path, video_status, external_id, error_message
    
    # Versiones (próximamente)
    version, parent_scene
```

---

## 🔧 Servicios

### SceneService
- `create_scenes_from_n8n_data()`: Crea Scenes desde webhook
- `generate_preview_image()`: Genera preview con Gemini
- `generate_scene_video()`: Genera video según servicio
- `check_scene_video_status()`: Consulta estado en APIs externas
- `get_scene_with_signed_urls()`: Obtiene URLs firmadas

### VideoCompositionService
- `combine_scene_videos()`: Combina con FFmpeg
- `get_video_duration()`: Obtiene duración con FFprobe

### N8nService (Extendido)
- Detecta `agent_flow=True`
- Crea escenas automáticamente
- Inicia generación de previews

---

## 🛣️ URLs

```python
# Flujo principal
/projects/<id>/agent/create/      # Paso 1: Contenido
/projects/<id>/agent/configure/   # Paso 2: Configurar
/projects/<id>/agent/scenes/      # Paso 3: Escenas
/projects/<id>/agent/final/       # Paso 4: Final

# Acciones de escenas
/scenes/<id>/generate/            # Generar video
/scenes/<id>/status/              # Consultar estado (API)
/scenes/<id>/regenerate/          # Regenerar (próximamente)
```

---

## 🎨 Templates

- `templates/agent/create.html`: Paso 1
- `templates/agent/configure.html`: Paso 2
- `templates/agent/scenes.html`: Paso 3
- `templates/agent/final.html`: Paso 4

Todos incluyen:
- Progress bar de 4 pasos
- Breadcrumbs
- Manejo de errores
- Loading states
- Polling cuando necesario

---

## 📡 Integración con n8n

### Request a n8n:
```json
{
  "script_id": 123,
  "guion": "Texto del guión...",
  "duracion_minutos": 5
}
```

### Response esperada:
```json
{
  "status": "success",
  "script_id": 123,
  "project": {
    "platform_mode": "mixto",
    "num_scenes": 3,
    "language": "es",
    "total_estimated_duration_min": 5
  },
  "scenes": [
    {
      "id": "Escena 1",
      "duration_sec": 45,
      "summary": "...",
      "script_text": "...",
      "avatar": "si",
      "platform": "heygen",
      "broll": [...],
      "transition": "fundido",
      "text_on_screen": "...",
      "audio_notes": "..."
    }
  ]
}
```

Ver: `docs/guides/videos/n8n-agent-prompt.md`

---

## 🔄 Polling y Estados

### Script Status (Paso 2)
- Poll cada 3 segundos
- Endpoint: `/scripts/{id}/status-partial/`
- Máximo: 60 polls (3 minutos)
- Cuando completa: Redirige con `script_id`

### Scene Status (Paso 3)
- Poll cada 5 segundos
- Endpoint: `/scenes/{id}/status/`
- Retorna JSON con `video_status`, `preview_status`, `video_url`
- Recarga página cuando hay cambios para mostrar videos

### Estados posibles:
- `pending`: No iniciado
- `processing`: En proceso
- `completed`: Completado
- `error`: Error (con mensaje)

---

## 🎬 Generación de Videos

### Por Escena:

**HeyGen:**
```python
# Usa HeyGenClient.generate_video()
# Requiere: avatar_id, voice_id
# Config: voice_speed, voice_pitch, voice_emotion
```

**Gemini Veo:**
```python
# Usa GeminiVeoClient.generate_video()
# Duración: 5-8s (máx 8s)
# Config: veo_model, aspect_ratio, sample_count
```

**Sora:**
```python
# Usa SoraClient.generate_video()
# Duración: 4-12s
# Config: sora_model, size
```

### Combinación Final:

**FFmpeg:**
```bash
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy output.mp4
```

- Descarga videos de GCS a temp
- Crea archivo concat con lista
- Ejecuta FFmpeg con `-c copy` (sin re-encode)
- Sube resultado a GCS
- Limpia archivos temporales

---

## 🔑 Variables de Entorno Requeridas

```env
# IA Services
GEMINI_API_KEY=your_key_here
HEYGEN_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Storage
GCS_BUCKET_NAME=your_bucket_name

# Redis (para n8n)
REDIS_URL=redis://host:port
REDIS_PASSWORD=your_password
```

---

## 📊 Estructura de GCS

```
gs://bucket/
├── scene_previews/
│   └── project_{id}/
│       └── scene_{id}/
│           └── {timestamp}_preview.png
├── projects/
│   └── {project_id}/
│       ├── scenes/
│       │   └── {scene_id}/
│       │       └── video.mp4
│       └── combined_videos/
│           └── {timestamp}_{title}.mp4
```

---

## 🐛 Troubleshooting

### Preview images no se generan
- Verificar `GEMINI_API_KEY`
- Revisar logs: `logs/atenea.log`
- Verificar permisos de GCS

### Videos de escenas fallan
- Verificar API keys de cada servicio
- Verificar configuración de escena (avatar_id, voice_id para HeyGen)
- Revisar external_id en BD

### FFmpeg falla al combinar
- Verificar FFmpeg instalado: `ffmpeg -version`
- Revisar logs para ver error específico
- Verificar que todos los videos tengan mismo codec
- Si fallan diferentes codecs, cambiar a re-encode:
  ```python
  '-c:v', 'libx264', '-c:a', 'aac'  # En lugar de '-c', 'copy'
  ```

### Polling no funciona
- Verificar que Redis esté corriendo
- Verificar endpoints de status en DevTools
- Revisar console logs del navegador

---

## 🚀 Próximas Mejoras

### Alta Prioridad:
- [ ] Upload PDF (extraer texto con PyPDF2)
- [ ] Editar texto de escena
- [ ] Regenerar escenas individuales
- [ ] Replace preview image

### Media Prioridad:
- [ ] Generación async de previews con Celery
- [ ] Generación paralela de videos (con rate limiting)
- [ ] Transiciones visuales con FFmpeg
- [ ] Thumbnails para videos de escenas

### Baja Prioridad:
- [ ] Re-ordenar escenas (drag & drop)
- [ ] Duplicar escenas
- [ ] Presets de configuración por servicio
- [ ] Export/Import de configuraciones

---

## 📝 Testing

### Test Manual:
1. Ir a un proyecto
2. Click "✨ Generar Video con Agente"
3. Escribir guión de prueba (2-3 minutos)
4. Esperar procesamiento de n8n
5. Verificar escenas creadas
6. Verificar preview images generadas
7. Configurar servicios de IA
8. Continuar a Escenas
9. Esperar generación de videos
10. Verificar polling y actualización de UI
11. Continuar a Final
12. Ingresar título
13. Combinar con FFmpeg
14. Verificar video final

### Casos de Prueba:
- ✅ Guión corto (1-2 min) → 2-3 escenas
- ✅ Guión medio (3-5 min) → 5-7 escenas
- ✅ Guión largo (5-10 min) → 10-15 escenas
- ✅ Solo HeyGen (avatar en todas)
- ✅ Solo Veo/Sora (sin avatar)
- ✅ Mixto (alternando servicios)
- ✅ Manejo de errores en APIs
- ✅ Timeout de n8n

---

## 🔗 Referencias

- Prompt de n8n: `docs/guides/videos/n8n-agent-prompt.md`
- Modelos: `core/models.py` (líneas 418-620)
- Servicios: `core/services.py` (SceneService, VideoCompositionService)
- Vistas: `core/views.py` (AgentCreateView, AgentConfigureView, etc.)
- Templates: `templates/agent/*.html`

