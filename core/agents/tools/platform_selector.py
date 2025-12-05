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
def validate_platform_avatar_consistency(scenes: List[Dict], video_type: str = 'general') -> Dict[str, any]:
    """
    Valida que la combinación platform/avatar sea consistente con el tipo de video.
    
    Args:
        scenes: Lista de escenas
        video_type: Tipo de video ('ultra', 'avatar', 'general')
        
    Returns:
        Dict con 'valid' (bool), 'errors' (lista de errores)
    """
    errors = []
    heygen_count = 0
    total_count = len(scenes)
    
    for idx, scene in enumerate(scenes):
        # Soportar ambos nombres de campo: platform y ai_service
        platform = (scene.get('platform') or scene.get('ai_service') or '').lower()
        avatar = scene.get('avatar', '').lower()
        
        # Contar escenas de HeyGen
        if platform in ['heygen', 'heygen_v2', 'heygen_avatar_iv']:
            heygen_count += 1
        
        # Validar consistencia platform/avatar
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
        
        # Validar según video_type
        if video_type == 'ultra':
            # Modo Ultra: NO permite HeyGen
            if platform in ['heygen', 'heygen_v2', 'heygen_avatar_iv'] or avatar == 'si':
                errors.append(
                    f'Escena {idx + 1}: Tipo "ultra" no permite HeyGen ni avatares. '
                    f'Usa gemini_veo o sora.'
                )
    
    # Validar proporción para tipo "avatar"
    if video_type == 'avatar' and total_count > 0:
        heygen_ratio = heygen_count / total_count
        if heygen_ratio < 0.7:
            errors.append(
                f'Tipo "avatar" requiere al menos 70% escenas HeyGen. '
                f'Actual: {heygen_ratio * 100:.0f}% ({heygen_count}/{total_count})'
            )
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

