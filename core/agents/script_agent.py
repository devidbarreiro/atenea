"""
Script Agent con LangGraph
Reemplaza el workflow de n8n para análisis de guiones
"""

import json
import logging
from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage

from core.llm.factory import LLMFactory
from core.agents.prompts.script_analysis_prompt import get_script_analysis_prompt
from core.agents.tools.duration_validator import validate_all_scenes_durations
from core.agents.tools.json_validator import validate_json_structure
from core.agents.tools.auto_corrector import auto_correct_all_scenes
from core.agents.tools.platform_selector import validate_platform_avatar_consistency

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Estado del agente durante el procesamiento"""
    script_text: str
    duration_min: int
    llm_response: str
    parsed_json: Dict[str, Any]
    validation_errors: List[str]
    corrections_applied: List[str]
    final_output: Dict[str, Any]
    metrics: Dict[str, Any]


class ScriptAgent:
    """
    Agente LangGraph para procesar guiones y generar escenas.
    Reemplaza completamente el workflow de n8n.
    """
    
    def __init__(
        self,
        llm_provider: str = 'openai',
        llm_model: str = None,
        temperature: float = 0.7,
        max_retries: int = 2
    ):
        """
        Inicializa el agente
        
        Args:
            llm_provider: 'openai' o 'gemini'
            llm_model: Nombre del modelo específico (opcional)
            temperature: Temperatura para sampling
            max_retries: Número máximo de reintentos
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Crear LLM
        self.llm = LLMFactory.get_llm(
            provider=llm_provider,
            model_name=llm_model,
            temperature=temperature
        )
        
        # Crear prompt template
        self.prompt_template = get_script_analysis_prompt()
        
        # Crear grafo LangGraph
        self.graph = self._create_graph()
        self.agent_executor = self.graph.compile()
        
        logger.info(f"ScriptAgent inicializado con {llm_provider}/{llm_model or 'default'}")
    
    def _create_graph(self) -> StateGraph:
        """Crea el grafo LangGraph con los nodos de procesamiento"""
        
        workflow = StateGraph(AgentState)
        
        # Agregar nodos
        workflow.add_node("analyze_script", self._analyze_script_node)
        workflow.add_node("parse_response", self._parse_response_node)
        workflow.add_node("validate_output", self._validate_output_node)
        workflow.add_node("auto_correct", self._auto_correct_node)
        workflow.add_node("format_output", self._format_output_node)
        
        # Definir flujo
        workflow.set_entry_point("analyze_script")
        workflow.add_edge("analyze_script", "parse_response")
        workflow.add_edge("parse_response", "validate_output")
        workflow.add_conditional_edges(
            "validate_output",
            self._should_correct,
            {
                "correct": "auto_correct",
                "continue": "format_output"
            }
        )
        workflow.add_edge("auto_correct", "validate_output")  # Re-validar después de corregir
        workflow.add_edge("format_output", END)
        
        return workflow
    
    def _analyze_script_node(self, state: AgentState) -> AgentState:
        """Nodo: Analiza el guión con el LLM"""
        logger.info("🔵 [NODO] analyze_script - Iniciando análisis del guión")
        logger.info(f"   Duración: {state['duration_min']} min")
        logger.info(f"   Texto: {len(state['script_text'])} caracteres")
        
        # Crear mensajes
        messages = self.prompt_template.format_messages(
            duracion_minutos=state['duration_min'],
            guion=state['script_text']
        )
        
        # Invocar LLM
        try:
            logger.debug(f"📤 Invocando LLM ({self.llm_provider}/{self.llm_model or 'default'})")
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Trackear métricas
            input_tokens = self._estimate_tokens(state['script_text'])
            output_tokens = self._estimate_tokens(response_text)
            
            state['llm_response'] = response_text
            state['metrics'] = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'provider': self.llm_provider,
                'model': self.llm_model or 'default'
            }
            
            logger.info(f"✅ [NODO] analyze_script - Completado")
            logger.info(f"   Respuesta: {len(response_text)} caracteres")
            logger.info(f"   Tokens: {input_tokens} input + {output_tokens} output")
            
        except Exception as e:
            logger.error(f"❌ [NODO] analyze_script - Error: {e}")
            raise
        
        return state
    
    def _parse_response_node(self, state: AgentState) -> AgentState:
        """Nodo: Parsea la respuesta JSON del LLM"""
        logger.info("🔵 [NODO] parse_response - Parseando respuesta JSON")
        
        response_text = state['llm_response']
        
        # Intentar extraer JSON si está envuelto en markdown
        json_text = self._extract_json_from_response(response_text)
        
        try:
            parsed = json.loads(json_text)
            state['parsed_json'] = parsed
            scenes_count = len(parsed.get('scenes', []))
            logger.info(f"✅ [NODO] parse_response - Completado")
            logger.info(f"   Escenas encontradas: {scenes_count}")
            logger.info(f"   Project mode: {parsed.get('project', {}).get('platform_mode', 'N/A')}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ [NODO] parse_response - Error al parsear JSON")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Respuesta recibida (primeros 500 chars): {response_text[:500]}...")
            raise ValueError(f"Respuesta del LLM no es JSON válido: {str(e)}")
        
        return state
    
    def _validate_output_node(self, state: AgentState) -> AgentState:
        """Nodo: Valida la estructura y duraciones"""
        logger.info("🔵 [NODO] validate_output - Validando salida")
        
        parsed = state['parsed_json']
        errors = []
        
        # Validar estructura JSON
        structure_validation = validate_json_structure.invoke({'data': parsed})
        if not structure_validation['valid']:
            errors.extend(structure_validation['errors'])
            logger.warning(f"⚠️  Errores de estructura: {len(structure_validation['errors'])}")
            for error in structure_validation['errors'][:3]:  # Mostrar primeros 3
                logger.warning(f"   - {error}")
        else:
            logger.debug("✅ Estructura JSON válida")
        
        # Validar duraciones
        scenes = parsed.get('scenes', [])
        if scenes:
            duration_validation = validate_all_scenes_durations.invoke({'scenes': scenes})
            if not duration_validation['all_valid']:
                errors.extend(duration_validation['errors'])
                logger.warning(f"⚠️  Errores de duración: {len(duration_validation['errors'])}")
                for error in duration_validation['errors'][:3]:
                    logger.warning(f"   - {error}")
            else:
                logger.debug("✅ Duraciones válidas")
            
            # Validar consistencia platform/avatar
            consistency_validation = validate_platform_avatar_consistency.invoke({'scenes': scenes})
            if not consistency_validation['valid']:
                errors.extend(consistency_validation['errors'])
                logger.warning(f"⚠️  Errores de consistencia: {len(consistency_validation['errors'])}")
            else:
                logger.debug("✅ Consistencia platform/avatar válida")
        
        state['validation_errors'] = errors
        
        if errors:
            logger.warning(f"❌ [NODO] validate_output - {len(errors)} errores encontrados")
        else:
            logger.info(f"✅ [NODO] validate_output - Validación exitosa")
        
        return state
    
    def _should_correct(self, state: AgentState) -> str:
        """Decide si necesita corrección automática"""
        if len(state['validation_errors']) > 0:
            logger.info(f"Errores encontrados, aplicando corrección automática")
            return "correct"
        return "continue"
    
    def _auto_correct_node(self, state: AgentState) -> AgentState:
        """Nodo: Corrige errores automáticamente"""
        logger.info("🔵 [NODO] auto_correct - Aplicando corrección automática")
        
        parsed = state['parsed_json']
        scenes = parsed.get('scenes', [])
        
        if scenes:
            correction_result = auto_correct_all_scenes.invoke({'scenes': scenes})
            parsed['scenes'] = correction_result['corrected_scenes']
            
            # Obtener correcciones detalladas del resultado
            corrections = correction_result.get('all_corrections', [])
            total_corrections = correction_result['total_corrections']
            
            state['parsed_json'] = parsed
            state['corrections_applied'] = corrections
            
            if total_corrections > 0:
                logger.info(f"✅ [NODO] auto_correct - {total_corrections} correcciones aplicadas")
            else:
                logger.info(f"✅ [NODO] auto_correct - No se requirieron correcciones")
        
        return state
    
    def _format_output_node(self, state: AgentState) -> AgentState:
        """Nodo: Formatea la salida final"""
        logger.info("🔵 [NODO] format_output - Formateando salida final")
        
        parsed = state['parsed_json']
        
        # Asegurar formato compatible con n8n
        formatted = {
            'status': 'success',
            'project': parsed.get('project', {}),
            'characters': parsed.get('characters', []),
            'scenes': parsed.get('scenes', [])
        }
        
        state['final_output'] = formatted
        
        scenes_count = len(formatted.get('scenes', []))
        logger.info(f"✅ [NODO] format_output - Completado")
        logger.info(f"   Escenas finales: {scenes_count}")
        logger.info(f"   Personajes: {len(formatted.get('characters', []))}")
        
        return state
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extrae JSON de la respuesta, incluso si está envuelto en markdown"""
        # Intentar parsear directamente
        try:
            json.loads(response_text)
            return response_text
        except:
            pass
        
        # Buscar JSON en bloques de código
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Buscar JSON entre llaves
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        return response_text
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima número de tokens (aproximación: 1 token ≈ 4 caracteres)"""
        return len(text) // 4
    
    def process_script(
        self,
        script_text: str,
        duration_min: int,
        script_id: int = None
    ) -> Dict[str, Any]:
        """
        Procesa un guión y retorna escenas estructuradas.
        
        Args:
            script_text: Texto del guión
            duration_min: Duración deseada en minutos
            script_id: ID del script (opcional, para logging)
            
        Returns:
            Dict con estructura compatible con n8n:
            {
                'status': 'success',
                'project': {...},
                'characters': [...],
                'scenes': [...]
            }
            
        Raises:
            ValueError: Si el procesamiento falla después de todos los reintentos
        """
        logger.info("=" * 80)
        logger.info(f"🚀 INICIANDO PROCESAMIENTO DE GUION")
        logger.info(f"   Script ID: {script_id}")
        logger.info(f"   Duración: {duration_min} min")
        logger.info(f"   Proveedor LLM: {self.llm_provider}")
        logger.info(f"   Modelo: {self.llm_model or 'default'}")
        logger.info("=" * 80)
        
        # Estado inicial
        initial_state: AgentState = {
            'script_text': script_text,
            'duration_min': duration_min,
            'llm_response': '',
            'parsed_json': {},
            'validation_errors': [],
            'corrections_applied': [],
            'final_output': {},
            'metrics': {}
        }
        
        # Ejecutar agente con reintentos
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔄 Intento {attempt + 1}/{self.max_retries + 1}")
                result = self.agent_executor.invoke(initial_state)
                
                if result.get('final_output'):
                    scenes_count = len(result['final_output'].get('scenes', []))
                    metrics = result.get('metrics', {})
                    
                    logger.info("=" * 80)
                    logger.info(f"✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
                    logger.info(f"   Escenas generadas: {scenes_count}")
                    logger.info(f"   Tokens usados: {metrics.get('input_tokens', 0)} + {metrics.get('output_tokens', 0)}")
                    logger.info(f"   Intento: {attempt + 1}")
                    logger.info("=" * 80)
                    
                    # Agregar métricas a la salida
                    output = result['final_output'].copy()
                    output['_metrics'] = metrics
                    output['_corrections'] = result.get('corrections_applied', [])
                    
                    return output
                else:
                    raise ValueError("El agente no generó salida final")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  Intento {attempt + 1} falló: {e}")
                if attempt < self.max_retries:
                    logger.info(f"🔄 Reintentando... ({attempt + 1}/{self.max_retries})")
                else:
                    logger.error(f"❌ Todos los intentos fallaron")
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error("=" * 80)
        logger.error(f"❌ ERROR FINAL: No se pudo procesar después de {self.max_retries + 1} intentos")
        logger.error(f"   Último error: {str(last_error)}")
        logger.error("=" * 80)
        raise ValueError(f"Error al procesar guión después de {self.max_retries + 1} intentos: {str(last_error)}")


# ====================
# FACTORY FUNCTION PARA LANGGRAPH STUDIO
# ====================

def create_script_agent_graph():
    """
    Factory function para crear el grafo del agente.
    Usado por LangGraph Studio para visualización.
    
    Returns:
        StateGraph: Grafo SIN compilar (Studio lo compila internamente)
    """
    import os
    import sys
    
    # Configurar Django
    if 'django' not in sys.modules or not sys.modules.get('django').conf.settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
        import django
        django.setup()
    
    try:
        # Crear el agente
        agent = ScriptAgent(
            llm_provider='openai',
            llm_model=None,
            temperature=0.7,
            max_retries=2
        )
        
        # Devolver grafo SIN compilar
        # LangGraph Studio lo compila internamente para visualización
        return agent.graph
        
    except Exception as e:
        # Loguear el error para debugging
        import traceback
        logger.error(f"Error en create_script_agent_graph: {e}")
        logger.error(traceback.format_exc())
        raise

