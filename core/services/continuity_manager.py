"""
Servicio para gestionar continuidad cinematográfica (raccord) entre escenas
"""

import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class ContinuityManager:
    """Gestiona continuidad cinematográfica entre escenas"""
    
    @staticmethod
    def extract_global_context(script_text: str, processed_data: Optional[Dict] = None) -> Dict:
        """
        Extrae contexto global del guion:
        - Época/contexto histórico
        - Personajes principales
        - Paleta de colores
        - Estilo visual
        
        Args:
            script_text: Texto completo del guion
            processed_data: Datos procesados del script (opcional, si ya está analizado)
        
        Returns:
            Dict con contexto global extraído
        """
        context = {
            'time_period': None,
            'historical_context': None,
            'characters': {},
            'color_palette': [],
            'visual_style': None,
            'mood': None,
            'location_types': []
        }
        
        # Si hay processed_data, extraer información ya analizada
        if processed_data:
            project_data = processed_data.get('project', {})
            characters_data = processed_data.get('characters', [])
            
            # Extraer estilo visual del proyecto
            context['visual_style'] = project_data.get('visual_style_reference')
            context['color_palette'] = project_data.get('color_palette', '')
            context['mood'] = project_data.get('tone_and_mood')
            
            # Extraer personajes
            for char in characters_data:
                char_id = char.get('id')
                if char_id:
                    context['characters'][char_id] = {
                        'name': char.get('name'),
                        'visual_description': char.get('visual_description'),
                        'role': char.get('role'),
                        'age': char.get('age'),
                        'gender': char.get('gender')
                    }
        
        # Detectar época/contexto histórico del texto
        script_lower = script_text.lower()
        
        # Detectar períodos históricos comunes
        historical_keywords = {
            'segunda guerra mundial': {'period': '1940s', 'context': 'Segunda Guerra Mundial'},
            'world war ii': {'period': '1940s', 'context': 'Segunda Guerra Mundial'},
            'ww2': {'period': '1940s', 'context': 'Segunda Guerra Mundial'},
            'wwii': {'period': '1940s', 'context': 'Segunda Guerra Mundial'},
            'primera guerra mundial': {'period': '1910s', 'context': 'Primera Guerra Mundial'},
            'world war i': {'period': '1910s', 'context': 'Primera Guerra Mundial'},
            'ww1': {'period': '1910s', 'context': 'Primera Guerra Mundial'},
            'edad media': {'period': 'Medieval', 'context': 'Edad Media'},
            'medieval': {'period': 'Medieval', 'context': 'Edad Media'},
            'renacimiento': {'period': '1400s-1600s', 'context': 'Renacimiento'},
            'victoriano': {'period': '1800s', 'context': 'Era Victoriana'},
            'años 80': {'period': '1980s', 'context': 'Década de 1980'},
            'años 90': {'period': '1990s', 'context': 'Década de 1990'},
        }
        
        for keyword, info in historical_keywords.items():
            if keyword in script_lower:
                context['time_period'] = info['period']
                context['historical_context'] = info['context']
                break
        
        # Si no se detectó período histórico, asumir moderno
        if not context['time_period']:
            context['time_period'] = 'Moderno'
            context['historical_context'] = 'Época contemporánea'
        
        # Detectar tipos de locaciones comunes
        location_keywords = {
            'oficina': 'interior',
            'casa': 'interior',
            'apartamento': 'interior',
            'calle': 'exterior',
            'campo': 'exterior',
            'playa': 'exterior',
            'montaña': 'exterior',
            'ciudad': 'exterior',
            'trinchera': 'exterior',
            'cuartel': 'interior',
            'hospital': 'interior',
        }
        
        for keyword, location_type in location_keywords.items():
            if keyword in script_lower and location_type not in context['location_types']:
                context['location_types'].append(location_type)
        
        logger.info(f"Contexto global extraído: {context}")
        return context
    
    @staticmethod
    def enhance_prompt_with_continuity(
        scene_data: Dict,
        previous_scenes: List[Dict],
        global_context: Dict
    ) -> Dict:
        """
        Mejora el visual_prompt de una escena con contexto de continuidad
        
        Args:
            scene_data: Datos de la escena actual
            previous_scenes: Lista de escenas anteriores procesadas
            global_context: Contexto global del proyecto
        
        Returns:
            scene_data mejorado con continuity_notes y referencias
        """
        scene_id = scene_data.get('id', '')
        visual_prompt = scene_data.get('visual_prompt', {})
        
        if isinstance(visual_prompt, str):
            try:
                visual_prompt = json.loads(visual_prompt)
            except (json.JSONDecodeError, TypeError):
                visual_prompt = {}
        
        # Inicializar continuity_notes si no existe
        if 'continuity_notes' not in visual_prompt:
            visual_prompt['continuity_notes'] = ''
        
        continuity_notes = []
        
        # Agregar contexto histórico si aplica
        if global_context.get('historical_context'):
            continuity_notes.append(
                f"Contexto histórico: {global_context['historical_context']}. "
                f"Mantener consistencia de época en todos los elementos visuales."
            )
        
        # Agregar descripciones detalladas de personajes presentes en la escena
        characters_in_scene = visual_prompt.get('characters_in_scene', [])
        
        if characters_in_scene:
            character_descriptions = []
            for char_id in characters_in_scene:
                char_info = global_context.get('characters', {}).get(char_id, {})
                if char_info.get('visual_description'):
                    char_name = char_info.get('name', char_id)
                    char_desc = char_info['visual_description']
                    character_descriptions.append(
                        f"Personaje {char_name} ({char_id}): {char_desc}"
                    )
            
            if character_descriptions:
                continuity_notes.append(
                    f"Personajes en escena - MANTENER consistencia visual exacta: {' | '.join(character_descriptions)}"
                )
        
        # Agregar referencias a escenas anteriores con personajes compartidos
        if characters_in_scene and previous_scenes:
            referenced_scenes = []
            for prev_scene in previous_scenes:
                prev_visual = prev_scene.get('visual_prompt', {})
                if isinstance(prev_visual, str):
                    try:
                        prev_visual = json.loads(prev_visual)
                    except (json.JSONDecodeError, TypeError):
                        prev_visual = {}
                
                prev_characters = prev_visual.get('characters_in_scene', [])
                
                # Si hay personajes compartidos, agregar referencia
                shared_chars = set(characters_in_scene) & set(prev_characters)
                if shared_chars:
                    prev_id = prev_scene.get('id', '')
                    if prev_id:
                        referenced_scenes.append(prev_id)
            
            if referenced_scenes:
                continuity_notes.append(
                    f"Referencias a escenas anteriores: {', '.join(referenced_scenes)}. "
                    f"Mantener consistencia visual con estas escenas."
                )
        
        # Agregar paleta de colores si está definida
        color_palette = global_context.get('color_palette')
        if color_palette:
            continuity_notes.append(f"Paleta de colores consistente: {color_palette}")
        
        # Agregar estilo visual si está definido
        visual_style = global_context.get('visual_style')
        if visual_style:
            continuity_notes.append(f"Estilo visual: {visual_style}")
        
        # Actualizar continuity_notes
        if continuity_notes:
            visual_prompt['continuity_notes'] = ' '.join(continuity_notes)
        
        # Mejorar description del visual_prompt con descripciones de personajes si aplica
        if characters_in_scene and visual_prompt.get('description'):
            char_descriptions_text = []
            for char_id in characters_in_scene:
                char_info = global_context.get('characters', {}).get(char_id, {})
                if char_info.get('visual_description'):
                    char_descriptions_text.append(char_info['visual_description'])
            
            if char_descriptions_text:
                # Agregar descripciones de personajes al inicio de la descripción
                original_description = visual_prompt.get('description', '')
                characters_text = f"Personajes presentes: {', '.join(char_descriptions_text)}. "
                visual_prompt['description'] = characters_text + original_description
        
        # Actualizar scene_data
        scene_data['visual_prompt'] = visual_prompt
        
        # Crear continuity_context para guardar en la base de datos
        continuity_context = {
            'references_previous_scenes': [],
            'time_progression': None,
            'maintained_elements': [],
            'characters_present': []
        }
        
        # Extraer referencias de escenas anteriores
        if previous_scenes:
            for prev_scene in previous_scenes:
                prev_id = prev_scene.get('id')
                if prev_id:
                    continuity_context['references_previous_scenes'].append(prev_id)
        
        # Detectar elementos mantenidos (personajes compartidos)
        if characters_in_scene:
            continuity_context['maintained_elements'].extend(
                [f"personaje_{char_id}" for char_id in characters_in_scene]
            )
            # Guardar información de personajes presentes
            for char_id in characters_in_scene:
                char_info = global_context.get('characters', {}).get(char_id, {})
                continuity_context['characters_present'].append({
                    'id': char_id,
                    'name': char_info.get('name'),
                    'visual_description': char_info.get('visual_description')
                })
        
        scene_data['continuity_context'] = continuity_context
        
        return scene_data
    
    @staticmethod
    def validate_continuity(scenes: List[Dict], global_context: Dict) -> List[Dict]:
        """
        Valida consistencia entre escenas
        
        Args:
            scenes: Lista de escenas a validar
            global_context: Contexto global del proyecto
        
        Returns:
            Lista de problemas de continuidad encontrados
        """
        issues = []
        
        # Mapeo de personajes por escena
        character_appearances = {}
        
        for scene in scenes:
            scene_id = scene.get('id', '')
            visual_prompt = scene.get('visual_prompt', {})
            
            if isinstance(visual_prompt, str):
                try:
                    visual_prompt = json.loads(visual_prompt)
                except (json.JSONDecodeError, TypeError):
                    visual_prompt = {}
            
            characters = visual_prompt.get('characters_in_scene', [])
            
            for char_id in characters:
                if char_id not in character_appearances:
                    character_appearances[char_id] = []
                character_appearances[char_id].append(scene_id)
        
        # Validar que personajes tengan descripciones consistentes
        for char_id, scene_ids in character_appearances.items():
            if len(scene_ids) > 1:
                # Personaje aparece en múltiples escenas
                char_info = global_context.get('characters', {}).get(char_id, {})
                
                if not char_info.get('visual_description'):
                    issues.append({
                        'type': 'missing_character_description',
                        'severity': 'medium',
                        'character_id': char_id,
                        'scenes': scene_ids,
                        'message': f"Personaje {char_id} aparece en múltiples escenas pero no tiene descripción visual detallada"
                    })
        
        # Validar consistencia de contexto histórico
        historical_context = global_context.get('historical_context')
        if historical_context:
            for scene in scenes:
                visual_prompt = scene.get('visual_prompt', {})
                if isinstance(visual_prompt, str):
                    try:
                        visual_prompt = json.loads(visual_prompt)
                    except (json.JSONDecodeError, TypeError):
                        visual_prompt = {}
                
                continuity_notes = visual_prompt.get('continuity_notes', '')
                
                if historical_context.lower() not in continuity_notes.lower():
                    issues.append({
                        'type': 'missing_historical_context',
                        'severity': 'low',
                        'scene_id': scene.get('id'),
                        'message': f"Escena no menciona contexto histórico {historical_context}"
                    })
        
        logger.info(f"Validación de continuidad: {len(issues)} problemas encontrados")
        return issues

