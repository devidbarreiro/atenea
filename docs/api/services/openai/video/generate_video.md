# Generar Video - Sora

**Endpoint:** `POST /v1/videos`
**Función:** `generate_video(prompt: str, model: str = "sora-2", seconds: int = 8, size: str = "1280x720") -> dict`

---

## Descripción

Genera un video a partir de un **prompt textual** usando **Sora**.
Modalidad **Text-to-Video**: solo se requiere un prompt de texto.

---

## Parámetros principales

| Parámetro | Tipo | Descripción                                                |
| --------- | ---- | ---------------------------------------------------------- |
| prompt    | str  | Descripción del video a generar                            |
| model     | str  | Modelo a usar (`sora-2` o `sora-2-pro`)                    |
| seconds   | int  | Duración del video en segundos (4, 8, 12)                  |
| size      | str  | Resolución del video (`720x1280`, `1280x720`, `1024x1024`) |

---

## Ejemplo (Python)

```python
client = SoraClient(api_key="TU_API_KEY")
result = client.generate_video(
    prompt="Un paisaje futurista al atardecer",
    model="sora-2",
    seconds=8,
    size="1280x720"
)
print(result['video_id'])
```

---

## Notas importantes

* Retorna `video_id` y estado inicial (`queued`).
* Validaciones internas: modelo, duración y tamaño permitidos.
* Se puede usar `get_video_status` para consultar progreso.
