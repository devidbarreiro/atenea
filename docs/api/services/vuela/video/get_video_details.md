# Obtener Detalles de Video - Vuela.ai

**Endpoint:** `GET /my-videos/{video_id}`
**Función:** `get_video_details(video_id: str) -> dict`

---

## Descripción

Obtiene información detallada de un video generado:

* Estado: `creating`, `completed`, `failed`
* URL del video (si completado)
* Parámetros usados para la generación

---

## Parámetros principales

| Parámetro | Tipo | Descripción  |
| --------- | ---- | ------------ |
| video_id  | str  | ID del video |

---

## Ejemplo (Python)

```python
details = client.get_video_details("video_123")
print(details['status'], details.get('video_url'))
```
