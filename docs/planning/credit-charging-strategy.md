# Estrategias de Implementación: Cobro de Créditos

## Opción 2: Servicio Explícito (CreditService)

### Cómo Funciona

Crear un servicio `CreditService` que se llama **explícitamente** en cada punto donde se genera contenido.

```python
# core/services/credits.py
class CreditService:
    @staticmethod
    def deduct_credits_for_video(user, video):
        """Calcula y deduce créditos para un video"""
        cost = CreditService.calculate_video_cost(video)
        CreditService.deduct_credits(user, cost, service='video', resource_id=video.id)
    
    @staticmethod
    def calculate_video_cost(video):
        """Calcula costo según tipo de video"""
        duration = video.duration or video.metadata.get('duration', 0)
        
        if video.type == 'heygen_avatar_v2':
            return duration * 5  # 5 créditos/segundo
        elif video.type == 'heygen_avatar_iv':
            return duration * 15  # 15 créditos/segundo
        elif video.type == 'gemini_veo':
            # Verificar si tiene audio
            has_audio = video.metadata.get('generate_audio', False)
            return duration * (75 if has_audio else 50)
        elif video.type == 'sora':
            model = video.config.get('sora_model', 'sora-2')
            return duration * (50 if model == 'sora-2-pro' else 10)
        # ...
```

**Uso en el código**:

```python
# core/services.py - VideoService._check_heygen_status()
def _check_heygen_status(self, video: Video) -> Dict:
    # ... código existente ...
    
    if api_status == 'completed':
        video_url = status_data.get('video_url')
        if video_url:
            # ... guardar video ...
            video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
            
            # ✅ COBRAR EXPLÍCITAMENTE
            from core.services.credits import CreditService
            CreditService.deduct_credits_for_video(video.created_by, video)
            
            logger.info(f"Video {video.id} completado: {gcs_full_path}")
```

### Ventajas ✅

1. **Control Total**: Sabes exactamente cuándo y dónde se cobra
2. **Claridad**: Es explícito en el código, fácil de entender
3. **Flexibilidad**: Puedes agregar lógica específica por caso
4. **Debugging**: Fácil de debuggear, puedes poner breakpoints
5. **Testing**: Fácil de testear, puedes mockear el servicio
6. **Manejo de Errores**: Puedes manejar errores específicos por caso
7. **Validaciones**: Puedes validar créditos ANTES de generar contenido

### Desventajas ❌

1. **Repetición**: Tienes que recordar llamar el servicio en cada lugar
2. **Fácil de Olvidar**: Si olvidas llamarlo en un lugar, no se cobra
3. **Código Duplicado**: Puede haber código repetido en varios lugares
4. **Mantenimiento**: Si cambias la lógica, tienes que cambiar en varios lugares

---

## Opción 3: Signal de Django

### Cómo Funciona

Usar signals de Django para detectar automáticamente cuando un modelo se marca como `completed` y cobrar automáticamente.

```python
# core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Video, Image, Audio, Scene

@receiver(post_save, sender=Video)
def charge_credits_for_video(sender, instance, created, **kwargs):
    """Cobra créditos cuando un video se completa"""
    # Solo cobrar si se acaba de marcar como completado
    if not created and instance.status == 'completed':
        # Verificar que no se haya cobrado antes
        if not instance.metadata.get('credits_charged', False):
            from core.services.credits import CreditService
            CreditService.deduct_credits_for_video(instance.created_by, instance)
            
            # Marcar como cobrado para evitar doble cobro
            instance.metadata['credits_charged'] = True
            instance.save(update_fields=['metadata'])

@receiver(post_save, sender=Image)
def charge_credits_for_image(sender, instance, created, **kwargs):
    """Cobra créditos cuando una imagen se completa"""
    if not created and instance.status == 'completed':
        if not instance.metadata.get('credits_charged', False):
            from core.services.credits import CreditService
            CreditService.deduct_credits_for_image(instance.created_by, instance)
            
            instance.metadata['credits_charged'] = True
            instance.save(update_fields=['metadata'])

# ... similar para Audio, Scene, etc.
```

