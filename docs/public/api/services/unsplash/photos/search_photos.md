# Buscar Fotos

**Endpoint:** `https://api.unsplash.com/search/photos`
**Método:** `GET`
**Función:** `search_photos(...) -> Dict`

---

## Descripción

Busca fotos en Unsplash.
Ofrece filtros avanzados de color y orientación.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| orientation | str | Orientación (`landscape`, `portrait`, `squarish`) | — |
| order_by | str | Orden (`latest`, `relevant`, `popular`) | `relevant` |
| content_filter | str | Content safety filter | `low` |
| color | str | Filtro de color (ej: `black_and_white`, `red`) | — |
| page | int | Página de resultados | 1 |
| per_page | int | Resultados por página | 10 |

---

## Ejemplo (Python)

```python
from core.ai_services.unsplash import UnsplashClient, UnsplashOrientation

client = UnsplashClient(api_key="TU_ACCESS_KEY")
results = client.search_photos(
    "arquitectura",
    orientation=UnsplashOrientation.LANDSCAPE
)
```

---

## Notas importantes

* Requiere Access Key en header Authorization.
* Respetar los límites de la API (rate limits).
