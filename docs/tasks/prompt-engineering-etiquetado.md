# Tarea: Sistema de Etiquetado de Guiones

## Asignado a: [Nombre del desarrollador - Prompt Engineering]

## Objetivo
Mejorar el agente actual (`ScriptAgent`) agregando capacidades de etiquetado automático de guiones para clasificación, extracción de entidades y análisis de sentimiento/tono.

---

## Contexto Actual

El agente actual (`core/agents/script_agent.py`) procesa guiones y genera escenas con:
- Análisis del guión completo
- División en escenas
- Asignación de plataformas (HeyGen, Gemini Veo, Sora)
- Generación de `visual_prompt` detallado

**Archivos relevantes:**
- `core/agents/script_agent.py` - Agente principal
- `core/agents/prompts/script_analysis_prompt.py` - Prompt actual
- `core/models.py` - Modelos Django (Script, Project, etc.)

---

## Tareas Específicas

### 1. Clasificación de Escenas
**Objetivo:** Etiquetar automáticamente cada escena con:
- **Tipo de contenido:** `intro`, `desarrollo`, `conclusion`, `transicion`, `b-roll`, `presentacion`
- **Plataforma sugerida:** `heygen`, `gemini_veo`, `sora` (basado en contenido, no solo duración)
- **Duración estimada:** Validar contra restricciones técnicas actuales
- **Complejidad visual:** `simple`, `media`, `compleja`

**Formato de salida:**
```json
{
  "scene_classification": {
    "content_type": "intro",
    "suggested_platform": "heygen",
    "estimated_duration_sec": 45,
    "visual_complexity": "simple",
    "confidence": 0.85
  }
}
```

### 2. Extracción de Entidades
**Objetivo:** Identificar y extraer:
- **Personajes:** Nombres, roles, menciones
- **Lugares:** Ubicaciones mencionadas
- **Objetos:** Elementos visuales importantes
- **Conceptos clave:** Términos técnicos, temas principales

**Formato de salida:**
```json
{
  "entities": {
    "characters": [
      {
        "name": "Dr. Smith",
        "role": "presentador",
        "mentions": 3,
        "scenes": ["Escena 1", "Escena 3"]
      }
    ],
    "locations": [
      {
        "name": "laboratorio",
        "type": "setting",
        "mentions": 2
      }
    ],
    "objects": [
      {
        "name": "microscopio",
        "type": "equipment",
        "visual_importance": "high"
      }
    ],
    "key_concepts": ["inteligencia artificial", "machine learning", "neural networks"]
  }
}
```

### 3. Análisis de Sentimiento/Tono
**Objetivo:** Analizar el tono emocional y el sentimiento:
- **Sentimiento general:** `positivo`, `neutro`, `negativo`
- **Tono:** `profesional`, `educativo`, `inspirador`, `técnico`, `casual`
- **Emociones detectadas:** `confianza`, `curiosidad`, `entusiasmo`, etc.
- **Intensidad:** `baja`, `media`, `alta`

**Formato de salida:**
```json
{
  "sentiment_analysis": {
    "overall_sentiment": "positivo",
    "tone": "profesional",
    "emotions": ["confianza", "curiosidad"],
    "intensity": "media",
    "confidence": 0.78
  }
}
```

---

## Integración con el Agente Actual

### Opción A: Agregar como nodos adicionales en el grafo
```python
# En script_agent.py, agregar nuevos nodos:
workflow.add_node("classify_scenes", self._classify_scenes_node)
workflow.add_node("extract_entities", self._extract_entities_node)
workflow.add_node("analyze_sentiment", self._analyze_sentiment_node)
```

### Opción B: Agregar como herramientas/funciones que se ejecutan en paralelo
```python
# Ejecutar análisis en paralelo después de parse_response
# y agregar resultados al estado
```

