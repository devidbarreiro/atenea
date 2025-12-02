# Migración a LangGraph - Overview Técnico

## 📋 Resumen Ejecutivo

Estamos migrando de **n8n** (workflow externo) a **LangGraph** (agente propio integrado) para el procesamiento de guiones. Esta migración nos da:

- ✅ **Control total** sobre el proceso
- ✅ **Observabilidad completa** (LangSmith + Django)
- ✅ **Costos reducidos** (sin dependencia externa)
- ✅ **Velocidad mejorada** (procesamiento síncrono)
- ✅ **Escalabilidad** (nuestro propio código)

---

## 1. ✅ Configuración de API Keys

**Estado:** ✅ **COMPLETO**

- Claves configuradas en `.env` para OpenAI y Gemini
- Sistema de fallback automático si un proveedor falla
- Factory pattern (`LLMFactory`) para crear instancias LLM
- Soporte para múltiples modelos por proveedor

**Ubicación:** `core/llm/factory.py`

---

## 2. ✅ Variables de Entorno

**Estado:** ✅ **COMPLETO**

- Todas las API keys en `.env`
- Sistema robusto que lee de Django settings o variables de entorno
- Funciona incluso cuando Django no está inicializado (útil para notebooks)

---

## 3. 🎯 LangGraph vs LangChain: ¿Cuál usar?

### **LangGraph** (Recomendado para tu caso) ✅

**Qué es:** Framework para construir **grafos de agentes** con estado persistente y control de flujo.

**Ventajas para tu solución:**
- ✅ **Grafos visuales** - Fácil de entender y depurar
- ✅ **Estado compartido** - Mantiene contexto entre nodos
- ✅ **Control de flujo** - Edges condicionales, loops, human-in-the-loop
- ✅ **Persistencia** - Puede guardar estado entre ejecuciones
- ✅ **Streaming** - Ver el progreso en tiempo real
- ✅ **Perfecto para workflows complejos** como tu proceso de guiones

**Cuándo usar:** Cuando necesitas un **flujo de trabajo con múltiples pasos** y decisiones.

### **LangChain** (Base)

**Qué es:** Framework para construir aplicaciones LLM con chains, tools, y memory.

**Ventajas:**
- ✅ Más simple para casos básicos
- ✅ Mejor para single-shot prompts
- ✅ Más documentación y ejemplos

**Cuándo usar:** Para prompts simples sin flujo complejo.

### **Recomendación para tu caso:**

**Usa LangGraph** porque:
1. Tu proceso tiene **múltiples pasos** (analizar → parsear → validar → corregir → formatear)
2. Necesitas **validaciones condicionales** (si hay errores, corregir automáticamente)
3. Quieres **observabilidad** del flujo completo
4. Planeas añadir **human-in-the-loop** en el futuro

**Nota:** LangGraph está construido sobre LangChain, así que puedes usar ambas juntas.

---

## 4. 🛠️ Herramientas (Tools) Interesantes

### Ya implementadas:
- ✅ **Validación de duraciones** (`duration_validator`)
- ✅ **Validación de estructura JSON** (`json_validator`)
- ✅ **Corrección automática** (`auto_corrector`)
- ✅ **Validación platform/avatar** (`platform_selector`)

### Herramientas adicionales recomendadas:

#### **Búsqueda y Web Scraping:**
- `TavilySearchResults` - Búsqueda web para contexto
- `DuckDuckGoSearchRun` - Búsqueda sin API key
- `ArxivSearch` - Búsqueda académica

#### **Análisis de Texto:**
- `TextSplitter` - Dividir guiones largos
- `SemanticSimilarity` - Encontrar guiones similares
- `SentimentAnalysis` - Análisis de sentimiento

#### **Validación Avanzada:**
- `SchemaValidator` - Validar contra JSON Schema
- `ContentModerator` - Moderar contenido inapropiado
- `LanguageDetector` - Detectar idioma del guión

#### **Integraciones Externas:**
- `GoogleSearch` - Búsqueda con Google API
- `Wikipedia` - Consultar Wikipedia
- `YouTubeTranscript` - Obtener transcripciones

**Recomendación:** Empieza con las que ya tienes. Añade más según necesidades específicas.

---

