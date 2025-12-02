# Listar Videos - Vuela.ai

**Endpoint:** `GET /my-videos`
**Función:** `list_videos(page: int = 1, limit: int = 10, search: Optional[str] = None) -> dict`

---

## Descripción

Lista los videos generados con paginación y búsqueda opcional.

---

## Parámetros principales

| Parámetro | Tipo          | Descripción                 |
| --------- | ------------- | --------------------------- |
| page      | int           | Número de página            |
| limit     | int           | Número de videos por página |
| search    | Optional[str] | Término de búsqueda         |

---

## Ejemplo (Python)

```python
videos = client.list_videos(limit=5, search="tutorial")
for v in videos.get('data', []):
    print(v['video_id'], v['status'])
```
