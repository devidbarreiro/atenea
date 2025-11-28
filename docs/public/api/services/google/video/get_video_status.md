# Estado de Video - Gemini Veo API

**Funcionalidad:** Consultar el estado de una operación de generación de video en curso o completada.

**Método principal:** `get_video_status(operation_name: str) -> dict`

---

## Descripción

Esta función permite obtener información detallada sobre una operación de generación de video. Incluye:

* Estado de la operación (`processing`, `completed`, `failed`, `error`).
* URLs de los videos generados (si la operación se completó).
* Conteo de videos filtrados por RAI (Responsible AI) en caso de contenido sensible.
* Metadatos adicionales de la operación.

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
status = client.get_video_status("projects/.../operations/xyz123")
print(status)
```

---

## Posibles valores de retorno

| Campo              | Tipo | Descripción                                                            |
| ------------------ | ---- | ---------------------------------------------------------------------- |
| status             | str  | Estado de la operación: `processing`, `completed`, `failed`, `error`   |
| video_url          | str  | URL del primer video generado (solo si `completed`)                    |
| all_video_urls     | list | Lista con todos los videos generados, cada uno con `url` y `mime_type` |
| operation_data     | dict | Datos completos retornados por Gemini Veo                              |
| rai_filtered_count | int  | Número de videos filtrados por Responsible AI                          |
| metadata           | dict | Información de progreso si la operación aún está procesando            |
| error              | str  | Mensaje de error (si aplica)                                           |
