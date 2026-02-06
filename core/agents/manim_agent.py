"""
Agente especializado en la creación de videos con Manim
"""
import logging
import json
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from .tools.list_manim_templates_tool import list_manim_templates_tool
from .tools.create_video_tool import create_video_tool
from .tools.search_web_tool import search_web_tool
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class ManimVideoAgent(BaseAgent):
    """
    Agente que orquesta la creación de videos Manim.
    Usa el patrón LCEL manual (sin AgentExecutor) para mayor control y compatibilidad.
    """
    
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        
        # Herramientas que el agente puede usar
        self.tools = [list_manim_templates_tool, create_video_tool, search_web_tool]
        
        # LLM
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o")
        
        # Bind tools
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
    def get_system_prompt(self) -> str:
        return """Eres un experto en visualización de datos y animaciones matemáticas usando Manim.
Tu objetivo es ayudar al usuario a crear videos animados a partir de sus descripciones.

Tienes acceso a una "biblioteca de templates" de Manim y una herramienta de búsqueda web.

### 🌟 Flujo de Trabajo Inteligente:

1.  **ANÁLISIS**: Lee la petición del usuario.
    *   ¿Tiene datos concretos? (ej: "Ventas: 10, 20, 30") -> Ve al paso 3.
    *   ¿Es una petición vaga o sin datos? (ej: "Gráfico de natalidad en España", "Evolución del Bitcoin") -> **VE AL PASO 2**.

2.  **INVESTIGACIÓN (Búsqueda Web)**:
    *   Usa `search_web_tool` para encontrar los datos REALES y RECIENTES necesarios.
    *   Ejemplo: `search_web_tool(query="tasa natalidad España últimos 5 años valores")`.
    *   Analiza los resultados y extrae una lista de valores y etiquetas coherentes.

3.  **SELECCIÓN DE TEMPLATE**:
    *   Llama a `list_manim_templates_tool` (si no lo has hecho ya) para ver qué animaciones existen.
    *   Elige el template más adecuado para los datos (ej: `modern_bar_chart` para comparativas, `line_chart` para tendencias temporales).

4.  **GENERACIÓN**:
    *   Mapea los datos (del usuario o de la búsqueda) al esquema del template.
    *   Llama a `create_video_tool` con `service='manim'`, `manim_template_type` y `manim_parameters`.
    *   **IMPORTANTE**: Si usaste datos de internet, añade una nota en el título o descripción indicando la fuente o el año si es relevante.

### Reglas:
*   **SIEMPRE** usa `user_id` en las llamadas a tools.
*   Si buscas datos, intenta obtener al menos 5 puntos de datos para que el gráfico quede bien.
*   Si no encuentras datos exactos, usa una aproximación razonable basada en lo que encuentres, pero avisa en la respuesta final de texto.

Ejemplo de flujo con Búsqueda:
Usuario: "Haz un gráfico de la inflación en Argentina"
Tú:
1. Detectas que faltan valores numéricos.
2. Llamas `search_web_tool(query="inflación anual Argentina últimos 5 años")`.
3. Recibes: "2019: 53.8%, 2020: 36.1%, 2021: 50.9%..."
4. Llamas `create_video_tool` con:
   template='line_chart'
   parameters={'values': [53.8, 36.1, 50.9...], 'labels': ['2019', '2020'...], 'title': 'Inflación Argentina (Estimada)'}
"""

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el agente
        Args:
            input_data: Dict con 'input' (prompt) y opcionalmente 'project_id'
        """
        try:
            prompt = input_data.get('input', '')
            project_id = input_data.get('project_id')
            
            if not prompt:
                return {"status": "error", "message": "No input provided"}

            # Mensajes iniciales
            messages = [
                ("system", self.get_system_prompt()),
                ("user", self._enrich_prompt(prompt, project_id))
            ]
            
            # Invocar LLM
            response = self.llm_with_tools.invoke(messages)
            
            # Procesar llamadas a herramientas (bucle simple: 1 iteración de tools es suficiente para este caso de uso)
            # Si se requiere multi-step, haríamos un while loop, pero aquí esperamos (Listar -> Crear) o (Listar -> Respuesta)
            # En la práctica, el LLM puede decidir llamar a Listar, luego volvemos a invocar, y luego llamar a Crear.
            
            # Implementamos un bucle limitado (max 3 iteraciones)
            MAX_ITERATIONS = 3
            final_output = ""
            
            current_messages = messages.copy()
            if not isinstance(current_messages[0], tuple): # Si ya convertimos a objetos message
                 pass 
            else:
                 # Langchain acepta tuplas, pero para el append necesitamos objetos
                 current_messages = [
                     SystemMessage(content=messages[0][1]),
                     HumanMessage(content=messages[1][1])
                 ]

            for _ in range(MAX_ITERATIONS):
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # El LLM quiere usar tools
                    current_messages.append(response) # Agregar el AIMessage con tool_calls
                    
                    tool_calls = response.tool_calls
                    logger.info(f"ManimAgent invocando {len(tool_calls)} tools")
                    
                    for tool_call in tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']
                        tool_call_id = tool_call['id']
                        
                        # Inyectar user_id si falta (aunque el prompt lo pide)
                        if 'user_id' not in tool_args:
                            tool_args['user_id'] = self.user_id
                        
                        # Ejecutar herramienta
                        tool_result = self._execute_tool(tool_name, tool_args)
                        
                        # Agregar resultado como ToolMessage
                        current_messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call_id,
                            name=tool_name
                        ))
                    
                    # Volver a invocar al LLM con los resultados
                    response = self.llm_with_tools.invoke(current_messages)
                else:
                    # Respuesta final (texto)
                    final_output = response.content
                    break
            
            return {
                "status": "success",
                "output": final_output
            }
            
        except Exception as e:
            logger.error(f"Error en ManimVideoAgent: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    def _execute_tool(self, tool_name: str, args: Dict) -> Any:
        try:
            if tool_name == 'list_manim_templates_tool':
                return list_manim_templates_tool.invoke(args)
            elif tool_name == 'create_video_tool':
                return create_video_tool.invoke(args)
            elif tool_name == 'search_web_tool':
                return search_web_tool.invoke(args)
            else:
                return f"Error: Tool {tool_name} not found"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _enrich_prompt(self, prompt: str, project_id: int) -> str:
        return f"""
        Petición del usuario: {prompt}
        
        CONTEXTO DE EJECUCIÓN (SYSTEM USE ONLY):
        - User ID actual: {self.user_id}
        - Project ID actual: {project_id if project_id else 'None'}
        
        IMPORTANTE: Cuando llames a `create_video_tool`, DEBES pasar el `user_id` ({self.user_id}) explícitamente.
        Si `project_id` no es None, pásalo también.
        """
