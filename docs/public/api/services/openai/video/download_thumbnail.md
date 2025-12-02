# Descargar Thumbnail - Sora

**Endpoint:** `GET /v1/videos/{video_id}/content?variant=thumbnail`
**Función:** `download_thumbnail(video_id: str, output_path: str) -> bool`

---

## Descripción

Descarga el **thumbnail** de un video generado en Sora.

---

## Parámetros principales

| Parámetro   | Tipo | Descripción                     |
| ----------- | ---- | ------------------------------- |
| video_id    | str  | ID del video                    |
| output_path | str  | Ruta donde guardar el thumbnail |

---

## Ejemplo (Python)

```python
success = client.download_thumbnail("video_123", "thumb.png")
print("Thumbnail descargado:", success)
```

---

## Notas importantes

* Devuelve `True` si la descarga fue exitosa.
* Utiliza streaming para archivos pequeños.