## 5. 📊 Observabilidad: Qué Trackear

### Ya implementado:
- ✅ **LangSmith** - Traces completos de ejecución
- ✅ **Django Logging** - Logs estructurados

### Métricas adicionales recomendadas:

#### **Performance:**
- ⏱️ **Latencia por nodo** - Tiempo de cada paso
- 🔄 **Throughput** - Requests por minuto
- ⚡ **Cache hit rate** - Eficiencia del caché

#### **Calidad:**
- ✅ **Tasa de éxito** - % de requests exitosas
- 🔁 **Tasa de retry** - Cuántas veces necesita reintentar
- 🎯 **Calidad de respuesta** - Score de calidad (LLM eval)

#### **Costos:**
- 💰 **Costo por request** - USD por guión procesado
- 📈 **Costo diario/mensual** - Tracking acumulado
- 🔍 **Costo por proveedor** - Comparar OpenAI vs Gemini

#### **Errores:**
- ❌ **Tipos de error** - Clasificación de errores
- 🔍 **Errores por nodo** - Dónde falla más
- 📊 **Tendencias de error** - Errores a lo largo del tiempo

**Herramientas recomendadas:**
- **LangSmith** (ya tienes) - Traces y debugging
- **Prometheus + Grafana** - Métricas en tiempo real
- **Sentry** - Alertas de errores
- **Datadog** - APM completo (si tienes presupuesto)

---

## 6. 📈 Tracking Detallado

### Ya implementado:
- ✅ Tokens (input/output) - `AgentMetrics.track_request()`
- ✅ Costos estimados - `LLMFactory.get_cost_estimate()`
- ✅ Latencia básica

### Mejoras recomendadas:

#### **Tracking de Tokens:**
```python
# Ya tienes esto en AgentMetrics
input_tokens, output_tokens, total_tokens
```

#### **Tracking de Latencia:**
```python
# Añadir latencia por nodo
latency_by_node = {
    'analyze_script': 2.5,
    'parse_response': 0.1,
    'validate_output': 0.3,
    'auto_correct': 1.2,
    'format_output': 0.05
}
```

#### **Tracking de Costos:**
```python
# Ya tienes costo por request
# Añadir: costo acumulado diario/mensual
daily_cost = sum(costs_today)
monthly_cost = sum(costs_this_month)
```

#### **Tracking de Errores:**
```python
error_types = {
    'json_parse_error': 5,
    'validation_error': 12,
    'llm_timeout': 2,
    'api_error': 1
}
```

#### **Tracking de Retries:**
```python
retry_stats = {
    'total_retries': 8,
    'retries_by_node': {
        'analyze_script': 3,
        'validate_output': 5
    },
    'avg_retries_per_request': 0.4
}
```

#### **Calidad de Respuestas:**
```python
# Evaluar calidad con LLM
quality_score = evaluate_response_quality(response)
# O métricas simples:
- Completeness: ¿Tiene todos los campos?
- Correctness: ¿Pasa validaciones?
- Consistency: ¿Es consistente con otros guiones?
```

**Recomendación:** Implementa gradualmente. Empieza con lo básico (ya lo tienes) y añade métricas según necesidades.

---

## 7. 🔄 n8n: Estado Actual

**Estado:** ✅ **DEPRECADO pero conservado**

- Código comentado para referencia histórica
- Ya no se usa en producción
- Formato de respuesta mantenido para compatibilidad
- `create_scenes_from_n8n_data()` sigue funcionando (formato compatible)

**Ventajas de mantener el formato:**
- ✅ Compatibilidad con código existente
- ✅ Migración gradual sin romper nada
- ✅ Referencia para entender estructura esperada

**Recomendación:** Mantener formato compatible hasta que toda la migración esté completa.

---

## 8. 🔁 Sistema de Retry

**Estado actual:** ✅ **Implementado**

- Retry a nivel de agente (`max_retries=2`)
- Retry automático si falla un nodo
- Corrección automática antes de retry

**Recomendación:** 
- ✅ **Mantener retry propio** - Más control
- ✅ **Añadir exponential backoff** - Esperar más entre retries
- ✅ **Retry inteligente** - Solo retry errores recuperables (no errores de validación lógica)

