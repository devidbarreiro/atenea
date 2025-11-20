# Buscar Iconos

**Endpoint:** `https://api.freepik.com/v1/icons`  
**Método:** `GET`  
**Función:** `search_icons(...) -> Dict`

---

## Descripción

Busca exclusivamente iconos en Freepik, retornando lista de recursos con thumbnail y preview.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| query | str | Término de búsqueda | — |
| page | int | Página de resultados | 1 |
| limit | int | Resultados por página | 20 |

---

## Ejemplo (Python)

```python
results = client.search_icons("redes sociales", limit=5)
for icon in results['data']:
    print(icon['title'], icon['preview'])
```

---

## Ejemplo (cURL)

```bash
curl -X GET "https://api.freepik.com/v1/icons?term=redes%20sociales&limit=5" \
-H "x-freepik-api-key: TU_API_KEY"
```

---

## Notas importantes

* Retorna solo iconos.
* Cada recurso incluye `thumbnail`, `preview` y `download_url`.
