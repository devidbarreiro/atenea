"""
Production House - Orquestador de múltiples agentes especializados
Coordina el trabajo de todos los agentes sobre un estado compartido
"""

import logging
from typing import Dict, Any, Optional
from core.agents.production_house.shared_state import SharedState
from core.agents.production_house.scriptwriter_agent import ScriptWriterAgent
from core.agents.production_house.director_agent import DirectorAgent
from core.agents.production_house.producer_agent import ProducerAgent
from core.agents.production_house.continuity_agent import ContinuityAgent
from core.agents.production_house.quality_agent import QualityAgent
from core.agents.production_house.corrector_agent import CorrectorAgent

logger = logging.getLogger(__name__)


class ProductionHouse:
    """
    Orquestador de múltiples agentes especializados.
    Coordina el flujo de trabajo como una productora de cine real.
    """
    
    def __init__(
        self,
        llm_provider: str = 'openai',
        use_expensive_models: bool = True
    ):
        """
        Inicializa la productora con todos los agentes.
        
        Args:
            llm_provider: Proveedor LLM ('openai' o 'gemini')
            use_expensive_models: Si usar modelos caros (GPT-4) o baratos (GPT-3.5)
        """
        self.llm_provider = llm_provider
        
        # Determinar modelos según configuración
        if use_expensive_models:
            creative_model = 'gpt-4'  # Para creatividad
            analysis_model = 'gpt-3.5-turbo'  # Para análisis
        else:
            creative_model = 'gpt-3.5-turbo'
            analysis_model = 'gpt-3.5-turbo'
        
        # Inicializar agentes
        self.scriptwriter = ScriptWriterAgent(
            llm_provider=llm_provider,
            llm_model=creative_model
        )
        
        self.director = DirectorAgent(
            llm_provider=llm_provider,
            llm_model=creative_model
        )
        
        self.producer = ProducerAgent(
            llm_provider=llm_provider,
            llm_model=analysis_model
        )
        
        self.continuity = ContinuityAgent(
            llm_provider=llm_provider,
            llm_model=analysis_model
        )
        
        self.quality = QualityAgent()  # No usa LLM
        
        self.corrector = CorrectorAgent(
            llm_provider=llm_provider,
            llm_model=analysis_model
        )
        
        logger.info(f"ProductionHouse inicializada (provider: {llm_provider}, expensive: {use_expensive_models})")
    
    def process_script(
        self,
        script_id: int,
        script_text: str,
        duration_min: float,
        duration_seconds: int,
        video_format: str,
        video_type: str,
        video_orientation: str = '16:9'
    ) -> Dict[str, Any]:
        """
        Procesa un guión completo usando todos los agentes.
        
        Args:
            script_id: ID del script en BD
            script_text: Texto del guión
            duration_min: Duración deseada en minutos
            duration_seconds: Duración deseada en segundos
            video_format: 'social', 'educational', 'longform'
            video_type: 'ultra', 'avatar', 'general'
            video_orientation: '16:9' o '9:16'
            
        Returns:
            Dict con el resultado procesado (compatible con formato actual)
        """
        # Inicializar estado compartido
        state = SharedState(
            script_id=script_id,
            script_text=script_text,
            duration_min=duration_min,
            duration_seconds=duration_seconds,
            video_format=video_format,
            video_type=video_type,
            video_orientation=video_orientation
        )
        
        logger.info(f"🎬 ProductionHouse iniciando procesamiento de script {script_id}")
        
        max_iterations = 3  # Máximo de iteraciones de corrección
        
        try:
            # FASE 1: ScriptWriter - Estructura narrativa
            logger.info("📝 Fase 1: ScriptWriter - Creando estructura narrativa")
            state = self.scriptwriter.process(state)
            
            if not state.scenes:
                raise ValueError("ScriptWriter no generó escenas")
            
            # FASE 2: Director - Visión visual
            logger.info("🎥 Fase 2: Director - Añadiendo visión visual")
            state = self.director.process(state)
            
            # FASE 3: Producer - Optimización de recursos
            logger.info("💰 Fase 3: Producer - Optimizando recursos y sincronización")
            state = self.producer.process(state)
            
            # FASE 4: Continuity - Continuidad cinematográfica
            logger.info("🎬 Fase 4: Continuity - Analizando continuidad")
            state = self.continuity.process(state)
            
            # FASE 5: Quality - Validación
            logger.info("✅ Fase 5: Quality - Validando calidad")
            state = self.quality.process(state)
            
            # FASE 6: Corrector - Correcciones iterativas
            iteration = 0
            while iteration < max_iterations:
                validation = state.validation
                if not validation or not validation.get('critical_errors'):
                    logger.info("✅ No hay errores críticos, proceso completado")
                    break
                
                iteration += 1
                logger.info(f"🔧 Fase 6 (Iteración {iteration}): Corrector - Corrigiendo errores")
                state = self.corrector.process(state)
                
                # Re-validar después de correcciones
                logger.info("✅ Re-validando después de correcciones")
                state = self.quality.process(state)
            
            if iteration >= max_iterations:
                validation = state.validation or {}
                if validation.get('critical_errors'):
                    logger.warning(f"⚠️ Máximo de iteraciones alcanzado ({max_iterations}), continuando con errores")
            
            # Convertir estado a formato compatible con el sistema actual
            result = self._format_output(state)
            
            logger.info(f"✅ ProductionHouse completó procesamiento de script {script_id}")
            logger.info(f"   Escenas generadas: {len(state.scenes)}")
            logger.info(f"   Errores: {len(state.validation.get('errors', []))}")
            logger.info(f"   Advertencias: {len(state.validation.get('warnings', []))}")
            logger.info(f"   Score de calidad: {state.validation.get('quality_score', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en ProductionHouse: {e}", exc_info=True)
            state.add_log("ProductionHouse", f"Error: {str(e)}")
            raise
    
    def _format_output(self, state: SharedState) -> Dict[str, Any]:
        """
        Convierte el estado compartido al formato esperado por el sistema actual.
        Asegura compatibilidad con create_scenes_from_n8n_data.
        """
        # Calcular duración total estimada
        total_duration_sec = sum(scene.get('duration_sec', 0) for scene in state.scenes)
        total_duration_min = total_duration_sec / 60
        
        # Formatear escenas para compatibilidad con create_scenes_from_n8n_data
        formatted_scenes = []
        for scene in state.scenes:
            # Asegurar campos requeridos por create_scenes_from_n8n_data
            formatted_scene = {
                'id': scene.get('id', scene.get('scene_id', '')),
                'scene_id': scene.get('scene_id', scene.get('id', '')),
                'summary': scene.get('summary', ''),
                'script_text': scene.get('script_text', ''),
                'duration_sec': scene.get('duration_sec', 8),
                'visual_prompt': scene.get('visual_prompt', ''),
                'platform': scene.get('ai_service', scene.get('platform', 'gemini_veo')),
                'avatar': 'si' if scene.get('ai_service', '').startswith('heygen') else 'no'
            }
            
            # Añadir campos adicionales si existen
            if 'continuity_context' in scene:
                formatted_scene['continuity_context'] = scene['continuity_context']
            
            # Añadir metadata si existe
            if 'metadata' in scene:
                formatted_scene['metadata'] = scene['metadata']
            
            formatted_scenes.append(formatted_scene)
        
        # Formato compatible con el sistema actual
        result = {
            'project': {
                'platform_mode': state.video_type,
                'num_scenes': len(state.scenes),
                'language': 'es',  # Por defecto español
                'total_estimated_duration_min': f"{total_duration_min:.2f}"
            },
            'scenes': formatted_scenes,
            'characters': [],  # Se puede extraer después si es necesario
            '_metrics': {
                'provider': self.llm_provider,
                'model': 'production-house',
                'input_tokens': 0,  # Se puede calcular si es necesario
                'output_tokens': 0,
                'agents_used': list(state.metrics.keys()),
                'quality_score': state.validation.get('quality_score', 0)
            },
            '_production_house_state': state.to_dict()  # Estado completo para debugging
        }
        
        return result

