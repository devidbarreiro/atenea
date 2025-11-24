# Plan de Implementación: Sistema de Créditos (Híbrido)

## Mantenibilidad y Escalabilidad del Híbrido

### ✅ Mantenibilidad

**¿Por qué es fácil de mantener?**

1. **Un solo lugar por modelo**: La lógica de cobro está en `mark_as_completed()` de cada modelo
   - Si cambias cómo se cobra un video, solo cambias en `Video.mark_as_completed()`
   - No necesitas buscar en múltiples archivos

2. **Servicio centralizado**: Toda la lógica de cálculo está en `CreditService`
   - Si cambian los precios, solo actualizas `CreditService.calculate_*_cost()`
   - Un solo lugar para toda la lógica de créditos

3. **Fácil de entender**: Cualquier desarrollador ve claramente que se cobra en `mark_as_completed()`
   - No hay "magia oculta" como en signals o decoradores
   - El código es auto-documentado

4. **Fácil de modificar**: Si necesitas agregar un nuevo tipo de contenido, solo:
   - Agregas método en `CreditService.deduct_credits_for_*()`
   - Modificas `mark_as_completed()` del modelo correspondiente

### ✅ Escalabilidad

**¿Por qué escala bien?**

1. **Fácil agregar nuevos servicios**: 
   - Agregas un nuevo servicio de IA → Agregas método en `CreditService`
   - No necesitas tocar código existente

2. **Fácil cambiar precios**:
   - Cambias precios → Solo actualizas `CreditService.calculate_*_cost()`
   - Todos los lugares se actualizan automáticamente

3. **Fácil agregar nuevas funcionalidades**:
   - Descuentos por volumen → Lo agregas en `CreditService`
   - Planes premium → Lo agregas en `CreditService`
   - Promociones → Lo agregas en `CreditService`

4. **Performance**: 
   - No hay overhead de signals (que se ejecutan en cada save)
   - Solo se ejecuta cuando realmente se completa contenido
   - Puedes optimizar queries fácilmente

---

## Fase 1: Modelos de Base de Datos

### 1.1 UserCredits (Saldo de créditos por usuario)

```python
# core/models.py
class UserCredits(models.Model):
    """Saldo de créditos por usuario"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='credits'
    )
    credits = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Saldo actual de créditos'
    )
    total_purchased = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Total de créditos comprados históricamente'
    )
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Total de créditos gastados históricamente'
    )
    monthly_limit = models.IntegerField(
        default=1000,
        help_text='Límite mensual de créditos'
    )
    current_month_usage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Créditos usados en el mes actual'
    )
    last_reset_date = models.DateField(
        null=True,
        blank=True,
        help_text='Última fecha de reset mensual'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Créditos de Usuario'
        verbose_name_plural = 'Créditos de Usuarios'
    
    def __str__(self):
        return f"{self.user.username}: {self.credits} créditos"
    
    def reset_monthly_usage(self):
        """Resetea el uso mensual"""
        self.current_month_usage = 0
        self.last_reset_date = timezone.now().date()
        self.save(update_fields=['current_month_usage', 'last_reset_date'])
```

### 1.2 CreditTransaction (Historial de transacciones)

```python
class CreditTransaction(models.Model):
    """Historial de transacciones de créditos"""
    TRANSACTION_TYPES = [
        ('purchase', 'Compra'),
        ('spend', 'Gasto'),
        ('refund', 'Reembolso'),
        ('adjustment', 'Ajuste'),
        ('monthly_reset', 'Reset Mensual'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_transactions'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Cantidad de créditos (positivo para compras, negativo para gastos)'
    )
    balance_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Saldo antes de la transacción'
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Saldo después de la transacción'
    )
    description = models.TextField(
        blank=True,
        help_text='Descripción de la transacción'
    )
    
    # Relación genérica al recurso relacionado
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    service_name = models.CharField(
        max_length=50,
        blank=True,
        help_text='Nombre del servicio usado (gemini_veo, sora, etc.)'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Información adicional (duración, tokens, etc.)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['service_name', '-created_at']),
        ]
        verbose_name = 'Transacción de Créditos'
        verbose_name_plural = 'Transacciones de Créditos'
    
    def __str__(self):
        return f"{self.user.username}: {self.transaction_type} {self.amount} créditos"
```

### 1.3 ServiceUsage (Tracking de uso por servicio)

