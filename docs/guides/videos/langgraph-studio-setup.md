# 🎨 LangGraph Studio: Visualización del Grafo en Tiempo Real

## 🚀 Instalación Rápida

```bash
pip install langgraph-cli
```

## 📋 Configuración

Ya está creado el archivo `langgraph.json` en la raíz del proyecto.

## 🎯 Uso Básico

### 1. Iniciar LangGraph Studio

```bash
langgraph dev
```

Esto abrirá una interfaz web en `http://localhost:8123`

### 2. En la UI de LangGraph Studio

1. **Selecciona el grafo:** `script_agent`
2. **Ingresa datos de prueba:**
   ```json
   {
     "script_text": "Bienvenidos a este video sobre inteligencia artificial. Hoy exploraremos los conceptos fundamentales.",
     "duration_min": 2
   }
   ```
3. **Click en "Run"**
4. **Observa la ejecución paso a paso:**
   - Cada nodo se ejecuta en tiempo real
   - Puedes ver el estado en cada paso
   - Logs detallados de cada operación

## 🔍 Características de Visualización

### Ver el Grafo

- **Nodos:** Cada paso del proceso (analyze, parse, validate, etc.)
- **Flechas:** Flujo de datos entre nodos
- **Colores:** Estado de cada nodo (pendiente/ejecutando/completado/error)

### Ver Estado en Tiempo Real

- **Estado actual:** Ver qué datos tiene el agente en cada momento
- **Logs:** Ver logs detallados de cada operación
- **Errores:** Si algo falla, ver exactamente dónde y por qué

### Debugging

- **Pausar ejecución:** Pausar en cualquier punto
- **Inspeccionar estado:** Ver el contenido completo del estado
- **Step-by-step:** Ejecutar un paso a la vez

## 📊 Ejemplo de Uso

```bash
# Terminal 1: Iniciar LangGraph Studio
langgraph dev

# Terminal 2: Ejecutar test (opcional, para ver logs también)
python test_agent.py
```

En LangGraph Studio verás:
- El grafo completo
- La ejecución en tiempo real
- Cada nodo cambiando de color según su estado
- Logs detallados de cada paso

## 🎨 Personalización

### Agregar más información al grafo

Modifica `core/agents/script_agent.py` para agregar más metadata a los nodos:

```python
workflow.add_node(
    "analyze_script", 
    self._analyze_script_node,
    metadata={"description": "Analiza el guión con LLM"}
)
```

## 🐛 Troubleshooting

### "No se encuentra el grafo"

- Verifica que `langgraph.json` esté en la raíz
- Verifica que el path sea correcto: `core.agents.script_agent:ScriptAgent`

### "Error al importar"

- Asegúrate de tener todas las dependencias instaladas
- Verifica que Django esté configurado correctamente

### "Puerto 8123 ya en uso"

```bash
# Usar otro puerto
langgraph dev --port 8124
```

---

**¡Disfruta visualizando tu agente en acción!** 🎉

