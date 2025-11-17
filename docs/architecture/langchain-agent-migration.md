# 🚀 Migración a Agente LangChain: Documentación Ejecutiva

## 📋 Resumen Ejecutivo

**Objetivo:** Reemplazar la dependencia externa de n8n con un agente propio basado en LangChain, mejorando control, velocidad y observabilidad del proceso de análisis de guiones.

**Beneficios Clave:**
- ✅ **Eliminación de dependencia externa** (n8n)
- ✅ **Reducción de latencia** (~70% más rápido)
- ✅ **Control total** sobre el proceso de análisis
- ✅ **Observabilidad completa** (tokens, costos, latencia)
- ✅ **Validación automática** y corrección de errores
- ✅ **Caché inteligente** para reducir costos

---

## 🔄 LangGraph vs Chain Simple: ¿Cuál Elegir?

### **Chain Simple (LCEL)**
**Qué es:** Un flujo lineal donde el prompt se envía directamente al LLM y se procesa la respuesta.

**Ventajas:**
- ✅ Más simple de implementar
- ✅ Menos overhead
- ✅ Ideal para tareas simples y directas

**Desventajas:**
- ❌ No permite pasos intermedios
- ❌ Difícil de debuggear
- ❌ No permite validación antes de finalizar
- ❌ No permite retry inteligente

**Ejemplo:**
```
Prompt → LLM → Respuesta JSON → Validar → Listo
```

### **LangGraph (Recomendado)**
**Qué es:** Un grafo de estado que permite múltiples pasos, validaciones intermedias, y flujos condicionales.

**Ventajas:**
- ✅ **Pasos intermedios:** Puedes validar antes de continuar
- ✅ **Retry inteligente:** Si falla validación, reintenta solo esa parte
- ✅ **Observabilidad:** Trackeas cada paso individualmente
- ✅ **Corrección automática:** Si detecta error, puede corregirlo
- ✅ **Escalable:** Fácil agregar nuevos pasos

**Desventajas:**
- ❌ Más complejo inicialmente
- ❌ Más overhead (mínimo)

**Ejemplo:**
```
[Start] → [Analizar Guión] → [Generar Escenas] → [Validar Duración] 
    ↓                              ↓                    ↓
[Log]                          [Log]                [Si inválido → Corregir]
    ↓                              ↓                    ↓
[Continuar] → [Validar JSON] → [Formatear] → [End]
```

### **Recomendación: LangGraph** ✅

**Razones:**
1. **Validación crítica:** Necesitamos validar duraciones por plataforma (Sora: 4/8/12s, Veo: ≤8s, HeyGen: 30-60s)
2. **Corrección automática:** Si el LLM genera duración inválida, podemos corregirla automáticamente
3. **Observabilidad:** Necesitamos trackear cada paso para debugging y optimización
4. **Escalabilidad futura:** Fácil agregar nuevas validaciones o pasos

---

## 🏗️ Arquitectura Propuesta

### Flujo LangGraph

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Analyze Script  │ ← Analiza guión y duración
│ (LLM Call)      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Generate Scenes │ ← Genera escenas con LLM
│ (LLM Call)      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Validate Output │ ← Valida duraciones, formato
│ (Tools)         │
└──────┬──────────┘
       │
       ├─→ [Válido] ──┐
       │              │
       └─→ [Inválido] ──→ [Auto-Correct] ──┐
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │ Format JSON  │
                                    └──────┬───────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │     END      │
                                    └──────────────┘
