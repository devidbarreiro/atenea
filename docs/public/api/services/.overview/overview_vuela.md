# Overview - Vuela.ai Video API

**Base de la API:**

* Gestionada internamente por `VuelaAIClient`.
* Base URL: `https://api.vuela.ai`
* Todas las llamadas requieren **API Key de Vuela.ai**.

Este documento sirve como **resumen central** de la API de Vuela.ai dentro de nuestra aplicación.
Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python y parámetros importantes.

---

## Endpoints disponibles

### Generación de video

| Nombre                                                                | Endpoint               | Método | Función                       |
| --------------------------------------------------------------------- | ---------------------- | ------ | ----------------------------- |
| <a href="#" data-route="vuela/video/generate_video">Generar video</a> | `POST /generate/video` | POST   | `generate_video(...) -> dict` |

### Gestión de videos

| Nombre                                                                      | Endpoint                        | Método | Función                                                   |
| --------------------------------------------------------------------------- | ------------------------------- | ------ | --------------------------------------------------------- |
| <a href="#" data-route="vuela/video/get_video_details">Obtener detalles</a> | `GET /my-videos/{video_id}`     | GET    | `get_video_details(video_id: str) -> dict`                |
| <a href="#" data-route="vuela/video/list_videos">Listar videos</a>          | `GET /my-videos`                | GET    | `list_videos(page: int, limit: int, search: str) -> dict` |
| <a href="#" data-route="vuela/video/validate_token">Validar token</a>       | `POST /generate/validate-token` | POST   | `validate_token() -> dict`                                |

### Utilidades

| Nombre                                                                                   | Endpoint | Método | Función                                               |
| ---------------------------------------------------------------------------------------- | -------- | ------ | ----------------------------------------------------- |
| <a href="#" data-route="vuela/video/format_script_for_scenes">Formatear guión scenes</a> | N/A      | N/A    | `format_script_for_scenes(scenes: List[Dict]) -> str` |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.
2. Revisa la columna **Endpoint** para conocer la URL y el método de la API.
3. Utiliza los ejemplos de Python como guía para implementar llamadas a la API de Vuela.ai en tu aplicación.

---

## Notas generales

* Todos los endpoints requieren **API Key de Vuela.ai**.
* La generación de video soporta múltiples modos: `single_voice`, `scenes` y `avatar`.
* Cada modo tiene parámetros específicos de **voz, media, avatar, subtítulos y música de fondo**.
* Para modos de varias escenas, usar `format_script_for_scenes` facilita la generación correcta.
* Manejar siempre errores HTTP y logs de la API.
* La navegación dentro de la documentación funciona con enlaces `data-route` que reflejan la estructura de carpetas del proyecto.
