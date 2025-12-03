# Texto a Voz con Timestamps

### Información rápida
- **Endpoint:** `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format={output_format}`
- **Método:** POST
- **Función:** `text_to_speech_with_timestamps(...) -> Dict`

## Descripción
Genera audio a partir de un texto incluyendo **timestamps por carácter**, lo que permite sincronizar texto con audio para subtítulos, animaciones o visualizaciones interactivas.  
Cada carácter del texto tendrá información de inicio y fin en milisegundos.  
Es útil para aplicaciones de aprendizaje, karaoke o asistentes virtuales que requieran sincronización exacta.

> Nota: la respuesta incluye `audio_base64`, `alignment` y `normalized_alignment`.

## Parámetros principales
| Parámetro        | Tipo  | Descripción                                | Default |
| ---------------- | ----- | ------------------------------------------ | ------- |
| text             | str   | Texto a convertir                          | -       |
| voice_id         | str   | ID de la voz                               | -       |
| model_id         | str   | Modelo de ElevenLabs                        | "eleven_turbo_v2_5" |
| language_code    | str   | Código de idioma ISO 639-1                 | "es"    |
| output_format    | str   | Formato de salida (`mp3_44100_128`)        | "mp3_44100_128" |
| stability        | float | Estabilidad de la voz (0.0–1.0)           | 0.5     |
| similarity_boost | float | Similitud con la voz original (0.0–1.0)   | 0.75    |
| style            | float | Estilo de la voz (0.0–1.0)                | 0.0     |
| speed            | float | Velocidad de la voz (0.25–4.0)            | 1.0     |

## Ejemplo (Python)
```python
result = client.text_to_speech_with_timestamps(
    text="Hola mundo",
    voice_id="voice_id_ejemplo"
)
import base64
audio_bytes = base64.b64decode(result["audio_base64"])
```

## Ejemplo (cURL)
```bash
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/voice_id_ejemplo/with-timestamps?output_format=mp3_44100_128" \
-H "xi-api-key: TU_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "text": "Hola mundo",
  "model_id": "eleven_turbo_v2_5",
  "language_code": "es",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "speed": 1.0
  }
}'
```
