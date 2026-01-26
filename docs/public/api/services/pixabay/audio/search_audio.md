# Buscar Audio

**Endpoint:** `https://pixabay.com/api/audio/`
**Método:** `GET`
**Función:** `search_audio(...) -> Dict`

---

## Descripción

Busca música y efectos de sonido en Pixabay.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| audio_type | str | Tipo (`all`, `music`, `sound_effects`) | `all` |
| category | str | Categoría (ej: `ambient`) | — |
| safesearch | bool | Filtro de contenido seguro | `True` |
| page | int | Página de resultados | 1 |
| per_page | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
from core.ai_services.pixabay import PixabayClient

client = PixabayClient(api_key="TU_API_KEY")
results = client.search_audio(
    "piano",
    audio_type="music"
)
```
