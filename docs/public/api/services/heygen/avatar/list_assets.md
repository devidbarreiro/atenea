# Listar Assets - HeyGen

**Endpoint:** `GET /v1/asset/list`
**Función:** `list_assets(file_type: str = None, limit: int = 100) -> List[Dict]`

---

## Descripción

Lista los **assets disponibles** (imágenes, videos, audio) en HeyGen.

---

## Parámetros principales

| Parámetro | Tipo | Descripción                                            |
| --------- | ---- | ------------------------------------------------------ |
| file_type | str  | Filtrar por tipo: "image", "video", "audio" (opcional) |
| limit     | int  | Número máximo de resultados (default 100)              |

---

## Ejemplo (Python)

```python
assets = client.list_assets(file_type="image", limit=50)
for a in assets:
    print(a['id'], a['name'], a['file_type'])
```

---

## Notas importantes

* Para listar solo imágenes, usar `list_image_assets()`.
