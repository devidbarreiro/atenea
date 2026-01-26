# Buscar Videos

**Endpoint:** `https://pixabay.com/api/videos/`
**Método:** `GET`
**Función:** `search_videos(...) -> Dict`

---

## Descripción

Busca videos en Pixabay.
Soporta filmaciones y animaciones.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| video_type | str | Tipo (`all`, `film`, `animation`) | `all` |
| category | str | Categoría (ej: `nature`) | — |
| min_width | int | Ancho mínimo | — |
| min_height | int | Alto mínimo | — |
| safesearch | bool | Filtro de contenido seguro | `True` |
| page | int | Página de resultados | 1 |
| per_page | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
from core.ai_services.pixabay import PixabayClient

client = PixabayClient(api_key="TU_API_KEY")
results = client.search_videos(
    "oceano",
    video_type="film"
)
```
