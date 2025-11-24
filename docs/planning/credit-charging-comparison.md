# Comparación Completa: Estrategias de Cobro de Créditos

## Las 4 Opciones

1. **Opción 1**: Decorador/Middleware
2. **Opción 2**: Servicio Explícito (llamada manual)
3. **Opción 3**: Signal de Django (automático)
4. **Opción 4**: Híbrido (Servicio + Helpers en Modelos) ⭐

---

## Opción 1: Decorador/Middleware

### Cómo Funciona

Crear un decorador que envuelva los métodos de generación o los métodos `mark_as_completed()`.

```python
# core/decorators.py
from functools import wraps

def charge_credits(service_type):
    """Decorador que cobra créditos después de completar"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Detectar objeto completado
            obj = args[0] if args else kwargs.get('video') or kwargs.get('image')
            if obj and obj.status == 'completed':
                from core.services.credits import CreditService
                if service_type == 'video':
                    CreditService.deduct_credits_for_video(obj.created_by, obj)
                elif service_type == 'image':
                    CreditService.deduct_credits_for_image(obj.created_by, obj)
            
            return result
        return wrapper
    return decorator

# Uso:
class Video(models.Model):
    @charge_credits('video')
    def mark_as_completed(self, gcs_path=None, metadata=None):
        self.status = 'completed'
        # ... resto del código
```

### Ventajas ✅
- ✅ Automático una vez decorado
- ✅ Código limpio en los modelos
- ✅ Fácil de aplicar a múltiples métodos

### Desventajas ❌
- ❌ Menos explícito (el decorador puede pasar desapercibido)
- ❌ Difícil de debuggear (el decorador intercepta la llamada)
- ❌ No puedes validar créditos ANTES de generar
- ❌ Puede ser confuso con múltiples decoradores
- ❌ Testing más complejo (necesitas mockear el decorador)

---

## Opción 2: Servicio Explícito (Llamada Manual)

### Cómo Funciona

Llamar explícitamente `CreditService.deduct_credits()` en cada lugar donde se completa contenido.

```python
# core/services.py
def _check_heygen_status(self, video: Video) -> Dict:
    if api_status == 'completed':
        video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
        
        # ✅ LLAMADA EXPLÍCITA
        from core.services.credits import CreditService
        CreditService.deduct_credits_for_video(video.created_by, video)
```

### Ventajas ✅
- ✅ **Muy explícito** - Ves claramente dónde se cobra
- ✅ **Control total** - Decides exactamente cuándo cobrar
- ✅ **Fácil debugging** - Puedes poner breakpoints fácilmente
- ✅ **Validación previa** - Puedes validar créditos ANTES de generar
- ✅ **Testing fácil** - Fácil de mockear y testear
- ✅ **Manejo de errores** - Puedes manejar errores específicos por caso

### Desventajas ❌
- ❌ **Fácil de olvidar** - Si olvidas llamarlo en un lugar, no se cobra
- ❌ **Código repetitivo** - Tienes que llamarlo en muchos lugares
- ❌ **Mantenimiento** - Si cambias la lógica, tienes que cambiar en varios lugares
- ❌ **Inconsistencias** - Puede haber diferencias entre lugares

---

## Opción 3: Signal de Django

### Cómo Funciona

Usar signals de Django para detectar automáticamente cuando un modelo cambia a `status='completed'`.

```python
# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Video)
def charge_credits_for_video(sender, instance, created, **kwargs):
    if not created and instance.status == 'completed':
        if not instance.metadata.get('credits_charged'):
            CreditService.deduct_credits_for_video(instance.created_by, instance)
            instance.metadata['credits_charged'] = True
            instance.save(update_fields=['metadata'])

# core/services.py
def _check_heygen_status(self, video: Video) -> Dict:
    if api_status == 'completed':
        # ✅ NO NECESITAS LLAMAR NADA - El signal lo hace automáticamente
        video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
```