**Ejemplo mejorado:**
```python
def should_retry(error):
    retryable_errors = ['timeout', 'rate_limit', 'api_error']
    return any(e in str(error).lower() for e in retryable_errors)
```

---

## 9. 📤 Respuesta Completa

**Estado:** ✅ **Correcto**

- Respuesta completa con `project`, `characters`, `scenes`
- Formato compatible con n8n
- Incluye métricas y correcciones aplicadas

**Recomendación:** Mantener formato actual. Es simple y funcional.

---

## 10. 💾 Sistema de Caché

### **Cómo funciona actualmente:**

Ya tienes `AgentCache` implementado en `core/agents/cache.py`:

```python
# Guardar respuesta
AgentCache.set(script_text, duration_min, response)

# Obtener respuesta cacheada
cached = AgentCache.get(script_text, duration_min)
```

**Cómo funciona:**
1. **Hash del contenido** - Crea hash SHA256 de `script_text + duration_min`
2. **Redis/Django Cache** - Guarda respuesta en caché
3. **TTL** - Expira después de 24 horas (configurable)
4. **Cache hit** - Si mismo guión + duración → retorna cacheado

### **Recomendaciones:**

#### **Estrategia de Caché:**
- ✅ **Cache por contenido** - Ya implementado (hash del guión)
- ✅ **TTL configurable** - Ya implementado
- ⚠️ **Cache warming** - Pre-cachear guiones comunes
- ⚠️ **Cache invalidation** - Invalidar cuando prompt cambia

#### **Backend de Caché:**
- ✅ **Redis** (recomendado) - Rápido, persistente, escalable
- ⚠️ **Django Cache** (fallback) - Funciona pero menos eficiente

#### **Mejoras sugeridas:**
1. **Cache por versión de prompt** - Si cambias el prompt, invalidar caché
2. **Cache inteligente** - Cachear solo guiones > X caracteres (evitar cachear tests)
3. **Cache stats** - Trackear hit rate para optimizar

**Ejemplo mejorado:**
```python
def get_cache_key(script_text, duration_min, prompt_version):
    content = f"{script_text}:{duration_min}:{prompt_version}"
    return hashlib.sha256(content.encode()).hexdigest()
```

---

## 11. 🚦 Rate Limiting: Establecer Límites

### **Cómo establecer límites bien:**

#### **1. Analizar uso actual:**
```python
# Trackear durante 1-2 semanas:
- Requests por día
- Tokens por día
- Costo por día
- Picos de uso (horas del día)
```

#### **2. Calcular límites razonables:**
```python
# Ejemplo:
daily_avg = 1000 requests/day
peak_hour = 200 requests/hour
safety_margin = 1.5x

daily_limit = daily_avg * safety_margin  # 1500/day
hourly_limit = peak_hour * safety_margin  # 300/hour
```

#### **3. Límites por tipo de usuario:**
```python
limits = {
    'free': {
        'monthly_tokens': 100_000,
        'daily_requests': 10
    },
    'pro': {
        'monthly_tokens': 1_000_000,
        'daily_requests': 100
    },
    'enterprise': {
        'monthly_tokens': 10_000_000,
        'daily_requests': 1000
    }
}
```

#### **4. Límites por proveedor:**
```python
provider_limits = {
    'openai': {
        'tpm': 50000,  # tokens per minute
        'rpm': 500     # requests per minute
    },
    'gemini': {
        'tpm': 100000,
        'rpm': 1000
    }
}
```

#### **5. Implementación recomendada:**
- ✅ **Redis counters** - Contadores en Redis (ya tienes Redis)
- ✅ **Sliding window** - Ventana deslizante para límites por hora
- ✅ **Graceful degradation** - Si límite alcanzado, usar proveedor alternativo
- ✅ **Alertas** - Notificar cuando se acerca al límite

**Recomendación:** Empieza con límites generosos y ajusta según uso real.

---

## 12. ✅ Validaciones y Corrección Automática

**Estado:** ✅ **Bien implementado**

- Validación de estructura JSON
- Validación de duraciones
- Validación de consistencia platform/avatar
- Corrección automática de errores
- Reintento después de corrección

**Recomendación:** Mantener como está. Funciona bien.

---

