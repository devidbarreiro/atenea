# Tarea: Sistema de Rate Limiting de Tokens

## Asignado a: [Nombre del desarrollador - Rate Limiting]

## Objetivo
Implementar un sistema de rate limiting para controlar el uso de tokens/llamadas a APIs de LLM y generación de contenido (videos, imágenes) por usuario y por clave API.

---

## Contexto Actual

El sistema actual usa múltiples proveedores:
- **OpenAI** (GPT-4o, Sora) - Generación de texto y videos
- **Gemini** (Gemini Pro, Veo) - Generación de texto y videos
- **HeyGen** - Generación de videos con avatar

**Operaciones que consumen tokens/llamadas:**
- Generación de guiones con el agente (`ScriptAgent`)
- Generación de videos (HeyGen, Sora, Gemini Veo)
- Generación de imágenes (Gemini Image)
- Cualquier llamada a LLM

**Archivos relevantes:**
- `core/llm/factory.py` - Factory de LLMs
- `core/services.py` - Servicios de generación (VideoService, ImageService)
- `core/agents/script_agent.py` - Agente que usa LLMs
- `core/models.py` - Modelos Django (User, Project, etc.)

---

## Requisitos

### 1. Límites por Usuario
- Cada usuario tiene un límite mensual de tokens/llamadas
- Diferentes límites según tipo de usuario (free, pro, enterprise)
- Tracking del consumo actual del mes

### 2. Límites por Clave API
- Las claves API compartidas también tienen límites
- Útil para controlar costos en desarrollo/staging

### 3. Límites Mensuales
- Se resetean el primer día de cada mes
- Ventana deslizante de 30 días (opcional, más complejo)

### 4. Todos los Proveedores
- OpenAI (GPT-4o, Sora)
- Gemini (Gemini Pro, Veo)
- HeyGen

---

## Opciones de Implementación

### Opción A: Middleware Django (Recomendado para inicio)
**Ventajas:**
- Fácil de implementar
- Intercepta todas las requests automáticamente
- Bueno para rate limiting a nivel de request

**Desventajas:**
- Menos granular (solo a nivel de request HTTP)
- No funciona bien para operaciones asíncronas (Celery)

**Cuándo usar:** Si el rate limiting es principalmente por requests HTTP del usuario.

### Opción B: Decoradores Python
**Ventajas:**
- Muy granular (puedes decorar funciones específicas)
- Flexible y reutilizable
- Funciona con funciones asíncronas

**Desventajas:**
- Requiere decorar cada función manualmente
- Puede ser fácil olvidarse de decorar alguna función

**Cuándo usar:** Si quieres control fino sobre qué operaciones limitar.

**Ejemplo:**
```python
@rate_limit(user_limit=10000, api_key_limit=50000)
def generate_video(self, video: Video):
    # ...
```

### Opción C: Servicio Separado (Recomendado para producción)
**Ventajas:**
- Más escalable
- Puede ser un microservicio independiente
- Fácil de testear
- Funciona con cualquier tipo de operación (HTTP, Celery, etc.)

**Desventajas:**
- Más complejo de implementar inicialmente
- Requiere infraestructura adicional (Redis, DB)

**Cuándo usar:** Si necesitas escalabilidad y el sistema crecerá.

**Ejemplo:**
```python
from core.services.rate_limiting import RateLimitingService

rate_limiter = RateLimitingService()
if not rate_limiter.check_limit(user_id, operation_type="video_generation"):
    raise RateLimitExceeded("Límite mensual alcanzado")
```

---

## Recomendación: Enfoque Híbrido

**Fase 1 (MVP):** Decoradores + Servicio simple
- Crear servicio `RateLimitingService` con decoradores
- Usar Redis para contadores (rápido y eficiente)
- Decorar funciones clave en `VideoService`, `ImageService`, `ScriptAgent`

**Fase 2 (Escalado):** Servicio separado + Middleware
- Servicio más robusto con su propia API
- Middleware para requests HTTP
- Integración con Celery para tareas asíncronas

---

## Estructura de Datos

### Modelo para Tracking de Uso
```python
# core/models.py
class TokenUsage(models.Model):
    """Tracking de uso de tokens/llamadas"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    api_key = models.CharField(max_length=255, null=True, blank=True)  # Para límites por clave
    
    # Tipo de operación
    operation_type = models.CharField(
        max_length=50,
        choices=[
            ('script_generation', 'Generación de Guión'),
            ('video_generation', 'Generación de Video'),
            ('image_generation', 'Generación de Imagen'),
            ('llm_call', 'Llamada LLM'),
        ]
    )
    
    # Proveedor
    provider = models.CharField(
        max_length=50,
        choices=[
            ('openai', 'OpenAI'),
            ('gemini', 'Gemini'),
            ('heygen', 'HeyGen'),
        ]
    )
    
    # Consumo
    tokens_used = models.IntegerField(default=0)  # Tokens consumidos
    calls_made = models.IntegerField(default=1)   # Número de llamadas
    
    # Metadata
    resource_id = models.CharField(max_length=255, null=True, blank=True)  # ID del video/imagen generado
    metadata = models.JSONField(default=dict)  # Info adicional
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    month = models.IntegerField()  # Mes del consumo (1-12)
    year = models.IntegerField()   # Año del consumo
```

