"""
Configuración centralizada de capacidades de todos los modelos de IA

Este módulo define las capacidades de cada modelo disponible en Atenea,
permitiendo que el frontend muestre campos dinámicos según el modelo seleccionado.
"""

from typing import Dict, List, Optional

# Mapeo de tipos de video en la BD a IDs de modelo
VIDEO_TYPE_TO_MODEL_ID = {
    'gemini_veo': 'veo-3.1-generate-preview',  # Default
    'sora': 'sora-2',
    'higgsfield_dop_standard': 'higgsfield-ai/dop/standard',
    'higgsfield_dop_preview': 'higgsfield-ai/dop/preview',
    'higgsfield_seedance_v1_pro': 'bytedance/seedance/v1/pro/image-to-video',
    'higgsfield_kling_v2_1_pro': 'kling-video/v2.1/pro/image-to-video',
    'kling_v1': 'kling-v1',
    'kling_v1_5': 'kling-v1-5',
    'kling_v1_6': 'kling-v1-6',
    'kling_v2_master': 'kling-v2-master',
    'kling_v2_1': 'kling-v2-1',
    'kling_v2_5_turbo': 'kling-v2-5-turbo',
    'heygen_avatar_v2': 'heygen-avatar-v2',
    'heygen_avatar_iv': 'heygen-avatar-iv',
    'vuela_ai': 'vuela-ai',
}

