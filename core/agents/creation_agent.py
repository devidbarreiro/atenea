"""
Creation Agent - Agente para crear contenido desde el chat
Usa LangChain con bind_tools para ejecutar tools directamente
"""

import logging
import os
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from core.llm.factory import LLMFactory
from core.agents.tools.create_video_tool import create_video_tool
from core.agents.tools.create_image_tool import create_image_tool
from core.monitoring.langsmith_config import setup_langsmith

logger = logging.getLogger(__name__)

# Configurar LangSmith con proyecto específico para Creation Agent
def setup_creation_agent_langsmith():
    """Configura LangSmith específicamente para Creation Agent"""
    from django.conf import settings
    langsmith_api_key = getattr(settings, 'LANGSMITH_API_KEY', None)
    if langsmith_api_key:
        os.environ['LANGCHAIN_TRACING_V2'] = 'true'
        os.environ['LANGCHAIN_API_KEY'] = langsmith_api_key
        os.environ['LANGCHAIN_PROJECT'] = 'atenea-creation-agent'
        logger.info("LangSmith configurado para Creation Agent (proyecto: atenea-creation-agent)")


class CreationAgent:
    """Agente para crear contenido audiovisual desde el chat"""
    
    def __init__(self, user_id: int):
        """
        Inicializa el agente de creación
        
        Args:
            user_id: ID del usuario que usa el agente
        """
        # Configurar LangSmith para este agente
        setup_creation_agent_langsmith()
        
        self.user_id = user_id
        
        # Crear LLM
        self.llm = LLMFactory.get_llm(
            provider='openai',  # Por ahora OpenAI, luego configurable
            temperature=0.7
        )
        
        # Tools disponibles (por ahora solo imagen)
        self.tools = [
            create_image_tool,
            create_video_tool
        ]
        
        # Bind tools al LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Prompt del sistema
        system_prompt = """Eres un asistente especializado en creación de contenido audiovisual con IA.

Puedes crear:
1. IMÁGENES: Usa create_image_tool para generar imágenes desde texto con Gemini Image
   - Ejemplo: "Crea una imagen de un perro haciendo surf"
   - Ejemplo: "Genera una imagen de un paisaje montañoso al atardecer"

2. VIDEOS: Usa create_video_tool para generar un video desde texto con Gemini Veo
    - Ejemplo: "Crea un video de un dinosaurio haciedno un backflip"
    - Ejemplo: "Genera un video de una cascada en un rio mediaval"
    - Ejemplo: "Haz un clip de 4 segundos de un mapache haciendo boxeo"

Cuando el usuario solicite crear contenido:
1. Identifica el tipo de contenido solicitado
2. Extrae el prompt/descripción del mensaje
3. Usa la tool correspondiente (siempre pasa user_id={user_id})
4. Informa al usuario del resultado de forma clara y amigable

Si falta información, pregunta al usuario antes de crear.
Sé conciso pero amigable en tus respuestas.""".format(user_id=self.user_id)
        
        # Crear prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
        
        logger.info(f"CreationAgent inicializado para usuario {user_id}")
    
    def chat(self, message: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario
        
        Args:
            message: Mensaje del usuario
            chat_history: Historial de conversación (opcional)
        
        Returns:
            Dict con 'answer' y 'tool_results' si se ejecutaron tools
        """
        try:
            # Convertir historial a formato LangChain
            langchain_messages = []
            if chat_history:
                for msg in chat_history:
                    if msg.get('role') == 'user':
                        langchain_messages.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        langchain_messages.append(AIMessage(content=msg.get('content', '')))
            
            # Agregar mensaje actual del usuario
            langchain_messages.append(HumanMessage(content=message))
            
            # Construir mensajes con prompt del sistema
            import json
            # Formatear prompt con historial y mensaje actual
            formatted_messages = self.prompt.format_messages(
                chat_history=langchain_messages,
                input=message
            )
            messages = formatted_messages
            
            # Invocar LLM con tools
            response = self.llm_with_tools.invoke(messages)
            
            # Verificar si el LLM quiere usar alguna tool
            tool_results = []
            answer = ""
            
            # En LangChain 1.0+, tool_calls puede estar en diferentes lugares
            tool_calls = None
            if hasattr(response, 'tool_calls'):
                tool_calls = response.tool_calls
            elif hasattr(response, 'additional_kwargs'):
                tool_calls = response.additional_kwargs.get('tool_calls', [])
            
            if tool_calls:
                # El LLM quiere usar tools
                for tool_call in tool_calls:
                    # tool_call puede ser dict o objeto
                    if isinstance(tool_call, dict):
                        tool_name = tool_call.get('name') or tool_call.get('function', {}).get('name')
                        tool_args_str = tool_call.get('args') or tool_call.get('function', {}).get('arguments', '{}')
                        # Si es string JSON, parsearlo
                        if isinstance(tool_args_str, str):
                            try:
                                tool_args = json.loads(tool_args_str)
                            except:
                                tool_args = {}
                        else:
                            tool_args = tool_args_str or {}
                    else:
                        tool_name = getattr(tool_call, 'name', None)
                        tool_args = getattr(tool_call, 'args', {}) or {}
                    
                    if not tool_name:
                        continue
                    
                    # Agregar user_id a los argumentos
                    tool_args['user_id'] = self.user_id
                    
                    # Ejecutar tool
                    tool_func = None
                    for tool in self.tools:
                        if tool.name == tool_name:
                            tool_func = tool
                            break
                    
                    if tool_func:
                        try:
                            tool_result = tool_func.invoke(tool_args)
                            tool_results.append((tool_name, tool_result))
                            
                            # Obtener tool_call_id del tool_call
                            tool_call_id = None
                            if isinstance(tool_call, dict):
                                tool_call_id = tool_call.get('id') or tool_call.get('tool_call_id')
                            else:
                                tool_call_id = getattr(tool_call, 'id', None)
                            
                            # Agregar resultado al historial usando ToolMessage (requerido por OpenAI)
                            messages.append(response)  # Mensaje del asistente con tool_calls
                            
                            # Crear ToolMessage con el resultado
                            tool_result_str = json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                            tool_message = ToolMessage(
                                content=tool_result_str,
                                tool_call_id=tool_call_id or f"call_{tool_name}"
                            )
                            messages.append(tool_message)
                            
                            # Invocar nuevamente para obtener respuesta final
                            final_response = self.llm_with_tools.invoke(messages)
                            answer = final_response.content if hasattr(final_response, 'content') else str(final_response)
                        except Exception as e:
                            logger.error(f"Error ejecutando tool {tool_name}: {e}", exc_info=True)
                            answer = f"Error al ejecutar {tool_name}: {str(e)}"
                    else:
                        answer = f"No se encontró la herramienta: {tool_name}"
            else:
                # Respuesta directa sin tools
                answer = response.content if hasattr(response, 'content') else str(response)
            
            return {
                'answer': answer,
                'tool_results': tool_results
            }
            
        except Exception as e:
            logger.error(f"Error en CreationAgent.chat: {e}", exc_info=True)
            return {
                'answer': f'Lo siento, ocurrió un error: {str(e)}',
                'tool_results': []
            }

