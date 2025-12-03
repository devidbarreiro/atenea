# Buscar Recursos en Freepik

**Endpoint:** `https://api.freepik.com/v1/resources`  
**Método:** `GET`  
**Función:** `search_resources(...) -> Dict`

---

## Descripción

Permite buscar recursos en Freepik, incluyendo fotos, vectores, PSDs, iconos y videos.  
Se pueden aplicar filtros por tipo de contenido, orientación y licencia.  
Retorna un diccionario con la lista de recursos (`data`) y metadata de paginación (`meta`).

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| content_types | List[str] | Tipos de contenido (`photo`, `vector`, `psd`, `icon`, `video`) | Todos |
| orientation | str | Orientación (`horizontal`, `vertical`, `square`) | — |
| page | int | Página de resultados | 1 |
| limit | int | Resultados por página (máx 200) | 20 |
| order | str | Orden (`latest`, `popular`, `random`) | `latest` |
| license_filter | str | Filtrar por licencia (`all`, `free`, `premium`) | `all` |

---

## Ejemplo (Python)

```python
from core.ai_services_freepik import FreepikClient, FreepikContentType, FreepikOrientation

client = FreepikClient(api_key="TU_API_KEY")
results = client.search_resources(
    query="paisaje",
    content_types=[FreepikContentType.PHOTO, FreepikContentType.VECTOR],
    orientation=FreepikOrientation.HORIZONTAL,
    page=1,
    limit=10,
    license_filter='free'
)
for item in results['data']:
    print(item['title'], item['preview'])
```

---

## Ejemplo (cURL)

```bash
curl -X GET "https://api.freepik.com/v1/resources?term=paisaje&page=1&limit=10" \
-H "x-freepik-api-key: TU_API_KEY" \
-H "Accept: application/json"
```

---

## Notas importantes

* `license_filter` se aplica durante el parseo para excluir recursos no deseados.
* Cada recurso incluye `thumbnail`, `preview` y `download_url`.
* Manejar correctamente paginación usando `meta['total_pages']` si se requieren más resultados.
