# Generar Video: Last Frame (Fill-in-the-Blank)

**Endpoint:** `generate_video(...) -> dict`
**Método:** `POST`
**Función:** `generate_video(last_frame_gcs_uri/base64: str, ...) -> dict`

---

## Descripción

Genera un video a partir de un **último frame** existente.
Modalidad **Last Frame**: permite continuar o completar un video (fill-in-the-blank).

---

## Parámetros principales

| Parámetro                 | Tipo | Descripción                            |
| ------------------------- | ---- | -------------------------------------- |
| last_frame_gcs_uri/base64 | str  | Último frame usado como base           |
| prompt                    | str  | Descripción de cómo continuar el video |
| duration                  | int  | Duración del video a generar           |
| aspect_ratio              | str  | Relación de aspecto                    |
| sample_count              | int  | Número de videos a generar             |
| generate_audio            | bool | Solo Veo 3/3.1                         |
| resolution                | str  | Solo Veo 3/3.1 ("720p", "1080p")       |

---

## Ejemplo (Python)

```python
client = GeminiVeoClient(model_name="veo-3.1-generate-preview")
result = client.generate_video(
    prompt="Continúa la escena del atardecer",
    last_frame_gcs_uri="gs://bucket/last_frame.png",
    duration=4
)
print(result['video_id'])
```

---

## Notas importantes

* Solo modelos compatibles soportan **Last Frame**.
* Retorna `video_id` para seguimiento con `get_video_status`.
