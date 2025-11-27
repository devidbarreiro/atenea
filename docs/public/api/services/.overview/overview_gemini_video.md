# Overview - Gemini Veo API (Vertex AI)

**Base de la API:**

* Gestionada internamente por `GeminiVeoClient` con modelos `veo-2.0-*`, `veo-3.0-*` y `veo-3.1-*`.
* No hay URL pública directa; todas las llamadas se hacen a través del cliente Python (`GeminiVeoClient`) usando el modelo seleccionado.

Este documento sirve como **resumen central** de la API de generación de videos de Google Gemini dentro de nuestra aplicación.
Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python, parámetros y notas importantes.

---

## Endpoints disponibles

### Generación de video

| Nombre                                                                                      | Endpoint      | Método | Función                                                        |
| ------------------------------------------------------------------------------------------- | ------------- | ------ | -------------------------------------------------------------- |
| <a href="#" data-route="google/gemini_video/text_to_video">Text-to-Video</a>       | No disponible | POST   | `generate_video(prompt: str, ...) -> dict`                     |
| <a href="#" data-route="google/gemini_video/image_to_video">Image-to-Video</a>     | No disponible | POST   | `generate_video(input_image_gcs_uri/base64: str, ...) -> dict` |
| <a href="#" data-route="google/gemini_video/reference_images">Reference Images</a> | No disponible | POST   | `generate_video(reference_images: List[Dict], ...) -> dict`    |
| <a href="#" data-route="google/gemini_video/last_frame">Last Frame</a>             | No disponible | POST   | `generate_video(last_frame_gcs_uri/base64: str, ...) -> dict`  |
| <a href="#" data-route="google/gemini_video/video_extension">Video Extension</a>   | No disponible | POST   | `generate_video(video_gcs_uri/base64: str, ...) -> dict`       |
| <a href="#" data-route="google/gemini_video/mask">Mask (Edición)</a>               | No disponible | POST   | `generate_video(mask_gcs_uri/base64: str, ...) -> dict`        |

### Operaciones avanzadas

| Nombre               | Endpoint                                                                                     | Método | Función                                               |
| -------------------- | -------------------------------------------------------------------------------------------- | ------ | ----------------------------------------------------- |
| <a href="#" data-route="google/gemini_video/get_video_status">Estado de video</a>      | `/projects/{project}/locations/{loc}/publishers/google/models/{model}:fetchPredictOperation` | POST   | `get_video_status(operation_name: str) -> dict`       |
| <a href="#" data-route="google/gemini_video/get_video_url">Obtener URL de video</a> | No disponible                                                                                | GET    | `get_video_url(operation_name: str) -> Optional[str]` |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.
2. Revisa la columna **Endpoint** para conocer el modelo y método utilizados en la API interna de Gemini Veo.
3. Utiliza los ejemplos de Python como guía para implementar llamadas a Gemini Veo en tu aplicación.

---

## Notas generales

* Todos los endpoints requieren credenciales de **Google Cloud** con scopes para Vertex AI.
* Los videos pueden generarse con texto, imagen inicial, referencias, último frame, extensión o máscara según el modelo.
* Cada modelo tiene **restricciones específicas**: duración, soporte de audio, resolución, imágenes de referencia, extensión de video o máscara.
* Todos los endpoints de video usan `generate_video()`; no existen endpoints separados para cada tipo de generación.
* Manejar siempre errores HTTP y filtros de contenido sensible según los logs.
* La navegación dentro de la documentación funciona con enlaces `data-route` que reflejan la estructura de carpetas del proyecto.
