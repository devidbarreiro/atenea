"""
Script Agent con LangGraph
Reemplaza el workflow de n8n para análisis de guiones
"""

# IMPORTANTE: Configurar Django ANTES de cualquier import que use Django
from core.agents._django_setup import setup_django
setup_django()

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
from core.agents.tools.word_counter import validate_text_length_for_duration, count_words

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Estado del agente durante el procesamiento"""
    script_text: str
    duration_min: float  # Puede ser decimal (ej: 1.5 para 1 min 30 seg)
    duration_seconds: int  # Duración total en segundos
    video_format: str
    video_type: str  # 'ultra', 'avatar', 'general'
    llm_response: str
    parsed_json: Dict[str, Any]
    validation_errors: List[str]
    corrections_applied: List[str]
    correction_attempts: int  # Contador de intentos de corrección
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
        logger.info(f"   Tipo: {state.get('video_type', 'general')}")
        logger.info(f"   Formato: {state.get('video_format', 'educational')}")
        logger.info(f"   Texto: {len(state['script_text'])} caracteres")
        
        # Calcular duración en segundos
        duration_min = state['duration_min']
        duration_seconds = state.get('duration_seconds', int(duration_min * 60))
        
        # Crear mensajes
        messages = self.prompt_template.format_messages(
            duracion_minutos=f"{duration_min:.2f}",  # Formato con 2 decimales
            duracion_segundos=str(duration_seconds),
            guion=state['script_text'],
            formato_video=state.get('video_format', 'educational'),
            tipo_video=state.get('video_type', 'general')
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
            
            # Validar tipo de video
            video_type = state.get('video_type', 'general')
            video_type_errors = self._validate_video_type(scenes, video_type)
            if video_type_errors:
                errors.extend(video_type_errors)
                logger.warning(f"⚠️  Errores de tipo de video: {len(video_type_errors)}")
                for error in video_type_errors[:3]:
                    logger.warning(f"   - {error}")
            else:
                logger.debug(f"✅ Tipo de video '{video_type}' respetado")
            
            # Validar longitud de texto vs duración (REGLA DE ORO)
            text_length_errors = self._validate_text_length_for_scenes(scenes)
            if text_length_errors:
                errors.extend(text_length_errors)
                logger.warning(f"⚠️  Errores de longitud de texto: {len(text_length_errors)}")
                for error in text_length_errors[:3]:
                    logger.warning(f"   - {error}")
            else:
                logger.debug("✅ Longitud de texto válida para todas las escenas")
        
        state['validation_errors'] = errors
        
        if errors:
            logger.warning(f"❌ [NODO] validate_output - {len(errors)} errores encontrados")
        else:
            logger.info(f"✅ [NODO] validate_output - Validación exitosa")
        
        return state
    
    def _validate_video_type(self, scenes: List[Dict], video_type: str) -> List[str]:
        """
        Valida que las escenas respeten el tipo de video seleccionado
        
        Args:
            scenes: Lista de escenas
            video_type: Tipo de video ('ultra', 'avatar', 'general')
        
        Returns:
            Lista de errores encontrados
        """
        errors = []
        
        if video_type == 'ultra':
            # Modo Ultra: PROHIBIDO HeyGen
            heygen_scenes = [s for s in scenes if s.get('platform', '').lower() == 'heygen']
            if heygen_scenes:
                errors.append(
                    f"Tipo 'ultra' no permite HeyGen. "
                    f"Encontradas {len(heygen_scenes)} escenas con HeyGen. "
                    f"Usa solo 'gemini_veo' o 'sora'."
                )
            
            # Verificar que todas las escenas tengan avatar: "no"
            avatar_scenes = [s for s in scenes if s.get('avatar', '').lower() == 'si']
            if avatar_scenes:
                errors.append(
                    f"Tipo 'ultra' requiere todas las escenas con avatar: 'no'. "
                    f"Encontradas {len(avatar_scenes)} escenas con avatar: 'si'."
                )
        
        elif video_type == 'avatar':
            # Con Avatares: Al menos 70% debe ser HeyGen
            total_scenes = len(scenes)
            if total_scenes > 0:
                heygen_scenes = [s for s in scenes if s.get('platform', '').lower() == 'heygen']
                heygen_percentage = (len(heygen_scenes) / total_scenes) * 100
                
                if heygen_percentage < 70:
                    errors.append(
                        f"Tipo 'avatar' requiere al menos 70% de escenas con HeyGen. "
                        f"Actual: {heygen_percentage:.1f}% ({len(heygen_scenes)}/{total_scenes} escenas)."
                    )
        
        # 'general' no tiene restricciones específicas
        
        return errors
    
    def _validate_text_length_for_scenes(self, scenes: List[Dict]) -> List[str]:
        """
        Valida que cada escena tenga el número correcto de palabras según su duración.
        REGLA DE ORO: El guión no debe superar el tiempo de video.
        
        Args:
            scenes: Lista de escenas
        
        Returns:
            Lista de errores encontrados
        """
        errors = []
        
        for idx, scene in enumerate(scenes):
            script_text = scene.get('script_text', '')
            duration_sec = scene.get('duration_sec')
            scene_id = scene.get('id', f'Escena {idx + 1}')
            
            if not script_text:
                errors.append(f"{scene_id}: script_text está vacío")
                continue
            
            if duration_sec is None:
                errors.append(f"{scene_id}: duration_sec faltante")
                continue
            
            # Validar longitud de texto
            validation_result = validate_text_length_for_duration.invoke({
                'text': script_text,
                'duration_sec': duration_sec
            })
            
            if not validation_result['valid']:
                word_count = validation_result['word_count']
                min_words, max_words = validation_result['expected_range']
                
                if word_count > max_words:
                    # Texto demasiado largo - CRÍTICO
                    errors.append(
                        f"{scene_id}: Texto demasiado largo ({word_count} palabras para {duration_sec}s). "
                        f"Esperado: {min_words}-{max_words} palabras. "
                        f"El guión supera el tiempo de video disponible."
                    )
                elif word_count < min_words:
                    # Texto demasiado corto - advertencia menor
                    errors.append(
                        f"{scene_id}: Texto muy corto ({word_count} palabras para {duration_sec}s). "
                        f"Esperado: {min_words}-{max_words} palabras."
                    )
        
        return errors
    
    def _should_correct(self, state: AgentState) -> str:
        """Decide si necesita corrección automática"""
        MAX_CORRECTION_ATTEMPTS = 3  # Límite de intentos de corrección
        
        errors = state.get('validation_errors', [])
        attempts = state.get('correction_attempts', 0)
        
        # Si hay errores y no hemos excedido el límite de intentos
        if len(errors) > 0 and attempts < MAX_CORRECTION_ATTEMPTS:
            # Filtrar errores críticos vs advertencias
            critical_errors = self._filter_critical_errors(errors)
            
            if len(critical_errors) > 0:
                logger.info(f"Errores críticos encontrados ({len(critical_errors)}/{len(errors)}), aplicando corrección automática (intento {attempts + 1}/{MAX_CORRECTION_ATTEMPTS})")
                return "correct"
            else:
                # Solo advertencias, continuar sin corregir
                logger.info(f"Solo advertencias encontradas ({len(errors)}), continuando sin corrección")
                return "continue"
        elif len(errors) > 0 and attempts >= MAX_CORRECTION_ATTEMPTS:
            # Límite alcanzado, continuar con advertencias
            logger.warning(f"Límite de correcciones alcanzado ({MAX_CORRECTION_ATTEMPTS}), continuando con errores")
            return "continue"
        
        return "continue"
    
    def _filter_critical_errors(self, errors: List[str]) -> List[str]:
        """
        Filtra errores críticos que requieren corrección automática.
        Los errores de longitud de texto son críticos, pero algunos otros pueden ser advertencias.
        """
        critical = []
        warnings = []
        
        for error in errors:
            # Errores críticos que deben corregirse
            if any(keyword in error.lower() for keyword in [
                'texto demasiado largo',
                'texto muy largo',
                'supera el tiempo',
                'duración inválida',
                'platform',
                'avatar',
                'tipo de video',
                'estructura json',
                'duration_sec faltante'
            ]):
                critical.append(error)
            else:
                warnings.append(error)
        
        # Si hay errores críticos, retornar solo esos
        # Si solo hay advertencias, retornar vacío para continuar
        return critical
    
    def _auto_correct_node(self, state: AgentState) -> AgentState:
        """Nodo: Corrige errores automáticamente"""
        # Incrementar contador de intentos
        attempts = state.get('correction_attempts', 0) + 1
        state['correction_attempts'] = attempts
        
        logger.info(f"🔵 [NODO] auto_correct - Aplicando corrección automática (intento {attempts})")
        
        parsed = state['parsed_json']
        scenes = parsed.get('scenes', [])
        
        if scenes:
            # Intentar corregir errores de longitud de texto primero
            scenes = self._correct_text_length_errors(scenes)
            
            # Luego aplicar correcciones generales
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
    
    def _correct_text_length_errors(self, scenes: List[Dict]) -> List[Dict]:
        """
        Corrige errores de longitud de texto ajustando el texto a la duración.
        Si el texto es demasiado largo, lo trunca manteniendo el sentido.
        Si es demasiado corto, lo expande con información adicional.
        """
        corrected_scenes = []
        
        for scene in scenes:
            script_text = scene.get('script_text', '')
            duration_sec = scene.get('duration_sec')
            
            if not script_text or not duration_sec:
                corrected_scenes.append(scene)
                continue
            
            # Validar longitud
            validation = validate_text_length_for_duration.invoke({
                'text': script_text,
                'duration_sec': duration_sec
            })
            
            if validation['valid']:
                corrected_scenes.append(scene)
                continue
            
            word_count = validation['word_count']
            min_words, max_words = validation['expected_range']
            
            # Si el texto es demasiado largo, truncar
            if word_count > max_words:
                words = script_text.split()
                # Tomar aproximadamente max_words palabras, pero intentar mantener frases completas
                target_words = max_words
                truncated_words = words[:target_words]
                
                # Intentar mantener una frase completa (buscar punto, coma, etc.)
                truncated_text = ' '.join(truncated_words)
                if truncated_text and truncated_text[-1] not in '.!?':
                    # Buscar el último punto o coma
                    last_punctuation = max(
                        truncated_text.rfind('.'),
                        truncated_text.rfind(','),
                        truncated_text.rfind('!'),
                        truncated_text.rfind('?')
                    )
                    if last_punctuation > len(truncated_text) * 0.5:  # Si está en la segunda mitad
                        truncated_text = truncated_text[:last_punctuation + 1]
                
                scene['script_text'] = truncated_text
                logger.debug(f"Escena {scene.get('id', '?')}: Texto truncado de {word_count} a ~{len(truncated_text.split())} palabras")
            
            # Si el texto es demasiado corto, no hacemos nada (el auto_corrector puede manejar esto)
            # porque expandir texto requiere contexto del LLM
            
            corrected_scenes.append(scene)
        
        return corrected_scenes
    
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
        except (json.JSONDecodeError, TypeError, ValueError):
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
        duration_min: float,  # Ahora puede ser decimal (ej: 1.5 para 1 min 30 seg)
        script_id: int = None,
        video_format: str = 'educational',
        video_type: str = 'general',
        duration_seconds: int = None,  # Duración total en segundos (opcional, se calcula si no se proporciona)
        config: Dict[str, Any] = None  # Configuración de LangGraph (recursion_limit, etc.)
    ) -> Dict[str, Any]:
        """
        Procesa un guión y retorna escenas estructuradas.
        
        Args:
            script_text: Texto del guión
            duration_min: Duración deseada en minutos (puede ser decimal, ej: 1.5 para 1 min 30 seg)
            script_id: ID del script (opcional, para logging)
            video_format: Formato de video ('social', 'educational', 'longform')
            video_type: Tipo de video ('ultra', 'avatar', 'general')
            duration_seconds: Duración total en segundos (opcional, se calcula si no se proporciona)
            
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
        # Calcular duración total en segundos si no se proporciona
        if duration_seconds is None:
            duration_seconds = int(duration_min * 60)
        
        logger.info("=" * 80)
        logger.info(f"🚀 INICIANDO PROCESAMIENTO DE GUION")
        logger.info(f"   Script ID: {script_id}")
        logger.info(f"   Duración: {duration_min} min ({duration_seconds} seg)")
        logger.info(f"   Proveedor LLM: {self.llm_provider}")
        logger.info(f"   Modelo: {self.llm_model or 'default'}")
        logger.info("=" * 80)
        
        # Estado inicial
        initial_state: AgentState = {
            'script_text': script_text,
            'duration_min': duration_min,
            'duration_seconds': duration_seconds or int(duration_min * 60),
            'video_format': video_format,
            'video_type': video_type,
            'llm_response': '',
            'parsed_json': {},
            'validation_errors': [],
            'corrections_applied': [],
            'correction_attempts': 0,  # Inicializar contador
            'final_output': {},
            'metrics': {}
        }
        
        # Ejecutar agente con reintentos
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔄 Intento {attempt + 1}/{self.max_retries + 1}")
                # Usar configuración si se proporciona, sino usar valores por defecto
                graph_config = config or {"recursion_limit": 50}
                
                result = self.agent_executor.invoke(initial_state, config=graph_config)
                
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
    # Django ya está configurado por el import de _django_setup al inicio del módulo
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