**Registro de signals**:

```python
# core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        import core.signals  # Registrar signals
```

**Uso en el código**:

```python
# core/services.py - VideoService._check_heygen_status()
def _check_heygen_status(self, video: Video) -> Dict:
    # ... código existente ...
    
    if api_status == 'completed':
        video_url = status_data.get('video_url')
        if video_url:
            # ... guardar video ...
            # ✅ NO NECESITAS LLAMAR NADA - El signal lo hace automáticamente
            video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
            logger.info(f"Video {video.id} completado: {gcs_full_path}")
```

### Ventajas ✅

1. **Automático**: No tienes que recordar llamarlo en cada lugar
2. **DRY (Don't Repeat Yourself)**: La lógica está en un solo lugar
3. **Menos Errores**: Imposible olvidar cobrar en algún lugar
4. **Mantenimiento**: Cambias la lógica en un solo lugar
5. **Consistencia**: Siempre se cobra de la misma manera
6. **Menos Código**: El código de servicios queda más limpio

### Desventajas ❌

1. **Menos Explícito**: No es obvio que se está cobrando al leer el código
2. **Debugging Más Difícil**: Los signals pueden ser difíciles de debuggear
3. **Orden de Ejecución**: Puede haber problemas con el orden de signals
4. **Doble Cobro**: Riesgo de cobrar dos veces si no se maneja bien
5. **Testing**: Más difícil de testear, necesitas mockear signals
6. **Validaciones Previas**: No puedes validar créditos ANTES de generar (solo después)
7. **Casos Especiales**: Difícil manejar casos especiales o excepciones

---

## Comparación Directa

| Aspecto | Servicio Explícito | Signal de Django |
|---------|-------------------|------------------|
| **Claridad** | ✅ Muy claro | ❌ Menos obvio |
| **Control** | ✅ Total control | ⚠️ Menos control |
| **Mantenimiento** | ❌ Múltiples lugares | ✅ Un solo lugar |
| **Errores Humanos** | ❌ Fácil olvidar | ✅ Imposible olvidar |
| **Debugging** | ✅ Fácil | ❌ Más difícil |
| **Testing** | ✅ Fácil | ❌ Más difícil |
| **Validación Previa** | ✅ Posible | ❌ No posible |
| **Casos Especiales** | ✅ Fácil | ❌ Difícil |
| **Código Limpio** | ⚠️ Más verboso | ✅ Menos código |

---

## Recomendación: **Híbrida** 🎯

### Estrategia Recomendada: Servicio Explícito + Helper Methods

Usar **servicio explícito** pero con **métodos helper** que simplifiquen el código y reduzcan errores.

```python
# core/services/credits.py
class CreditService:
    @staticmethod
    def deduct_credits_for_video(user, video):
        """Calcula y deduce créditos para un video"""
        # Validar que no se haya cobrado antes
        if video.metadata.get('credits_charged'):
            logger.warning(f"Video {video.id} ya fue cobrado")
            return
        
        cost = CreditService.calculate_video_cost(video)
        
        # Validar créditos disponibles
        if not CreditService.has_enough_credits(user, cost):
            raise InsufficientCreditsException(f"Usuario no tiene suficientes créditos: necesita {cost}")
        
        # Deducir créditos
        CreditService.deduct_credits(user, cost, service='video', resource_id=video.id)
        
        # Marcar como cobrado
        video.metadata['credits_charged'] = True
        video.save(update_fields=['metadata'])
    
    @staticmethod
    def deduct_credits_for_image(user, image):
        """Calcula y deduce créditos para una imagen"""
        if image.metadata.get('credits_charged'):
            return
        
        cost = 2  # 2 créditos por imagen
        
        if not CreditService.has_enough_credits(user, cost):
            raise InsufficientCreditsException(f"Usuario no tiene suficientes créditos: necesita {cost}")
        
        CreditService.deduct_credits(user, cost, service='image', resource_id=image.id)
        
        image.metadata['credits_charged'] = True
        image.save(update_fields=['metadata'])
    
    # ... métodos similares para audio, scene, etc.
```

**Uso simplificado con decorador opcional**:

```python
# core/decorators.py
from functools import wraps

def charge_credits_on_completion(service_type):
    """Decorador que cobra créditos cuando se completa una operación"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Detectar el objeto creado/completado
            if service_type == 'video':
                video = args[0] if args else kwargs.get('video')
                if video and video.status == 'completed':
                    CreditService.deduct_credits_for_video(video.created_by, video)
            # ... otros tipos
            
            return result
        return wrapper
    return decorator

# Uso:
@charge_credits_on_completion('video')
def mark_as_completed(self, gcs_path=None, metadata=None):
    self.status = 'completed'
    # ... resto del código
```

**O mejor aún, método helper en los modelos**:

```python
# core/models.py - Video
class Video(models.Model):
    # ... campos existentes ...
    
    def mark_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
        """Marca el video como completado y cobra créditos si es necesario"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if charge_credits and self.created_by:
            from core.services.credits import CreditService
            try:
                CreditService.deduct_credits_for_video(self.created_by, self)
            except Exception as e:
                logger.error(f"Error al cobrar créditos para video {self.id}: {e}")
                # No fallar la operación si falla el cobro, pero loguear
```

---

## Recomendación Final

### Usar Servicio Explícito con Helpers en los Modelos

**Por qué**:
1. ✅ **Control total** sobre cuándo y cómo se cobra
2. ✅ **Claridad** - Es obvio que se está cobrando
3. ✅ **Validación previa** - Puedes validar créditos ANTES de generar
4. ✅ **Manejo de errores** - Puedes manejar errores específicos
5. ✅ **Testing fácil** - Fácil de testear y mockear
6. ✅ **Menos errores** - Los helpers en modelos aseguran que siempre se llame
7. ✅ **Flexibilidad** - Puedes deshabilitar cobro con `charge_credits=False` si es necesario

**Implementación**:
- Agregar método `mark_as_completed_with_credits()` en cada modelo
- O mejor: modificar `mark_as_completed()` existente para que cobre automáticamente
- El servicio `CreditService` maneja toda la lógica de cálculo y deducción
- Los métodos de los modelos llaman al servicio automáticamente

**Ventaja sobre Signals**:
- Más explícito y fácil de entender
- Puedes validar créditos ANTES de generar contenido (importante para UX)
- Mejor manejo de errores y casos especiales
- Más fácil de debuggear y testear

**Ventaja sobre Servicio Puro**:
- Menos propenso a errores (los helpers aseguran que siempre se llame)
- Código más limpio (no necesitas recordar llamarlo en cada lugar)
- Consistencia automática

---

## Ejemplo de Implementación Completa

```python
# core/models.py
class Video(models.Model):
    def mark_as_completed(self, gcs_path=None, metadata=None):
        """Marca el video como completado y cobra créditos"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gcs_path:
            self.gcs_path = gcs_path
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'gcs_path', 'metadata', 'updated_at'])
        
        # Cobrar créditos automáticamente
        if self.created_by:
            from core.services.credits import CreditService
            CreditService.deduct_credits_for_video(self.created_by, self)

# core/services.py
def _check_heygen_status(self, video: Video) -> Dict:
    # ... código existente ...
    
    if api_status == 'completed':
        video_url = status_data.get('video_url')
        if video_url:
            # ... guardar video ...
            # ✅ Se cobra automáticamente en mark_as_completed()
            video.mark_as_completed(gcs_path=gcs_full_path, metadata=metadata)
            logger.info(f"Video {video.id} completado: {gcs_full_path}")
```

**Resultado**: Código limpio, automático, pero explícito y fácil de entender.



