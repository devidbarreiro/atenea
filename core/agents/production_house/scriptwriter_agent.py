"""
ScriptWriter Agent - Especializado en estructura narrativa
Responsabilidad: Dividir guión en escenas con estructura narrativa coherente
"""

import logging
from typing import Dict, Any
from core.agents.production_house.base_agent import BaseAgent
from core.agents.production_house.shared_state import SharedState
from core.agents.prompts.script_analysis_prompt import get_script_analysis_prompt
import json

logger = logging.getLogger(__name__)


class ScriptWriterAgent(BaseAgent):
    """
    Agente especializado en estructura narrativa.
    Divide el guión en escenas con coherencia narrativa.
    """
    
    def __init__(self, llm_provider: str = 'openai', llm_model: str = None):
        super().__init__(
            name="ScriptWriter",
            llm_provider=llm_provider,
            llm_model=llm_model,
            temperature=0.7  # Creatividad moderada para estructura
        )
        self.prompt_template = get_script_analysis_prompt()
    
    def process(self, state: SharedState) -> SharedState:
        """
        Analiza el guión y genera la estructura básica de escenas.
        """
        self.log(state, "Iniciando análisis de estructura narrativa")
        
        try:
            # Crear mensajes para el LLM
            messages = self.prompt_template.format_messages(
                duracion_minutos=f"{state.duration_min:.2f}",
                duracion_segundos=str(state.duration_seconds),
                guion=state.script_text,
                formato_video=state.video_format,
                tipo_video=state.video_type
            )
            
            # Llamar al LLM
            llm = self.get_llm()
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.log(state, f"Respuesta recibida ({len(response_text)} caracteres)")
            
            # Parsear JSON de la respuesta
            parsed_json = self._parse_response(response_text)
            
            if not parsed_json or 'scenes' not in parsed_json:
                raise ValueError("Respuesta del LLM no contiene escenas válidas")
            
            # Extraer escenas
            scenes = parsed_json.get('scenes', [])
            
            # Añadir metadatos básicos a cada escena
            for i, scene in enumerate(scenes):
                if 'id' not in scene:
                    scene['id'] = f"scene_{i+1}"
                if 'scene_id' not in scene:
                    scene['scene_id'] = f"Escena {i+1}"
                # Asegurar campos requeridos por create_scenes_from_n8n_data
                if 'summary' not in scene:
                    scene['summary'] = scene.get('scene_id', f"Escena {i+1}")
                if 'script_text' not in scene:
                    scene['script_text'] = ''
                if 'duration_sec' not in scene:
                    scene['duration_sec'] = 8
                if 'visual_prompt' not in scene:
                    scene['visual_prompt'] = ''
                if 'platform' not in scene:
                    scene['platform'] = scene.get('ai_service', 'gemini_veo')
                if 'avatar' not in scene:
                    scene['avatar'] = 'si' if scene.get('platform', '').startswith('heygen') else 'no'
            
            # Actualizar estado
            state.scenes = scenes
            state.metrics['scriptwriter'] = {
                'num_scenes': len(scenes),
                'response_length': len(response_text),
                'parsed_successfully': True
            }
            
            state.add_history(
                agent_name=self.name,
                action='created_scenes',
                details={'num_scenes': len(scenes)}
            )
            
            self.log(state, f"Estructura creada: {len(scenes)} escenas")
            
            return state
            
        except Exception as e:
            self.log(state, f"Error: {str(e)}")
            state.metrics['scriptwriter'] = {
                'error': str(e),
                'parsed_successfully': False
            }
            raise
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM extrayendo el JSON.
        """
        try:
            # Intentar encontrar JSON en la respuesta
            # El LLM puede devolver texto antes/después del JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No se encontró JSON en la respuesta")
            
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.error(f"Respuesta completa: {response_text[:500]}")
            raise ValueError(f"Error parseando JSON: {str(e)}")

