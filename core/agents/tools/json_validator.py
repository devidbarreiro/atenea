"""
Tool para validar estructura JSON de respuesta
"""

from langchain.tools import tool
from typing import Dict, List, Any
import json


@tool
def validate_json_structure(data: Dict[str, Any]) -> Dict[str, any]:
    """
    Valida que la estructura JSON tenga todos los campos requeridos.
    
    Args:
        data: Dict con la estructura a validar
        
    Returns:
        Dict con 'valid' (bool), 'errors' (lista de errores), 'warnings' (lista de advertencias)
    """
    errors = []
    warnings = []
    
    # Validar estructura de nivel superior
    required_top_level = ['project', 'scenes']
    for field in required_top_level:
        if field not in data:
            errors.append(f'Campo requerido faltante: {field}')
    
    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Validar 'project'
    project = data.get('project', {})
    project_required = ['platform_mode', 'num_scenes', 'language', 'total_estimated_duration_min']
    for field in project_required:
        if field not in project:
            warnings.append(f'Campo recomendado faltante en project: {field}')
    
    # Validar 'scenes'
    scenes = data.get('scenes', [])
    if not isinstance(scenes, list):
        errors.append('scenes debe ser una lista')
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    if len(scenes) == 0:
        errors.append('scenes no puede estar vacío')
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Validar cada escena
    scene_required = [
        'id', 'duration_sec', 'summary', 'script_text',
        'visual_prompt', 'avatar', 'platform'
    ]
    
    for idx, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f'Escena {idx + 1}: debe ser un objeto')
            continue
        
        # Validar campos requeridos
        for field in scene_required:
            if field not in scene:
                errors.append(f'Escena {idx + 1}: campo requerido faltante: {field}')
        
        # Validar visual_prompt
        if 'visual_prompt' in scene:
            vp = scene['visual_prompt']
            if not isinstance(vp, dict):
                errors.append(f'Escena {idx + 1}: visual_prompt debe ser un objeto')
            else:
                vp_required = [
                    'description', 'camera', 'lighting', 'composition',
                    'atmosphere', 'style_reference', 'continuity_notes', 'characters_in_scene'
                ]
                for vp_field in vp_required:
                    if vp_field not in vp:
                        warnings.append(f'Escena {idx + 1}: visual_prompt.{vp_field} faltante (recomendado)')
        
        # Validar tipos
        if 'duration_sec' in scene and not isinstance(scene['duration_sec'], (int, float)):
            errors.append(f'Escena {idx + 1}: duration_sec debe ser un número')
        
        if 'avatar' in scene and scene['avatar'] not in ['si', 'no']:
            errors.append(f'Escena {idx + 1}: avatar debe ser "si" o "no"')
        
        if 'platform' in scene:
            platform = scene['platform'].lower()
            valid_platforms = ['heygen', 'gemini_veo', 'sora', 'heygen_v2', 'heygen_avatar_iv']
            if platform not in valid_platforms:
                errors.append(f'Escena {idx + 1}: platform inválida: {platform}. Debe ser: {valid_platforms}')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


@tool
def parse_json_string(json_string: str) -> Dict[str, Any]:
    """
    Parsea un string JSON y retorna el objeto.
    
    Args:
        json_string: String con JSON
        
    Returns:
        Dict parseado
        
    Raises:
        ValueError: Si el JSON es inválido
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON inválido: {str(e)}')

