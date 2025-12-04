"""
Quality Agent - Especializado en validación y control de calidad
Responsabilidad: Validar todas las escenas y detectar problemas
"""

import logging
from typing import Dict, Any, List
from core.agents.production_house.base_agent import BaseAgent
from core.agents.production_house.shared_state import SharedState
from core.agents.tools.duration_validator import validate_all_scenes_durations
from core.agents.tools.word_counter import validate_text_length_for_duration
from core.agents.tools.platform_selector import validate_platform_avatar_consistency

logger = logging.getLogger(__name__)


class QualityAgent(BaseAgent):
    """
    Agente especializado en validación y control de calidad.
    No usa LLM, solo herramientas de validación locales (rápido y barato).
    """
    
    def __init__(self):
        super().__init__(
            name="Quality",
            llm_provider='openai',  # No se usa, pero necesario para BaseAgent
            llm_model=None,
            temperature=0.0
        )
    
    def process(self, state: SharedState) -> SharedState:
        """
        Valida todas las escenas y genera reporte de calidad.
        """
        self.log(state, f"Validando calidad de {len(state.scenes)} escenas")
        
        if not state.scenes:
            self.log(state, "No hay escenas para validar")
            state.validation = {
                'valid': False,
                'errors': ['No hay escenas para validar'],
                'warnings': []
            }
            return state
        
        errors = []
        warnings = []
        critical_errors = []
        
        # 1. Validar duraciones por plataforma
        try:
            duration_errors = validate_all_scenes_durations.invoke({
                'scenes': state.scenes
            })
            if duration_errors.get('errors'):
                errors.extend(duration_errors['errors'])
                critical_errors.extend(duration_errors['errors'])
        except Exception as e:
            self.log(state, f"Error validando duraciones: {e}")
            errors.append(f"Error validando duraciones: {str(e)}")
        
        # 2. Validar longitud de texto vs duración (REGLA DE ORO)
        for scene in state.scenes:
            scene_id = scene.get('id', 'unknown')
            script_text = scene.get('script_text', '')
            duration_sec = scene.get('duration_sec')
            
            if not script_text:
                errors.append(f"{scene_id}: script_text está vacío")
                critical_errors.append(f"{scene_id}: script_text está vacío")
                continue
            
            if duration_sec is None:
                errors.append(f"{scene_id}: duration_sec faltante")
                critical_errors.append(f"{scene_id}: duration_sec faltante")
                continue
            
            # Validar longitud de texto
            try:
                validation = validate_text_length_for_duration.invoke({
                    'text': script_text,
                    'duration_sec': duration_sec
                })
                
                if not validation['valid']:
                    word_count = validation['word_count']
                    min_words, max_words = validation['expected_range']
                    
                    if word_count > max_words:
                        error_msg = (
                            f"{scene_id}: Texto demasiado largo ({word_count} palabras para {duration_sec}s). "
                            f"Esperado: {min_words}-{max_words} palabras."
                        )
                        errors.append(error_msg)
                        critical_errors.append(error_msg)
                    elif word_count < min_words:
                        warning_msg = (
                            f"{scene_id}: Texto muy corto ({word_count} palabras para {duration_sec}s). "
                            f"Esperado: {min_words}-{max_words} palabras."
                        )
                        warnings.append(warning_msg)
            except Exception as e:
                self.log(state, f"Error validando longitud de texto para {scene_id}: {e}")
                warnings.append(f"{scene_id}: Error validando longitud de texto")
        
        # 3. Validar consistencia de plataforma/avatar
        try:
            platform_errors = validate_platform_avatar_consistency.invoke({
                'scenes': state.scenes,
                'video_type': state.video_type
            })
            if platform_errors.get('errors'):
                errors.extend(platform_errors['errors'])
                # No son críticos, solo advertencias
        except Exception as e:
            self.log(state, f"Error validando plataformas: {e}")
            warnings.append(f"Error validando consistencia de plataformas")
        
        # 4. Validar sincronización audio/video
        for scene in state.scenes:
            scene_id = scene.get('id', 'unknown')
            duration_sec = scene.get('duration_sec')
            metadata = scene.get('metadata', {})
            audio_duration = metadata.get('audio_duration_sec')
            
            if audio_duration and duration_sec:
                # Audio no debe exceder video (con margen del 10%)
                max_audio_duration = duration_sec * 1.1
                if audio_duration > max_audio_duration:
                    error_msg = (
                        f"{scene_id}: Audio demasiado largo ({audio_duration:.1f}s) para video "
                        f"({duration_sec}s). Máximo permitido: {max_audio_duration:.1f}s"
                    )
                    errors.append(error_msg)
                    critical_errors.append(error_msg)
                elif audio_duration < duration_sec * 0.8:
                    warning_msg = (
                        f"{scene_id}: Audio muy corto ({audio_duration:.1f}s) para video "
                        f"({duration_sec}s). Puede haber silencio al final."
                    )
                    warnings.append(warning_msg)
        
        # 5. Validar que todas las escenas tengan campos requeridos
        required_fields = ['id', 'script_text', 'visual_prompt', 'ai_service', 'duration_sec']
        for scene in state.scenes:
            scene_id = scene.get('id', 'unknown')
            for field in required_fields:
                if field not in scene or not scene[field]:
                    error_msg = f"{scene_id}: Campo requerido '{field}' faltante o vacío"
                    errors.append(error_msg)
                    if field in ['script_text', 'duration_sec']:
                        critical_errors.append(error_msg)
        
        # Generar reporte de validación
        state.validation = {
            'valid': len(critical_errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'critical_errors': critical_errors,
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'total_critical': len(critical_errors),
            'quality_score': self._calculate_quality_score(len(errors), len(warnings), len(state.scenes))
        }
        
        state.metrics['quality'] = {
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'total_critical': len(critical_errors),
            'quality_score': state.validation['quality_score']
        }
        
        state.add_history(
            agent_name=self.name,
            action='validated_quality',
            details={
                'errors': len(errors),
                'warnings': len(warnings),
                'critical_errors': len(critical_errors),
                'quality_score': state.validation['quality_score']
            }
        )
        
        if len(critical_errors) > 0:
            self.log(state, f"Validación completada: {len(critical_errors)} errores críticos encontrados")
        else:
            self.log(state, f"Validación completada: {len(warnings)} advertencias, sin errores críticos")
        
        return state
    
    def _calculate_quality_score(self, errors: int, warnings: int, total_scenes: int) -> float:
        """
        Calcula un score de calidad (0-1)
        """
        if total_scenes == 0:
            return 0.0
        
        # Penalizar errores más que advertencias
        error_penalty = (errors * 0.1) / total_scenes
        warning_penalty = (warnings * 0.05) / total_scenes
        
        score = max(0.0, 1.0 - error_penalty - warning_penalty)
        return round(score, 2)

