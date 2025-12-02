# Overview - Freepik Stock Content API

**Base de la API:**

* V1: `https://api.freepik.com/v1`

Este documento sirve como **resumen central** de la API de Freepik Stock Content dentro de nuestra aplicación.
Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python y cURL, parámetros y notas importantes.

---

## Endpoints disponibles

### Recursos (general)

| Nombre                                                                                    | Endpoint                                                          | Método | Función                                                       |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| <a href="#" data-route="freepik/resources/search_resources">Buscar recursos</a>         | `GET https://api.freepik.com/v1/resources`                        | GET    | `search_resources(...) -> Dict`                               |
| <a href="#" data-route="freepik/resources/get_resource_details">Detalles de recurso</a> | `GET https://api.freepik.com/v1/resources/{resource_id}`          | GET    | `get_resource_details(resource_id: str) -> Dict`              |
| <a href="#" data-route="freepik/resources/get_download_url">URL de descarga</a>         | `GET https://api.freepik.com/v1/resources/{resource_id}/download` | GET    | `get_download_url(resource_id: str, image_size: str) -> Dict` |

### Contenido específico

| Nombre                                                                      | Endpoint                                   | Método | Función                      |
| --------------------------------------------------------------------------- | ------------------------------------------ | ------ | ---------------------------- |
| <a href="#" data-route="freepik/images/search_images">Buscar imágenes</a> | `GET https://api.freepik.com/v1/resources` | GET    | `search_images(...) -> Dict` |
| <a href="#" data-route="freepik/images/search_videos">Buscar videos</a>   | `GET https://api.freepik.com/v1/videos`    | GET    | `search_videos(...) -> Dict` |
| <a href="#" data-route="freepik/images/search_icons">Buscar iconos</a>    | `GET https://api.freepik.com/v1/icons`     | GET    | `search_icons(...) -> Dict`  |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.
2. Revisa la columna **Endpoint** para conocer la URL real de la API y cómo realizar las llamadas.
3. Utiliza los ejemplos de Python y cURL como guía para implementar llamadas a la API de Freepik en tu aplicación.

---

## Notas generales

* Todos los endpoints requieren una **API Key** de Freepik.
* Los resultados incluyen recursos como imágenes, vectores, iconos y videos.
* Puedes filtrar por tipo de contenido, orientación y licencia (`free` o `premium`).
* Cada recurso incluye **thumbnail, preview y download_url**.
* Maneja correctamente **errores HTTP** y límites de requests.
* La navegación dentro de la documentación funciona con enlaces `data-route` para evitar recargas y errores 404.