# Configuración completa de capacidades de modelos
MODEL_CAPABILITIES: Dict[str, Dict] = {
    # ==================== GEMINI VEO ====================
    'veo-2.0-generate-001': {
        'service': 'gemini_veo',
        'name': 'Veo 2.0',
        'description': 'Modelo base estable de Google Veo',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 8, 'options': [5, 6, 7, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
            'last_frame': True,
            'video_extension': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-2.0-generate-exp': {
        'service': 'gemini_veo',
        'name': 'Veo 2.0 Experimental',
        'description': 'Soporta imágenes de referencia (Asset y Style)',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 8, 'options': [5, 6, 7, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': True,
                'asset_image': True,
            },
            'negative_prompt': True,
            'seed': True,
            'last_frame': False,
            'video_extension': False,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-2.0-generate-preview': {
        'service': 'gemini_veo',
        'name': 'Veo 2.0 Preview',
        'description': 'Soporta máscaras para edición',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 8, 'options': [5, 6, 7, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
            'mask': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-3.0-generate-001': {
        'service': 'gemini_veo',
        'name': 'Veo 3.0',
        'description': 'Generación con audio y alta resolución',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 4, 'max': 8, 'options': [4, 6, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': True,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
            'resize_mode': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-3.0-fast-generate-001': {
        'service': 'gemini_veo',
        'name': 'Veo 3.0 Fast',
        'description': 'Generación rápida con audio',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 4, 'max': 8, 'options': [4, 6, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': True,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
            'resize_mode': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-3.0-generate-preview': {
        'service': 'gemini_veo',
        'name': 'Veo 3.0 Preview',
        'description': 'Con extensión de video',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 4, 'max': 8, 'options': [4, 6, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': True,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': True,
            'seed': True,
            'last_frame': True,
            'video_extension': True,
            'resize_mode': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-3.1-generate-preview': {
        'service': 'gemini_veo',
        'name': 'Veo 3.1 Preview',
        'description': 'Última versión con imágenes de referencia',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 4, 'max': 8, 'options': [4, 6, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': True,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': True,  # Solo Asset, no Style
            },
            'negative_prompt': True,
            'seed': True,
            'last_frame': True,
            'resize_mode': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    'veo-3.1-fast-generate-preview': {
        'service': 'gemini_veo',
        'name': 'Veo 3.1 Fast Preview',
        'description': 'Rápido con todas las características',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 4, 'max': 8, 'options': [4, 6, 8]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': True,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': True,
            },
            'negative_prompt': True,
            'seed': True,
            'last_frame': True,
            'resize_mode': True,
        },
        'logo': '/static/img/logos/google.png',
        'video_type': 'gemini_veo',
    },
    
    # ==================== OPENAI SORA ====================
    'sora-2': {
        'service': 'openai',
        'name': 'Sora 2',
        'description': 'Velocidad y flexibilidad para exploración y redes sociales',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': False,
            'duration': {'min': 4, 'max': 12, 'options': [4, 8, 12]},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['720p', '1080p'],  # Basado en sizes: 1280x720, 720x1280, 1024x1024
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
        },
        'logo': '/static/img/logos/openai.svg',
        'video_type': 'sora',
    },
    'sora-2-pro': {
        'service': 'openai',
        'name': 'Sora 2 Pro',
        'description': 'Alta calidad para producción profesional',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': False,
            'duration': {'min': 4, 'max': 12, 'options': [4, 8, 12]},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['720p', '1080p'],
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
        },
        'logo': '/static/img/logos/openai.svg',
        'video_type': 'sora',
    },
    
    # ==================== HIGGSFIELD ====================
    'higgsfield-ai/dop/standard': {
        'service': 'higgsfield',
        'name': 'DoP Standard',
        'description': 'Generación de video de alta calidad a partir de imágenes',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'fixed': 3},
            'aspect_ratio': ['16:9', '9:16', '1:1'],  # Asumido, verificar en docs
            'resolution': ['720p'],
            'audio': False,
            'references': {
                'start_image': True,  # image_url requerido
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
        },
        'logo': '/static/img/logos/higgsfield.png',
        'video_type': 'higgsfield_dop_standard',
    },
    'higgsfield-ai/dop/preview': {
        'service': 'higgsfield',
        'name': 'DoP Preview',
        'description': 'Generación rápida de video a partir de imágenes',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'fixed': 3},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['720p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
        },
        'logo': '/static/img/logos/higgsfield.png',
        'video_type': 'higgsfield_dop_preview',
    },
    'bytedance/seedance/v1/pro/image-to-video': {
        'service': 'higgsfield',
        'name': 'Seedance V1 Pro',
        'description': 'Generación profesional de video a partir de imágenes (ByteDance)',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'fixed': 5},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['1080p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
        },
        'logo': '/static/img/logos/higgsfield.png',
        'video_type': 'higgsfield_seedance_v1_pro',
    },
    'kling-video/v2.1/pro/image-to-video': {
        'service': 'higgsfield',
        'name': 'Kling V2.1 Pro (via Higgsfield)',
        'description': 'Generación avanzada de video a partir de imágenes',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'fixed': 5},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['1080p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
        },
        'logo': '/static/img/logos/higgsfield.png',
        'video_type': 'higgsfield_kling_v2_1_pro',
    },
    'higgsfield-ai/soul/standard': {
        'service': 'higgsfield',
        'name': 'Soul Standard',
        'description': 'Generación de imágenes de alta calidad a partir de texto',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '16:9', '9:16'],  # Asumido
            'resolution': False,
        },
        'logo': '/static/img/logos/higgsfield.png',
    },
    'reve/text-to-image': {
        'service': 'higgsfield',
        'name': 'Reve Text-to-Image',
        'description': 'Generación versátil de imágenes a partir de texto',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '16:9', '9:16'],
            'resolution': False,
        },
        'logo': '/static/img/logos/higgsfield.png',
    },
    
    # ==================== KLING ====================
    'kling-v1': {
        'service': 'kling',
        'name': 'Kling V1',
        'description': 'Modelo base de Kling AI',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 10, 'options': [5, 10]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': ['std', 'pro'],
        },
        'logo': '/static/img/logos/kling.png',
        'video_type': 'kling_v1',
    },
    'kling-v1-5': {
        'service': 'kling',
        'name': 'Kling V1.5',
        'description': 'Mejoras sobre V1',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 10, 'options': [5, 10]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],  # std: 720p, pro: 1080p
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': ['std', 'pro'],
        },
        'logo': '/static/img/logos/kling.png',
        'video_type': 'kling_v1_5',
    },
    'kling-v1-6': {
        'service': 'kling',
        'name': 'Kling V1.6',
        'description': 'Versión mejorada con text-to-video',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 10, 'options': [5, 10]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': ['std', 'pro'],
        },
        'logo': '/static/img/logos/kling.png',
        'video_type': 'kling_v1_6',
    },
    'kling-v2-master': {
        'service': 'kling',
        'name': 'Kling V2 Master',
        'description': 'Modelo master sin modos STD/PRO',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 10, 'options': [5, 10]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': [],
        },
        'logo': '/static/img/logos/kling.png',
        'video_type': 'kling_v2_master',
    },
    'kling-v2-1': {
        'service': 'kling',
        'name': 'Kling V2.1',
        'description': 'Versión 2.1 mejorada',
        'type': 'video',
        'supports': {
            'text_to_video': False,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 10, 'options': [5, 10]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['720p', '1080p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': ['std', 'pro'],
        },
        'logo': '/static/img/logos/kling.png',
        'video_type': 'kling_v2_1',
    },
    'kling-v2-5-turbo': {
        'service': 'kling',
        'name': 'Kling V2.5 Turbo',
        'description': 'Versión turbo más rápida',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,
            'duration': {'min': 5, 'max': 10, 'options': [5, 10]},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': ['1080p'],
            'audio': False,
            'references': {
                'start_image': True,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': ['std', 'pro'],
        },
        'logo': '/static/img/logos/kling.png',
        'video_type': 'kling_v2_5_turbo',
    },
    
    # ==================== HEYGEN ====================
    'heygen-avatar-v2': {
        'service': 'heygen',
        'name': 'HeyGen Avatar V2',
        'description': 'Videos con avatares AI personalizables',
        'type': 'video',
        'supports': {
            'text_to_video': True,  # Con script/guion
            'image_to_video': False,
            'duration': {'variable': True},  # Depende del script
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': True,  # Incluido en el video
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'avatar_id': True,
            'voice_id': True,
            'background': True,
        },
        'logo': '/static/img/logos/heygen.png',
        'video_type': 'heygen_avatar_v2',
    },
    'heygen-avatar-iv': {
        'service': 'heygen',
        'name': 'HeyGen Avatar IV',
        'description': 'Avatar desde imagen',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': True,  # Requiere imagen de avatar
            'duration': {'variable': True},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': True,
            'references': {
                'start_image': True,  # Imagen del avatar
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'voice_id': True,
        },
        'logo': '/static/img/logos/heygen.png',
        'video_type': 'heygen_avatar_iv',
    },
    
    # ==================== VUELA.AI ====================
    'vuela-ai': {
        'service': 'vuela_ai',
        'name': 'Vuela.ai',
        'description': 'Generación de videos con múltiples modos',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': False,
            'duration': {'variable': True},
            'aspect_ratio': ['16:9', '9:16'],
            'resolution': False,
            'audio': True,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'modes': ['single_voice', 'scenes', 'avatar'],
            'voice_id': True,
            'avatar_id': True,
        },
        'logo': '/static/img/logos/vuela.png',
        'video_type': 'vuela_ai',
    },
    
    # ==================== GEMINI IMAGE ====================
    'gemini-2.5-flash-image': {
        'service': 'gemini_image',
        'name': 'Gemini 2.5 Flash Image',
        'description': 'Generación de imágenes con Gemini',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'],
            'resolution': False,
        },
        'logo': '/static/img/logos/google.png',
    },
    
    # ==================== ELEVENLABS ====================
    'elevenlabs': {
        'service': 'elevenlabs',
        'name': 'ElevenLabs',
        'description': 'Text-to-Speech de alta calidad',
        'type': 'audio',
        'supports': {
            'text_to_speech': True,
            'voice_id': True,
            'voice_settings': True,
        },
        'logo': '/static/img/logos/elevenlabs.png',
    },
}


