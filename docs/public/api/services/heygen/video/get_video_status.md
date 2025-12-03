# Estado de Video - HeyGen

**Endpoint:** `GET /v1/video_status.get?video_id={video_id}`
**Función:** `get_video_status(video_id: str) -> dict`

---

## Descripción

Consulta el **estado de un video** en HeyGen.
Posibles estados: `pending`, `processing`, `completed`, `failed`.

---

## Parámetros principales

| Parámetro | Tipo | Descripción           |
| --------- | ---- | --------------------- |
| video_id  | str  | ID del video generado |

---

## Ejemplo (Python)

```python
status = client.get_video_status("video_123")
print(status['status'])
if status['status'] == 'completed':
    print("Video listo en:", status['video_url'])
```

---

## Notas importantes

* Loguea información detallada: duración, thumbnail, estado, errores.
* Útil para polling hasta que el video esté `completed`.
