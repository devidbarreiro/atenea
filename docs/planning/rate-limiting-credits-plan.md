# Plan de Implementación: Rate Limiting y Sistema de Créditos

## Objetivos

1. **Rate Limiting**: Limitar el uso de servicios por usuario
2. **Tracking de Tokens**: Llevar cuenta de tokens gastados por usuario
3. **Tracking por Servicio**: Saber cuánto ha gastado cada usuario en cada servicio
4. **Sistema de Créditos Propios**: 
   - 100 créditos Atenea = 1 euro
   - Tracking de créditos propios que se van gastando según uso de usuarios
5. **Conversión Tokens → Créditos**: Definir equivalencias por servicio

---

## Estado Actual de los Servicios

### ✅ Servicios que YA devuelven información de tokens/precio:

#### 1. **LLM (OpenAI/Gemini)**
- ✅ **Tokens**: Ya se trackean en `core/monitoring/metrics.py`
- ✅ **Costo**: Ya se calcula en `core/llm/factory.py` con `get_cost_estimate()`
- ✅ **Información disponible**: `input_tokens`, `output_tokens`, `cost_usd`
- 📍 **Uso actual**: `core/services_agent.py` ya trackea métricas

#### 2. **Gemini Image**
- ✅ **Tokens**: Información disponible en `core/ai_services/gemini_image.py`
- ✅ **Tokens por imagen**: 1290 tokens (constante según aspect ratio)
- ⚠️ **Costo**: NO está calculado actualmente, pero podemos usar pricing de Gemini

### ❌ Servicios que NO devuelven información de tokens/precio:

#### 3. **Gemini Veo (Video Generation)**
- ❌ **Tokens**: NO devuelve información de tokens
- ❌ **Costo**: NO devuelve costo por llamada
- 📍 **Necesita**: Investigar pricing de Vertex AI Veo API
- 📍 **Alternativa**: Calcular costo basado en duración/resolución del video

#### 4. **OpenAI Sora**
- ❌ **Tokens**: NO devuelve información de tokens
- ❌ **Costo**: NO devuelve costo por llamada
- 📍 **Necesita**: Investigar pricing de Sora API
- 📍 **Alternativa**: Calcular costo basado en duración/resolución del video

#### 5. **HeyGen**
- ❌ **Tokens**: NO devuelve información de tokens
- ❌ **Costo**: NO devuelve costo por llamada
- 📍 **Necesita**: Investigar pricing de HeyGen API
- 📍 **Alternativa**: Costo fijo por video o basado en duración

#### 6. **ElevenLabs (TTS)**
- ❌ **Tokens**: NO devuelve información de tokens
- ❌ **Costo**: NO devuelve costo por llamada
- 📍 **Necesita**: Investigar pricing de ElevenLabs API
- 📍 **Alternativa**: Calcular costo basado en caracteres/duración del audio

#### 7. **Vuela.ai**
- ❌ **Tokens**: NO devuelve información de tokens
- ❌ **Costo**: NO devuelve costo por llamada
- 📍 **Necesita**: Investigar pricing de Vuela.ai API
- 📍 **Alternativa**: Costo fijo por video o basado en duración/calidad

---

## Preguntas para Resolver ANTES de Implementar

### 1. **Rate Limiting**
- [ ] ¿Qué límites queremos por usuario?
  - ¿Límites diarios, semanales, mensuales?
  - ¿Límites por servicio o globales?
  - ¿Límites en tokens o en créditos?
- [ ] ¿Hay diferentes planes de usuario (free, pro, enterprise)?
- [ ] ¿Los límites se resetean automáticamente o manualmente?

### 2. **Tracking de Tokens**
- [ ] ¿Queremos tracking histórico completo o solo agregados?
- [ ] ¿Necesitamos granularidad por operación (cada llamada) o solo totales?
- [ ] ¿Qué período de retención de datos necesitamos?

