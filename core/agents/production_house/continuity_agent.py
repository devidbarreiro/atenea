"""
Continuity Agent - Especializado en continuidad cinematográfica (Raccord)
Responsabilidad: Analizar y mejorar la continuidad entre escenas
"""

import logging
from typing import Dict, Any, List
from core.agents.production_house.base_agent import BaseAgent
from core.agents.production_house.shared_state import SharedState
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
import json

logger = logging.getLogger(__name__)


class ContinuityAgent(BaseAgent):
    """
    Agente especializado en continuidad cinematográfica (Raccord).
    Analiza y mejora la consistencia visual y narrativa entre escenas.
    """
    
    def __init__(self, llm_provider: str = 'openai', llm_model: str = None):
        super().__init__(
            name="Continuity",
            llm_provider=llm_provider,
            llm_model=llm_model or 'gpt-3.5-turbo',  # Modelo más barato para análisis
            temperature=0.5  # Temperatura moderada para análisis preciso
        )
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crea el template de prompt para Continuity"""
        
        system_prompt = """Eres un Script Supervisor (Continuista) especializado en continuidad cinematográfica (Raccord).

Tu responsabilidad es analizar las escenas y asegurar continuidad en:
1. **Personajes**: Vestuario, posición, gestos, expresiones
2. **Escenarios**: Decorado, objetos, iluminación
3. **Tiempo**: Continuidad temporal entre escenas
4. **Estilo Visual**: Consistencia de estilo cinematográfico

TIPOS DE CONTINUIDAD A VALIDAR:

**Continuidad de Personajes:**
- Vestuario debe ser consistente
- Posición y gestos deben tener sentido entre escenas consecutivas
- Expresiones deben seguir una progresión lógica

**Continuidad de Escenarios:**
- Decorado debe ser consistente si es el mismo lugar
- Objetos deben aparecer/desaparecer de forma coherente
- Iluminación debe tener continuidad temporal

**Continuidad de Estilo:**
- Estilo visual debe ser consistente (realista, cinematográfico, etc.)
- Movimientos de cámara deben tener sentido narrativo
- Transiciones entre escenas deben ser suaves

FORMATO DE RESPUESTA:
{
  "continuity_analysis": {
    "characters": {
      "consistency_score": 0.9,  // 0-1
      "issues": ["Lista de problemas encontrados"],
      "recommendations": ["Recomendaciones para mejorar"]
    },
    "scenarios": {
      "consistency_score": 0.85,
      "issues": [],
      "recommendations": []
    },
    "style": {
      "consistency_score": 0.9,
      "issues": [],
      "recommendations": []
    }
  },
  "scene_corrections": [
    {
      "scene_id": "scene_1",
      "corrections": {
        "visual_prompt": "Prompt mejorado con continuidad",
        "notes": "Ajustes para mantener continuidad con escena anterior"
      }
    }
  ]
}"""

        human_prompt = """Analiza la continuidad cinematográfica de las siguientes escenas.

Contexto del proyecto:
- Formato: {video_format}
- Tipo: {video_type}
- Guión completo: {script_text}

Escenas a analizar:
{scenes_json}

Analiza:
1. Continuidad de personajes entre escenas consecutivas
2. Continuidad de escenarios y decorados
3. Continuidad de estilo visual
4. Genera correcciones específicas para mejorar la continuidad"""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(human_prompt)
        ])
    
    def process(self, state: SharedState) -> SharedState:
        """
        Analiza y mejora la continuidad cinematográfica.
        """
        self.log(state, f"Analizando continuidad de {len(state.scenes)} escenas")
        
        if not state.scenes:
            self.log(state, "No hay escenas para analizar")
            return state
        
        try:
            # Preparar datos para el LLM
            scenes_for_llm = []
            for scene in state.scenes:
                scenes_for_llm.append({
                    'id': scene.get('id'),
                    'scene_id': scene.get('scene_id'),
                    'script_text': scene.get('script_text', ''),
                    'visual_prompt': scene.get('visual_prompt', ''),
                    'summary': scene.get('summary', '')
                })
            
            # Crear mensajes
            messages = self.prompt_template.format_messages(
                video_format=state.video_format,
                video_type=state.video_type,
                script_text=state.script_text[:2000],  # Limitar tamaño
                scenes_json=json.dumps(scenes_for_llm, indent=2, ensure_ascii=False)
            )
            
            # Llamar al LLM
            llm = self.get_llm()
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.log(state, "Respuesta recibida del Continuity")
            
            # Parsear respuesta
            continuity_data = self._parse_response(response_text)
            
            # Guardar análisis de continuidad
            state.continuity = continuity_data.get('continuity_analysis', {})
            
            # Aplicar correcciones
            corrections_applied = 0
            for correction in continuity_data.get('scene_corrections', []):
                scene_id = correction.get('scene_id')
                corrections = correction.get('corrections', {})
                
                # Buscar y actualizar escena
                for i, scene in enumerate(state.scenes):
                    if scene.get('id') == scene_id:
                        if 'visual_prompt' in corrections:
                            state.scenes[i]['visual_prompt'] = corrections['visual_prompt']
                        
                        # Guardar notas de continuidad
                        if 'metadata' not in state.scenes[i]:
                            state.scenes[i]['metadata'] = {}
                        state.scenes[i]['metadata']['continuity_notes'] = corrections.get('notes', '')
                        
                        corrections_applied += 1
                        break
            
            state.metrics['continuity'] = {
                'corrections_applied': corrections_applied,
                'consistency_scores': {
                    'characters': state.continuity.get('characters', {}).get('consistency_score', 0),
                    'scenarios': state.continuity.get('scenarios', {}).get('consistency_score', 0),
                    'style': state.continuity.get('style', {}).get('consistency_score', 0)
                }
            }
            
            state.add_history(
                agent_name=self.name,
                action='analyzed_continuity',
                details={
                    'corrections_applied': corrections_applied,
                    'avg_consistency': sum(state.metrics['continuity']['consistency_scores'].values()) / 3
                }
            )
            
            self.log(state, f"Aplicadas {corrections_applied} correcciones de continuidad")
            
            return state
            
        except Exception as e:
            self.log(state, f"Error: {str(e)}")
            state.metrics['continuity'] = {
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
            logger.error(f"Error parseando JSON del Continuity: {e}")
            raise ValueError(f"Error parseando JSON: {str(e)}")

