# Buscar Imágenes

**Endpoint:** `https://api.freepik.com/v1/resources`  
**Método:** `GET`  
**Función:** `search_images(...) -> Dict`

---

## Descripción

Busca exclusivamente **fotos y vectores** en Freepik.  
Se pueden aplicar filtros de orientación y licencia.  
Retorna lista de recursos con metadata y URLs de preview y descarga.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| orientation | str | Orientación (`horizontal`, `vertical`, `square`) | — |
| page | int | Página de resultados | 1 |
| limit | int | Resultados por página | 20 |
| license_filter | str | Filtrar por licencia (`all`, `free`, `premium`) | `all` |

---

## Ejemplo (Python)

```python
results = client.search_images("montaña", orientation=FreepikOrientation.VERTICAL, limit=5)
for img in results['data']:
    print(img['title'], img['preview'])
```

---

## Ejemplo (cURL)

```bash
curl -X GET "https://api.freepik.com/v1/resources?term=montaña&limit=5" \
-H "x-freepik-api-key: TU_API_KEY"
```

---

## Notas importantes

* Retorna solo fotos y vectores.
* Manejar paginación y filtros según necesidad.
