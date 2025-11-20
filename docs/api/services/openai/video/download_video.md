# Descargar Video - Sora

**Endpoint:** `GET /v1/videos/{video_id}/content`
**Función:** `download_video(video_id: str, output_path: str) -> bool`

---

## Descripción

Descarga el contenido de un video completo generado en Sora.

---

## Parámetros principales

| Parámetro   | Tipo | Descripción                 |
| ----------- | ---- | --------------------------- |
| video_id    | str  | ID del video a descargar    |
| output_path | str  | Ruta donde guardar el video |

---

## Ejemplo (Python)

```python
success = client.download_video("video_123", "video.mp4")
print("Descargado:", success)
```

---

## Notas importantes

* Devuelve `True` si la descarga fue exitosa.
* Utiliza streaming para archivos grandes.
