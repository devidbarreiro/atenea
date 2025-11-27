# Listar Avatares - HeyGen

**Endpoint:** `GET /v2/avatars`
**Función:** `list_avatars() -> List[Dict]`

---

## Descripción

Retorna la lista de todos los **avatares disponibles** en HeyGen.

---

## Ejemplo (Python)

```python
avatars = client.list_avatars()
for a in avatars:
    print(a['id'], a['name'])
```

---

## Notas importantes

* Útil para seleccionar `avatar_id` en `generate_video`.
