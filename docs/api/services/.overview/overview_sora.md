# Overview - Sora API (OpenAI)

**Base de la API:**

* Gestionada internamente por `SoraClient` usando los endpoints de OpenAI Sora.
* Base URL: `https://api.openai.com/v1`
* Todas las llamadas requieren **API Key de OpenAI Sora**.

Este documento sirve como **resumen central** de la API de Sora dentro de nuestra aplicación.
Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python y parámetros importantes.

---

## Endpoints disponibles

### Generación de video

| Nombre                                                                                       | Endpoint       | Método | Función                                                                          |
| -------------------------------------------------------------------------------------------- | -------------- | ------ | -------------------------------------------------------------------------------- |
| <a href="#" data-route="openai/video/generate_video">Generar video</a>                       | `POST /videos` | POST   | `generate_video(prompt: str, model: str, ...) -> dict`                           |
| <a href="#" data-route="openai/video/generate_video_with_image">Generar video con imagen</a> | `POST /videos` | POST   | `generate_video_with_image(prompt: str, input_reference_path: str, ...) -> dict` |

### Operaciones avanzadas

| Nombre                                                                             | Endpoint                                           | Método | Función                                                             |
| ---------------------------------------------------------------------------------- | -------------------------------------------------- | ------ | ------------------------------------------------------------------- |
| <a href="#" data-route="openai/video/get_video_status">Estado de video</a>         | `GET /videos/{video_id}`                           | GET    | `get_video_status(video_id: str) -> dict`                           |
| <a href="#" data-route="openai/video/download_video">Descargar video</a>           | `GET /videos/{video_id}/content`                   | GET    | `download_video(video_id: str, output_path: str) -> bool`           |
| <a href="#" data-route="openai/video/download_thumbnail">Descargar thumbnail</a>   | `GET /videos/{video_id}/content?variant=thumbnail` | GET    | `download_thumbnail(video_id: str, output_path: str) -> bool`       |
| <a href="#" data-route="openai/video/wait_for_completion">Esperar finalización</a> | Interno                                            | GET    | `wait_for_completion(video_id: str, ...) -> dict`                   |
| <a href="#" data-route="openai/video/list_videos">Listar videos</a>                | `GET /videos`                                      | GET    | `list_videos(limit: int, after: Optional[str], order: str) -> dict` |
| <a href="#" data-route="openai/video/delete_videos">Eliminar video</a>             | `DELETE /videos/{video_id}`                        | DELETE | `delete_video(video_id: str) -> bool`                               |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.
2. Revisa la columna **Endpoint** para conocer la URL y el método de la API.
3. Utiliza los ejemplos de Python como guía para implementar llamadas a la API de Sora en tu aplicación.

---

## Notas generales

* Todos los endpoints requieren **API Key de OpenAI Sora**.
* Los videos pueden generarse desde prompt de texto o con imagen de referencia.
* Cada modelo tiene **restricciones específicas**: duración (4, 8, 12 s), tamaño (720x1280, 1280x720, 1024x1024), v