def get_models_by_type(item_type: str) -> List[Dict]:
    """
    Retorna todos los modelos de un tipo específico
    
    Args:
        item_type: 'video', 'image', o 'audio'
    
    Returns:
        Lista de diccionarios con información de modelos
    """
    return [
        {**model, 'id': model_id}
        for model_id, model in MODEL_CAPABILITIES.items()
        if model.get('type') == item_type
    ]


def get_model_capabilities(model_id: str) -> Optional[Dict]:
    """
    Retorna las capacidades de un modelo específico
    
    Args:
        model_id: ID del modelo
    
    Returns:
        Diccionario con capacidades o None si no existe
    """
    return MODEL_CAPABILITIES.get(model_id)


def get_supported_fields(model_id: str) -> List[str]:
    """
    Retorna lista de campos soportados por un modelo
    
    Args:
        model_id: ID del modelo
    
    Returns:
        Lista de nombres de campos soportados
    """
    model = MODEL_CAPABILITIES.get(model_id)
    if not model:
        return []
    
    supports = model.get('supports', {})
    fields = []
    
    # Campos básicos
    if supports.get('text_to_video') or supports.get('text_to_image') or supports.get('text_to_speech'):
        fields.append('prompt')
    
    if supports.get('image_to_video') or supports.get('references', {}).get('start_image'):
        fields.append('start_image')
    
    if supports.get('references', {}).get('end_image'):
        fields.append('end_image')
    
    if supports.get('references', {}).get('style_image'):
        fields.append('style_image')
    
    if supports.get('references', {}).get('asset_image'):
        fields.append('asset_image')
    
    # Campos de configuración
    if supports.get('duration'):
        fields.append('duration')
    
    if supports.get('aspect_ratio'):
        fields.append('aspect_ratio')
    
    if supports.get('resolution'):
        fields.append('resolution')
    
    if supports.get('audio'):
        fields.append('audio')
    
    if supports.get('negative_prompt'):
        fields.append('negative_prompt')
    
    if supports.get('seed'):
        fields.append('seed')
    
    # Campos específicos
    if supports.get('avatar_id'):
        fields.append('avatar_id')
    
    if supports.get('voice_id'):
        fields.append('voice_id')
    
    if supports.get('modes'):
        fields.append('mode')
    
    return fields


