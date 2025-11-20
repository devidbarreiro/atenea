# Generar Video: Image-to-Video

**Endpoint:** `generate_video(...) -> dict`
**Método:** `POST`
**Función:** `generate_video(input_image_gcs_uri/base64: str, ...) -> dict`

---

## Descripción

Genera un video a partir de una **imagen inicial**.
Modalidad **Image-to-Video**: se utiliza una imagen como base para la animación.

---

## Parámetros principales

| Parámetro                  | Tipo | Descripción                                        |
| -------------------------- | ---- | -------------------------------------------------- |
| input_image_gcs_uri/base64 | str  | Imagen inicial (GCS o Base64)                      |
| input_image_mime_type      | str  | Tipo MIME de la imagen ("image/jpeg", "image/png") |
| duration                   | int  | Duración del video en segundos                     |
| aspect_ratio               | str  | Relación de aspecto ("16:9", "9:16")               |
| sample_count               | int  | Número de videos a generar                         |
| resize_mode                | str  | Solo Veo 3 image-to-video ("pad", "crop")          |
| generate_audio             | bool | Solo Veo 3/3.1                                     |
| resolution                 | str  | Solo Veo 3/3.1 ("720p", "1080p")                   |

---

## Ejemplo (Python)

```python
client = GeminiVeoClient(model_name="veo-3.0-generate-preview")
result = client.generate_video(
    prompt="Animar esta ilustración futurista",
    input_image_gcs_uri="gs://bucket/imagen_inicial.jpg",
    duration=6
)
print(result['video_id'])
```

---

## Notas importantes

* Requiere imagen inicial (`input_image_gcs_uri` o `input_image_base64`).
* `resize_mode` solo aplica para Veo 3 image-to-video.
* Retorna `video_id` para seguimiento con `get_video_status`.
