# Editar Imagen Existente

**Endpoint:** `gemini-2.5-flash-image`
**Método:** `POST`
**Función:** `generate_image_from_image(prompt: str, input_image_data: bytes, aspect_ratio: str, response_modalities: List[str]) -> Dict`

---

## Descripción

Permite editar una imagen existente aplicando instrucciones de texto (Image-to-Image).
El resultado incluye la imagen editada y opcionalmente texto de respuesta.

---

## Parámetros principales

| Parámetro           | Tipo      | Descripción                                               | Default   |
| ------------------- | --------- | --------------------------------------------------------- | --------- |
| prompt              | str       | Instrucciones de edición (ej: "Agregar sombrero al gato") | —         |
| input_image_data    | bytes     | Imagen de entrada en bytes                                | —         |
| aspect_ratio        | str       | Relación de aspecto                                       | 1:1       |
| response_modalities | List[str] | Modalidades de respuesta (`Text`, `Image`)                | ['Image'] |

---

## Ejemplo (Python)

```python
with open("cat.png", "rb") as f:
    input_bytes = f.read()

result = client.generate_image_from_image(
    prompt="Agregar sombrero de mago al gato",
    input_image_data=input_bytes,
    aspect_ratio="1:1"
)

with open("edited_cat.png", "wb") as f:
    f.write(result['image_data'])
```

---

## Notas importantes

* La imagen de entrada debe ser **compatible con PIL**.
* Se puede especificar `response_modalities` para incluir o excluir texto.
* Valida el **aspect ratio** antes de generar para evitar errores.
