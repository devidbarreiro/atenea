# Overview - ElevenLabs Text-to-Speech API

**Base de la API:**  
- V1: `https://api.elevenlabs.io/v1`  
- V2: `https://api.elevenlabs.io/v2`

Este documento sirve como **resumen central** de la API de ElevenLabs Text-to-Speech dentro de nuestra aplicación.  
Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python y cURL, parámetros y notas importantes.

---

## Endpoints disponibles

### Voces

| Nombre | Endpoint | Método | Función |
| ------ | -------- | ------ | ------- |
| <a href="#" data-route="elevenlabs/voices/list_voices">Listar voces</a> | `GET https://api.elevenlabs.io/v2/voices?page_size={page_size}` | GET | `list_voices(page_size: int = 30) -> List[Dict]` |
| <a href="#" data-route="elevenlabs/voices/get_voice">Obtener voz</a> | `GET https://api.elevenlabs.io/v1/voices/{voice_id}` | GET | `get_voice(voice_id: str) -> Dict` |

### Text-to-Speech (TTS)

| Nombre | Endpoint | Método | Función |
| ------ | -------- | ------ | ------- |
| <a href="#" data-route="elevenlabs/tts/text_to_speech">Convertir texto a voz</a> | `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={output_format}` | POST | `text_to_speech(...) -> bytes` |
| <a href="#" data-route="elevenlabs/tts/text_to_speech_with_timestamps">Texto a voz con timestamps</a> | `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format={output_format}` | POST | `text_to_speech_with_timestamps(...) -> Dict` |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.  
2. Revisa la columna **Endpoint** para conocer la URL real de la API y cómo realizar las llamadas.  
3. Utiliza los ejemplos de Python y cURL como guía para implementar llamadas a la API de ElevenLabs en tu aplicación.

---

## Notas generales

* Todos los endpoints requieren una **API Key** de ElevenLabs.
* Las respuestas de TTS son binarias (MP3, WAV u otro formato según `output_format`) o en JSON si incluyen timestamps.
* Ajusta parámetros de voz como `stability`, `similarity_boost`, `style` y `speed` para controlar la naturalidad y estilo del audio generado.
* Maneja **errores HTTP** y límites de requests para producción.
