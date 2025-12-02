# Formatear Guión para Scenes - Vuela.ai

**Función:** `format_script_for_scenes(scenes: List[Dict[str, str]]) -> str`

---

## Descripción

Formatea un guión de múltiples escenas y personajes para el modo `scenes` de Vuela.ai.

---

## Ejemplo (Python)

```python
scenes = [
    {'character': 'Alice', 'text': 'Hola, ¿cómo estás?'},
    {'character': 'Bob', 'text': 'Bien, gracias!'}
]

script = client.format_script_for_scenes(scenes)
print(script)
```

---

## Notas importantes

* Genera un bloque `[characters]` con personajes únicos.
* Cada escena se formatea como `[scene: Character] ... [end]`.
* Útil para pasar directamente a `generate_video` en modo `scenes`.
