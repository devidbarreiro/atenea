# Detalles de Sonido

**Endpoint:** `https://freesound.org/apiv2/sounds/<sound_id>/`
**Método:** `GET`
**Función:** `get_sound_details(...) -> Dict`

---

## Descripción

Obtiene información completa de un sonido específico.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| sound_id | int | ID del sonido | — |

---

## Ejemplo (Python)

```python
from core.ai_services.freesound import FreeSoundClient

client = FreeSoundClient(api_key="TU_API_KEY")
details = client.get_sound_details(123456)
print(details['name'], details['url'])
```
