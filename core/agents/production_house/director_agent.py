"""
Director Agent - Especializado en visión visual y cinematográfica
Responsabilidad: Generar prompts visuales especializados y seleccionar plataformas
"""

import logging
from typing import Dict, Any, List
from core.agents.production_house.base_agent import BaseAgent
from core.agents.production_house.shared_state import SharedState
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
import json

logger = logging.getLogger(__name__)


class DirectorAgent(BaseAgent):
    """
    Agente especializado en visión visual y cinematográfica.
    Genera prompts visuales detallados y selecciona la mejor plataforma.
    """
    
    def __init__(self, llm_provider: str = 'openai', llm_model: str = None):
        super().__init__(
            name="Director",
            llm_provider=llm_provider,
            llm_model=llm_model or 'gpt-4',  # Usar GPT-4 para creatividad visual
            temperature=0.8  # Mayor creatividad para visión visual
        )
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crea el template de prompt para el Director"""
        
        system_prompt = """Eres un Director de Cine y Fotografía especializado en generar prompts visuales cinematográficos para videos generados por IA.

Tu responsabilidad es:
1. Analizar cada escena y generar un prompt visual detallado y cinematográfico
2. Seleccionar la mejor plataforma (gemini_veo, sora, o heygen) según el contenido
3. Añadir detalles técnicos cinematográficos (cámara, iluminación, movimiento)

REGLAS POR PLATAFORMA:

**Gemini Veo:**
- Ideal para: Movimientos de cámara suaves, paisajes, B-roll cinematográfico
- Prompts deben incluir: Movimiento de cámara específico, iluminación, estilo visual
- Ejemplo: "Plano medio de [sujeto], cámara en movimiento suave de izquierda a derecha, iluminación dorada al atardecer, estilo cinematográfico realista"

**Sora:**
- Ideal para: Efectos visuales complejos, movimientos dinámicos, escenas creativas
- Prompts deben incluir: Efectos visuales, movimiento dinámico, estilo creativo
- Ejemplo: "Primer plano de [sujeto] con efectos de partículas flotantes, cámara en movimiento circular, iluminación dramática con contrastes"

**HeyGen:**
- Ideal para: Presentaciones con avatar, explicaciones directas
- Prompts deben incluir: Estilo de presentación, fondo, ambiente
- Ejemplo: "Avatar profesional en estudio moderno, fondo minimalista con elementos relacionados al tema, iluminación profesional de estudio"

FORMATO DE RESPUESTA:
Debes devolver un JSON con este formato:
{
  "scenes": [
    {
      "id": "scene_1",
      "visual_prompt": "Prompt visual detallado y cinematográfico",
      "platform": "gemini_veo" | "sora" | "heygen",
      "camera_movement": "Descripción del movimiento de cámara",
      "lighting": "Descripción de la iluminación",
      "style": "Estilo visual (realista, cinematográfico, creativo, etc.)"
    }
  ]
}

IMPORTANTE:
- Respetar el video_type del proyecto (ultra, avatar, general)
- Si video_type es "ultra": NO usar heygen
- Si video_type es "avatar": Preferir heygen para la mayoría de escenas
- Generar prompts específicos y detallados, no genéricos"""

        human_prompt = """Analiza las siguientes escenas y genera prompts visuales cinematográficos especializados para cada una.

Tipo de video: {video_type}
Formato: {video_format}
Orientación: {video_orientation}

Escenas a procesar:
{scenes_json}

Genera prompts visuales detallados y selecciona la mejor plataforma para cada escena."""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(human_prompt)
        ])
    
    def process(self, state: SharedState) -> SharedState:
        """
        Procesa cada escena añadiendo prompts visuales especializados.
        """
        self.log(state, f"Procesando {len(state.scenes)} escenas para visión visual")
        
        if not state.scenes:
            self.log(state, "No hay escenas para procesar")
            return state
        
        try:
            # Preparar escenas para el LLM (solo datos necesarios)
            scenes_for_llm = []
            for scene in state.scenes:
                scenes_for_llm.append({
                    'id': scene.get('id'),
                    'scene_id': scene.get('scene_id'),
                    'script_text': scene.get('script_text', ''),
                    'summary': scene.get('summary', '')
                })
            
            # Crear mensajes
            messages = self.prompt_template.format_messages(
                video_type=state.video_type,
                video_format=state.video_format,
                video_orientation=state.video_orientation,
                scenes_json=json.dumps(scenes_for_llm, indent=2, ensure_ascii=False)
            )
            
            # Llamar al LLM
            llm = self.get_llm()
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.log(state, f"Respuesta recibida del Director")
            
            # Parsear respuesta
            director_data = self._parse_response(response_text)
            
            # Aplicar cambios a las escenas
            scenes_updated = 0
            for director_scene in director_data.get('scenes', []):
                scene_id = director_scene.get('id')
                if not scene_id:
                    continue
                
                # Buscar la escena en el estado
                for i, scene in enumerate(state.scenes):
                    if scene.get('id') == scene_id:
                        # Actualizar con datos del director
                        state.scenes[i]['visual_prompt'] = director_scene.get('visual_prompt', scene.get('visual_prompt', ''))
                        state.scenes[i]['ai_service'] = director_scene.get('platform', scene.get('ai_service', 'gemini_veo'))
                        
                        # Añadir metadatos cinematográficos
                        if 'camera_movement' in director_scene:
                            if 'metadata' not in state.scenes[i]:
                                state.scenes[i]['metadata'] = {}
                            state.scenes[i]['metadata']['camera_movement'] = director_scene['camera_movement']
                        
                        if 'lighting' in director_scene:
                            if 'metadata' not in state.scenes[i]:
                                state.scenes[i]['metadata'] = {}
                            state.scenes[i]['metadata']['lighting'] = director_scene['lighting']
                        
                        if 'style' in director_scene:
                            if 'metadata' not in state.scenes[i]:
                                state.scenes[i]['metadata'] = {}
                            state.scenes[i]['metadata']['style'] = director_scene['style']
                        
                        scenes_updated += 1
                        break
            
            state.metrics['director'] = {
                'scenes_processed': scenes_updated,
                'total_scenes': len(state.scenes)
            }
            
            state.add_history(
                agent_name=self.name,
                action='added_visuals',
                details={'scenes_updated': scenes_updated}
            )
            
            self.log(state, f"Prompts visuales añadidos a {scenes_updated} escenas")
            
            return state
            
        except Exception as e:
            self.log(state, f"Error: {str(e)}")
            state.metrics['director'] = {
                'error': str(e),
                'scenes_processed': 0
            }
            raise
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parsea la respuesta del LLM"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No se encontró JSON en la respuesta")
            
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON del Director: {e}")
            raise ValueError(f"Error parseando JSON: {str(e)}")

