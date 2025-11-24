# Sistema de Créditos y Rate Limiting

## Tabla de Contenidos
1. [Visión General](#visión-general)
2. [Tabla de Precios](#tabla-de-precios)
3. [Arquitectura Técnica](#arquitectura-técnica)
4. [Modelos de Base de Datos](#modelos-de-base-de-datos)
5. [CreditService](#creditservice)
6. [Integración](#integración)
7. [Comandos de Gestión](#comandos-de-gestión)
8. [API y Endpoints](#api-y-endpoints)

---

## Visión General

El sistema de créditos de Atenea permite controlar y rastrear el uso de servicios de generación de contenido audiovisual por parte de los usuarios.

### Características Principales

- ✅ **Cobro automático** cuando se completa contenido
- ✅ **Validación previa** antes de generar (mejor UX)
- ✅ **Límites mensuales** que se resetean automáticamente
- ✅ **Historial completo** de transacciones y uso por servicio
- ✅ **Tracking detallado** por servicio durante 1 año
- ✅ **Sistema flexible** para agregar nuevos servicios fácilmente

### Equivalencia Base

**100 créditos Atenea = 1 USD**

### Servicios que NO se cobran

❌ **NO cobramos llamadas a LLM** (OpenAI GPT, Google Gemini para texto)
✅ **Solo cobramos** cuando se hace generación propia de contenido audiovisual con servicios de IA

---

## Tabla de Precios

### Precios por Servicio (Actualizados)

| Servicio | Tipo | Unidad | Precio USD | Créditos Atenea |
|----------|------|--------|------------|----------------|
| **Gemini Veo 2/3** | Video | Por segundo | $0.50 | **50 créditos** |
| **Gemini Veo 3 + Audio** | Video+Audio | Por segundo | $0.75 | **75 créditos** |
| **OpenAI Sora-2** | Video | Por segundo | $0.10 | **10 créditos** |
| **OpenAI Sora-2 Pro** | Video | Por segundo | $0.50 | **50 créditos** |
| **Gemini Image** | Imagen | Por imagen | $0.02 | **2 créditos** |
| **HeyGen Avatar V2** | Video | Por segundo | $0.05 | **5 créditos** |
| **HeyGen Avatar IV** | Video | Por segundo | $0.15 | **15 créditos** |
| **ElevenLabs TTS** | Audio | Por carácter | $0.00017 | **0.017 créditos** |
| **Vuela.ai** | Video | Por segundo | ~$0.03 (orientativo) | **3 créditos** |

### Ejemplos de Cálculo

- **Video Veo de 8 segundos**: 8s × 50 créditos/s = **400 créditos**
- **Video Sora-2 de 8 segundos**: 8s × 10 créditos/s = **80 créditos**
- **Imagen generada**: **2 créditos**
- **HeyGen Avatar IV de 30 segundos**: 30s × 15 créditos/s = **450 créditos**
- **ElevenLabs texto de 500 caracteres**: 500 × 0.017 créditos = **8.5 créditos** (redondeado a 9)

### Casos Especiales: Video con Agente

Cuando se genera un video completo con el agente, se cobran **todos los servicios utilizados**:

1. **Script generation** (LLM): ❌ NO se cobra
2. **Imágenes preview** (Gemini Image): ✅ Se cobra cada imagen (2 créditos)
3. **Videos de escenas** (Veo/Sora/HeyGen): ✅ Se cobra cada video por segundo
4. **Audios** (ElevenLabs): ✅ Se cobra por caracteres
5. **Combinación final**: ❌ NO se cobra (proceso interno)

**Ejemplo**: Video de 5 escenas de 8 segundos cada una:
- 5 imágenes preview: 5 × 2 créditos = **10 créditos**
- 5 videos Veo de 8s: 5 × 8s × 50 créditos/s = **2,000 créditos**
- 5 audios de ~200 caracteres: 5 × 200 × 0.017 = **17 créditos**
- **Total: ~2,027 créditos**

---

## Arquitectura Técnica

### Estrategia de Implementación: Híbrida

El sistema usa una **estrategia híbrida** que combina lo mejor de ambas aproximaciones:

- **Automático**: Los métodos `mark_as_completed()` de los modelos cobran automáticamente
- **Explícito**: Se ve claramente en el código que se está cobrando
- **Validación previa**: Se validan créditos ANTES de generar contenido

### Flujo de Cobro

```
Usuario solicita generar contenido
    ↓
Servicio valida créditos ANTES de generar
    ↓
Si hay créditos suficientes → Genera contenido
    ↓
Cuando se completa → mark_as_completed() cobra automáticamente
    ↓
Se registra transacción y uso del servicio
```

---

## Modelos de Base de Datos

### UserCredits

Almacena el saldo y límites mensuales por usuario.

```python
class UserCredits(models.Model):
    user = OneToOneField(User)
    credits = DecimalField(max_digits=10, decimal_places=2)  # Saldo actual
    total_purchased = DecimalField(...)  # Total comprado históricamente
    total_spent = DecimalField(...)  # Total gastado históricamente
    monthly_limit = IntegerField(default=1000)  # Límite mensual
    current_month_usage = DecimalField(...)  # Usado este mes
    last_reset_date = DateField(...)  # Última fecha de reset
```

**Propiedades**:
- `credits_remaining`: Créditos restantes del mes
- `usage_percentage`: Porcentaje de uso mensual

### CreditTransaction

Historial completo de transacciones de créditos.

```python
class CreditTransaction(models.Model):
    user = ForeignKey(User)
    transaction_type = CharField(choices=[
        ('purchase', 'Compra'),
        ('spend', 'Gasto'),
        ('refund', 'Reembolso'),
        ('adjustment', 'Ajuste'),
        ('monthly_reset', 'Reset Mensual'),
    ])
    amount = DecimalField(...)  # Positivo para compras, negativo para gastos
    balance_before = DecimalField(...)
    balance_after = DecimalField(...)
    description = TextField(...)
    service_name = CharField(...)  # Nombre del servicio usado
    metadata = JSONField(...)  # Info adicional (duración, tokens, etc.)
    related_object = GenericForeignKey(...)  # Recurso relacionado
```

### ServiceUsage

Tracking detallado de uso por servicio.

```python
class ServiceUsage(models.Model):
    user = ForeignKey(User)
    service_name = CharField(choices=[
        ('gemini_veo', 'Gemini Veo'),
        ('sora', 'OpenAI Sora'),
        ('heygen_avatar_v2', 'HeyGen Avatar V2'),
        ('heygen_avatar_iv', 'HeyGen Avatar IV'),
        ('vuela_ai', 'Vuela.ai'),
        ('gemini_image', 'Gemini Image'),
        ('elevenlabs', 'ElevenLabs TTS'),
    ])
    operation_type = CharField(choices=[
        ('video_generation', 'Generación de Video'),
        ('image_generation', 'Generación de Imagen'),
        ('audio_generation', 'Generación de Audio'),
        ('preview_generation', 'Generación de Preview'),
    ])
    credits_spent = DecimalField(...)
    tokens_used = IntegerField(...)  # Si aplica
    cost_usd = DecimalField(...)  # Costo real en USD
    metadata = JSONField(...)  # Duración, resolución, caracteres, etc.
    resource = GenericForeignKey(...)  # Recurso generado
```

---

## CreditService

### Ubicación

`core/services/credits.py`

### Métodos Principales

#### Gestión de Créditos

```python
# Obtener o crear créditos del usuario
credits = CreditService.get_or_create_user_credits(user)

# Verificar créditos disponibles
has_credits = CreditService.has_enough_credits(user, amount)

# Verificar límite mensual
CreditService.check_rate_limit(user, amount)

# Agregar créditos (para asignación manual)
CreditService.add_credits(user, amount, description='', transaction_type='purchase')

# Deducir créditos
CreditService.deduct_credits(user, amount, service_name, operation_type, resource, metadata)
```

#### Cálculo de Costos

```python
# Calcular costo de video
cost = CreditService.calculate_video_cost(video)

# Calcular costo de imagen
cost = CreditService.calculate_image_cost(image)

# Calcular costo de audio
cost = CreditService.calculate_audio_cost(audio)

# Calcular costo de video de escena
cost = CreditService.calculate_scene_video_cost(scene)

# Estimar costo antes de generar (para mostrar al usuario)
estimated_cost = CreditService.estimate_video_cost(video_type, duration, config)
estimated_cost = CreditService.estimate_image_cost()
estimated_cost = CreditService.estimate_audio_cost(text)
```

#### Deducción Automática

```python
# Deducir créditos para video
CreditService.deduct_credits_for_video(user, video)

# Deducir créditos para imagen
CreditService.deduct_credits_for_image(user, image)

# Deducir créditos para audio
CreditService.deduct_credits_for_audio(user, audio)

# Deducir créditos para preview de escena
CreditService.deduct_credits_for_scene_preview(user, scene)

# Deducir créditos para video de escena
CreditService.deduct_credits_for_scene_video(user, scene)
```

### Tabla de Precios (PRICING)

```python
PRICING = {
    'gemini_veo': {
        'video': 50,  # por segundo
        'video_audio': 75,  # por segundo (con audio)
    },
    'sora': {
        'sora-2': 10,  # por segundo
        'sora-2-pro': 50,  # por segundo
    },
    'heygen_avatar_v2': {
        'video': 5,  # por segundo
    },
    'heygen_avatar_iv': {
        'video': 15,  # por segundo
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
```

---

## Integración

### Puntos de Cobro

El sistema cobra automáticamente cuando se completa contenido en los siguientes puntos:

#### 1. Videos (`Video.mark_as_completed()`)
- HeyGen Avatar V2
- HeyGen Avatar IV
- Gemini Veo
- OpenAI Sora

#### 2. Imágenes (`Image.mark_as_completed()`)
- Gemini Image Generation

#### 3. Audios (`Audio.mark_as_completed()`)
- ElevenLabs TTS

#### 4. Escenas (`Scene.mark_*_as_completed()`)
- Preview de escena (Gemini Image)
- Video de escena (HeyGen, Veo, Sora, Vuela.ai)
- Audio de escena (ElevenLabs)

### Validación Previa

Los servicios validan créditos **ANTES** de generar contenido:

```python
# En VideoService.generate_video()
if not CreditService.has_enough_credits(user, estimated_cost):
    raise InsufficientCreditsException(...)

CreditService.check_rate_limit(user, estimated_cost)
```

### Manejo de Errores en Views

Las views capturan excepciones de créditos y muestran mensajes amigables:

```python
try:
    video_service.generate_video(video)
except InsufficientCreditsException as e:
    messages.error(request, str(e))
except RateLimitExceededException as e:
    messages.error(request, str(e))
```

---

## Comandos de Gestión

### 1. `add_credits`

Asigna créditos a un usuario.

```bash
python manage.py add_credits <username> <amount> [--description "Descripción"]
```

**Ejemplos**:
```bash
# Asignar 1000 créditos al usuario admin
python manage.py add_credits admin 1000 --description "Créditos iniciales"

# Asignar créditos con descripción personalizada
python manage.py add_credits username 500 --description "Créditos de promoción"
```

### 2. `show_user_credits`

Muestra información de créditos de un usuario.

```bash
python manage.py show_user_credits <username> [--detailed]
```

**Ejemplos**:
```bash
# Ver créditos básicos
python manage.py show_user_credits admin

# Ver créditos con uso detallado por servicio
python manage.py show_user_credits admin --detailed
```

### 3. `reset_monthly_credits`

Resetea el uso mensual de créditos de todos los usuarios.

```bash
python manage.py reset_monthly_credits [--dry-run]
```

**Ejemplos**:
```bash
# Resetear uso mensual
python manage.py reset_monthly_credits

# Ver qué usuarios serían reseteados sin hacer cambios
python manage.py reset_monthly_credits --dry-run
```

### 4. `list_users_credits`

Lista todos los usuarios con sus créditos.

```bash
python manage.py list_users_credits [--min-credits MIN] [--sort-by SORT] [--active-only]
```

**Opciones**:
- `--min-credits`: Mostrar solo usuarios con al menos esta cantidad de créditos
- `--sort-by`: Campo por el que ordenar (`username`, `credits`, `usage`, `percentage`)
- `--active-only`: Mostrar solo usuarios activos (con créditos > 0 o uso > 0)

**Ejemplos**:
```bash
# Listar todos los usuarios
python manage.py list_users_credits

# Listar solo usuarios con más de 100 créditos, ordenados por créditos
python manage.py list_users_credits --min-credits 100 --sort-by credits

# Listar solo usuarios activos, ordenados por porcentaje de uso
python manage.py list_users_credits --active-only --sort-by percentage
```

### 5. `stats_credits`

Muestra estadísticas generales del sistema de créditos.

```bash
python manage.py stats_credits [--period PERIOD]
```

**Opciones**:
- `--period`: Período de tiempo (`today`, `week`, `month`, `all`)

**Ejemplos**:
```bash
# Estadísticas de todo el tiempo
python manage.py stats_credits

# Estadísticas de hoy
python manage.py stats_credits --period today

# Estadísticas de la última semana
python manage.py stats_credits --period week

# Estadísticas del último mes
python manage.py stats_credits --period month
```

**Información mostrada**:
- Estadísticas de usuarios (total, con créditos, activos)
- Estadísticas de créditos (totales, promedios, comprados, gastados)
- Transacciones (totales, por tipo)
- Uso por servicio
- Top 10 usuarios por uso
- Resumen financiero (en USD)
- Tendencias (comparación con período anterior)

---

## API y Endpoints

### Dashboard de Créditos

**URL**: `/credits/`

**Vista**: `CreditsDashboardView`

**Template**: `templates/credits/dashboard.html`

**Funcionalidad**:
- Muestra saldo actual
- Uso del mes con barra de progreso
- Total gastado históricamente
- Uso por servicio (últimos 30 días)
- Transacciones recientes

### Sidebar de Créditos

**Ubicación**: `templates/includes/sidebar.html`

**Funcionalidad**:
- Muestra créditos restantes
- Barra de progreso del uso mensual
- Link clickeable al dashboard

---

## Excepciones

### InsufficientCreditsException

Se lanza cuando el usuario no tiene suficientes créditos para realizar una operación.

```python
raise InsufficientCreditsException(
    f"Créditos insuficientes. Disponibles: {credits.credits}, Necesarios: {amount}"
)
```

### RateLimitExceededException

Se lanza cuando el usuario excede su límite mensual.

```python
raise RateLimitExceededException(
    f"Límite mensual excedido. Usado: {credits.current_month_usage}/{credits.monthly_limit}"
)
```

---

## Reset Automático Mensual

El sistema resetea automáticamente el uso mensual cuando cambia el mes:

- Se verifica en `CreditService.get_or_create_user_credits()`
- Si `last_reset_date` es de un mes diferente, se resetea `current_month_usage`
- Se actualiza `last_reset_date` a la fecha actual

---

## Notas de Implementación

### Estrategia Híbrida

- ✅ **Automático**: No puedes olvidar cobrar (está en `mark_as_completed()`)
- ✅ **Explícito**: Se ve claramente en el código
- ✅ **Validación previa**: Mejor UX (el usuario sabe antes si tiene créditos)
- ✅ **Fácil debugging**: Breakpoints claros
- ✅ **Flexible**: Puedes agregar `charge_credits=False` para casos especiales

### Mantenibilidad

- **Un solo lugar por modelo**: Cambios en `mark_as_completed()` de cada modelo
- **Servicio centralizado**: Toda la lógica en `CreditService`
- **Fácil agregar servicios**: Solo agregas precio en `PRICING` dict
- **Fácil cambiar precios**: Solo actualizas `PRICING` dict

### Escalabilidad

- **Fácil agregar nuevos servicios**: Agregas método en `CreditService`
- **Fácil cambiar precios**: Solo actualizas `PRICING` dict
- **Fácil agregar funcionalidades**: Descuentos, planes, promociones en `CreditService`
- **Performance**: Sin overhead de signals, solo cuando se completa contenido

---

## Archivos del Sistema

### Nuevos Archivos
- `core/services/credits.py` - Servicio de créditos
- `core/management/commands/add_credits.py` - Comando para asignar créditos
- `core/management/commands/reset_monthly_credits.py` - Comando para reset mensual
- `core/management/commands/show_user_credits.py` - Comando para mostrar créditos
- `templates/credits/dashboard.html` - Dashboard de créditos

### Archivos Modificados
- `core/models.py` - Agregados modelos de créditos y modificados métodos `mark_as_completed()`
- `core/services.py` - Agregada validación previa en servicios de generación
- `core/views.py` - Agregado manejo de excepciones de créditos
- `core/urls.py` - Agregada URL del dashboard
- `templates/includes/sidebar.html` - Agregada barra de créditos

---

## Migraciones

**Migración**: `0018_usercredits_credittransaction_serviceusage.py`

**Aplicar**:
```bash
python manage.py migrate
```

---

## Testing

### Ejemplo de Uso Completo

```python
from core.services.credits import CreditService
from core.models import Video

# Asignar créditos
CreditService.add_credits(user, 1000, description="Créditos iniciales")

# Generar contenido (el sistema valida y cobra automáticamente)
video = Video.objects.create(...)
video_service.generate_video(video)  # Valida créditos antes
# Cuando se completa → mark_as_completed() cobra automáticamente

# Ver créditos restantes
credits = CreditService.get_or_create_user_credits(user)
print(f"Créditos restantes: {credits.credits}")
```

---

## Próximas Mejoras (Opcionales)

- Gráficos de uso por servicio en dashboard
- Filtros por fecha en transacciones
- Estadísticas mensuales más detalladas
- Tests unitarios e integración
- Sistema de alertas para créditos bajos
- Descuentos por volumen
- Planes premium

