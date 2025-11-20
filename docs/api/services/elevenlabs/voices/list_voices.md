# Listar Voces

### Información rápida
- **Endpoint:** `https://api.elevenlabs.io/v2/voices?page_size={page_size}`
- **Método:** GET
- **Función:** `list_voices(page_size: int = 30) -> List[Dict]`

## Descripción
Obtiene todas las voces disponibles en ElevenLabs.  
Este endpoint permite listar voces con información resumida como `voice_id`, `name`, `category`, `description`, `preview_url`, `labels` y `settings`.  
Se puede usar para mostrar opciones de voces en interfaces de usuario o para seleccionar la voz adecuada antes de generar audio.

> Nota: la API devuelve un máximo de 100 voces por página; utiliza `page_size` para ajustar la cantidad de resultados.

## Parámetros
| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| page_size | int  | Número de voces por página (máx 100) | 30 |

## Ejemplo (Python)
```python
from core.ai_services_elevenlabs import ElevenLabsClient

client = ElevenLabsClient(api_key="TU_API_KEY")
voices = client.list_voices(page_size=50)
for v in voices:
    print(v["name"], v["voice_id"])
```

## Ejemplo (cURL)
```bash
curl -X GET "https://api.elevenlabs.io/v2/voices?page_size=50" \
-H "xi-api-key: TU_API_KEY"
```
