# Generar Avatar IV Video - HeyGen

**Endpoint:** `POST /v2/video/av4/generate`
**Función:** `generate_avatar_iv_video(script: str, image_key: str, voice_id: str, ...) -> dict`

---

## Descripción

Genera un **Avatar IV** usando una imagen subida (`image_key`) y una voz (`voice_id`).

---

## Parámetros principales

| Parámetro         | Tipo | Descripción                                  |
| ----------------- | ---- | -------------------------------------------- |
| script            | str  | Texto que dirá el avatar                     |
| image_key         | str  | Image key del asset subido                   |
| voice_id          | str  | ID de la voz a usar                          |
| title             | str  | Título del video (default: "Untitled Video") |
| video_orientation | str  | Orientación ("portrait", "landscape")        |
| fit               | str  | Ajuste del avatar ("cover", "contain")       |

---

## Ejemplo (Python)

```python
result = client.generate_avatar_iv_video(
    script="Hola, soy un avatar IV",
    image_key="img_123",
    voice_id="voice_456",
    title="Avatar IV Test",
    video_orientation="portrait",
    fit="cover"
)
print(result['data']['video_id'])
```

---

## Notas importantes

* Requiere un `image_key` válido.
* Retorna `video_id` para usar con `get_video_status` y `get_video_url`.
