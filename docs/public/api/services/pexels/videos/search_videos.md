# Buscar Videos

**Endpoint:** `https://api.pexels.com/videos/search`
**Método:** `GET`
**Función:** `search_videos(...) -> Dict`

---

## Descripción

Busca videos en Pexels.
Permite filtrar por orientación, tamaño y locale.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| orientation | str | Orientación (`landscape`, `portrait`, `square`) | — |
| size | str | Tamaño (`large`, `medium`, `small`) | — |
| locale | str | Idioma de búsqueda (ej: `es-ES`) | `es-ES` |
| page | int | Página de resultados | 1 |
| per_page | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
from core.ai_services.pexels import PexelsClient, PexelsOrientation

client = PexelsClient(api_key="TU_API_KEY")
results = client.search_videos(
    "playa",
    orientation=PexelsOrientation.LANDSCAPE
)
```

---

## Notas importantes

* Todo el contenido es gratuito.
* La respuesta incluye archivos de video en diferentes calidades.