### 3. **Sistema de Créditos**
- [ ] ¿Los créditos se compran o se asignan manualmente?
- [ ] ¿Hay recarga automática cuando se agotan?
- [ ] ¿Los créditos tienen fecha de expiración?
- [ ] ¿Queremos mostrar saldo de créditos en la UI?

### 4. **Conversión Tokens → Créditos**
- [ ] ¿Cómo calculamos el costo real de cada servicio?
  - Necesitamos investigar pricing de cada API
  - ¿Usamos pricing público o tenemos descuentos?
- [ ] ¿Aplicamos un margen/markup sobre el costo real?
- [ ] ¿Los créditos se deducen ANTES o DESPUÉS de la llamada?

### 5. **Servicios sin Información de Tokens**
- [ ] ¿Cómo calculamos el costo de servicios que no devuelven tokens?
  - **Veo/Sora**: ¿Basado en duración? ¿Resolución?
  - **HeyGen**: ¿Costo fijo por video? ¿Por segundo?
  - **ElevenLabs**: ¿Por carácter? ¿Por segundo de audio?
  - **Vuela.ai**: ¿Costo fijo? ¿Por segundo?

### 6. **Créditos Propios (Atenea)**
- [ ] ¿Cómo trackeamos nuestros propios créditos?
  - ¿Un modelo separado para créditos del sistema?
  - ¿Solo tracking de gastos sin saldo?
- [ ] ¿Queremos alertas cuando nuestros créditos estén bajos?
- [ ] ¿Necesitamos dashboard de gastos propios?

---

## Verificaciones Necesarias en los Servicios

### Servicios que NECESITAN adaptación:

1. **Gemini Veo** (`core/ai_services/gemini_veo.py`)
   - [ ] Verificar si la respuesta incluye información de billing/cost
   - [ ] Si no, necesitamos calcular costo basado en parámetros
   - [ ] Investigar pricing de Vertex AI Veo

2. **Sora** (`core/ai_services/sora.py`)
   - [ ] Verificar si la respuesta incluye información de billing/cost
   - [ ] Si no, necesitamos calcular costo basado en parámetros
   - [ ] Investigar pricing de OpenAI Sora

3. **HeyGen** (`core/ai_services/heygen.py`)
   - [ ] Verificar si la respuesta incluye información de billing/cost
   - [ ] Si no, necesitamos calcular costo basado en parámetros
   - [ ] Investigar pricing de HeyGen API

4. **ElevenLabs** (`core/ai_services/elevenlabs.py`)
   - [ ] Verificar si la respuesta incluye información de billing/cost
   - [ ] Si no, necesitamos calcular costo basado en parámetros
   - [ ] Investigar pricing de ElevenLabs TTS

5. **Vuela.ai** (`core/ai_services/vuela_ai.py`)
   - [ ] Verificar si la respuesta incluye información de billing/cost
   - [ ] Si no, necesitamos calcular costo basado en parámetros
   - [ ] Investigar pricing de Vuela.ai

6. **Gemini Image** (`core/ai_services/gemini_image.py`)
   - [x] Ya tiene información de tokens
   - [ ] Necesita cálculo de costo basado en tokens
   - [ ] Investigar pricing de Gemini Image API

---

## Arquitectura Propuesta

### Modelos de Base de Datos

#### 1. `UserCredits` (Saldo de créditos por usuario)
```python
- user: ForeignKey(User)
- credits: DecimalField (saldo actual)
- total_purchased: DecimalField (total comprado históricamente)
- total_spent: DecimalField (total gastado históricamente)
- created_at, updated_at
```

#### 2. `CreditTransaction` (Historial de transacciones)
```python
- user: ForeignKey(User)
- transaction_type: CharField ('purchase', 'spend', 'refund', 'adjustment')
- amount: DecimalField (cantidad de créditos)
- balance_before: DecimalField
- balance_after: DecimalField
- description: TextField
- related_object: GenericForeignKey (Video, Image, Audio, etc.)
- created_at
```