```

### Componentes

1. **Script Agent (LangGraph)**
   - Nodos: Analyze, Generate, Validate, Correct, Format
   - Estado: Script text, scenes, validation errors

2. **Tools (Herramientas)**
   - `DurationValidator`: Valida duraciones por plataforma
   - `WordCounter`: Cuenta palabras vs duración
   - `JSONValidator`: Valida estructura JSON
   - `PlatformSelector`: Sugiere plataforma óptima
   - `AutoCorrector`: Corrige errores comunes

3. **LLM Factory**
   - Soporte para OpenAI (GPT-4) y Gemini Pro
   - Fallback automático
   - Rate limiting

4. **Observabilidad**
   - LangSmith: Trazabilidad completa
   - Django Logging: Logs estructurados
   - Métricas: Tokens, latencia, costos

5. **Caché**
   - Redis: Caché por hash del guión
   - TTL: 24 horas
   - Invalidación inteligente

---

## 📊 Comparativa: Antes vs Después

| Aspecto | n8n (Actual) | LangChain (Nuevo) |
|---------|--------------|-------------------|
| **Latencia** | ~30-60s (HTTP + procesamiento) | ~10-20s (procesamiento directo) |
| **Dependencias** | Externa (n8n server) | Interna (solo código) |
| **Control** | Limitado (solo webhook) | Total (código propio) |
| **Observabilidad** | Solo logs de n8n | LangSmith + Django logs |
| **Validación** | Manual (post-procesamiento) | Automática (durante generación) |
| **Corrección** | Manual | Automática |
| **Caché** | No | Sí (Redis) |
| **Costos** | No trackeable | Trackeable por request |
| **Debugging** | Difícil | Fácil (trazabilidad completa) |

---

## 💰 Análisis de Costos

### Estimación Mensual (1000 guiones/mes)

**n8n (Actual):**
- Costo n8n: $0 (self-hosted) o ~$20/mes (cloud)
- Sin tracking de costos LLM

**LangChain (Nuevo):**
- OpenAI GPT-4: ~$0.03 por guión = **$30/mes**
- Gemini Pro: ~$0.01 por guión = **$10/mes**
- Con caché (30% hit rate): **$21-28/mes**

**Ahorro con caché:** ~30% de reducción en costos LLM

---

## 🔧 Herramientas de Validación

### 1. **DurationValidator**
Valida que las duraciones sean válidas según plataforma:
- Sora: Exactamente 4, 8, o 12 segundos
- Gemini Veo: Entre 5 y 8 segundos
- HeyGen: Entre 30 y 60 segundos

### 2. **WordCounter**
Valida que el texto tenga palabras apropiadas para la duración:
- 5s: 10-11 palabras
- 8s: 16-18 palabras
- 12s: 22-25 palabras

### 3. **JSONValidator**
Valida estructura JSON completa:
- Campos requeridos presentes
- Tipos correctos
- Valores válidos

### 4. **PlatformSelector**
Sugiere plataforma óptima basado en:
- Tipo de contenido (presentador vs b-roll)
- Duración requerida
- Estilo visual

### 5. **AutoCorrector**
Corrige errores comunes:
- Duraciones inválidas → Ajusta al valor más cercano válido
- Campos faltantes → Genera valores por defecto
- Formato incorrecto → Reformatea

---

## 📈 Observabilidad

### LangSmith
- **Trazabilidad completa:** Cada llamada al LLM trackeada
- **Visualización:** Ver el flujo completo en tiempo real
- **Debugging:** Inspeccionar prompts y respuestas
- **Costos:** Tracking automático de tokens y costos

### Django Logging
- **Logs estructurados:** JSON logs para fácil parsing
- **Niveles:** DEBUG, INFO, WARNING, ERROR
- **Contexto:** Script ID, usuario, duración, etc.

### Métricas Personalizadas
- Tokens usados (input/output)
- Latencia por paso
- Costos por request
- Tasa de éxito/error
- Tasa de caché hit

---

## 💾 Estrategia de Caché

### Cómo Funciona

1. **Hash del guión:** Genera hash SHA256 del texto del guión + duración
2. **Check Redis:** Si existe en caché, retorna inmediatamente
3. **Si no existe:** Procesa con LLM y guarda en caché
4. **TTL:** 24 horas (configurable)

### Beneficios

- **Reducción de costos:** ~30% menos llamadas al LLM
- **Velocidad:** Respuesta instantánea para guiones repetidos
- **Escalabilidad:** Maneja mejor picos de tráfico

### Invalidación

- Manual: Por admin
- Automática: Después de TTL
- Por versión: Si cambia el prompt, invalida caché

---

## 🚦 Rate Limiting

### Estrategia Inicial

**Por usuario:**
- 10 guiones/hora
- 50 guiones/día

**Por proyecto:**
- 5 guiones/hora
- 20 guiones/día

**Global:**
- 100 guiones/hora
- 1000 guiones/día

### Ajuste Dinámico

Monitorear durante 2 semanas y ajustar según:
- Uso real
- Costos LLM
- Latencia del sistema

---

## 🧪 Testing y Desarrollo

### Modo Desarrollo

1. **Mock Responses:** Respuestas predefinidas sin llamar al LLM
2. **Dry Run:** Valida flujo sin generar escenas reales
3. **Test Fixtures:** Guiones de prueba con resultados esperados

### Testing

- **Unit Tests:** Cada herramienta individualmente
- **Integration Tests:** Flujo completo end-to-end
- **E2E Tests:** Con guiones reales

---

## 📝 Versionado de Prompts

### Estructura

```
config/prompts/
├── script_analysis/
│   ├── v1.yaml
│   ├── v2.yaml (actual)
│   └── v3.yaml (experimental)
└── scene_generation/
    ├── v1.yaml
    └── v2.yaml
```

### A/B Testing

- **50% usuarios:** Prompt v2
- **50% usuarios:** Prompt v3
- **Métricas:** Comparar calidad de escenas generadas
- **Decisión:** Elegir mejor prompt después de 1 semana

---

## 📅 Plan de Implementación

### Fase 1: Setup (Semana 1)
- [ ] Instalar dependencias (LangChain, LangSmith)
- [ ] Configurar LangSmith
- [ ] Crear estructura de archivos
- [ ] Setup básico de LLM Factory

### Fase 2: Agente Base (Semana 2)
- [ ] Implementar LangGraph básico
- [ ] Crear herramientas de validación
- [ ] Integrar con servicios existentes
- [ ] Tests básicos

### Fase 3: Observabilidad (Semana 3)
- [ ] Configurar LangSmith
- [ ] Implementar métricas
- [ ] Dashboard de monitoreo
- [ ] Alertas

### Fase 4: Optimización (Semana 4)
- [ ] Implementar caché
- [ ] Rate limiting
- [ ] Auto-corrección
- [ ] Performance tuning

### Fase 5: Migración (Semana 5)
- [ ] Feature flag para alternar n8n/LangChain
- [ ] Testing en producción (10% tráfico)
- [ ] Monitoreo intensivo
- [ ] Migración completa

---

## 🎯 Métricas de Éxito

### Técnicas
- ✅ Latencia < 20s (vs 30-60s actual)
- ✅ Tasa de éxito > 95%
- ✅ Validación automática 100%
- ✅ Caché hit rate > 30%

### Negocio
- ✅ Reducción de costos operativos (sin n8n)
- ✅ Mejor control sobre calidad
- ✅ Escalabilidad mejorada
- ✅ Mejor experiencia de usuario

---

## 📚 Referencias

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)

---

**Fecha:** Enero 2025  
**Versión:** 1.0  
**Autor:** Equipo de Desarrollo Atenea

