# Generar Imagen Compuesta

**Endpoint:** `gemini-2.5-flash-image`
**Método:** `POST`
**Función:** `generate_image_from_multiple_images(prompt: str, input_images_data: List[bytes], aspect_ratio: str, response_modalities: List[str]) -> Dict`

---

## Descripción

Crea una imagen compuesta a partir de múltiples imágenes de entrada, aplicando un prompt de composición o transferencia de estilo.

---

## Parámetros principales

| Parámetro           | Tipo        | Descripción                                                                | Default   |
| ------------------- | ----------- | -------------------------------------------------------------------------- | --------- |
| prompt              | str         | Instrucciones de composición (ej: "Combinar estas imágenes en una escena") | —         |
| input_images_data   | List[bytes] | Lista de imágenes de entrada en bytes                                      | —         |
| aspect_ratio        | str         | Relación de aspecto                                                        | 1:1       |
| response_modalities | List[str]   | Modalidades de respuesta (`Text`, `Image`)                                 | ['Image'] |

---

## Ejemplo (Python)

```python
images_bytes = []
for filename in ["img1.png", "img2.png"]:
    with open(filename, "rb") as f:
        images_bytes.append(f.read())

result = client.generate_image_from_multiple_images(
    prompt="Combinar en una escena futurista",
    input_images_data=images_bytes,
    aspect_ratio="4:3"
)

with open("composite.png", "wb") as f:
    f.write(result['image_data'])
```

---

## Notas importantes

* Cada imagen debe ser compatible con **PIL**.
* Se pueden combinar varias imágenes para generar composiciones o transferencias de estilo.
* Valida el **aspect ratio** antes de generar para evitar errores.
