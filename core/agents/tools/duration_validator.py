"""
Tool para validar duraciones según plataforma
"""

from langchain.tools import tool
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


@tool
def validate_duration(platform: str, duration_sec: int) -> Dict[str, any]:
    """
    Valida que una duración sea válida para la plataforma especificada.
    
    Args:
        platform: Plataforma ('sora', 'gemini_veo', 'heygen')
        duration_sec: Duración en segundos
        
    Returns:
        Dict con 'valid' (bool), 'message' (str), y 'corrected_duration' (int si necesita corrección)
    """
    platform = platform.lower()
    
    # Normalizar variantes de HeyGen
    if platform in ['heygen_v2', 'heygen_avatar_iv']:
        platform = 'heygen'
    
    # Reglas de validación
    rules = {
        'sora': {
            'valid': [4, 8, 12],
            'max': 12,
            'message': 'Sora solo acepta duraciones de exactamente 4, 8, o 12 segundos'
        },
        'gemini_veo': {
            'valid': [4, 6, 8],  # Solo 4, 6, u 8 segundos para veo-3.1-generate-preview
            'max': 8,
            'message': 'Gemini Veo (veo-3.1-generate-preview) solo acepta duraciones de exactamente 4, 6, u 8 segundos'
        },
        'heygen': {
            'valid': list(range(15, 61)),  # 15-60 segundos (15-25 para social, 30-45 para educational, 45-60 para longform)
            'max': 60,
            'message': 'HeyGen acepta duraciones entre 15 y 60 segundos'
        }
    }
    
    if platform not in rules:
        return {
            'valid': False,
            'message': f'Plataforma desconocida: {platform}',
            'corrected_duration': None
        }
    
    rule = rules[platform]
    
    # Validar
    if duration_sec in rule['valid']:
        return {
            'valid': True,
            'message': f'Duración válida para {platform}',
            'corrected_duration': duration_sec
        }
    
    # Intentar corregir
    corrected = None
    if platform == 'sora':
        # Encontrar el valor válido más cercano
        valid_values = rule['valid']
        corrected = min(valid_values, key=lambda x: abs(x - duration_sec))
    elif platform == 'gemini_veo':
        # Ajustar al valor válido más cercano (4, 6, u 8)
        valid_values = [4, 6, 8]
        corrected = min(valid_values, key=lambda x: abs(x - duration_sec))
    elif platform == 'heygen':
        # Ajustar al rango válido (15-60 segundos)
        if duration_sec > 60:
            corrected = 60
        elif duration_sec < 15:
            corrected = 15
        else:
            corrected = duration_sec
    
    return {
        'valid': False,
        'message': f'{rule["message"]}. Duración recibida: {duration_sec}s',
        'corrected_duration': corrected
    }


@tool
def validate_all_scenes_durations(scenes: List[Dict]) -> Dict[str, any]:
    """
    Valida las duraciones de todas las escenas.
    
    Args:
        scenes: Lista de escenas con 'platform' y 'duration_sec'
        
    Returns:
        Dict con 'all_valid' (bool), 'errors' (lista de errores), 'corrections' (dict de correcciones)
    """
    errors = []
    corrections = {}
    
    for idx, scene in enumerate(scenes):
        platform = scene.get('platform', '').lower()
        duration = scene.get('duration_sec')
        
        if duration is None:
            errors.append(f'Escena {idx + 1}: duration_sec faltante')
            continue
        
        result = validate_duration.invoke({'platform': platform, 'duration_sec': duration})
        
        if not result['valid']:
            errors.append(f'Escena {idx + 1}: {result["message"]}')
            if result['corrected_duration']:
                corrections[f'scene_{idx}'] = {
                    'original': duration,
                    'corrected': result['corrected_duration'],
                    'platform': platform
                }
    
    return {
        'all_valid': len(errors) == 0,
        'errors': errors,
        'corrections': corrections
    }

