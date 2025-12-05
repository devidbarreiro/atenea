"""
Producer Agent - Especializado en optimización de recursos y sincronización
Responsabilidad: Optimizar duraciones, calcular costos, sincronizar audio/video exactamente
"""

import logging
from typing import Dict, Any, List
from core.agents.production_house.base_agent import BaseAgent
from core.agents.production_house.shared_state import SharedState
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
import json

logger = logging.getLogger(__name__)


class ProducerAgent(BaseAgent):
    """
    Agente especializado en optimización de recursos y sincronización.
    Calcula duraciones exactas de audio y ajusta videos para sincronización perfecta.
    """
    
    def __init__(self, llm_provider: str = 'openai', llm_model: str = None):
        super().__init__(
            name="Producer",
            llm_provider=llm_provider,
            llm_model=llm_model or 'gpt-3.5-turbo',  # Modelo más barato para cálculos
            temperature=0.3  # Baja temperatura para precisión
        )
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crea el template de prompt para el Producer"""
        
        system_prompt = """Eres un Productor de Cine especializado en optimización de recursos y sincronización técnica.

Tu responsabilidad es:
1. Optimizar las duraciones de cada escena según la plataforma seleccionada
2. Asegurar que las duraciones sean válidas para cada plataforma:
   - Gemini Veo: Solo 4, 6, u 8 segundos
   - Sora: Solo 4, 8, o 12 segundos
   - HeyGen: 15-60 segundos (según formato)
3. Calcular duración estimada del audio TTS basado en el texto
4. Ajustar duration_sec para que coincida con la duración del audio

REGLAS DE DURACIÓN POR PLATAFORMA:

**Gemini Veo:**
- Duraciones permitidas: 4, 6, u 8 segundos
- Si el texto requiere más tiempo, dividir en múltiples escenas
- Optimizar para calidad visual (preferir 6-8s para contenido complejo)

**Sora:**
- Duraciones permitidas: 4, 8, o 12 segundos
- Preferir 8s para contenido estándar
- Usar 12s solo para contenido complejo que lo requiera

**HeyGen:**
- Redes Sociales (social): 15-25 segundos (preferido: 20s)
- Educativo (educational): 30-45 segundos (preferido: 35s)
- Largo (longform): 45-60 segundos (preferido: 50s)

CÁLCULO DE DURACIÓN DE AUDIO:
- Velocidad promedio de narración: 2.5 palabras/segundo (español)
- Añadir 10% de margen para pausas naturales
- Duración estimada = (palabras / 2.5) * 1.1

FORMATO DE RESPUESTA:
{
  "scenes": [
    {
      "id": "scene_1",
      "duration_sec": 6,  // Duración optimizada y válida para la plataforma
      "audio_duration_sec": 5.8,  // Duración estimada del audio TTS
      "word_count": 15,
      "optimization_notes": "Notas sobre la optimización"
    }
  ],
  "total_cost_estimate": 0.05,  // Costo estimado total
  "total_duration_sec": 120  // Duración total del video
}"""

        human_prompt = """Optimiza las duraciones de las siguientes escenas y calcula la sincronización audio/video.

Formato de video: {video_format}
Tipo de video: {video_type}

Escenas a optimizar:
{scenes_json}

Para cada escena:
1. Contar palabras en script_text
2. Calcular duración estimada del audio TTS
3. Ajustar duration_sec para que sea válido para la plataforma seleccionada
4. Asegurar que duration_sec >= audio_duration_sec (con margen del 10%)"""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(human_prompt)
        ])
    
    def process(self, state: SharedState) -> SharedState:
        """
        Optimiza duraciones y calcula sincronización audio/video.
        """
        self.log(state, f"Optimizando {len(state.scenes)} escenas")
        
        if not state.scenes:
            self.log(state, "No hay escenas para optimizar")
            return state
        
        try:
            # Preparar datos para el LLM
            scenes_for_llm = []
            for scene in state.scenes:
                script_text = scene.get('script_text', '')
                word_count = len(script_text.split()) if script_text else 0
                
                scenes_for_llm.append({
                    'id': scene.get('id'),
                    'script_text': script_text,
                    'word_count': word_count,
                    'platform': scene.get('ai_service', 'gemini_veo'),
                    'current_duration_sec': scene.get('duration_sec')
                })
            
            # Crear mensajes
            messages = self.prompt_template.format_messages(
                video_format=state.video_format,
                video_type=state.video_type,
                scenes_json=json.dumps(scenes_for_llm, indent=2, ensure_ascii=False)
            )
            
            # Llamar al LLM
            llm = self.get_llm()
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            self.log(state, "Respuesta recibida del Producer")
            
            # Parsear respuesta
            producer_data = self._parse_response(response_text)
            
            # Aplicar optimizaciones
            scenes_optimized = 0
            total_duration = 0
            
            for producer_scene in producer_data.get('scenes', []):
                scene_id = producer_scene.get('id')
                if not scene_id:
                    continue
                
                # Buscar la escena en el estado
                for i, scene in enumerate(state.scenes):
                    if scene.get('id') == scene_id:
                        # Actualizar duración optimizada
                        optimized_duration = producer_scene.get('duration_sec')
                        if optimized_duration:
                            state.scenes[i]['duration_sec'] = optimized_duration
                            total_duration += optimized_duration
                        
                        # Guardar duración estimada del audio
                        audio_duration = producer_scene.get('audio_duration_sec')
                        if audio_duration:
                            if 'metadata' not in state.scenes[i]:
                                state.scenes[i]['metadata'] = {}
                            state.scenes[i]['metadata']['audio_duration_sec'] = audio_duration
                            state.scenes[i]['metadata']['word_count'] = producer_scene.get('word_count', 0)
                        
                        scenes_optimized += 1
                        break
            
            # Guardar métricas
            state.metrics['producer'] = {
                'scenes_optimized': scenes_optimized,
                'total_duration_sec': total_duration,
                'total_duration_min': total_duration / 60,
                'cost_estimate': producer_data.get('total_cost_estimate', 0)
            }
            
            state.add_history(
                agent_name=self.name,
                action='optimized_durations',
                details={
                    'scenes_optimized': scenes_optimized,
                    'total_duration_sec': total_duration
                }
            )
            
            self.log(state, f"Optimizadas {scenes_optimized} escenas, duración total: {total_duration}s")
            
            return state
            
        except Exception as e:
            self.log(state, f"Error: {str(e)}")
            state.metrics['producer'] = {
                'error': str(e),
                'scenes_optimized': 0
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
            logger.error(f"Error parseando JSON del Producer: {e}")
            raise ValueError(f"Error parseando JSON: {str(e)}")

