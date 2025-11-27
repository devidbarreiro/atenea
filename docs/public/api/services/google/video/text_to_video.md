# Generar Video: Text-to-Video

**Endpoint:** `generate_video(...) -> dict`
**Método:** `POST`
**Función:** `generate_video(prompt: str, ...) -> dict`

---

## Descripción

Genera un video a partir de un **prompt textual** usando Gemini Veo.
Modalidad **Text-to-Video**: solo se requiere un prompt de texto para la creación del video.

---

## Parámetros principales

| Parámetro       | Tipo | Descripción                                        |
| --------------- | ---- | -------------------------------------------------- |
| prompt          | str  | Descripción del video a generar (obligatorio)      |
| duration        | int  | Duración del video en segundos (según modelo)      |
| aspect_ratio    | str  | Relación de aspecto ("16:9", "9:16")               |
| sample_count    | int  | Número de videos a generar (1-4)                   |
| negative_prompt | str  | Qué no quieres que aparezca en el video (opcional) |
| enhance_prompt  | bool | Mejora automática del prompt (default: True)       |
| generate_audio  | bool | Solo Veo 3/3.1                                     |
| resolution      | str  | Solo Veo 3/3.1 ("720p", "1080p")                   |

---

## Ejemplo (Python)

```python
client = GeminiVeoClient(model_name="veo-3.1-generate-preview")
result = client.generate_video(
    prompt="Paisaje futurista al atardecer",
    duration=6,
    sample_count=2
)
print(result['video_id'])
```

---

## Notas importantes

* Solo requiere un **prompt textual**.
* Para videos con audio, usar Veo 3/3.1 y activar `generate_audio`.
* Retorna `video_id` para usar en `get_video_status` y `get_video_url`.
