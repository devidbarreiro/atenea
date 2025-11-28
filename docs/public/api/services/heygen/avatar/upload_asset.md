# Subir Asset - HeyGen

**Endpoints:**

* `upload_asset_from_file(file_path, content_type)`
* `upload_asset_from_bytes(file_content, content_type)`
* `upload_asset_from_url(image_url, content_type)`

**Función:** Retorna `image_key` para usar en Avatar IV

---

## Descripción

Permite subir imágenes a HeyGen desde **archivo, bytes o URL**.

---

## Ejemplo (Python)

```python
# Desde archivo
key = client.upload_asset_from_file("foto.jpg")
# Desde memoria
key2 = client.upload_asset_from_bytes(b"contenido_imagen")
# Desde URL
key3 = client.upload_asset_from_url("https://example.com/foto.jpg")
```

---

## Notas importantes

* `image_key` resultante se usa en `generate_avatar_iv_video`.
* `content_type` se detecta automáticamente si no se proporciona.
