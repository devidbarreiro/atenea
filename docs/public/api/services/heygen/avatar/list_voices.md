# Listar Voces - HeyGen

**Endpoint:** `GET /v2/voices`
**Función:** `list_voices() -> List[Dict]`

---

## Descripción

Retorna la lista de todas las **voces disponibles**.

---

## Ejemplo (Python)

```python
voices = client.list_voices()
for v in voices:
    print(v['id'], v['name'])
```

---

## Notas importantes

* Útil para seleccionar `voice_id` en `generate_video` o `generate_avatar_iv_video`.
