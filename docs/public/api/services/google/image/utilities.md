# Utilities - Gemini Image API

Este documento describe las funciones utilitarias disponibles en el cliente de Gemini Image.
Permiten **convertir imágenes**, validar relaciones de aspecto y obtener dimensiones soportadas.

---

## Funciones disponibles

| Nombre                        | Función                                                          |
| ----------------------------- | ---------------------------------------------------------------- |
| `image_bytes_to_base64`       | Convierte bytes de imagen a string base64.                       |
| `base64_to_image_bytes`       | Convierte string base64 a bytes de imagen.                       |
| `validate_aspect_ratio`       | Valida si un aspect ratio está soportado.                        |
| `get_supported_aspect_ratios` | Retorna lista de todos los aspect ratios soportados.             |
| `get_aspect_ratio_dimensions` | Retorna dimensiones (`width`, `height`) de un aspect ratio dado. |

---

## Ejemplos (Python)

```python
from gemini_image import GeminiImageClient

# Convertir bytes a base64
with open("output.png", "rb") as f:
    img_bytes = f.read()
base64_str = GeminiImageClient.image_bytes_to_base64(img_bytes)

# Convertir base64 a bytes
bytes_back = GeminiImageClient.base64_to_image_bytes(base64_str)

# Validar un aspect ratio
is_valid = GeminiImageClient.validate_aspect_ratio("16:9")

# Obtener todos los aspect ratios soportados
ratios = GeminiImageClient.get_supported_aspect_ratios()

# Obtener dimensiones de un aspect ratio
dims = GeminiImageClient.get_aspect_ratio_dimensions("4:3")
print(dims)  # -> {'width': 1184, 'height': 864}
```

---

## Notas importantes

* Todas estas funciones son **estáticas o de clase**, por lo que no requieren inicializar el cliente con API Key.
* Se recomienda usar `validate_aspect_ratio` antes de generar imágenes para evitar errores en la API.