### Modelo para Límites
```python
class RateLimit(models.Model):
    """Límites configurados por usuario o clave API"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    api_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    
    # Límites mensuales
    monthly_token_limit = models.IntegerField(default=0)  # 0 = ilimitado
    monthly_call_limit = models.IntegerField(default=0)
    
    # Límites por operación (opcional)
    video_generation_limit = models.IntegerField(default=0)
    image_generation_limit = models.IntegerField(default=0)
    script_generation_limit = models.IntegerField(default=0)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## Servicio de Rate Limiting

### Estructura Base
```python
# core/services/rate_limiting.py
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

class RateLimitingService:
    """
    Servicio para gestionar rate limiting de tokens y llamadas.
    Usa Redis para contadores rápidos y DB para persistencia.
    """
    
    def __init__(self):
        self.cache_prefix = "rate_limit"
        self.cache_ttl = 86400 * 32  # 32 días (más que un mes)
    
    def check_limit(
        self,
        user_id: Optional[int] = None,
        api_key: Optional[str] = None,
        operation_type: str = "llm_call",
        provider: str = "openai",
        tokens_to_use: int = 0,
        calls_to_make: int = 1
    ) -> Tuple[bool, Dict]:
        """
        Verifica si el usuario/clave puede realizar la operación.
        
        Returns:
            (allowed: bool, info: dict)
            info contiene: remaining, limit, reset_date
        """
        # 1. Obtener límites configurados
        # 2. Obtener consumo actual del mes
        # 3. Verificar si hay espacio
        # 4. Retornar resultado
        pass
    
    def record_usage(
        self,
        user_id: Optional[int] = None,
        api_key: Optional[str] = None,
        operation_type: str = "llm_call",
        provider: str = "openai",
        tokens_used: int = 0,
        calls_made: int = 1,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Registra el uso de tokens/llamadas"""
        pass
    
    def get_current_usage(
        self,
        user_id: Optional[int] = None,
        api_key: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> Dict:
        """Obtiene el consumo actual del mes"""
        pass
    
    def reset_monthly_limits(self):
        """Resetea los límites mensuales (ejecutar el día 1 de cada mes)"""
        pass
```

---

## Integración con el Código Actual

### 1. En LLMFactory
```python
# core/llm/factory.py
from core.services.rate_limiting import RateLimitingService

class LLMFactory:
    rate_limiter = RateLimitingService()
    
    @staticmethod
    def create_openai_llm(...):
        # Verificar límites antes de crear
        user_id = get_current_user_id()  # Necesitas implementar esto
        allowed, info = LLMFactory.rate_limiter.check_limit(
            user_id=user_id,
            operation_type="llm_call",
            provider="openai",
            tokens_to_use=estimated_tokens
        )
        if not allowed:
            raise RateLimitExceeded(f"Límite alcanzado. Disponible: {info['remaining']}")
        
        # Crear LLM y usar...
        llm = ChatOpenAI(...)
        return llm
```

### 2. En VideoService
```python
# core/services.py
from core.services.rate_limiting import RateLimitingService

class VideoService:
    def __init__(self):
        self.rate_limiter = RateLimitingService()
    
    def generate_video(self, video: Video) -> str:
        # Verificar límites
        user_id = video.project.user.id
        provider = self._get_provider_for_video_type(video.type)
        
        allowed, info = self.rate_limiter.check_limit(
            user_id=user_id,
            operation_type="video_generation",
            provider=provider
        )
        if not allowed:
            raise RateLimitExceeded("Límite mensual de generación de videos alcanzado")
        
        # Generar video...
        result = self._generate_video_internal(video)
        
        # Registrar uso
        self.rate_limiter.record_usage(
            user_id=user_id,
            operation_type="video_generation",
            provider=provider,
            resource_id=str(video.id)
        )
        
        return result
```

### 3. Decorador para simplificar
```python
# core/decorators/rate_limiting.py
from functools import wraps
from core.services.rate_limiting import RateLimitingService

def rate_limit(
    operation_type: str,
    provider: str = "openai",
    get_user_id=None,  # Función para obtener user_id
    get_api_key=None   # Función para obtener api_key
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rate_limiter = RateLimitingService()
            
            # Obtener user_id o api_key
            user_id = get_user_id(*args, **kwargs) if get_user_id else None
            api_key = get_api_key(*args, **kwargs) if get_api_key else None
            
            # Verificar límites
            allowed, info = rate_limiter.check_limit(
                user_id=user_id,
                api_key=api_key,
                operation_type=operation_type,
                provider=provider
            )
            if not allowed:
                raise RateLimitExceeded(f"Límite alcanzado: {info}")
            
            # Ejecutar función
            result = func(*args, **kwargs)
            
            # Registrar uso (necesitas estimar tokens/calls)
            # rate_limiter.record_usage(...)
            
            return result
        return wrapper
    return decorator

# Uso:
@rate_limit(operation_type="video_generation", provider="heygen", get_user_id=lambda self, video: video.project.user.id)
def generate_video(self, video: Video):
    # ...
```

---

## Almacenamiento: Redis vs Database

### Redis (Recomendado para contadores)
**Ventajas:**
- Muy rápido para incrementar contadores
- Atomic operations (INCR)
- TTL automático
- Escalable

**Uso:**
```python
# Contador mensual por usuario
cache_key = f"rate_limit:{user_id}:{year}:{month}:tokens"
current = cache.get(cache_key, 0)
cache.set(cache_key, current + tokens_used, timeout=32*86400)
```

### Database (Para persistencia y reportes)
**Ventajas:**
- Persistencia permanente
- Fácil de hacer queries y reportes
- Historial completo

**Uso:**
```python
# Guardar registro detallado
TokenUsage.objects.create(
    user_id=user_id,
    operation_type="video_generation",
    provider="heygen",
    tokens_used=tokens_used,
    month=current_month,
    year=current_year
)
```

**Recomendación:** Usar ambos - Redis para checks rápidos, DB para persistencia.

---

## Tareas Específicas

### Fase 1: Investigación y Diseño (Semana 1)
1. Investigar opciones de implementación (Middleware vs Decoradores vs Servicio)
2. Decidir arquitectura final
3. Diseñar esquema de base de datos
4. Investigar cómo obtener user_id en diferentes contextos (HTTP, Celery, etc.)

### Fase 2: Implementación Base (Semanas 2-3)
1. Crear modelos `TokenUsage` y `RateLimit`
2. Crear migraciones Django
3. Implementar `RateLimitingService` básico
4. Implementar decorador `@rate_limit`
5. Integrar con `LLMFactory`

### Fase 3: Integración Completa (Semana 4)
1. Integrar con `VideoService`
2. Integrar con `ImageService`
3. Integrar con `ScriptAgent`
4. Crear comandos de administración (reset mensual, reportes)

### Fase 4: Testing y Optimización (Semana 5)
1. Tests unitarios
2. Tests de integración
3. Optimizar queries Redis/DB
4. Documentar uso

---

## Preguntas para Investigar

1. **¿Cómo obtener user_id en diferentes contextos?**
   - HTTP request → `request.user.id`
   - Celery task → Pasar como parámetro
   - Script directo → ¿Cómo manejar?

2. **¿Cómo estimar tokens antes de hacer la llamada?**
   - Usar aproximación (1 token ≈ 4 caracteres)
   - O hacer la llamada y luego registrar?

3. **¿Qué hacer cuando se alcanza el límite?**
   - Lanzar excepción `RateLimitExceeded`
   - Retornar error HTTP 429
   - Enviar notificación al usuario

4. **¿Cómo manejar límites compartidos?**
   - Si varios usuarios usan la misma API key
   - ¿Límite compartido o individual?

5. **¿Necesitamos límites por operación específica?**
   - Ej: 100 videos/mes pero 1000 imágenes/mes
   - O solo límite total de tokens?

---

## Recursos y Referencias

- **Django Rate Limiting:** https://django-ratelimit.readthedocs.io/
- **Redis Rate Limiting:** https://redis.io/docs/manual/patterns/rate-limiting/
- **Celery Rate Limiting:** https://docs.celeryq.dev/en/stable/userguide/tasks.html#rate-limits
- **Token Counting:** https://platform.openai.com/tokenizer

---

## Criterios de Éxito

- ✅ Sistema previene exceder límites mensuales
- ✅ Tracking preciso de tokens/llamadas por usuario
- ✅ Funciona con todos los proveedores (OpenAI, Gemini, HeyGen)
- ✅ Performance: checks en <10ms (usando Redis)
- ✅ Persistencia en DB para reportes históricos
- ✅ Fácil de integrar en código existente (decoradores)
- ✅ Comandos de administración para reset mensual

---

## Contacto y Soporte

Si tienes dudas sobre:
- La estructura del código actual → Revisa `core/services.py`, `core/llm/factory.py`
- Los modelos de datos → Revisa `core/models.py`
- Cómo obtener user_id → Revisa `core/views.py` (ejemplos en las views)

