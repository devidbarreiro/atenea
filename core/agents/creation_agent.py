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
from core.agents.tools.create_quote_tool import create_quote_tool
from core.agents.tools.list_avatars_tool import list_avatars_tool
from core.agents.tools.list_voices_tool import list_voices_tool
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
        
        # Tools disponibles
        self.tools = [
            create_image_tool,
            create_video_tool,
            create_quote_tool,
            list_avatars_tool,
            list_voices_tool
        ]
        
        # Bind tools al LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Prompt del sistema
        system_prompt = """Eres un asistente especializado en creación de contenido audiovisual con IA.

HERRAMIENTAS DISPONIBLES:

1. IMÁGENES: create_image_tool - Genera imágenes desde texto con Gemini Image
   - Ejemplo: "Crea una imagen de un perro haciendo surf"
   - Ejemplo: "Genera una imagen de un paisaje montañoso al atardecer"

2. VIDEOS: create_video_tool - Genera videos desde texto con múltiples servicios:
   - Gemini Veo (por defecto): "Crea un video de un dinosaurio haciendo un backflip"
   - Sora: "Genera un video con Sora de una cascada en un río medieval"
   - HeyGen: Requiere avatar_id y voice_id (usa list_avatars_tool y list_voices_tool primero)
   
   Parámetros opcionales:
   - service: 'gemini_veo' (default), 'sora', 'heygen', 'vuela_ai'
   - veo_model: Modelo de Veo (ej: 'veo-2.0-generate-001', 'veo-3.0-generate-001')
   - duration: Duración en segundos (5-8s para Veo 2.0, 4-8s para Veo 3.0, 4/8/12s para Sora)
   - aspect_ratio: '16:9' o '9:16' (default: '16:9')

3. CITAS ANIMADAS: create_quote_tool - Genera videos animados de citas con texto y autor opcional
   - Ejemplo: "Crea un video de cita con el texto 'La estrategia no se diseña en un despacho' y autor 'David Barreiro'"
   - Ejemplo: "Genera una cita animada: 'Solo texto sin autor'"
   - Parámetros opcionales:
   - author: Nombre del autor (opcional)
   - duration: Duración en segundos (opcional, se calcula automáticamente)
   - quality: 'l' (baja), 'm' (media), 'h' (alta), 'k' (4K máxima, default)

4. LISTAR AVATARES: list_avatars_tool - Lista avatares disponibles de HeyGen
   - Ejemplo: "Dime 5 avatares mujeres que empiecen con la letra A"
   - Ejemplo: "Lista avatares masculinos"
   - Parámetros: gender ('male', 'female'), starts_with (letra/texto inicial), limit

5. LISTAR VOCES: list_voices_tool - Lista voces disponibles de HeyGen
   - Ejemplo: "Dame voces en español"
   - Ejemplo: "Lista voces femeninas"
   - Parámetros: gender ('male', 'female'), language (ej: 'es', 'en'), limit

INSTRUCCIONES:
- Siempre pasa user_id={user_id} a todas las tools
- Si el usuario pide crear un video con HeyGen pero no especifica avatar/voice, primero lista opciones
- Para videos con HeyGen, primero usa list_avatars_tool y list_voices_tool si no se proporcionan
- Si falta información, pregunta al usuario antes de crear
- Sé conciso pero amigable en tus respuestas
- Cuando listes avatares/voces, presenta la información de forma clara y útil

IMPORTANTE - REGLAS CRÍTICAS:
- SOLO ejecuta tools para crear el contenido que el usuario está pidiendo EN ESTE MENSAJE ACTUAL
- NO ejecutes tools para crear contenido mencionado en mensajes anteriores del historial
- El historial es solo para contexto conversacional, NO para recrear contenido anterior
- Si el usuario dice "crea X" y luego "crea Y", solo crea Y (no vuelvas a crear X)
- Cuando crees contenido, menciona SOLO lo que acabas de crear ahora, nunca menciones contenido anterior
- NO generes enlaces con el título (ej: NO uses "[Imagen: Un gato](url)")
- El sistema mostrará automáticamente un enlace "Ver imagen →" o "Ver video →" usando la URL correcta
- Solo menciona el título como texto normal, sin crear enlaces markdown""".format(user_id=self.user_id)
        
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
                logger.info(f"LLM quiere usar {len(tool_calls)} tool(s): {[tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None) for tc in tool_calls]}")
                
                # Agregar el mensaje del asistente con tool_calls SOLO UNA VEZ
                messages.append(response)
                
                # Ejecutar todas las tools y recopilar resultados
                tool_messages = []
                executed_tool_ids = set()  # Para evitar ejecuciones duplicadas
                executed_prompts = set()  # Para evitar crear el mismo contenido múltiples veces
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
                        # Obtener tool_call_id del tool_call para evitar duplicados
                        tool_call_id = None
                        if isinstance(tool_call, dict):
                            tool_call_id = tool_call.get('id') or tool_call.get('tool_call_id')
                        else:
                            tool_call_id = getattr(tool_call, 'id', None)
                        
                        # Evitar ejecutar la misma tool múltiples veces
                        if tool_call_id and tool_call_id in executed_tool_ids:
                            logger.warning(f"Tool {tool_name} con ID {tool_call_id} ya fue ejecutada, saltando duplicado")
                            continue
                        
                        # Para create_image_tool, evitar crear el mismo prompt múltiples veces
                        if tool_name == 'create_image_tool' and 'prompt' in tool_args:
                            prompt_key = tool_args.get('prompt', '').strip().lower()[:100]  # Primeros 100 chars normalizados
                            if prompt_key in executed_prompts:
                                logger.warning(f"Prompt '{prompt_key[:50]}...' ya fue ejecutado en esta interacción, saltando duplicado")
                                continue
                            executed_prompts.add(prompt_key)
                        
                        try:
                            logger.info(f"Ejecutando tool: {tool_name} con args: {tool_args}")
                            tool_result = tool_func.invoke(tool_args)
                            tool_results.append((tool_name, tool_result))
                            logger.info(f"Tool {tool_name} ejecutada exitosamente. Resultado: {tool_result.get('status') if isinstance(tool_result, dict) else 'OK'}")
                            
                            # Marcar como ejecutada
                            if tool_call_id:
                                executed_tool_ids.add(tool_call_id)
                            
                            # Crear ToolMessage con el resultado
                            tool_result_str = json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                            tool_message = ToolMessage(
                                content=tool_result_str,
                                tool_call_id=tool_call_id or f"call_{tool_name}_{len(tool_messages)}"
                            )
                            tool_messages.append(tool_message)
                        except Exception as e:
                            logger.error(f"Error ejecutando tool {tool_name}: {e}", exc_info=True)
                            # Agregar mensaje de error como ToolMessage
                            error_message = ToolMessage(
                                content=json.dumps({'error': f'Error al ejecutar {tool_name}: {str(e)}'}),
                                tool_call_id=getattr(tool_call, 'id', None) if not isinstance(tool_call, dict) else tool_call.get('id', f"call_{tool_name}")
                            )
                            tool_messages.append(error_message)
                    else:
                        logger.warning(f"No se encontró la herramienta: {tool_name}")
                
                # Agregar todos los ToolMessages al historial
                messages.extend(tool_messages)
                
                # Invocar LLM UNA SOLA VEZ con todos los resultados de las tools
                final_response = self.llm_with_tools.invoke(messages)
                
                # Verificar si el LLM quiere usar más tools después de recibir los resultados
                # Si es así, solo usar la respuesta de texto, no ejecutar más tools
                final_tool_calls = None
                if hasattr(final_response, 'tool_calls'):
                    final_tool_calls = final_response.tool_calls
                elif hasattr(final_response, 'additional_kwargs'):
                    final_tool_calls = final_response.additional_kwargs.get('tool_calls', [])
                
                if final_tool_calls:
                    # El LLM quiere usar más tools, pero ya ejecutamos las que pidió
                    # Solo usar su respuesta de texto si la tiene
                    logger.warning(f"LLM intentó usar más tools después de recibir resultados. Ignorando tool_calls adicionales.")
                    if hasattr(final_response, 'content') and final_response.content:
                        answer = final_response.content
                    else:
                        # Si no hay contenido, generar respuesta basada en los tool_results
                        answer = "He completado tu solicitud."
                else:
                    answer = final_response.content if hasattr(final_response, 'content') else str(final_response)
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

