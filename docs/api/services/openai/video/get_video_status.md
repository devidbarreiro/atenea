# Estado del Video - Sora

**Endpoint:** `GET /v1/videos/{video_id}`
**Función:** `get_video_status(video_id: str) -> dict`

---

## Descripción

Consulta el estado de un video creado en Sora.

---

## Parámetros principales

| Parámetro | Tipo | Descripción              |
| --------- | ---- | ------------------------ |
| video_id  | str  | ID del video a consultar |

---

## Ejemplo (Python)

```python
status = client.get_video_status("video_123")
print(status['status'])
```

---

## Notas importantes

* Retorna información de progreso, estado (`queued`, `in_progress`, `completed`, `failed`), modelo, duración y timestamps.
* Para videos completados, incluye `completed_at` y `expires_at`.
