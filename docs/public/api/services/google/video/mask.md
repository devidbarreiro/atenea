no# Generar Video: Mask (Edición)

**Endpoint:** `generate_video(...) -> dict`
**Método:** `POST`
**Función:** `generate_video(mask_gcs_uri/base64: str, ...) -> dict`

---

## Descripción

Permite **editar un video existente usando máscara**.
Modalidad **Mask**: solo disponible en Veo 2.0-preview.

---

## Parámetros principales

| Parámetro            | Tipo | Descripción                               |
| -------------------- | ---- | ----------------------------------------- |
| video_gcs_uri/base64 | str  | Video a editar                            |
| mask_gcs_uri/base64  | str  | Máscara para determinar zonas a modificar |
| mask_mode            | str  | "background" o "foreground"               |
| prompt               | str  | Descripción de los cambios deseados       |
| duration             | int  | Duración del video a generar              |
| aspect_ratio         | str  | Relación de aspecto                       |
| sample_count         | int  | Número de videos a generar                |

---

## Ejemplo (Python)

```python
client = GeminiVeoClient(model_name="veo-2.0-preview")
result = client.generate_video(
    prompt="Cambiar el cielo a un atardecer naranja",
    video_gcs_uri="gs://bucket/video_base.mp4",
    mask_gcs_uri="gs://bucket/mask.png",
    mask_mode="background",
    duration=6
)
print(result['video_id'])
```

---

## Notas importantes

* Solo modelos Veo 2.0-preview soportan **Mask**.
* Retorna `video_id` para seguimiento con `get_video_status`.
