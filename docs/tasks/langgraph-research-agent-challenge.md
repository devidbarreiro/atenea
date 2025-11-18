# Reto: Research & Draft Agent con LangGraph

Equipo,

Estamos empezando la migración de la app actual hacia LangGraph y, mientras avanzamos con esa transición, quiero que vayáis explorando la tecnología, entendiendo su modelo de trabajo y realizando algunas pruebas internas. Cuando tengamos la base integrada en la app, podremos mover estos experimentos directamente in-app.

## 🎯 Reto: Construir un "Research & Draft Agent"

El objetivo es que entendáis cómo funcionan los grafos, la persistencia de estado, las transiciones y el uso de herramientas.

### El agente debe:

1. **Recibir un tema** (por ejemplo: "tendencias de IA en 2025").
2. **Buscar información** usando una herramienta (puede ser mock).
3. **Resumir los hallazgos** en un nodo separado.
4. **Generar un borrador** basado en el resumen.
5. **Incluir un punto de revisión humana** (human-in-the-loop).
6. **Usar estado o memoria** para mantener los pasos previos.
7. **Permitir ejecución** con `.invoke()` y `.stream()` para ver todo el flujo.
8. **Generar un diagrama ASCII** del grafo.

### Requisitos técnicos:

- Implementar un `StateGraph` con al menos cuatro nodos: `search_node`, `summarize_node`, `draft_node` y `review_node`.
- Usar **edges condicionales** para decidir si el borrador pasa por revisión o termina.
- Incluir al menos una **herramienta de LangChain** (real o mock).
- Mantener un **estado compartido** que registre los pasos del proceso.
- Entregar una ejecución de prueba junto con el diagrama.

## 📚 Documentación oficial:

- **LangGraph – Overview**: https://docs.langchain.com/oss/python/langgraph/overview
- **LangGraph – StateGraph**: https://docs.langchain.com/oss/python/langgraph/state
- **LangGraph – Edges y control de flujo**: https://docs.langchain.com/oss/python/langgraph/edges
- **LangGraph – Human-in-the-loop**: https://docs.langchain.com/oss/python/langgraph/human_in_the_loop
- **LangChain – Herramientas, modelos y chains**: https://python.langchain.com/docs
- **LangGraph Platform**: https://www.langchain.com/langgraph

## 📦 Entregables:

1. **Código del grafo**
2. **Diagrama ASCII**
3. **Ejecución de prueba** (input y trace)
4. **Explicación breve** de las decisiones técnicas

## 🚀 Cómo empezar:

1. Crear un notebook en tu carpeta personal (`notebooks/marcos/` o `notebooks/ruth/`)
2. O trabajar en `notebooks/challenges/research_agent/` si prefieres compartir el espacio
3. Configurar Django ejecutando `%run ../../setup_django.py` al inicio del notebook
4. Explorar el código existente en `core/agents/script_agent.py` como referencia
5. Empezar con un grafo simple y luego añadir complejidad

**Nota**: Puedes usar el notebook de ejemplo `notebooks/challenges/research_agent/01_setup.ipynb` como punto de partida.

---

**Nota**: Este es un ejercicio de aprendizaje. No hace falta que sea perfecto, lo importante es entender los conceptos y experimentar. ¡Ánimo!

