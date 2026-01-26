# Buscar Sonidos

**Endpoint:** `https://freesound.org/apiv2/search/text/`
**Método:** `GET`
**Función:** `search_sounds(...) -> Dict`

---

## Descripción

Busca sonidos en Freesound.
Permite filtros avanzados estilo Solr.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| filter | str | Filtros avanzados (ej: `duration:[1 TO 10]`) | — |
| sort | str | Orden (ej: `score`, `duration_desc`) | `score` |
| fields | str | Campos a retornar | `id,name,tags,username,license` |
| page | int | Página de resultados | 1 |
| page_size | int | Resultados por página | 15 |

---

## Ejemplo (Python)

```python
from core.ai_services.freesound import FreeSoundClient, FreeSoundSort

client = FreeSoundClient(api_key="TU_API_KEY")
results = client.search_sounds(
    "explosion",
    filter_query="duration:[0 TO 5]",
    sort=FreeSoundSort.DOWNLOADS_DESC
)
```
