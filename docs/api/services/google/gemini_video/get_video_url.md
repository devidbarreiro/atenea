# Obtener URL de Video - Gemini Veo API

**Funcionalidad:** Obtener la URL del video generado a partir de una operación completada.

**Método principal:** `get_video_url(operation_name: str) -> Optional[str]`

---

## Descripción

Esta función es un **acceso rápido** para obtener el URL del primer video generado por `generate_video()`. Internamente:

1. Llama a `get_video_status()`.
2. Extrae la URL principal del video si la operación se completó.
3. Devuelve `None` si el video aún no está listo o si ocurrió un error.

---

## Parámetros

| Parámetro      | Tipo | Obligatorio | Descripción                                             |
| -------------- | ---- | ----------- | ------------------------------------------------------- |
| operation_name | str  | Sí          | Nombre de la operación retornado por `generate_video()` |

---

## Ejemplo en Python

```python
from atenea.gemini import GeminiVeoClient

client = GeminiVeoClient(model_name="veo-3.1-generate-preview")
video_url = client.get_video_url("projects/.../operations/xyz123")
if video_url:
    print("Video disponible en:", video_url)
else:
    print("El video aún no está listo o ocurrió un error.")
```

---

## Retorno

| Tipo       | Descripción                                                       |
| ---------- | ----------------------------------------------------------------- |
| str o None | URL del primer video generado, o `None` si aún no está disponible |