```python
class ServiceUsage(models.Model):
    """Tracking detallado de uso por servicio"""
    SERVICE_CHOICES = [
        ('gemini_veo', 'Gemini Veo'),
        ('sora', 'OpenAI Sora'),
        ('heygen_v2', 'HeyGen Avatar V2'),
        ('heygen_avatar_iv', 'HeyGen Avatar IV'),
        ('vuela_ai', 'Vuela.ai'),
        ('gemini_image', 'Gemini Image'),
        ('elevenlabs', 'ElevenLabs TTS'),
        ('elevenlabs_music', 'ElevenLabs Music'),
    ]
    
    OPERATION_TYPES = [
        ('video_generation', 'Generación de Video'),
        ('image_generation', 'Generación de Imagen'),
        ('audio_generation', 'Generación de Audio'),
        ('music_generation', 'Generación de Música'),
        ('preview_generation', 'Generación de Preview'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='service_usage'
    )
    service_name = models.CharField(
        max_length=50,
        choices=SERVICE_CHOICES
    )
    operation_type = models.CharField(
        max_length=50,
        choices=OPERATION_TYPES
    )
    
    # Consumo
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text='Tokens consumidos (si aplica)'
    )
    credits_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Créditos gastados'
    )
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Costo real en USD'
    )
    
    # Recurso generado
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    resource = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text='Info adicional (duración, resolución, caracteres, etc.)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'service_name']),
            models.Index(fields=['service_name', '-created_at']),
            models.Index(fields=['created_at']),  # Para reportes por fecha
        ]
        verbose_name = 'Uso de Servicio'
        verbose_name_plural = 'Usos de Servicios'
    
    def __str__(self):
        return f"{self.user.username}: {self.service_name} - {self.credits_spent} créditos"
```

---

## Fase 2: CreditService

### 2.1 Estructura del Servicio

