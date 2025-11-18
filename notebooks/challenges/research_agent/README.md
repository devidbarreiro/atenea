# Research & Draft Agent - Notebooks

Este directorio contiene los notebooks para el reto del Research & Draft Agent.

## Estructura

- `01_setup.ipynb` - Configuración inicial y setup de Django
- `02_basic_graph.ipynb` - Grafo básico con nodos simples
- `03_with_tools.ipynb` - Añadir herramientas de LangChain
- `04_human_in_loop.ipynb` - Implementar human-in-the-loop
- `05_final_agent.ipynb` - Agente completo con todas las funcionalidades

## Cómo usar

1. Abre Jupyter Notebook o JupyterLab:
   ```bash
   jupyter notebook
   # o
   jupyter lab
   ```

2. En el primer cell del notebook, ejecuta:
   ```python
   %run ../../setup_django.py
   ```

3. O importa directamente:
   ```python
   from notebooks.setup_django import setup_django
   setup_django()
   ```

4. Ahora puedes importar modelos y servicios de Django:
   ```python
   from core.models import Script, Scene
   from core.agents.script_agent import ScriptAgent
   from core.llm.factory import LLMFactory
   ```

## Ejemplo básico

```python
# Setup Django
%run ../../setup_django.py

# Importar lo necesario
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from core.llm.factory import LLMFactory

# Crear LLM
llm = LLMFactory.get_llm(provider='openai', temperature=0.7)

# Definir estado
from typing import TypedDict

class ResearchState(TypedDict):
    topic: str
    search_results: str
    summary: str
    draft: str
    needs_review: bool

# Crear grafo básico
workflow = StateGraph(ResearchState)

def search_node(state: ResearchState):
    # Tu lógica aquí
    return {"search_results": "Resultados mock"}

workflow.add_node("search", search_node)
workflow.set_entry_point("search")
workflow.add_edge("search", END)

# Compilar y ejecutar
graph = workflow.compile()
result = graph.invoke({"topic": "tendencias de IA en 2025"})
print(result)
```

