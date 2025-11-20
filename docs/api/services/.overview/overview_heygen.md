# Overview - HeyGen API

**Base de la API:**

* Base URL: `https://api.heygen.com`
* Todos los endpoints requieren **API Key de HeyGen**.
* `HeyGenClient` es una capa de conveniencia en Python para interactuar con los endpoints de manera estructurada.

Este documento sirve como **resumen central** de la API de HeyGen dentro de nuestra aplicación. Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python y parámetros importantes.

---

## Endpoints disponibles

### Generación de video

| Nombre                                                                | Endpoint                      | Método | Función                                                              |
| --------------------------------------------------------------------- | ----------------------------- | ------ | -------------------------------------------------------------------- |
| <a href="#" data-route="heygen/video/generate_video">Generar video HeyGen</a>         | `POST /v2/video/generate`     | POST   | `generate_video(script, avatar_id, voice_id, heygen.) -> dict`           |
| <a href="#" data-route="heygen/avatar/generate_avatar_iv">Generar Avatar IV Video</a> | `POST /v2/video/av4/generate` | POST   | `generate_avatar_iv_video(script, image_key, voice_id, ...) -> dict` |

### Operaciones avanzadas de video

| Nombre                                                       | Endpoint                                       | Método | Función                                         |
| ------------------------------------------------------------ | ---------------------------------------------- | ------ | ----------------------------------------------- |
| <a href="#" data-route="heygen/video/get_video_status">Estado de video</a>   | `GET /v1/video_status.get?video_id={video_id}` | GET    | `get_video_status(video_id: str) -> dict`       |
| <a href="#" data-route="heygen/video/get_video_url">Obtener URL de video</a> | Interno (usa `get_video_status`)               | GET    | `get_video_url(video_id: str) -> Optional[str]` |

### Operaciones de assets y avatares

| Nombre                                                  | Endpoint             | Método | Función                                                              |
| ------------------------------------------------------- | -------------------- | ------ | -------------------------------------------------------------------- |
| <a href="#" data-route="heygen/avatar/list_avatars">Listar avatares</a> | `GET /v2/avatars`    | GET    | `list_avatars() -> List[Dict]`                                       |
| <a href="#" data-route="heygen/avatar/list_voices">Listar voces</a>     | `GET /v2/voices`     | GET    | `list_voices() -> List[Dict]`                                        |
| <a href="#" data-route="heygen/avatar/list_assets">Listar assets</a>    | `GET /v1/asset/list` | GET    | `list_assets(file_type: str = None, limit: int = 100) -> List[Dict]` |
| <a href="#" data-route="heygen/avatar/upload_asset">Subir asset</a>     | `POST /v1/asset`     | POST   | `upload_asset_from_file/bytes/url(...) -> str`                       |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.
2. Revisa la columna **Endpoint** para conocer la URL real y cómo realizar la llamada.
3. Utiliza los ejemplos de Python como guía para implementar llamadas directas a la API de HeyGen o mediante `HeyGenClient`.

---

## Notas generales

* Todos los endpoints requieren **API Key de HeyGen**.
* Los videos pueden generarse con **scripts de texto, avatares, voces, assets subidos o Avatar IV**.
* Cada endpoint tiene **restricciones específicas**: dimensiones, orientación, velocidad y emoción de voz, captions, background.
* Manejar siempre errores HTTP y logs de la API.
