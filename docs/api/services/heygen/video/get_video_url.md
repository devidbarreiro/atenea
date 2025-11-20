# Obtener URL de Video - HeyGen

**Endpoint:** `GET /v1/video_status.get?video_id={video_id}`
**Función:** `get_video_url(video_id: str) -> Optional[str]`

---

## Descripción

Retorna la **URL del video completado** si el estado es `completed`.

---

## Parámetros principales

| Parámetro | Tipo | Descripción           |
| --------- | ---- | --------------------- |
| video_id  | str  | ID del video generado |

---

## Ejemplo (Python)

```python
url = client.get_video_url("video_123")
if url:
    print("Video disponible en:", url)
else:
    print("Video aún en procesamiento")
```

---

## Notas importantes

* Retorna `None` si el video no está completado.
* Requiere que `get_video_status` retorne `completed`.
