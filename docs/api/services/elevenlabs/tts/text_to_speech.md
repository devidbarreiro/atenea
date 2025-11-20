# Convertir Texto a Voz (TTS)

### Información rápida
- **Endpoint:** `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={output_format}`
- **Método:** POST
- **Función:** `text_to_speech(...) -> bytes`

## Descripción
Genera un archivo de audio a partir de un texto usando la voz especificada.  
Se puede usar para crear narraciones, podcasts, respuestas de chatbots o cualquier aplicación que necesite texto hablado.  
Los parámetros de estilo (`stability`, `similarity_boost`, `style` y `speed`) permiten ajustar la naturalidad, velocidad y tonalidad de la voz.

> Nota: la respuesta es binaria (MP3, WAV u otro formato según `output_format`).

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
audio_bytes = client.text_to_speech(
    text="Hola, ¿cómo estás?",
    voice_id="voice_id_ejemplo"
)
with open("output.mp3", "wb") as f:
    f.write(audio_bytes)
```

## Ejemplo (cURL)
```bash
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/voice_id_ejemplo?output_format=mp3_44100_128" \
-H "xi-api-key: TU_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "text": "Hola, ¿cómo estás?",
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
