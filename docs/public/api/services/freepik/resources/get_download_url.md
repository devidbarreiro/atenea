# Obtener URL de Descarga

**Endpoint:** `https://api.freepik.com/v1/resources/{resource_id}/download`  
**Método:** `GET`  
**Función:** `get_download_url(resource_id: str, image_size: str) -> Dict`

---

## Descripción

Obtiene la URL oficial de descarga de un recurso en Freepik. Permite seleccionar tamaño de imagen (`small`, `medium`, `large`, `original`).  
La URL puede ser usada para descargar el recurso de forma segura.

---

## Parámetros principales

| Parámetro | Tipo | Descripción | Default |
| --------- | ---- | ----------- | ------- |
| resource_id | str | ID del recurso | — |
| image_size | str | Tamaño de la imagen (`small`, `medium`, `large`, `original`) | `large` |

---

## Ejemplo (Python)

```python
download_info = client.get_download_url("123456", image_size="original")
print(download_info["download_url"])
```

---

## Ejemplo (cURL)

```bash
curl -X GET "https://api.freepik.com/v1/resources/123456/download?image_size=original" \
-H "x-freepik-api-key: TU_API_KEY" \
-H "Accept: application/json"
```

---

## Notas importantes

* Usar siempre la URL de descarga oficial para cumplir con la política de Freepik.
* `download_url` es firme y temporal, lista para usar en descargas.
