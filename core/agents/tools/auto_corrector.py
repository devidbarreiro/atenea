"""
Tool para corregir automáticamente errores comunes en escenas
"""

from langchain.tools import tool
from typing import Dict, List
from .duration_validator import validate_duration


@tool
def auto_correct_scene(scene: Dict) -> Dict[str, any]:
    """
    Corrige automáticamente errores comunes en una escena.
    
    Args:
        scene: Escena a corregir
        
    Returns:
        Dict con 'corrected_scene' (dict), 'corrections_applied' (list)
    """
    corrected_scene = scene.copy()
    corrections_applied = []
    
    platform = scene.get('platform', '').lower()
    duration = scene.get('duration_sec')
    
    # Corrección 1: Duración inválida
    if duration is not None:
        validation = validate_duration.invoke({
            'platform': platform,
            'duration_sec': duration
        })
        
        if not validation['valid'] and validation['corrected_duration']:
            old_duration = corrected_scene['duration_sec']
            corrected_scene['duration_sec'] = validation['corrected_duration']
            corrections_applied.append(
                f'Duración corregida: {old_duration}s → {validation["corrected_duration"]}s'
            )
    
    # Corrección 2: Platform inconsistente con avatar
    avatar = scene.get('avatar', '').lower()
    if avatar == 'si' and platform not in ['heygen', 'heygen_v2', 'heygen_avatar_iv']:
        corrected_scene['platform'] = 'heygen'
        corrections_applied.append(f'Platform corregida: {platform} → heygen (requerido para avatar)')
    
    if avatar == 'no' and platform in ['heygen', 'heygen_v2', 'heygen_avatar_iv']:
        # Cambiar a Veo por defecto si no hay avatar
        corrected_scene['platform'] = 'gemini_veo'
        corrections_applied.append(f'Platform corregida: {platform} → gemini_veo (sin avatar)')
    
    # Corrección 3: Normalizar nombres de plataforma
    platform_mapping = {
        'heygen_v2': 'heygen',
        'heygen_avatar_iv': 'heygen',
        'hedra': 'gemini_veo',  # Nombre antiguo
    }
    
    if platform in platform_mapping:
        corrected_scene['platform'] = platform_mapping[platform]
        corrections_applied.append(f'Platform normalizada: {platform} → {platform_mapping[platform]}')
    
    # Corrección 4: Asegurar visual_prompt es objeto
    if 'visual_prompt' in corrected_scene:
        if isinstance(corrected_scene['visual_prompt'], str):
            # Intentar parsear si es string JSON
            try:
                import json
                corrected_scene['visual_prompt'] = json.loads(corrected_scene['visual_prompt'])
                corrections_applied.append('visual_prompt parseado desde string JSON')
            except:
                # Si falla, crear estructura básica
                corrected_scene['visual_prompt'] = {
                    'description': corrected_scene['visual_prompt'],
                    'camera': '',
                    'lighting': '',
                    'composition': '',
                    'atmosphere': '',
                    'style_reference': '',
                    'continuity_notes': '',
                    'characters_in_scene': []
                }
                corrections_applied.append('visual_prompt convertido a objeto con estructura básica')
    
    return {
        'corrected_scene': corrected_scene,
        'corrections_applied': corrections_applied
    }


@tool
def auto_correct_all_scenes(scenes: List[Dict]) -> Dict[str, any]:
    """
    Corrige automáticamente todas las escenas.
    
    Args:
        scenes: Lista de escenas a corregir
        
    Returns:
        Dict con 'corrected_scenes' (list), 'total_corrections' (int)
    """
    corrected_scenes = []
    total_corrections = 0
    
    for scene in scenes:
        result = auto_correct_scene.invoke({'scene': scene})
        corrected_scenes.append(result['corrected_scene'])
        total_corrections += len(result['corrections_applied'])
    
    return {
        'corrected_scenes': corrected_scenes,
        'total_corrections': total_corrections
    }