## 13. 🤔 Punto 13: ¿Qué no entiendes?

**Necesito más contexto** sobre qué punto específico no entiendes. ¿Es sobre:
- Human-in-the-loop?
- Persistencia de estado?
- Streaming?
- Algo más?

**Dime qué punto específico y te explico mejor.**

---

## 14. 📝 Versionado de Prompts y A/B Testing

### **Versionado de Prompts:**

**Por qué es importante:**
- ✅ Comparar resultados entre versiones
- ✅ Rollback si nueva versión empeora
- ✅ Tracking de qué versión generó qué resultado

**Implementación recomendada:**

```python
# En settings.py
PROMPT_VERSION = 'v1.2.3'

# En el prompt
prompt = f"""
[Version: {settings.PROMPT_VERSION}]
{base_prompt}
"""

# En caché
cache_key = f"{script_hash}:{PROMPT_VERSION}"
```

**Sistema de versionado:**
- `v1.0.0` - Versión inicial
- `v1.1.0` - Cambios menores (mejoras de claridad)
- `v1.2.0` - Cambios mayores (nuevas instrucciones)
- `v2.0.0` - Cambios significativos (restructuración)

### **A/B Testing:**

**Cómo funciona:**
1. **Dividir tráfico** - 50% versión A, 50% versión B
2. **Trackear métricas** - Calidad, costo, latencia
3. **Comparar resultados** - ¿Cuál es mejor?
4. **Decidir ganador** - Implementar versión ganadora

**Implementación:**

```python
def get_prompt_version(user_id):
    # Deterministic A/B test basado en user_id
    if hash(user_id) % 2 == 0:
        return 'v1.2.0'  # Versión A
    else:
        return 'v1.3.0'  # Versión B

# Trackear qué versión se usó
metrics['prompt_version'] = prompt_version
metrics['ab_test_group'] = 'A' if prompt_version == 'v1.2.0' else 'B'
```

**Métricas a comparar:**
- ✅ Tasa de éxito
- ✅ Calidad de respuesta (LLM eval)
- ✅ Costo promedio
- ✅ Latencia promedio
- ✅ Tasa de retry

**Recomendación:** 
- ✅ Implementar versionado primero (simple)
- ✅ A/B testing después (más complejo, pero muy valioso)

---

## 📊 Resumen: Estado Actual vs Recomendaciones

| Aspecto | Estado Actual | Recomendación |
|---------|---------------|---------------|
| **API Keys** | ✅ Configuradas | Mantener |
| **LangGraph** | ✅ Implementado | ✅ Correcto |
| **Herramientas** | ✅ Básicas | Añadir según necesidad |
| **Observabilidad** | ✅ LangSmith + Logs | Añadir métricas detalladas |
| **Tracking** | ✅ Básico | Expandir gradualmente |
| **n8n** | ✅ Deprecado | Mantener formato compatible |
| **Retry** | ✅ Implementado | Mejorar con backoff |
| **Caché** | ✅ Implementado | Añadir versionado de prompt |
| **Rate Limiting** | ⚠️ Pendiente | Implementar con Redis |
| **Validaciones** | ✅ Completas | Mantener |
| **Versionado** | ⚠️ Pendiente | Implementar pronto |
| **A/B Testing** | ⚠️ Pendiente | Después de versionado |

---

## 🎯 Próximos Pasos Recomendados

1. **Corto plazo (1-2 semanas):**
   - ✅ Implementar versionado de prompts
   - ✅ Mejorar tracking de métricas
   - ✅ Añadir rate limiting básico

2. **Medio plazo (1 mes):**
   - ✅ A/B testing de prompts
   - ✅ Dashboard de métricas
   - ✅ Alertas automáticas

3. **Largo plazo (2-3 meses):**
   - ✅ Optimización de caché
   - ✅ Análisis de calidad avanzado
   - ✅ Auto-tuning de prompts

---

## 📚 Documentación de Referencia

- **LangGraph Docs:** https://docs.langchain.com/oss/python/langgraph/
- **LangSmith:** https://docs.smith.langchain.com/
- **Django Caching:** https://docs.djangoproject.com/en/stable/topics/cache/
- **Redis Rate Limiting:** https://redis.io/docs/manual/patterns/rate-limiting/

