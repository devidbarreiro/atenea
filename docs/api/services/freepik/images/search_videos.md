# Buscar Videos

**Endpoint:** `https://api.freepik.com/v1/videos`  
**Método:** `GET`  
**Función:** `search_videos(...) -> Dict`

---

## Descripción

Busca exclusivamente videos en Freepik. Permite filtrar por orientación y controlar la paginación.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| orientation | str | Orientación (`horizontal`, `vertical`, `square`) | — |
| page | int | Página de resultados | 1 |
| limit | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
results = client.search_videos("naturaleza", limit=5)
for vid in results['data']:
    print(vid['title'], vid['preview'])
```

---

## Ejemplo (cURL)

```bash
curl -X GET "https://api.freepik.com/v1/videos?term=naturaleza&limit=5" \
-H "x-freepik-api-key: TU_API_KEY"
```

---

## Notas importantes

* Retorna únicamente recursos de video.
* `preview` permite previsualizar antes de descargar.
