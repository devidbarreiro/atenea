# Generar Video: Reference Images

**Endpoint:** `generate_video(...) -> dict`
**Método:** `POST`
**Función:** `generate_video(reference_images: List[Dict], ...) -> dict`

---

## Descripción

Genera un video usando **imágenes de referencia**.
Modalidad **Reference Images**: solo disponible en Veo 2.0-exp y Veo 3.1 con tipo 'asset'.

---

## Parámetros principales

| Parámetro        | Tipo       | Descripción                                         |
| ---------------- | ---------- | --------------------------------------------------- |
| reference_images | List[Dict] | Lista de imágenes de referencia con sus metadatos   |
| prompt           | str        | Texto descriptivo opcional para guiar la generación |
| duration         | int        | Duración del video en segundos                      |
| aspect_ratio     | str        | Relación de aspecto ("16:9", "9:16")                |
| sample_count     | int        | Número de videos a generar                          |
| generate_audio   | bool       | Solo Veo 3/3.1                                      |
| resolution       | str        | Solo Veo 3/3.1 ("720p", "1080p")                    |

---

## Ejemplo (Python)

```python
client = GeminiVeoClient(model_name="veo-3.1-generate-preview")
result = client.generate_video(
    prompt="Paisaje futurista inspirado en estas imágenes",
    reference_images=[{"gcs_uri": "gs://bucket/ref1.png"}],
    duration=5
)
print(result['video_id'])
```

---

## Notas importantes

* Solo aplica para modelos compatibles con **Reference Images**.
* Retorna `video_id` para seguimiento con `get_video_status`.
