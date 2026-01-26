# Buscar Fotos

**Endpoint:** `https://api.pexels.com/v1/search`
**Método:** `GET`
**Función:** `search_photos(...) -> Dict`

---

## Descripción

Busca fotos en Pexels.
Permite filtrar por orientación, tamaño, color y locale.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| orientation | str | Orientación (`landscape`, `portrait`, `square`) | — |
| size | str | Tamaño (`large`, `medium`, `small`) | — |
| color | str | Color dominante (ej: `red`, `blue`) | — |
| locale | str | Idioma de búsqueda (ej: `es-ES`) | `es-ES` |
| page | int | Página de resultados | 1 |
| per_page | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
from core.ai_services.pexels import PexelsClient, PexelsOrientation

client = PexelsClient(api_key="TU_API_KEY")
results = client.search_photos(
    "naturaleza",
    orientation=PexelsOrientation.LANDSCAPE,
    limit=5
)
```

---

## Notas importantes

* Todo el contenido es gratuito.
* La respuesta incluye URLs de diferentes tamaños.
