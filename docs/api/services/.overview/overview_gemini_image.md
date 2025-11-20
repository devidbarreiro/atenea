# Overview - Gemini Image API

**Base de la API:**

* Gestionada internamente por `genai.Client` con modelo `gemini-2.5-flash-image`
* No hay URL pública directa; todas las llamadas se hacen a través del cliente Python (`genai.Client`) usando el modelo.

Este documento sirve como **resumen central** de la API de generación de imágenes de Google Gemini dentro de nuestra aplicación.
Desde aquí puedes acceder a cada endpoint individual para ver **detalles completos**, ejemplos en Python, parámetros y notas importantes.

---

## Endpoints disponibles

### Generación de imágenes

| Nombre                                                                                                       | Endpoint                 | Método | Función                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------ | ------------------------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| <a href="#" data-route="google/gemini_image/generate_image_from_text">Generar imagen desde texto</a>         | `gemini-2.5-flash-image` | POST   | `generate_image_from_text(prompt: str, aspect_ratio: str, response_modalities: List[str]) -> Dict`                                            |
| <a href="#" data-route="google/gemini_image/generate_image_from_image">Editar imagen existente</a>           | `gemini-2.5-flash-image` | POST   | `generate_image_from_image(prompt: str, input_image_data: bytes, aspect_ratio: str, response_modalities: List[str]) -> Dict`                  |
| <a href="#" data-route="google/gemini_image/generate_image_from_multiple_image">Generar imagen compuesta</a> | `gemini-2.5-flash-image` | POST   | `generate_image_from_multiple_images(prompt: str, input_images_data: List[bytes], aspect_ratio: str, response_modalities: List[str]) -> Dict` |

### Utilidades

| Nombre                                                                                  | Función                                                                                  |
| --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| <a href="#" data-route="google/gemini_image/utilities">Utilities - Gemini Image API</a> | Conversión de imágenes, validación de aspect ratio y obtención de dimensiones soportadas |

---

## Cómo usar este resumen

1. Haz clic en el **Nombre** del endpoint para ver la documentación completa en su `.md` individual.
2. Revisa la columna **Endpoint** para conocer el modelo y método utilizados en la API interna de Gemini.
3. Utiliza los ejemplos de Python como guía para implementar llamadas a la API de Gemini en tu aplicación.

---

## Notas generales

* Todos los endpoints requieren una **API Key** de Google Gemini.
* Los resultados incluyen imágenes en distintos **aspect ratios** y, opcionalmente, texto de respuesta.
* Cada imagen generada se devuelve en **bytes**, lista para guardar o convertir a base64.
* Valida siempre el **aspect ratio** usando `GeminiImageClient.validate_aspect_ratio(aspect_ratio)` antes de generar imágenes.
* Maneja errores y excepciones de la API para producción.
* La navegación dentro de la documentación funciona con enlaces `data-route` que reflejan la estructura de carpetas del proyecto.
