# Eliminar Video - Sora

**Endpoint:** `DELETE /v1/videos/{video_id}`
**Función:** `delete_video(video_id: str) -> bool`

---

## Descripción

Elimina un video creado en Sora.

---

## Parámetros principales

| Parámetro | Tipo | Descripción             |
| --------- | ---- | ----------------------- |
| video_id  | str  | ID del video a eliminar |

---

## Ejemplo (Python)

```python
success = client.delete_video("video_123")
print("Eliminado:", success)
```

---

## Notas importantes

* Devuelve `True` si se eliminó correctamente.
* No se puede recuperar un video eliminado.