def get_model_id_from_video_type(video_type: str) -> Optional[str]:
    """
    Convierte un tipo de video de la BD a un ID de modelo
    
    Args:
        video_type: Tipo de video (ej: 'gemini_veo', 'sora')
    
    Returns:
        ID del modelo o None si no existe
    """
    return VIDEO_TYPE_TO_MODEL_ID.get(video_type)


def get_model_info_for_item(item_type: str, model_key: str = None) -> Dict:
    """
    Obtiene información del modelo para un item (video, image, audio)
    
    Args:
        item_type: 'video', 'image', o 'audio'
        model_key: Para videos es el video.type (ej: 'gemini_veo'), 
                   para imágenes es image.type (ej: 'text_to_image'),
                   para audios es None (ElevenLabs por defecto)
    
    Returns:
        Diccionario con name, logo, service
    """
    # Default por si no encontramos el modelo
    default_info = {
        'name': 'Modelo desconocido',
        'logo': '/static/img/logos/default.png',
        'service': 'unknown',
        'model_id': None
    }
    
    if item_type == 'video':
        # Mapear video.type a model_id
        model_id = VIDEO_TYPE_TO_MODEL_ID.get(model_key)
        if model_id and model_id in MODEL_CAPABILITIES:
            model = MODEL_CAPABILITIES[model_id]
            return {
                'name': model.get('name', model_key),
                'logo': model.get('logo', '/static/img/logos/default.png'),
                'service': model.get('service', 'unknown'),
                'model_id': model_id
            }
        # Fallback para tipos no mapeados
        return {
            'name': model_key.replace('_', ' ').title() if model_key else 'Video',
            'logo': '/static/img/logos/default.png',
            'service': model_key.split('_')[0] if model_key else 'unknown',
            'model_id': model_key
        }
    
    elif item_type == 'image':
        # Las imágenes por ahora solo usan Gemini
        return {
            'name': 'Gemini 2.5 Flash Image',
            'logo': '/static/img/logos/google.png',
            'service': 'gemini_image',
            'model_id': 'gemini-2.5-flash-image'
        }
    
    elif item_type == 'audio':
        # Audios usan ElevenLabs
        return {
            'name': 'ElevenLabs TTS',
            'logo': '/static/img/logos/elevenlabs.png',
            'service': 'elevenlabs',
            'model_id': 'elevenlabs-tts'
        }
    
    return default_info

