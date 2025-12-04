"""
Corrector Agent - Especializado en correcciones automáticas inteligentes
Responsabilidad: Corregir errores críticos detectados por Quality Agent
"""

import logging
from typing import Dict, Any, List
from core.agents.production_house.base_agent import BaseAgent
from core.agents.production_house.shared_state import SharedState
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from core.agents.tools.word_counter import count_words
import json

logger = logging.getLogger(__name__)


class CorrectorAgent(BaseAgent):
    """
    Agente especializado en correcciones automáticas.
    Corrige errores críticos detectados por Quality Agent.
    """
    
    def __init__(self, llm_provider: str = 'openai', llm_model: str = None):
        super().__init__(
            name="Corrector",
            llm_provider=llm_provider,
            llm_model=llm_model or 'gpt-3.5-turbo',  # Modelo más barato para correcciones
            temperature=0.3  # Baja temperatura para correcciones precisas
        )
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crea el template de prompt para Corrector"""
        
        system_prompt = """Eres un Asistente de Producción especializado en corregir errores técnicos en escenas de video.

Tu responsabilidad es corregir errores críticos manteniendo la intención original:
1. **Texto demasiado largo**: Truncar manteniendo el sentido
2. **Duración inválida**: Ajustar a valores válidos para la plataforma
3. **Campos faltantes**: Completar con valores por defecto sensatos
4. **Sincronización audio/video**: Ajustar duraciones para que coincidan

REGLAS DE CORRECCIÓN:

**Texto demasiado largo:**
- Truncar manteniendo frases completas
- Preferir mantener el inicio del texto
- Añadir "..." si es necesario para indicar truncamiento

**Duración inválida:**
- Gemini Veo: Ajustar a 4, 6, u 8 (el más cercano)
- Sora: Ajustar a 4, 8, o 12 (el más cercano)
- HeyGen: Ajustar según formato (social: 15-25s, educational: 30-45s, longform: 45-60s)

**Campos faltantes:**
- visual_prompt: Generar basado en script_text y summary
- ai_service: Usar gemini_veo por defecto
- duration_sec: Calcular basado en texto y plataforma

FORMATO DE RESPUESTA:
{
  "corrected_scenes": [
    {
      "id": "scene_1",
      "corrections_applied": ["Texto truncado", "Duración ajustada"],
      "script_text": "Texto corregido",
      "duration_sec": 6,
      "visual_prompt": "Prompt corregido si faltaba"
    }
  ],
  "total_corrections": 2
}"""

        human_prompt = """Corrige los siguientes errores críticos en las escenas.

Errores encontrados:
{errors_json}

Escenas a corregir:
{scenes_json}

Aplica las correcciones necesarias manteniendo la intención original."""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(human_prompt)
        ])
    
    def process(self, state: SharedState) -> SharedState:
        """
        Corrige errores críticos detectados por Quality Agent.
        """
        validation = state.validation
        if not validation or not validation.get('critical_errors'):
            self.log(state, "No hay errores críticos para corregir")
            return state
        
        critical_errors = validation.get('critical_errors', [])
        self.log(state, f"Corrigiendo {len(critical_errors)} errores críticos")
        
        try:
            # Preparar escenas con errores
            scenes_to_correct = []
            for scene in state.scenes:
                # Solo incluir escenas que tienen errores críticos
                # Usar coincidencia precisa para evitar falsos positivos (scene_1 vs scene_10)
                scene_id = scene.get('id', '')
                scene_errors = [
                    e for e in critical_errors 
                    if e.startswith(f"{scene_id}:") or f" {scene_id}:" in e or f"({scene_id})" in e
                ]
                if scene_errors:
                    scenes_to_correct.append({
                        'id': scene.get('id'),
                        'script_text': scene.get('script_text', ''),
                        'duration_sec': scene.get('duration_sec'),
                        'platform': scene.get('ai_service', 'gemini_veo'),
                        'errors': scene_errors
                    })
            
            if not scenes_to_correct:
                self.log(state, "No se encontraron escenas específicas para corregir")
                return state
            
            # Crear mensajes
            messages = self.prompt_template.format_messages(
                errors_json=json.dumps(critical_errors[:10], indent=2, ensure_ascii=False),  # Limitar errores
                scenes_json=json.dumps(scenes_to_correct, indent=2, ensure_ascii=False)
            )
            
            # Llamar al LLM
            llm = self.get_llm()
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.log(state, "Respuesta recibida del Corrector")
            
            # Parsear respuesta
            corrector_data = self._parse_response(response_text)
            
            # Aplicar correcciones
            corrections_applied = 0
            for corrected_scene in corrector_data.get('corrected_scenes', []):
                scene_id = corrected_scene.get('id')
                if not scene_id:
                    continue
                
                # Buscar y actualizar escena
                for i, scene in enumerate(state.scenes):
                    if scene.get('id') == scene_id:
                        # Aplicar correcciones
                        if 'script_text' in corrected_scene:
                            state.scenes[i]['script_text'] = corrected_scene['script_text']
                        
                        if 'duration_sec' in corrected_scene:
                            state.scenes[i]['duration_sec'] = corrected_scene['duration_sec']
                        
                        if 'visual_prompt' in corrected_scene and not state.scenes[i].get('visual_prompt'):
                            state.scenes[i]['visual_prompt'] = corrected_scene['visual_prompt']
                        
                        # Guardar notas de corrección
                        if 'metadata' not in state.scenes[i]:
                            state.scenes[i]['metadata'] = {}
                        state.scenes[i]['metadata']['corrections'] = corrected_scene.get('corrections_applied', [])
                        
                        corrections_applied += 1
                        break
            
            state.metrics['corrector'] = {
                'corrections_applied': corrections_applied,
                'total_corrections': corrector_data.get('total_corrections', 0)
            }
            
            state.add_history(
                agent_name=self.name,
                action='applied_corrections',
                details={
                    'corrections_applied': corrections_applied,
                    'total_corrections': corrector_data.get('total_corrections', 0)
                }
            )
            
            self.log(state, f"Aplicadas {corrections_applied} correcciones")
            
            return state
            
        except Exception as e:
            self.log(state, f"Error: {str(e)}")
            state.metrics['corrector'] = {
                'error': str(e),
                'corrections_applied': 0
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
            logger.error(f"Error parseando JSON del Corrector: {e}")
            raise ValueError(f"Error parseando JSON: {str(e)}")

