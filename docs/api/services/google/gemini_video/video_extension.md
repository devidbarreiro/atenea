# Generar Video: Video Extension

**Endpoint:** `generate_video(...) -> dict`
**Método:** `POST`
**Función:** `generate_video(video_gcs_uri/base64: str, ...) -> dict`

---

## Descripción

Extiende un video existente agregando frames adicionales.
Modalidad **Video Extension**: permite alargar un video previamente generado.

---

## Parámetros principales

| Parámetro            | Tipo | Descripción                            |
| -------------------- | ---- | -------------------------------------- |
| video_gcs_uri/base64 | str  | Video existente a extender             |
| prompt               | str  | Descripción de cómo continuar el video |
| duration             | int  | Duración a agregar en segundos         |
| aspect_ratio         | str  | Relación de aspecto                    |
| sample_count         | int  | Número de videos a generar             |
| generate_audio       | bool | Solo Veo 3/3.1                         |
| resolution           | str  | Solo Veo 3/3.1 ("720p", "1080p")       |

---

## Ejemplo (Python)

```python
client = GeminiVeoClient(model_name="veo-3.1-generate-preview")
result = client.generate_video(
    prompt="Extiende el video con un cielo estrellado",
    video_gcs_uri="gs://bucket/video_base.mp4",
    duration=5
)
print(result['video_id'])
```

---

## Notas importantes

* Solo modelos compatibles soportan **Video Extension**.
* Retorna `video_id` para seguimiento con `get_video_status`.