```python
# core/services/credits.py
from decimal import Decimal
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from core.models import UserCredits, CreditTransaction, ServiceUsage

class InsufficientCreditsException(Exception):
    """Excepción cuando no hay suficientes créditos"""
    pass

class RateLimitExceededException(Exception):
    """Excepción cuando se excede el límite mensual"""
    pass

class CreditService:
    """Servicio para manejar créditos de usuarios"""
    
    # Precios por servicio (en créditos)
    PRICING = {
        'gemini_veo': {
            'video': 50,  # por segundo
            'video_audio': 75,  # por segundo (con audio)
        },
        'sora': {
            'sora-2': 10,  # por segundo
            'sora-2-pro': 50,  # por segundo
        },
        'heygen': {
            'avatar_v2': 5,  # por segundo
            'avatar_iv': 15,  # por segundo
        },
        'vuela_ai': {
            'basic': 3,  # por segundo
            'premium': 5,  # por segundo
        },
        'gemini_image': {
            'image': 2,  # por imagen
        },
        'elevenlabs': {
            'per_character': Decimal('0.017'),  # por carácter
        },
    }
    
    @staticmethod
    def get_or_create_user_credits(user):
        """Obtiene o crea el registro de créditos del usuario"""
        credits, created = UserCredits.objects.get_or_create(
            user=user,
            defaults={
                'credits': 0,
                'monthly_limit': 1000,
            }
        )
        
        # Resetear uso mensual si es un nuevo mes
        CreditService._check_monthly_reset(credits)
        
        return credits
    
    @staticmethod
    def _check_monthly_reset(credits):
        """Verifica y resetea el uso mensual si es necesario"""
        today = timezone.now().date()
        
        if credits.last_reset_date is None:
            # Primera vez, establecer fecha actual
            credits.last_reset_date = today
            credits.save(update_fields=['last_reset_date'])
        elif credits.last_reset_date.month != today.month or credits.last_reset_date.year != today.year:
            # Nuevo mes, resetear
            credits.reset_monthly_usage()
    
    @staticmethod
    def has_enough_credits(user, amount):
        """Verifica si el usuario tiene suficientes créditos"""
        credits = CreditService.get_or_create_user_credits(user)
        return credits.credits >= Decimal(str(amount))
    
    @staticmethod
    def check_rate_limit(user, amount):
        """Verifica si el usuario puede gastar sin exceder límite mensual"""
        credits = CreditService.get_or_create_user_credits(user)
        
        if credits.current_month_usage + Decimal(str(amount)) > credits.monthly_limit:
            raise RateLimitExceededException(
                f"Límite mensual excedido. Usado: {credits.current_month_usage}/{credits.monthly_limit}"
            )
    
    @staticmethod
    def deduct_credits(user, amount, service_name, operation_type, resource=None, metadata=None):
        """Deduce créditos del usuario"""
        credits = CreditService.get_or_create_user_credits(user)
        amount_decimal = Decimal(str(amount))
        
        # Verificar créditos disponibles
        if credits.credits < amount_decimal:
            raise InsufficientCreditsException(
                f"Créditos insuficientes. Disponibles: {credits.credits}, Necesarios: {amount_decimal}"
            )
        
        # Verificar límite mensual
        CreditService.check_rate_limit(user, amount_decimal)
        
        # Guardar balances antes
        balance_before = credits.credits
        balance_after = balance_before - amount_decimal
        
        # Actualizar créditos
        credits.credits = balance_after
        credits.total_spent += amount_decimal
        credits.current_month_usage += amount_decimal
        credits.save(update_fields=['credits', 'total_spent', 'current_month_usage', 'updated_at'])
        
        # Crear transacción
        transaction = CreditTransaction.objects.create(
            user=user,
            transaction_type='spend',
            amount=-amount_decimal,  # Negativo para gastos
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"Gasto en {service_name} - {operation_type}",
            service_name=service_name,
            metadata=metadata or {},
            content_type=ContentType.objects.get_for_model(resource) if resource else None,
            object_id=resource.id if resource else None,
        )
        
        # Crear registro de uso
        ServiceUsage.objects.create(
            user=user,
            service_name=service_name,
            operation_type=operation_type,
            credits_spent=amount_decimal,
            metadata=metadata or {},
            content_type=ContentType.objects.get_for_model(resource) if resource else None,
            object_id=resource.id if resource else None,
        )
        
        logger.info(
            f"Créditos deducidos: {user.username} - {amount_decimal} créditos "
            f"({service_name}/{operation_type}). Balance: {balance_after}"
        )
        
        return transaction
    
    # Métodos de cálculo por tipo de servicio
    @staticmethod
    def calculate_video_cost(video):
        """Calcula costo de un video"""
        duration = video.duration or video.metadata.get('duration', 0)
        if duration == 0:
            logger.warning(f"Video {video.id} no tiene duración, usando estimación")
            duration = 8  # Estimación por defecto
        
        if video.type == 'heygen_avatar_v2':
            return duration * CreditService.PRICING['heygen']['avatar_v2']
        elif video.type == 'heygen_avatar_iv':
            return duration * CreditService.PRICING['heygen']['avatar_iv']
        elif video.type == 'gemini_veo':
            has_audio = video.metadata.get('generate_audio', False)
            price_key = 'video_audio' if has_audio else 'video'
            return duration * CreditService.PRICING['gemini_veo'][price_key]
        elif video.type == 'sora':
            model = video.config.get('sora_model', 'sora-2')
            return duration * CreditService.PRICING['sora'][model]
        
        return 0
    
    @staticmethod
    def calculate_image_cost(image):
        """Calcula costo de una imagen"""
        return CreditService.PRICING['gemini_image']['image']
    
    @staticmethod
    def calculate_audio_cost(audio):
        """Calcula costo de un audio"""
        character_count = len(audio.text)
        return character_count * CreditService.PRICING['elevenlabs']['per_character']
    
    @staticmethod
    def calculate_scene_video_cost(scene):
        """Calcula costo de un video de escena"""
        duration = scene.duration_sec or 8
        
        if scene.ai_service == 'heygen_v2':
            return duration * CreditService.PRICING['heygen']['avatar_v2']
        elif scene.ai_service == 'heygen_avatar_iv':
            return duration * CreditService.PRICING['heygen']['avatar_iv']
        elif scene.ai_service == 'gemini_veo':
            has_audio = scene.ai_config.get('generate_audio', False)
            price_key = 'video_audio' if has_audio else 'video'
            return duration * CreditService.PRICING['gemini_veo'][price_key]
        elif scene.ai_service == 'sora':
            model = scene.ai_config.get('sora_model', 'sora-2')
            return duration * CreditService.PRICING['sora'][model]
        elif scene.ai_service == 'vuela_ai':
            quality = scene.ai_config.get('quality_tier', 'premium')
            return duration * CreditService.PRICING['vuela_ai'][quality]
        
        return 0
    
    # Métodos específicos de deducción
    @staticmethod
    def deduct_credits_for_video(user, video):
        """Deduce créditos para un video"""
        if video.metadata.get('credits_charged'):
            logger.warning(f"Video {video.id} ya fue cobrado")
            return
        
        cost = CreditService.calculate_video_cost(video)
        if cost == 0:
            logger.warning(f"No se pudo calcular costo para video {video.id}")
            return
        
        metadata = {
            'duration': video.duration or video.metadata.get('duration'),
            'video_type': video.type,
            'model': video.config.get('sora_model') or video.config.get('veo_model'),
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name=video.type,
            operation_type='video_generation',
            resource=video,
            metadata=metadata
        )
        
        video.metadata['credits_charged'] = True
        video.save(update_fields=['metadata'])
    
    @staticmethod
    def deduct_credits_for_image(user, image):
        """Deduce créditos para una imagen"""
        if image.metadata.get('credits_charged'):
            return
        
        cost = CreditService.calculate_image_cost(image)
        
        metadata = {
            'image_type': image.type,
            'aspect_ratio': image.aspect_ratio,
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name='gemini_image',
            operation_type='image_generation',
            resource=image,
            metadata=metadata
        )
        
        image.metadata['credits_charged'] = True
        image.save(update_fields=['metadata'])
    
    @staticmethod
    def deduct_credits_for_audio(user, audio):
        """Deduce créditos para un audio"""
        if audio.metadata.get('credits_charged'):
            return
        
        cost = CreditService.calculate_audio_cost(audio)
        
        metadata = {
            'character_count': len(audio.text),
            'duration': audio.duration,
            'voice_id': audio.voice_id,
            'model_id': audio.model_id,
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name='elevenlabs',
            operation_type='audio_generation',
            resource=audio,
            metadata=metadata
        )
        
        audio.metadata['credits_charged'] = True
        audio.save(update_fields=['metadata'])
    
    @staticmethod
    def deduct_credits_for_scene_preview(user, scene):
        """Deduce créditos para preview de escena"""
        cost = CreditService.PRICING['gemini_image']['image']
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name='gemini_image',
            operation_type='preview_generation',
            resource=scene,
            metadata={'scene_id': scene.scene_id}
        )
    
    @staticmethod
    def deduct_credits_for_scene_video(user, scene):
        """Deduce créditos para video de escena"""
        if scene.metadata.get('credits_charged'):
            return
        
        cost = CreditService.calculate_scene_video_cost(scene)
        if cost == 0:
            logger.warning(f"No se pudo calcular costo para escena {scene.id}")
            return
        
        metadata = {
            'duration': scene.duration_sec,
            'ai_service': scene.ai_service,
            'ai_config': scene.ai_config,
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name=scene.ai_service,
            operation_type='video_generation',
            resource=scene,
            metadata=metadata
        )
        
        scene.metadata['credits_charged'] = True
        scene.save(update_fields=['metadata'])
    
    @staticmethod
    def estimate_video_cost(video_type, duration, config=None):
        """Estima costo antes de generar (para mostrar al usuario)"""
        if video_type == 'heygen_avatar_v2':
            return duration * CreditService.PRICING['heygen']['avatar_v2']
        elif video_type == 'heygen_avatar_iv':
            return duration * CreditService.PRICING['heygen']['avatar_iv']
        elif video_type == 'gemini_veo':
            has_audio = config and config.get('generate_audio', False)
            price_key = 'video_audio' if has_audio else 'video'
            return duration * CreditService.PRICING['gemini_veo'][price_key]
        elif video_type == 'sora':
            model = (config and config.get('sora_model')) or 'sora-2'
            return duration * CreditService.PRICING['sora'][model]
        
        return 0
```

