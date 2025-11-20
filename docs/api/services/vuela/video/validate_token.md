# Validar Token - Vuela.ai

**Endpoint:** `POST /generate/validate-token`
**Función:** `validate_token() -> dict`

---

## Descripción

Valida que el token API esté configurado correctamente.

---

## Ejemplo (Python)

```python
result = client.validate_token()
print(result['valid'], result['message'])
```