### Ventajas ✅
- ✅ **100% automático** - Imposible olvidar cobrar
- ✅ **DRY (Don't Repeat Yourself)** - Lógica en un solo lugar
- ✅ **Código limpio** - Los servicios no tienen código de cobro
- ✅ **Consistencia** - Siempre se cobra de la misma manera
- ✅ **Menos código** - No necesitas llamar nada explícitamente

### Desventajas ❌
- ❌ **Menos explícito** - No es obvio que se está cobrando
- ❌ **Debugging difícil** - Los signals pueden ser difíciles de seguir
- ❌ **No validación previa** - No puedes validar créditos ANTES de generar
- ❌ **Orden de ejecución** - Puede haber problemas con múltiples signals
- ❌ **Riesgo de doble cobro** - Necesitas flags para evitar cobrar dos veces
- ❌ **Testing complejo** - Necesitas mockear signals
- ❌ **Casos especiales** - Difícil manejar excepciones o casos especiales

---

## Opción 4: Híbrido (Servicio + Helpers en Modelos) ⭐

### Cómo Funciona

Modificar los métodos `mark_as_completed()` de los modelos para que llamen automáticamente al servicio de créditos.

```python
# core/models.py
class Video(models.Model):
    def mark_as_completed(self, gcs_path=None, metadata=None):
        """Marca el video como completado y cobra créditos automáticamente"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # ✅ COBRO AUTOMÁTICO pero EXPLÍCITO en el método
        if self.created_by:
            from core.services.credits import CreditService
            try:
                CreditService.deduct_credits_for_video(self.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para video {self.id}: {e}")
                # No fallar la operación si falla el cobro

# core/services.py
def _check_heygen_status(self, video: Video) -> Dict:
    if api_status == 'completed':
        # ✅ Se cobra automáticamente en mark_as_completed()
        video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
```

### Ventajas ✅
- ✅ **Automático** - No tienes que recordar llamarlo
- ✅ **Explícito** - Ves claramente que se cobra en el método del modelo
- ✅ **Control** - Puedes validar créditos ANTES de generar (en `generate_video()`)
- ✅ **Consistencia** - Siempre se cobra igual, en un solo lugar por modelo
- ✅ **Fácil debugging** - Puedes poner breakpoints en el método del modelo
- ✅ **Testing fácil** - Puedes mockear el servicio fácilmente
- ✅ **Manejo de errores** - Puedes manejar errores sin romper la operación
- ✅ **Flexibilidad** - Puedes agregar parámetro `charge_credits=False` si necesitas excepciones

### Desventajas ❌
- ⚠️ **Modificar métodos existentes** - Necesitas cambiar `mark_as_completed()` en todos los modelos
- ⚠️ **Acoplamiento** - Los modelos conocen el servicio de créditos (pero es aceptable)

---

## Comparación Directa

| Aspecto | Decorador | Servicio Explícito | Signal Django | Híbrido ⭐ |
|---------|-----------|-------------------|---------------|------------|
| **Automatización** | ✅ Alta | ❌ Manual | ✅ Total | ✅ Alta |
| **Claridad** | ⚠️ Media | ✅ Muy alta | ❌ Baja | ✅ Alta |
| **Control** | ⚠️ Medio | ✅ Total | ❌ Bajo | ✅ Alto |
| **Validación Previa** | ❌ No | ✅ Sí | ❌ No | ✅ Sí |
| **Fácil de Olvidar** | ✅ No | ❌ Sí | ✅ No | ✅ No |
| **Debugging** | ❌ Difícil | ✅ Fácil | ❌ Difícil | ✅ Fácil |
| **Testing** | ❌ Complejo | ✅ Fácil | ❌ Complejo | ✅ Fácil |
| **Mantenimiento** | ✅ Un lugar | ❌ Múltiples | ✅ Un lugar | ✅ Un lugar |
| **Código Limpio** | ✅ Sí | ⚠️ Verboso | ✅ Sí | ✅ Sí |
| **Consistencia** | ✅ Sí | ❌ Puede variar | ✅ Sí | ✅ Sí |
| **Casos Especiales** | ⚠️ Difícil | ✅ Fácil | ❌ Difícil | ✅ Fácil |
| **Riesgo de Doble Cobro** | ⚠️ Medio | ✅ Bajo | ⚠️ Alto | ✅ Bajo |

---

## Ejemplos de Código

### Opción 1: Decorador
```python
@charge_credits('video')
def mark_as_completed(self, ...):
    # ... código ...
```
**Problema**: No es obvio que se está cobrando, difícil de debuggear.

### Opción 2: Servicio Explícito
```python
video.mark_as_completed(...)
CreditService.deduct_credits_for_video(user, video)  # ← Fácil olvidar
```
**Problema**: Fácil olvidar llamarlo en algún lugar.

### Opción 3: Signal
```python
video.mark_as_completed(...)  # ← Se cobra automáticamente (pero no se ve)
```
**Problema**: No es explícito, difícil de debuggear, no puedes validar antes.

### Opción 4: Híbrido ⭐
```python
def mark_as_completed(self, ...):
    # ... código ...
    CreditService.deduct_credits_for_video(self.created_by, self)  # ← Explícito y automático
```
**Ventaja**: Explícito, automático, fácil de debuggear.

---

## Escenarios Reales

### Escenario 1: Validar Créditos ANTES de Generar
```python
# Usuario hace clic en "Generar Video"
def generate_video(self, video):
    # ✅ Solo con Opción 2 y 4 puedes validar ANTES
    if not CreditService.has_enough_credits(video.created_by, estimated_cost):
        raise InsufficientCreditsException("No tienes suficientes créditos")
    
    # Generar video...
```

**Resultado**:
- ✅ Opción 2: Puedes validar
- ✅ Opción 4: Puedes validar
- ❌ Opción 1: No puedes validar fácilmente
- ❌ Opción 3: No puedes validar (solo después)

### Escenario 2: Debuggear un Cobro Incorrecto
```python
# Usuario reporta que se cobró mal
```

**Resultado**:
- ✅ Opción 2: Fácil - ves la llamada explícita
- ✅ Opción 4: Fácil - ves la llamada en `mark_as_completed()`
- ❌ Opción 1: Difícil - el decorador intercepta
- ❌ Opción 3: Muy difícil - el signal se ejecuta automáticamente

### Escenario 3: Caso Especial: No Cobrar en Pruebas
```python
# En tests, no queremos cobrar créditos reales
```

**Resultado**:
- ✅ Opción 2: Fácil - simplemente no llamas el servicio
- ✅ Opción 4: Fácil - puedes agregar `charge_credits=False`
- ⚠️ Opción 1: Necesitas mockear el decorador
- ⚠️ Opción 3: Necesitas deshabilitar signals en tests

---

## Recomendación Final: **Opción 4 (Híbrido)** ⭐

### ¿Por qué?

1. **Lo mejor de ambos mundos**:
   - Automático como Signal (no puedes olvidar)
   - Explícito como Servicio (fácil de entender)

2. **Validación previa**:
   - Puedes validar créditos ANTES de generar contenido
   - Mejor UX (el usuario sabe antes si tiene créditos)

3. **Debugging y Testing**:
   - Fácil de debuggear (ves la llamada en el método)
   - Fácil de testear (puedes mockear el servicio)

4. **Flexibilidad**:
   - Puedes agregar `charge_credits=False` para casos especiales
   - Puedes manejar errores sin romper la operación

5. **Consistencia**:
   - Siempre se cobra igual, en un solo lugar por modelo
   - Menos propenso a errores

### Implementación Recomendada

```python
# core/models.py
class Video(models.Model):
    def mark_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
        """Marca el video como completado y cobra créditos si es necesario"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente (pero explícito)
        if charge_credits and self.created_by:
            from core.services.credits import CreditService
            try:
                CreditService.deduct_credits_for_video(self.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para video {self.id}: {e}")
                # No fallar la operación si falla el cobro

# core/services.py
def generate_video(self, video):
    # Validar créditos ANTES de generar
    estimated_cost = CreditService.estimate_video_cost(video)
    if not CreditService.has_enough_credits(video.created_by, estimated_cost):
        raise InsufficientCreditsException(f"Necesitas {estimated_cost} créditos")
    
    # Generar video...
    # Cuando se complete, se cobrará automáticamente en mark_as_completed()
```

**Resultado**: Código limpio, automático, explícito, fácil de debuggear y testear. 🎯



