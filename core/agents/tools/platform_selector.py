"""
Tool para seleccionar plataforma óptima basado en características de la escena
"""

from langchain.tools import tool
from typing import Dict, List


@tool
def suggest_platform(
    avatar: str,
    duration_sec: int,
    content_type: str = 'general'
) -> Dict[str, any]:
    """
    Sugiere la plataforma óptima basado en características de la escena.
    
    Args:
        avatar: 'si' o 'no' si necesita avatar
        duration_sec: Duración deseada en segundos
        content_type: Tipo de contenido ('presenter', 'b-roll', 'action', 'documentary')
        
    Returns:
        Dict con 'platform' (str), 'reason' (str), 'alternatives' (list)
    """
    avatar = avatar.lower()
    content_type = content_type.lower()
    
    # Regla 1: Si necesita avatar, solo HeyGen
    if avatar == 'si':
        return {
            'platform': 'heygen',
            'reason': 'HeyGen es la única plataforma que soporta avatares',
            'alternatives': []
        }
    
    # Regla 2: Basado en duración
    if duration_sec <= 8:
        # Puede ser Veo o Sora
        if content_type in ['action', 'complex', 'effects']:
            return {
                'platform': 'sora',
                'reason': 'Sora es mejor para escenas complejas con efectos',
                'alternatives': ['gemini_veo']
            }
        else:
            return {
                'platform': 'gemini_veo',
                'reason': 'Gemini Veo es ideal para b-roll cinematográfico',
                'alternatives': ['sora']
            }
    elif duration_sec <= 12:
        # Solo Sora puede manejar hasta 12s
        return {
            'platform': 'sora',
            'reason': 'Sora es la única opción para duraciones > 8s sin avatar',
            'alternatives': []
        }
    else:
        # Necesita HeyGen (única opción para > 12s)
        return {
            'platform': 'heygen',
            'reason': 'HeyGen es la única opción para duraciones > 12s',
            'alternatives': []
        }


@tool
def validate_platform_avatar_consistency(scenes: List[Dict]) -> Dict[str, any]:
    """
    Valida que la combinación platform/avatar sea consistente.
    
    Args:
        scenes: Lista de escenas
        
    Returns:
        Dict con 'valid' (bool), 'errors' (lista de errores)
    """
    errors = []
    
    for idx, scene in enumerate(scenes):
        platform = scene.get('platform', '').lower()
        avatar = scene.get('avatar', '').lower()
        
        # Validar consistencia
        if avatar == 'si' and platform not in ['heygen', 'heygen_v2', 'heygen_avatar_iv']:
            errors.append(
                f'Escena {idx + 1}: avatar="si" pero platform="{platform}". '
                f'Avatar solo está disponible en HeyGen'
            )
        
        if avatar == 'no' and platform in ['heygen', 'heygen_v2', 'heygen_avatar_iv']:
            errors.append(
                f'Escena {idx + 1}: avatar="no" pero platform="{platform}". '
                f'HeyGen requiere avatar="si"'
            )
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

