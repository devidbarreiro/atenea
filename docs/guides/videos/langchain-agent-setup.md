# 🚀 Guía de Setup: Agente LangChain

## 📋 Prerrequisitos

1. Python 3.10+
2. Django 5.2+
3. Redis (para caché)
4. API keys de OpenAI o Gemini

---

## 🔧 Instalación

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Las nuevas dependencias incluyen:
- `langchain==0.3.0`
- `langchain-openai==0.2.0`
- `langchain-google-genai==2.0.0`
- `langgraph==0.2.0`
- `langsmith==0.2.0` (opcional pero recomendado)

### 2. Configurar Variables de Entorno

Agrega a tu `.env`:

```env
# LangSmith (Opcional pero recomendado para observabilidad)
LANGSMITH_API_KEY=tu-api-key-aqui
LANGSMITH_PROJECT=atenea-script-agent

# LLM Provider
DEFAULT_LLM_PROVIDER=openai  # o 'gemini'
DEFAULT_LLM_MODEL=  # Dejar vacío para default
LLM_TEMPERATURE=0.7
LLM_MAX_RETRIES=2

# Cache
AGENT_CACHE_TTL=86400  # 24 horas
AGENT_CACHE_ENABLED=True
```

### 3. Obtener LangSmith API Key (Opcional)

1. Ve a https://smith.langchain.com/
2. Crea una cuenta
3. Obtén tu API key
4. Agrégalo a `.env`

**Nota:** LangSmith es gratuito para uso personal y permite ver todas las llamadas al LLM, métricas, y debugging.

---

## 🧪 Testing Básico

### Probar el Agente Directamente

```python
from core.services_agent import ScriptAgentService

# Crear servicio
service = ScriptAgentService(llm_provider='openai')

# Obtener un script
from core.models import Script
script = Script.objects.get(id=1)

# Procesar
script = service.process_script(script)

# Ver escenas creadas
print(f"Escenas creadas: {script.db_scenes.count()}")
for scene in script.db_scenes.all():
    print(f"- {scene.scene_id}: {scene.platform} ({scene.duration_sec}s)")
```

### Probar con Guión de Prueba

```python
from core.models import Script, Project
from core.services_agent import ScriptAgentService

# Crear proyecto de prueba
project = Project.objects.create(name="Test Project")

# Crear script
script = Script.objects.create(
    project=project,
    original_script="Bienvenidos a este video sobre inteligencia artificial. Hoy exploraremos los conceptos fundamentales.",
    desired_duration_min=2,
    agent_flow=True,
    generate_previews=False  # Deshabilitar previews para testing rápido
)

# Procesar
service = ScriptAgentService()
script = service.process_script(script)

# Verificar resultados
print(f"Status: {script.status}")
print(f"Escenas: {script.db_scenes.count()}")
```

---

## 🔄 Migración desde n8n

### Opción 1: Migración Gradual (Recomendado)

1. **Mantener ambos sistemas** durante la transición
2. **Usar feature flag** para alternar:

```python
# En views.py o services.py
USE_LANGCHAIN_AGENT = config('USE_LANGCHAIN_AGENT', default=False, cast=bool)

if USE_LANGCHAIN_AGENT:
    from core.services_agent import ScriptAgentService
    service = ScriptAgentService()
else:
    from core.services import N8nService
    service = N8nService()
```

3. **Probar en producción** con 10% del tráfico
4. **Monitorear métricas** y errores
5. **Migrar completamente** cuando esté estable

### Opción 2: Migración Completa

1. **Reemplazar todas las llamadas** a `N8nService` por `ScriptAgentService`
2. **Eliminar código de n8n** después de verificar que funciona

```python
# Antes
from core.services import N8nService
service = N8nService()
service.send_script_for_processing(script)

# Después
from core.services_agent import ScriptAgentService
service = ScriptAgentService()
service.process_script(script)  # Procesa directamente, sin webhook
```

---

## 📊 Monitoreo y Observabilidad

### LangSmith Dashboard

1. Ve a https://smith.langchain.com/
2. Selecciona tu proyecto (`atenea-script-agent`)
3. Verás:
   - Todas las llamadas al LLM
   - Prompts y respuestas completas
   - Tokens usados y costos
   - Latencia
   - Errores

### Métricas en Django

```python
from core.monitoring.metrics import AgentMetrics

# Estadísticas del día
stats = AgentMetrics.get_daily_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Por proveedor: {stats['by_provider']}")

# Métricas de un script específico
metrics = AgentMetrics.get_script_metrics(script_id=123)
print(f"Tokens: {metrics['input_tokens']} + {metrics['output_tokens']}")
print(f"Costo: ${metrics['cost_usd']:.4f}")
print(f"Latencia: {metrics['latency_ms']:.0f}ms")
```

---

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY no está configurada"

**Solución:** Agrega `OPENAI_API_KEY` a tu `.env`

### Error: "GEMINI_API_KEY no está configurada"

**Solución:** Agrega `GEMINI_API_KEY` a tu `.env` o cambia `DEFAULT_LLM_PROVIDER=gemini`

### Error: "JSON inválido" del LLM

**Solución:** 
- El agente tiene auto-corrección, pero si persiste:
- Revisa el prompt en `core/agents/prompts/script_analysis_prompt.py`
- Verifica que el LLM tenga suficiente contexto (max_tokens)

### Caché no funciona

**Solución:**
- Verifica que Redis esté corriendo
- Verifica `REDIS_URL` en `.env`
- Deshabilita caché temporalmente: `AGENT_CACHE_ENABLED=False`

### Latencia alta

**Solución:**
- Usa caché: `AGENT_CACHE_ENABLED=True`
- Usa Gemini (más rápido que GPT-4): `DEFAULT_LLM_PROVIDER=gemini`
- Reduce temperatura: `LLM_TEMPERATURE=0.5`

---

## 📈 Optimización

### Reducir Costos

1. **Usar Gemini** en lugar de GPT-4 (más barato)
2. **Habilitar caché** para guiones repetidos
3. **Reducir temperatura** (menos variabilidad = menos tokens)

### Mejorar Velocidad

1. **Caché** es la mejor optimización
2. **Gemini** es más rápido que GPT-4
3. **Procesamiento async** con Celery (futuro)

---

## 🔐 Seguridad

- **API Keys:** Nunca commitees `.env` con API keys reales
- **Rate Limiting:** Configura límites en `settings.py`
- **Validación:** El agente valida todas las respuestas antes de procesarlas

---

## 📚 Recursos

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)

---

**¿Problemas?** Revisa los logs en `logs/atenea.log` o en LangSmith dashboard.

