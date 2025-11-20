# Obtener Información de una Voz

### Información rápida
- **Endpoint:** `https://api.elevenlabs.io/v1/voices/{voice_id}`
- **Método:** GET
- **Función:** `get_voice(voice_id: str) -> Dict`

## Descripción
Obtiene información completa de una voz específica, incluyendo su nombre, categoría, descripción, URL de previsualización y configuraciones.  
Este endpoint es útil para conocer detalles de la voz antes de generar audio y para validar que la voz seleccionada cumpla con los requisitos de estilo o idioma.

## Parámetros
| Parámetro | Tipo | Descripción |
| --------- | ---- | ----------- |
| voice_id  | str  | ID de la voz a consultar |

## Ejemplo (Python)
```python
voice = client.get_voice("voice_id_ejemplo")
print(voice["name"], voice["description"])
```

## Ejemplo (cURL)
```bash
curl -X GET "https://api.elevenlabs.io/v1/voices/voice_id_ejemplo" \
-H "xi-api-key: TU_API_KEY"
```
