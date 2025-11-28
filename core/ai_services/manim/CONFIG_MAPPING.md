# Mapeo de Configuración - Manim Quote Animation

Este documento describe el mapeo entre los campos del formulario (views.py), la configuración del servicio (services.py), las variables de entorno (client.py), y los parámetros de la animación (quote.py).

## Flujo de Datos

```
views.py (_build_manim_quote_config)
    ↓
services.py (_generate_manim_quote_video)
    ↓
client.py (generate_quote_video)
    ↓
render_wrapper.py (variables de entorno)
    ↓
quote.py (QuoteAnimation.construct)
```

## Mapeo de Campos

### 1. Formulario → Config (views.py)

| Campo Formulario | Clave Config | Tipo | Validación |
|------------------|--------------|------|------------|
| `prompt` | `text` | str | Requerido, no vacío |
| `author` | `author` | str | Opcional |
| `duration` | `duration` | float | Opcional, > 0 si se proporciona |
| `container_color` / `container_color_text` | `container_color` | str | Opcional, formato hex (#RRGGBB) |
| `text_color` / `text_color_text` | `text_color` | str | Opcional, formato hex (#RRGGBB) |
| `font_family` | `font_family` | str | Opcional, default: 'normal' |
| `quality` | `quality` | str | Opcional, default: 'k' |

**Ubicación**: `core/views.py::_build_manim_quote_config()`

### 2. Config → Variables de Entorno (client.py)

| Clave Config | Variable Entorno | Codificación | Valores Válidos |
|--------------|------------------|--------------|-----------------|
| `text` | `QUOTE_ANIMATION_TEXT` | base64 | Cualquier string |
| `author` | `QUOTE_ANIMATION_AUTHOR` | base64 si existe | String o "None" |
| `duration` | `QUOTE_ANIMATION_DURATION` | string | Float como string o "None" |
| `container_color` | `QUOTE_ANIMATION_CONTAINER_COLOR` | string | Hex color (#RRGGBB) |
| `text_color` | `QUOTE_ANIMATION_TEXT_COLOR` | string | Hex color (#RRGGBB) |
| `font_family` | `QUOTE_ANIMATION_FONT_FAMILY` | string | 'normal', 'bold', 'italic', 'bold_italic' |
| - | `MANIM_ANIMATION_TYPE` | string | 'quote' |

**Ubicación**: `core/ai_services/manim/client.py::generate_quote_video()`

### 3. Variables de Entorno → Parámetros Animación (quote.py)

| Variable Entorno | Parámetro | Tipo | Default | Validación |
|------------------|-----------|------|---------|------------|
| `QUOTE_ANIMATION_TEXT` | `quote` | str | - | Requerido, no vacío |
| `QUOTE_ANIMATION_AUTHOR` | `author` | str | None | Opcional |
| `QUOTE_ANIMATION_DURATION` | `duration` | float | Auto-calculado | > 0 si se proporciona |
| `QUOTE_ANIMATION_CONTAINER_COLOR` | `container_color` | str | '#0066CC' | Formato hex válido |
| `QUOTE_ANIMATION_TEXT_COLOR` | `text_color` | str | '#FFFFFF' | Formato hex válido |
| `QUOTE_ANIMATION_FONT_FAMILY` | `font_family` | str | 'normal' | Valores válidos |

**Ubicación**: `core/ai_services/manim/animations/quote.py::construct()`

## Validaciones por Capa

### views.py
- ✅ `duration` se parsea a float si es posible
- ✅ Colores pueden venir de `container_color` o `container_color_text`
- ✅ `font_family` default: 'normal'

### client.py
- ✅ Valida `quality` en ['l', 'm', 'h', 'k']
- ✅ Valida `duration` > 0 si se proporciona
- ✅ Valida formato hex de colores (#RRGGBB)
- ✅ Valida `font_family` en valores válidos
- ✅ Codifica strings en base64 para preservar caracteres especiales

### quote.py
- ✅ Valida que `quote` no esté vacío
- ✅ Valida formato hex de colores
- ✅ Valida `font_family` (fallback a 'normal' si inválido)
- ✅ Valida `duration` > 0 si se proporciona
- ✅ Calcula duración automática si no se proporciona

## Valores por Defecto

| Parámetro | Valor por Defecto | Ubicación |
|-----------|-------------------|-----------|
| `container_color` | `#0066CC` | quote.py |
| `text_color` | `#FFFFFF` | quote.py |
| `font_family` | `'normal'` | views.py, quote.py |
| `quality` | `'k'` | views.py, client.py |
| `duration` | Auto-calculado (8-15s) | quote.py |

## Notas Importantes

1. **Codificación Base64**: Los strings `text` y `author` se codifican en base64 para preservar caracteres especiales. La animación los decodifica automáticamente.

2. **Duración**: Si no se proporciona, se calcula automáticamente basándose en la longitud del texto:
   - Base: 8.0 segundos
   - +0.05 segundos por carácter
   - Rango: 8.0 - 15.0 segundos

3. **Colores**: Deben estar en formato hex (#RRGGBB). Si no se proporcionan, se usan los valores por defecto.

4. **Font Family**: Valores válidos son 'normal', 'bold', 'italic', 'bold_italic'. Cualquier otro valor se convierte a 'normal'.

5. **Quality**: Valores válidos son 'l' (480p15), 'm' (720p30), 'h' (1080p60), 'k' (2160p60).

