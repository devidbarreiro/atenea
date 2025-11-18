# 🧪 Guía de Testing y Observabilidad: Agente LangChain

## 🎯 Testing Manual del Agente

### Opción 1: Django Shell (Rápido)

```bash
python manage.py shell
```

```python
from core.models import Script, Project
from core.services_agent import ScriptAgentService

# Obtener o crear proyecto
project = Project.objects.first()
if not project:
    project = Project.objects.create(name="Test Project")

# Crear script de prueba
script = Script.objects.create(
    project=project,
    title="Test Script",
    original_script="Bienvenidos a este video sobre inteligencia artificial. Hoy exploraremos los conceptos fundamentales de las redes neuronales y cómo están transformando nuestro mundo.",
    desired_duration_min=2,
    agent_flow=True,
    generate_previews=False  # Deshabilitar previews para test rápido
)

# Procesar con LangChain
service = ScriptAgentService(llm_provider='openai')  # o 'gemini'
script = service.process_script(script)

# Verificar resultados
print(f"Status: {script.status}")
print(f"Escenas creadas: {script.db_scenes.count()}")
for scene in script.db_scenes.all():
    print(f"  - {scene.scene_id}: {scene.platform} ({scene.duration_sec}s)")
    print(f"    Texto: {scene.script_text[:50]}...")
```

### Opción 2: Test Script (Más Completo)

Crea un archivo `test_agent.py` en la raíz:

```python
#!/usr/bin/env python
"""Script de prueba para el agente LangChain"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
django.setup()

from core.models import Script, Project
from core.services_agent import ScriptAgentService

def test_agent():
    # Crear proyecto de prueba
    project, _ = Project.objects.get_or_create(name="Test Agent Project")
    
    # Crear script
    script = Script.objects.create(
        project=project,
        title="Test LangChain Agent",
        original_script="""
        Bienvenidos a este video sobre inteligencia artificial. 
        Hoy exploraremos los conceptos fundamentales de las redes neuronales 
        y cómo están transformando nuestro mundo. 
        Desde asistentes virtuales hasta sistemas de recomendación, 
        la IA está en todas partes. El futuro promete avances aún más sorprendentes.
        """,
        desired_duration_min=3,
        agent_flow=True,
        generate_previews=False
    )
    
    print(f"📝 Procesando guión: {script.title}")
    print(f"   Texto: {len(script.original_script)} caracteres")
    print(f"   Duración deseada: {script.desired_duration_min} minutos")
    print()
    
    # Procesar
    service = ScriptAgentService(llm_provider='openai')
    script = service.process_script(script)
    
    # Resultados
    print(f"✅ Status: {script.status}")
    print(f"📊 Escenas creadas: {script.db_scenes.count()}")
    print()
    
    for idx, scene in enumerate(script.db_scenes.all(), 1):
        print(f"Escena {idx}:")
        print(f"  - ID: {scene.scene_id}")
        print(f"  - Plataforma: {scene.platform}")
        print(f"  - Duración: {scene.duration_sec}s")
        print(f"  - Avatar: {scene.avatar}")
        print(f"  - Texto: {scene.script_text[:80]}...")
        print()

if __name__ == '__main__':
    test_agent()
```

Ejecutar:
```bash
python test_agent.py
```

---

## 🔍 Observabilidad con LangSmith

### Setup LangSmith

1. **Crear cuenta en LangSmith:**
   - Ve a https://smith.langchain.com/
   - Crea una cuenta (gratis)
   - Obtén tu API key

2. **Configurar en `.env`:**
   ```env
   LANGSMITH_API_KEY=tu-api-key-aqui
   LANGSMITH_PROJECT=atenea-script-agent
   ```

3. **Verificar configuración:**
   ```python
   # En Django shell
   from core.monitoring.langsmith_config import setup_langsmith
   setup_langsmith()
   ```

### Ver Traces en LangSmith

1. **Ejecutar un test** (usando el script de arriba)

2. **Ir a LangSmith Dashboard:**
   - https://smith.langchain.com/
   - Selecciona tu proyecto (`atenea-script-agent`)

3. **Verás:**
   - Todas las llamadas al LLM
   - Prompts completos
   - Respuestas completas
   - Tokens usados
   - Latencia
   - Costos estimados

### Métricas en Tiempo Real

```python
from core.monitoring.metrics import AgentMetrics

# Estadísticas del día
stats = AgentMetrics.get_daily_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Por proveedor: {stats['by_provider']}")

# Métricas de un script específico
metrics = AgentMetrics.get_script_metrics(script_id=123)
if metrics:
    print(f"Tokens: {metrics['input_tokens']} + {metrics['output_tokens']}")
    print(f"Costo: ${metrics['cost_usd']:.4f}")
    print(f"Latencia: {metrics['latency_ms']:.0f}ms")
```