---

## Fase 3: Integración en Modelos

### 3.1 Modificar Video.mark_as_completed()

```python
# core/models.py - Video
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
            # No fallar la operación si falla el cobro
```

### 3.2 Modificar Image.mark_as_completed()

```python
# core/models.py - Image
def mark_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
    """Marca la imagen como completada y cobra créditos si es necesario"""
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
            CreditService.deduct_credits_for_image(self.created_by, self)
        except Exception as e:
            logger.error(f"Error al cobrar créditos para imagen {self.id}: {e}")
```

### 3.3 Modificar Audio.mark_as_completed()

```python
# core/models.py - Audio
def mark_as_completed(self, gcs_path=None, duration=None, metadata=None, alignment=None, charge_credits=True):
    """Marca el audio como completado y cobra créditos si es necesario"""
    self.status = 'completed'
    self.completed_at = timezone.now()
    if gcs_path:
        self.gcs_path = gcs_path
    if duration:
        self.duration = duration
    if metadata:
        self.metadata = metadata
    if alignment:
        self.alignment = alignment
    self.save(update_fields=[
        'status', 'completed_at', 'gcs_path', 'duration', 
        'metadata', 'alignment', 'updated_at'
    ])
    
    # Cobrar créditos automáticamente
    if charge_credits and self.created_by:
        from core.services.credits import CreditService
        try:
            CreditService.deduct_credits_for_audio(self.created_by, self)
        except Exception as e:
            logger.error(f"Error al cobrar créditos para audio {self.id}: {e}")
```

