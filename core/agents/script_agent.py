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
from core.agents.tools import (
    validate_all_scenes_durations,
    validate_json_structure,
    auto_correct_all_scenes,
    validate_platform_avatar_consistency
)

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
        logger.info(f"Analizando guión (duración: {state['duration_min']} min)")
        
        # Crear mensajes
        messages = self.prompt_template.format_messages(
            duracion_minutos=state['duration_min'],
            guion=state['script_text']
        )
        
        # Invocar LLM
        try:
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
            
            logger.info(f"Respuesta recibida del LLM ({len(response_text)} caracteres)")
            
        except Exception as e:
            logger.error(f"Error al invocar LLM: {e}")
            raise
        
        return state
    
    def _parse_response_node(self, state: AgentState) -> AgentState:
        """Nodo: Parsea la respuesta JSON del LLM"""
        logger.info("Parseando respuesta JSON")
        
        response_text = state['llm_response']
        
        # Intentar extraer JSON si está envuelto en markdown
        json_text = self._extract_json_from_response(response_text)
        
        try:
            parsed = json.loads(json_text)
            state['parsed_json'] = parsed
            logger.info(f"JSON parseado exitosamente ({len(parsed.get('scenes', []))} escenas)")
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}")
            logger.error(f"Respuesta recibida: {response_text[:500]}...")
            raise ValueError(f"Respuesta del LLM no es JSON válido: {str(e)}")
        
        return state
    
    def _validate_output_node(self, state: AgentState) -> AgentState:
        """Nodo: Valida la estructura y duraciones"""
        logger.info("Validando salida")
        
        parsed = state['parsed_json']
        errors = []
        
        # Validar estructura JSON
        structure_validation = validate_json_structure.invoke({'data': parsed})
        if not structure_validation['valid']:
            errors.extend(structure_validation['errors'])
            logger.warning(f"Errores de estructura: {structure_validation['errors']}")
        
        # Validar duraciones
        scenes = parsed.get('scenes', [])
        if scenes:
            duration_validation = validate_all_scenes_durations.invoke({'scenes': scenes})
            if not duration_validation['all_valid']:
                errors.extend(duration_validation['errors'])
                logger.warning(f"Errores de duración: {duration_validation['errors']}")
            
            # Validar consistencia platform/avatar
            consistency_validation = validate_platform_avatar_consistency.invoke({'scenes': scenes})
            if not consistency_validation['valid']:
                errors.extend(consistency_validation['errors'])
                logger.warning(f"Errores de consistencia: {consistency_validation['errors']}")
        
        state['validation_errors'] = errors
        
        return state
    
    def _should_correct(self, state: AgentState) -> str:
        """Decide si necesita corrección automática"""
        if len(state['validation_errors']) > 0:
            logger.info(f"Errores encontrados, aplicando corrección automática")
            return "correct"
        return "continue"
    
    def _auto_correct_node(self, state: AgentState) -> AgentState:
        """Nodo: Corrige errores automáticamente"""
        logger.info("Aplicando corrección automática")
        
        parsed = state['parsed_json']
        scenes = parsed.get('scenes', [])
        
        if scenes:
            correction_result = auto_correct_all_scenes.invoke({'scenes': scenes})
            parsed['scenes'] = correction_result['corrected_scenes']
            
            corrections = []
            for scene_idx, scene in enumerate(correction_result['corrected_scenes']):
                # Las correcciones ya están aplicadas en las escenas
                pass
            
            state['parsed_json'] = parsed
            state['corrections_applied'] = corrections
            logger.info(f"Correcciones aplicadas: {correction_result['total_corrections']}")
        
        return state
    
    def _format_output_node(self, state: AgentState) -> AgentState:
        """Nodo: Formatea la salida final"""
        logger.info("Formateando salida final")
        
        parsed = state['parsed_json']
        
        # Asegurar formato compatible con n8n
        formatted = {
            'status': 'success',
            'project': parsed.get('project', {}),
            'characters': parsed.get('characters', []),
            'scenes': parsed.get('scenes', [])
        }
        
        state['final_output'] = formatted
        
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
        logger.info(f"Procesando guión (ID: {script_id}, duración: {duration_min} min)")
        
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
                result = self.agent_executor.invoke(initial_state)
                
                if result.get('final_output'):
                    logger.info(f"✓ Guión procesado exitosamente (intento {attempt + 1})")
                    
                    # Agregar métricas a la salida
                    output = result['final_output'].copy()
                    output['_metrics'] = result.get('metrics', {})
                    output['_corrections'] = result.get('corrections_applied', [])
                    
                    return output
                else:
                    raise ValueError("El agente no generó salida final")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Intento {attempt + 1} falló: {e}")
                if attempt < self.max_retries:
                    logger.info(f"Reintentando... ({attempt + 1}/{self.max_retries})")
                else:
                    logger.error(f"Todos los intentos fallaron")
        
        # Si llegamos aquí, todos los intentos fallaron
        raise ValueError(f"Error al procesar guión después de {self.max_retries + 1} intentos: {str(last_error)}")

