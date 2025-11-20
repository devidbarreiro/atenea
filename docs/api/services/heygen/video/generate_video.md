# Generar Video - HeyGen

**Endpoint:** `POST /v2/video/generate`
**Función:** `generate_video(script: str, avatar_id: str, voice_id: str, ...) -> dict`

---

## Descripción

Genera un video con un **avatar en HeyGen** usando un script de texto.
Modalidad **Text-to-Video**: se requiere `script`, `avatar_id` y `voice_id`.

---

## Parámetros principales

| Parámetro      | Tipo  | Descripción                                     |
| -------------- | ----- | ----------------------------------------------- |
| script         | str   | Texto que dirá el avatar                        |
| avatar_id      | str   | ID del avatar a usar                            |
| voice_id       | str   | ID de la voz a usar                             |
| title          | str   | Título del video (default: "Untitled Video")    |
| has_background | bool  | Si se agrega background (default: False)        |
| background_url | str   | URL del background (si aplica)                  |
| dimension      | dict  | {"width": int, "height": int}, default 1280x720 |
| aspect_ratio   | str   | Relación de aspecto ("16:9", "9:16")            |
| caption        | bool  | Activar captions (default: True)                |
| voice_speed    | float | Velocidad de la voz (default: 1.0)              |
| voice_pitch    | int   | Pitch de la voz (default: 50)                   |
| voice_emotion  | str   | Emoción de la voz (default: "Excited")          |

---

## Ejemplo (Python)

```python
client = HeyGenClient(api_key="TU_API_KEY")
result = client.generate_video(
    script="Hola, este es un video de prueba",
    avatar_id="avatar_123",
    voice_id="voice_456",
    title="Mi Video",
    has_background=True,
    background_url="https://example.com/bg.jpg",
    dimension={"width":1280,"height":720}
)
print(result['data']['video_id'])
```

---

## Notas importantes

* Requiere avatar y voz válidos.
* Para background, `has_background=True` y `background_url`.
* Retorna `video_id` para usar con `get_video_status` y `get_video_url`.
