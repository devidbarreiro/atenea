# Detalles de un Recurso

**Endpoint:** `https://api.freepik.com/v1/resources/{resource_id}`  
**Método:** `GET`  
**Función:** `get_resource_details(resource_id: str) -> Dict`

---

## Descripción

Obtiene información detallada de un recurso específico en Freepik, incluyendo título, tipo de contenido, imágenes, licencias y metadatos adicionales.

---

## Parámetros principales

| Parámetro | Tipo | Descripción |
| --------- | ---- | ----------- |
| resource_id | str | ID del recurso |

---

## Ejemplo (Python)

```python
details = client.get_resource_details("123456")
print(details["title"], details["type"])
```

---

## Ejemplo (cURL)

```bash
curl -X GET "https://api.freepik.com/v1/resources/123456" \
-H "x-freepik-api-key: TU_API_KEY" \
-H "Accept: application/json"
```

---

## Notas importantes

* Útil para obtener metadatos antes de la descarga.
* Incluye información de licencia y URLs de preview/thumbnail.
