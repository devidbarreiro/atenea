# Generar Video con Imagen - Sora

**Endpoint:** `POST /v1/videos`
**Función:** `generate_video_with_image(prompt: str, input_reference_path: str, model: str = "sora-2-pro", ...) -> dict`

---

## Descripción

Genera un video usando **prompt textual** y **imagen de referencia**.
Modalidad **Text+Image-to-Video**: se requiere prompt y archivo de imagen.

---

## Parámetros principales

| Parámetro            | Tipo | Descripción                                                |
| -------------------- | ---- | ---------------------------------------------------------- |
| prompt               | str  | Descripción del video a generar                            |
| input_reference_path | str  | Ruta al archivo de imagen (JPEG, PNG, WEBP)                |
| model                | str  | Modelo a usar (`sora-2` o `sora-2-pro`)                    |
| seconds              | int  | Duración del video (4, 8, 12)                              |
| size                 | str  | Resolución del video (`720x1280`, `1280x720`, `1024x1024`) |

---

## Ejemplo (Python)

```python
client = SoraClient(api_key="TU_API_KEY")
result = client.generate_video_with_image(
    prompt="Animar un robot caminando",
    input_reference_path="robot.png",
    model="sora-2-pro",
    seconds=8,
    size="1280x720"
)
print(result['video_id'])
```

---

## Notas importantes

* ⚠️ La imagen debe tener exactamente las dimensiones indicadas en `size`.
* Retorna `video_id` y estado inicial (`queued`).
* Se puede usar `get_video_status` para seguimiento.
