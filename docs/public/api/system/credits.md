# Sistema de Créditos

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

---

## Tabla de Precios

### Precios por Servicio

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
| **Vuela.ai** | Video | Por segundo | ~$0.03 | **3 créditos** |
| **Manim** | Video | Por video | ~$0.01 | **1 crédito** |

### Ejemplos de Cálculo

- **Video Veo de 8 segundos**: 8s × 50 créditos/s = **400 créditos**
- **Video Sora-2 de 8 segundos**: 8s × 10 créditos/s = **80 créditos**
- **Imagen generada**: **2 créditos**
- **HeyGen Avatar IV de 30 segundos**: 30s × 15 créditos/s = **450 créditos**
- **ElevenLabs texto de 500 caracteres**: 500 × 0.017 créditos = **8.5 créditos** (redondeado a 9)

---

## Guía de Usuario

Para información sobre cómo usar los créditos desde la interfaz, consulta la [Guía de Usuario de Créditos](../app/GUIA_USUARIO.md#sistema-de-créditos).

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

### CreditTransaction

Historial completo de transacciones de créditos.

### ServiceUsage

Tracking detallado de uso por servicio.

---

## CreditService

### Ubicación

`core/services/credits.py`

### Métodos Principales

```python
# Obtener o crear créditos del usuario
credits = CreditService.get_or_create_user_credits(user)

# Verificar créditos disponibles
has_credits = CreditService.has_enough_credits(user, amount)

# Deducir créditos
CreditService.deduct_credits(user, amount, service_name, operation_type, resource, metadata)

# Calcular costos
cost = CreditService.calculate_video_cost(video)
cost = CreditService.calculate_image_cost(image)
cost = CreditService.calculate_audio_cost(audio)
```

---

## Integración

### Puntos de Cobro

El sistema cobra automáticamente cuando se completa contenido en:

- `Video.mark_as_completed()`
- `Image.mark_as_completed()`
- `Audio.mark_as_completed()`
- `Scene.mark_*_as_completed()`

### Validación Previa

Los servicios validan créditos **ANTES** de generar contenido.

---

## Comandos de Gestión

```bash
# Asignar créditos
python manage.py add_credits <username> <amount>

# Ver créditos de usuario
python manage.py show_user_credits <username> --detailed

# Resetear uso mensual
python manage.py reset_monthly_credits

# Listar usuarios con créditos
python manage.py list_users_credits --active-only

# Estadísticas del sistema
python manage.py stats_credits --period month
```

---

## Excepciones

### InsufficientCreditsException

Se lanza cuando el usuario no tiene suficientes créditos.

### RateLimitExceededException

Se lanza cuando el usuario excede su límite mensual.

---

Para más detalles técnicos, consulta el código fuente en `core/services/credits.py`.

