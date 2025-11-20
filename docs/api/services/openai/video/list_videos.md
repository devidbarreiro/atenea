# Listar Videos - Sora

**Endpoint:** `GET /v1/videos`
**Función:** `list_videos(limit: int = 20, after: Optional[str] = None, order: str = "desc") -> dict`

---

## Descripción

Lista los videos creados en Sora, con paginación y orden.

---

## Parámetros principales

| Parámetro | Tipo | Descripción                                           |
| --------- | ---- | ----------------------------------------------------- |
| limit     | int  | Número máximo de videos a retornar (default: 20)      |
| after     | str  | ID del video para paginación (opcional)               |
| order     | str  | Orden de resultados: "asc" o "desc" (default: "desc") |

---

## Ejemplo (Python)

```python
videos = client.list_videos(limit=10)
for v in videos.get('data', []):
    print(v['id'], v['status'])
```

---

## Notas importantes

* Retorna un dict con lista de videos bajo `data`.
* Permite paginación con `after`.
