# Buscar Imágenes

**Endpoint:** `https://pixabay.com/api/`
**Método:** `GET`
**Función:** `search_images(...) -> Dict`

---

## Descripción

Busca imágenes en Pixabay.
Soporta fotos, ilustraciones y vectores.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| image_type | str | Tipo (`all`, `photo`, `illustration`, `vector`) | `all` |
| category | str | Categoría (ej: `nature`, `science`) | — |
| orientation | str | Orientación (`all`, `horizontal`, `vertical`) | `all` |
| colors | str | Filtro de color (ej: `grayscale`, `transparent`, `red`) | — |
| safesearch | bool | Filtro de contenido seguro | `false` |
| page | int | Página de resultados | 1 |
| per_page | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
from core.ai_services.pixabay import PixabayClient, PixabayImageType

client = PixabayClient(api_key="TU_API_KEY")
results = client.search_images(
    "flores",
    image_type=PixabayImageType.PHOTO,
    colors="red"
)
```