### 3.4 Modificar Scene.mark_*_as_completed()

```python
# core/models.py - Scene
def mark_preview_as_completed(self, gcs_path, charge_credits=True):
    """Marca el preview como completado y cobra créditos si es necesario"""
    self.preview_image_status = 'completed'
    self.preview_image_gcs_path = gcs_path
    self.save(update_fields=['preview_image_status', 'preview_image_gcs_path', 'updated_at'])
    
    # Cobrar créditos automáticamente
    if charge_credits and self.script.created_by:
        from core.services.credits import CreditService
        try:
            CreditService.deduct_credits_for_scene_preview(self.script.created_by, self)
        except Exception as e:
            logger.error(f"Error al cobrar créditos para preview de escena {self.id}: {e}")

def mark_video_as_completed(self, gcs_path=None, metadata=None, charge_credits=True):
    """Marca el video como completado y cobra créditos si es necesario"""
    self.video_status = 'completed'
    self.completed_at = timezone.now()
    if gcs_path:
        self.video_gcs_path = gcs_path
    if metadata:
        self.metadata = metadata
    self.save(update_fields=['video_status', 'completed_at', 'video_gcs_path', 'metadata', 'updated_at'])
    
    # Cobrar créditos automáticamente
    if charge_credits and self.script.created_by:
        from core.services.credits import CreditService
        try:
            CreditService.deduct_credits_for_scene_video(self.script.created_by, self)
        except Exception as e:
            logger.error(f"Error al cobrar créditos para video de escena {self.id}: {e}")
```

---

## Fase 4: Validación Previa en Servicios

### 4.1 Validar créditos antes de generar

```python
# core/services.py - VideoService.generate_video()
def generate_video(self, video: Video) -> str:
    """Genera un video usando la API correspondiente"""
    # Validar créditos ANTES de generar
    from core.services.credits import CreditService
    
    estimated_cost = CreditService.estimate_video_cost(
        video_type=video.type,
        duration=video.config.get('duration', 8),
        config=video.config
    )
    
    if estimated_cost > 0:
        if not CreditService.has_enough_credits(video.created_by, estimated_cost):
            raise InsufficientCreditsException(
                f"No tienes suficientes créditos. Necesitas aproximadamente {estimated_cost} créditos."
            )
        
        try:
            CreditService.check_rate_limit(video.created_by, estimated_cost)
        except RateLimitExceededException as e:
            raise ValidationException(str(e))
    
    # Continuar con la generación...
    # El cobro real se hará automáticamente en mark_as_completed()
```

---

## Próximos Pasos

1. ✅ **Completado**: Plan de implementación
2. ⏳ **Pendiente**: Crear migraciones para los modelos
3. ⏳ **Pendiente**: Implementar CreditService completo
4. ⏳ **Pendiente**: Modificar métodos mark_as_completed() en modelos
5. ⏳ **Pendiente**: Agregar validación previa en servicios
6. ⏳ **Pendiente**: Crear comandos de gestión (asignar créditos, reset mensual)
7. ⏳ **Pendiente**: UI para mostrar créditos en sidebar
8. ⏳ **Pendiente**: Dashboard de uso

---

## Ventajas del Híbrido para Mantenibilidad y Escalabilidad

### Mantenibilidad ✅

1. **Un solo lugar por modelo**: Cambios en un solo método
2. **Servicio centralizado**: Toda la lógica en CreditService
3. **Código auto-documentado**: Se ve claramente qué hace
4. **Fácil debugging**: Breakpoints claros

### Escalabilidad ✅

1. **Fácil agregar servicios**: Solo agregas método en CreditService
2. **Fácil cambiar precios**: Solo actualizas PRICING dict
3. **Fácil agregar features**: Descuentos, planes, promociones en CreditService
4. **Performance**: Sin overhead de signals, solo cuando se completa

¿Empezamos con la implementación?



