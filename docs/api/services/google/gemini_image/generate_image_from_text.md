# Generar Imagen desde Texto

**Endpoint:** `gemini-2.5-flash-image`
**Método:** `POST`
**Función:** `generate_image_from_text(prompt: str, aspect_ratio: str, response_modalities: List[str]) -> Dict`

---

## Descripción

Convierte un prompt de texto en una imagen generada por Gemini (Text-to-Image).
Permite especificar **aspect ratio** y modalidades de respuesta (`Text` o `Image`).

---

## Parámetros principales

| Parámetro           | Tipo      | Descripción                                | Default   |
| ------------------- | --------- | ------------------------------------------ | --------- |
| prompt              | str       | Descripción textual de la imagen a generar | —         |
| aspect_ratio        | str       | Relación de aspecto (ej: 1:1, 16:9)        | 1:1       |
| response_modalities | List[str] | Modalidades de respuesta (`Text`, `Image`) | ['Image'] |

---

## Ejemplo (Python)

```python
from gemini_image import GeminiImageClient

client = GeminiImageClient(api_key="TU_API_KEY")
result = client.generate_image_from_text(
    prompt="Un paisaje futurista al atardecer",
    aspect_ratio="16:9",
    response_modalities=["Image"]
)

# Guardar imagen
with open("output.png", "wb") as f:
    f.write(result['image_data'])
```

---

## Notas importantes

* Valida que el **aspect ratio** esté soportado usando `GeminiImageClient.validate_aspect_ratio(aspect_ratio)`.
* La imagen se devuelve en **bytes**, lista para guardar o convertir a base64.
* Puede incluir texto de respuesta si `response_modalities` contiene `Text`.