#### 3. `ServiceUsage` (Tracking de uso por servicio)
```python
- user: ForeignKey(User)
- service_name: CharField ('gemini_veo', 'sora', 'heygen', 'elevenlabs', 'llm_openai', 'llm_gemini', 'gemini_image', 'vuela_ai')
- operation_type: CharField ('video_generation', 'image_generation', 'tts', 'llm_call')
- tokens_used: IntegerField (null=True, para servicios con tokens)
- credits_spent: DecimalField
- cost_usd: DecimalField (costo real en USD)
- resource_id: CharField (ID del recurso generado)
- metadata: JSONField (info adicional)
- created_at
```

#### 4. `RateLimit` (Límites por usuario)
```python
- user: ForeignKey(User)
- limit_type: CharField ('daily', 'weekly', 'monthly')
- service_name: CharField (null=True para límites globales)
- limit_value: IntegerField (en créditos o tokens)
- period_start: DateTimeField
- period_end: DateTimeField
- current_usage: IntegerField
```

#### 5. `SystemCredits` (Créditos propios del sistema)
```python
- service_name: CharField
- credits_available: DecimalField
- total_spent: DecimalField
- last_updated: DateTimeField
- metadata: JSONField
```

---

## Pasos de Implementación

### Fase 1: Investigación y Preparación
1. [ ] Investigar pricing de todos los servicios
2. [ ] Definir conversión tokens → créditos para cada servicio
3. [ ] Decidir límites y políticas de rate limiting
4. [ ] Adaptar servicios para capturar información de costo/tokens

### Fase 2: Modelos y Migraciones
1. [ ] Crear modelos de base de datos
2. [ ] Crear migraciones
3. [ ] Crear índices para consultas eficientes

### Fase 3: Servicios de Créditos
1. [ ] Crear `CreditService` para manejar créditos
2. [ ] Crear `UsageTrackingService` para trackear uso
3. [ ] Crear `RateLimitService` para verificar límites
4. [ ] Crear `CostCalculationService` para calcular costos

### Fase 4: Integración con Servicios Existentes
1. [ ] Integrar tracking en `VideoService`
2. [ ] Integrar tracking en `ImageService`
3. [ ] Integrar tracking en `AudioService`
4. [ ] Integrar tracking en `ScriptAgentService` (ya tiene métricas)
5. [ ] Integrar tracking en servicios de escenas

### Fase 5: Middleware y Validaciones
1. [ ] Crear middleware para verificar créditos antes de operaciones
2. [ ] Crear decoradores para validar límites
3. [ ] Manejar errores cuando no hay créditos/límites

### Fase 6: UI y Reportes
1. [ ] Dashboard de créditos para usuarios
2. [ ] Historial de transacciones
3. [ ] Reportes de uso por servicio
4. [ ] Dashboard de créditos propios (admin)

---

## Próximos Pasos Inmediatos

1. **Investigar Pricing**:
   - [ ] Google Vertex AI Veo pricing
   - [ ] OpenAI Sora pricing
   - [ ] HeyGen API pricing
   - [ ] ElevenLabs TTS pricing
   - [ ] Vuela.ai pricing
   - [ ] Gemini Image API pricing (ya tenemos tokens)

2. **Adaptar Servicios**:
   - [ ] Modificar servicios para devolver información de costo/tokens
   - [ ] Crear métodos helper para calcular costos cuando no están disponibles

3. **Definir Políticas**:
   - [ ] Decidir límites por usuario
   - [ ] Decidir conversión tokens → créditos
   - [ ] Decidir margen/markup

---

## Notas Importantes

- Los servicios de LLM ya tienen tracking de tokens implementado
- Necesitamos adaptar los servicios de video/audio/imagen para capturar costos
- El sistema debe ser flexible para agregar nuevos servicios fácilmente
- Necesitamos balance entre precisión y simplicidad en el cálculo de costos

