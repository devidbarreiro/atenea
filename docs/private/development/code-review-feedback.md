# Feedback de Code Review - Stock Search API

## Resumen
Este documento detalla los problemas encontrados en el PR de Stock Search API y cómo se corrigieron, para servir como guía de mejores prácticas.

## Problemas Encontrados y Correcciones

### 1. ❌ Imports locales dentro de funciones

**Problema:**
```python
def get(self, request):
    from core.services.stock_service import StockService
    from core.services.stock_cache import StockCache
    # ...
```

**Por qué es un problema:**
- Los imports deben estar al inicio del módulo según PEP 8
- Dificulta la detección de dependencias circulares
- Puede causar problemas de rendimiento si se ejecuta múltiples veces
- Hace el código menos legible

**Corrección:**
```python
# Al inicio del archivo
from .services.stock_service import StockService
from .services.stock_cache import StockCache
```

---

### 2. ❌ Falta de manejo de JSONDecodeError

**Problema:**
```python
data = json.loads(request.body)
```

**Por qué es un problema:**
- Si el JSON está mal formado, lanza una excepción no manejada
- El usuario recibe un error 500 genérico en lugar de un mensaje claro
- No hay logging del error para debugging

**Corrección:**
```python
try:
    data = json.loads(request.body)
except json.JSONDecodeError as e:
    logger.error(f"Error al parsear JSON: {e}")
    return JsonResponse({
        'success': False,
        'error': {
            'code': 'INVALID_JSON',
            'message': _('JSON inválido en el cuerpo de la petición')
        }
    }, status=400)
```

---

### 3. ❌ Formato JSON inconsistente

**Problema:**
```python
# Algunas respuestas usaban:
{'status': 'error', 'message': '...'}

# Otras usaban:
{'success': False, 'error': '...'}
```

**Por qué es un problema:**
- Dificulta el manejo en el frontend
- No hay estructura consistente para errores
- Falta información sobre el tipo de error

**Corrección:**
```python
# Formato estándar para éxito:
{
    'success': True,
    'data': {...},
    'cached': False  # opcional
}

# Formato estándar para error:
{
    'success': False,
    'error': {
        'code': 'ERROR_CODE',
        'message': 'Mensaje descriptivo'
    }
}
```

---

### 4. ❌ Falta de validación de entrada

**Problema:**
```python
page = int(request.GET.get('page', 1))
per_page = int(request.GET.get('per_page', 20))
```

**Por qué es un problema:**
- No valida valores negativos o cero
- No limita valores máximos (podría causar problemas de rendimiento)
- Lanza excepción si el valor no es numérico

**Corrección:**
```python
try:
    page = max(1, int(request.GET.get('page', 1)))
except (ValueError, TypeError):
    page = 1

try:
    per_page = max(1, min(100, int(request.GET.get('per_page', 20))))
except (ValueError, TypeError):
    per_page = 20
```

---

### 5. ❌ Falta de autenticación

**Problema:**
```python
class StockSearchView(View):
    # Sin LoginRequiredMixin
```

**Por qué es un problema:**
- Endpoints públicos pueden ser abusados
- No hay control de acceso
- Dificulta el tracking de uso por usuario

**Corrección:**
```python
class StockSearchView(LoginRequiredMixin, View):
    # Requiere autenticación
```

---

### 6. ❌ Falta de internacionalización

**Problema:**
```python
'message': 'El parámetro "query" es requerido'
```

**Por qué es un problema:**
- Mensajes hardcodeados en español
- No se pueden traducir fácilmente
- No sigue las convenciones del proyecto

**Corrección:**
```python
from django.utils.translation import gettext_lazy as _

'message': _('El parámetro "query" es requerido')
```

---

### 7. ❌ Logging insuficiente

**Problema:**
```python
except Exception as e:
    logger.error(f"Error en búsqueda de stock: {e}")
```

**Por qué es un problema:**
- Falta `exc_info=True` para el stack trace completo
- No diferencia entre tipos de errores
- Dificulta el debugging en producción

**Corrección:**
```python
except ValueError as e:
    logger.error(f"Error de validación en búsqueda de stock: {e}", exc_info=True)
except Exception as e:
    logger.error(f"Error inesperado en búsqueda de stock: {e}", exc_info=True)
```

---

### 8. ❌ Docstrings incompletos

**Problema:**
```python
def get(self, request):
    """Busca imágenes o videos en múltiples fuentes de stock"""
```

**Por qué es un problema:**
- No documenta parámetros de query
- No documenta el formato de respuesta
- No menciona requisitos de autenticación

**Corrección:**
```python
def get(self, request):
    """
    Busca imágenes o videos en múltiples fuentes de stock.
    
    Query params:
        - query: Término de búsqueda (requerido)
        - type: Tipo de contenido ('image' o 'video', default: 'image')
        # ... más parámetros
    
    Returns:
        JsonResponse con formato estándar:
        {
            'success': bool,
            'data': dict (si success=True),
            'error': dict (si success=False)
        }
    """
```

---

## Checklist para Futuros PRs

Antes de hacer merge, verificar:

- [ ] ✅ Imports al inicio del módulo (no dentro de funciones)
- [ ] ✅ Manejo de `JSONDecodeError` cuando se parsea JSON
- [ ] ✅ Formato JSON consistente en todas las respuestas
- [ ] ✅ Validación de entrada (tipos, rangos, valores permitidos)
- [ ] ✅ Autenticación/permisos apropiados (`LoginRequiredMixin`, etc.)
- [ ] ✅ Mensajes internacionalizados con `gettext_lazy`
- [ ] ✅ Logging con `exc_info=True` para excepciones
- [ ] ✅ Docstrings completos con parámetros y formato de respuesta
- [ ] ✅ Manejo de errores específicos (no solo `Exception` genérico)
- [ ] ✅ Códigos de error descriptivos para el frontend

---

## Recursos Útiles

- [Django Best Practices](https://docs.djangoproject.com/en/stable/misc/design-philosophies/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Django Translation](https://docs.djangoproject.com/en/stable/topics/i18n/translation/)
- [Django Logging](https://docs.djangoproject.com/en/stable/topics/logging/)