### Opción C: Crear servicio separado que se llama después del agente principal
```python
# En un nuevo archivo: core/services/script_tagging_service.py
class ScriptTaggingService:
    def tag_script(self, script_text: str, scenes: List[Dict]) -> Dict
```

**Recomendación:** Opción C (servicio separado) para mantener el código modular y testeable.

---

## Estructura de Datos

### Actualizar el modelo `Script` (si es necesario)
```python
# En core/models.py
class Script(models.Model):
    # ... campos existentes ...
    
    # Nuevos campos para etiquetado
    classification_metadata = models.JSONField(default=dict, blank=True)
    entities_metadata = models.JSONField(default=dict, blank=True)
    sentiment_metadata = models.JSONField(default=dict, blank=True)
```

### Actualizar `AgentState`
```python
class AgentState(TypedDict):
    # ... campos existentes ...
    classification_results: Dict[str, Any]
    entities_results: Dict[str, Any]
    sentiment_results: Dict[str, Any]
```

---

## Prompts a Desarrollar

### 1. Prompt para Clasificación
```
Eres un experto en análisis de contenido audiovisual.
Analiza la siguiente escena y clasifícala según:
- Tipo de contenido (intro, desarrollo, conclusión, transición, b-roll, presentación)
- Plataforma sugerida (heygen, gemini_veo, sora)
- Duración estimada en segundos
- Complejidad visual (simple, media, compleja)

Escena: {scene_text}

Responde SOLO con JSON válido.
```

### 2. Prompt para Extracción de Entidades
```
Eres un experto en procesamiento de lenguaje natural.
Extrae todas las entidades importantes del siguiente texto:
- Personajes (nombres, roles)
- Lugares (ubicaciones, settings)
- Objetos (elementos visuales importantes)
- Conceptos clave (términos técnicos, temas)

Texto: {script_text}

Responde SOLO con JSON válido.
```

### 3. Prompt para Análisis de Sentimiento
```
Eres un experto en análisis de sentimiento y tono.
Analiza el siguiente texto y determina:
- Sentimiento general (positivo, neutro, negativo)
- Tono (profesional, educativo, inspirador, técnico, casual)
- Emociones detectadas
- Intensidad emocional

Texto: {script_text}

Responde SOLO con JSON válido.
```

---

## Criterios de Éxito

- ✅ Cada escena tiene clasificación automática
- ✅ Se extraen al menos 3-5 entidades principales por guión
- ✅ El análisis de sentimiento tiene >70% de confianza
- ✅ Los resultados se guardan en formato JSON estructurado
- ✅ El sistema se integra sin romper el flujo actual del agente
- ✅ Los prompts son eficientes (no aumentan significativamente el costo de tokens)

---

## Recursos y Referencias

- **LangChain Entity Extraction:** https://python.langchain.com/docs/use_cases/extraction
- **Sentiment Analysis:** https://python.langchain.com/docs/use_cases/sentiment_analysis
- **Prompt Engineering Guide:** https://platform.openai.com/docs/guides/prompt-engineering

---

## Próximos Pasos

1. **Semana 1:** Investigar y diseñar los prompts para cada tarea
2. **Semana 2:** Implementar servicio de etiquetado (`ScriptTaggingService`)
3. **Semana 3:** Integrar con el agente actual y probar
4. **Semana 4:** Optimizar prompts y mejorar precisión

---

## Preguntas para Investigar

1. ¿Usar un solo LLM call con múltiples tareas o llamadas separadas?
2. ¿Qué modelo es mejor para cada tarea? (GPT-4o para clasificación, GPT-3.5 para entidades)
3. ¿Cómo manejar guiones muy largos? (chunking, resumen)
4. ¿Validar resultados con reglas de negocio o confiar 100% en el LLM?

---

## Contacto y Soporte

Si tienes dudas sobre:
- La estructura del código actual → Revisa `core/agents/script_agent.py`
- Los modelos de datos → Revisa `core/models.py`
- Los prompts existentes → Revisa `core/agents/prompts/script_analysis_prompt.py`