---

## 🎨 Visualización con LangGraph Studio

LangGraph Studio es una herramienta visual para ver y debuggear el grafo del agente.

### Instalación

```bash
pip install langgraph-cli
```

### Configurar el Proyecto

1. **Crear archivo `langgraph.json` en la raíz:**

```json
{
  "dependencies": ["."],
  "graphs": {
    "script_agent": {
      "path": "core.agents.script_agent:ScriptAgent",
      "description": "Agente para procesar guiones"
    }
  },
  "env": ".env"
}
```

2. **Exportar el grafo del agente:**

Necesitamos modificar `ScriptAgent` para que sea compatible con LangGraph Studio. Agregar método para exportar el grafo:

```python
# En core/agents/script_agent.py
def get_graph(self):
    """Retorna el grafo para LangGraph Studio"""
    return self.graph
```

### Ejecutar LangGraph Studio

```bash
langgraph dev
```

Esto abrirá una interfaz web en `http://localhost:8123` donde puedes:
- Ver el grafo visualmente
- Ejecutar el agente paso a paso
- Ver el estado en cada nodo
- Ver logs en tiempo real
- Debuggear errores

### Usar desde la UI

1. Abre http://localhost:8123
2. Selecciona el grafo `script_agent`
3. Ingresa datos de prueba:
   ```json
   {
     "script_text": "Bienvenidos a este video sobre IA...",
     "duration_min": 2
   }
   ```
4. Click en "Run"
5. Verás la ejecución paso a paso en tiempo real

---

## 📊 Logs en Tiempo Real

### Opción 1: Django Logging

```python
# En settings.py, ya está configurado
# Los logs van a la consola y a logs/atenea.log

# Ver logs en tiempo real:
tail -f logs/atenea.log | grep -i "agent\|langchain\|script"
```

### Opción 2: LangSmith Stream

LangSmith tiene un modo "stream" para ver logs en tiempo real:

```bash
# Instalar langsmith-cli
pip install langsmith-cli

# Ver logs en tiempo real
langsmith stream --project atenea-script-agent
```

### Opción 3: Python con Logging Avanzado

```python
import logging
from core.agents.script_agent import ScriptAgent

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Crear agente
agent = ScriptAgent(llm_provider='openai')

# Procesar (verás logs detallados)
result = agent.process_script(
    script_text="Test script",
    duration_min=2
)
```

---

## 🐛 Debugging Avanzado

### Ver Estado del Grafo en Cada Paso

Modificar `ScriptAgent` para agregar logging detallado:

```python
# En cada nodo del grafo, agregar:
def _analyze_script_node(self, state: AgentState) -> AgentState:
    logger.info(f"🔵 Nodo: analyze_script")
    logger.info(f"   Estado actual: {state.keys()}")
    # ... código ...
    logger.info(f"✅ Nodo completado")
    return state
```

### Inspeccionar Respuesta del LLM

```python
# En script_agent.py, después de invocar LLM:
response = self.llm.invoke(messages)
logger.debug(f"📥 Respuesta LLM completa:")
logger.debug(f"   Tipo: {type(response)}")
logger.debug(f"   Contenido: {response.content[:500]}...")
```

### Validar JSON Antes de Parsear

```python
# Agregar validación extra:
try:
    parsed = json.loads(json_text)
except json.JSONDecodeError as e:
    logger.error(f"❌ JSON inválido en línea {e.lineno}, columna {e.colno}")
    logger.error(f"   Texto problemático: {json_text[max(0, e.pos-50):e.pos+50]}")
    raise
```

---

## ✅ Checklist de Testing

- [ ] Test básico en Django shell
- [ ] Test con script real (3+ minutos)
- [ ] Verificar que se crean escenas correctamente
- [ ] Verificar duraciones válidas por plataforma
- [ ] Verificar visual_prompt es objeto JSON
- [ ] Ver traces en LangSmith
- [ ] Ver métricas de tokens y costos
- [ ] Probar con OpenAI
- [ ] Probar con Gemini (fallback)
- [ ] Probar con caché habilitado
- [ ] Verificar logs en tiempo real

---

## 🚀 Próximos Pasos

1. **Configurar LangSmith** (5 min)
2. **Ejecutar test básico** (2 min)
3. **Ver resultados en LangSmith** (explorar UI)
4. **Instalar LangGraph Studio** (opcional pero muy útil)
5. **Probar con guiones reales**

---

**¿Problemas?** Revisa:
- Logs en `logs/atenea.log`
- LangSmith dashboard para errores del LLM
- Console de Django para errores de Python

