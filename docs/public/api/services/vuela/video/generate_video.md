# Generar Video - Vuela.ai

**Endpoint:** `POST /generate/video`
**Función:** `generate_video(...) -> dict`

---

## Descripción

Genera un video usando un **guión de texto**, soportando modos:

* `single_voice` – Una voz principal
* `scenes` – Múltiples escenas y personajes
* `avatar` – Video con avatar animado

Soporta **voz, media, avatar, subtítulos y música de fondo**.

---

## Parámetros principales

| Parámetro            | Tipo                 | Descripción                                                |
| -------------------- | -------------------- | ---------------------------------------------------------- |
| mode                 | VuelaMode            | Modo de generación (`single_voice`, `scenes`, `avatar`)    |
| video_script         | str                  | Guión del video (usar `\n` para saltos de línea)           |
| aspect_ratio         | str                  | Relación de aspecto (`16:9` o `9:16`)                      |
| animation_type       | VuelaAnimationType   | Tipo de animación                                          |
| quality_tier         | VuelaQualityTier     | Nivel de calidad                                           |
| language             | str                  | Código de idioma                                           |
| country              | str                  | Código de país                                             |
| voice_id             | Optional[str]        | ID de voz (requerido para `single_voice` y `avatar`)       |
| voices               | Optional[List[Dict]] | Lista de voces para `scenes`                               |
| media_type           | VuelaMediaType       | Tipo de media (`ai_image`, `google_image`, `custom_image`) |
| add_subtitles        | bool                 | Añadir subtítulos                                          |
| add_background_music | bool                 | Añadir música de fondo                                     |
| avatar_id            | Optional[str]        | ID del avatar (modo `avatar`)                              |

---

## Ejemplo (Python)

```python
client = VuelaAIClient(api_key="TU_API_KEY")

result = client.generate_video(
    mode=VuelaMode.SINGLE_VOICE,
    video_script="Hola, esto es un ejemplo de Vuela.ai",
    voice_id="voice_123",
    aspect_ratio='16:9',
    animation_type=VuelaAnimationType.MOVING_IMAGE,
    quality_tier=VuelaQualityTier.PREMIUM
)

print(result['video_id'], result['status'])
```

---

## Notas importantes

* Para `scenes`, usar `format_script_for_scenes` para formatear correctamente el guión.
* Para `avatar`, `avatar_id` y `avatar_layout` son obligatorios.
* Para media personalizada, `custom_images_urls` debe estar definido.
* Retorna `video_id` y `status`.
