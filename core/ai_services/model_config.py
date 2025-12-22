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
    'manim_quote': 'manim-quote',
    'manim_intro_slide': 'manim-intro-slide',
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
        'name': 'Veo-2.0-Generate-Exp',
        'description': 'Soporta imágenes de referencia (Asset y Style)',
        'logo': '/static/img/logos/google.png',
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
    'veo-3.0-fast-generate-preview': {
        'service': 'gemini_veo',
        'name': 'Veo 3.0 Fast Preview',
        'description': 'Rápido con audio',
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
            'last_frame': False,
            'video_extension': False,
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
        'description': 'Rápido (sin reference images)',
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
                'asset_image': False,  # Los modelos "fast" NO soportan reference images
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
            'image_to_video': True,
            'duration': {'min': 4, 'max': 12, 'options': [4, 8, 12]},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['720p', '1080p'],  # Basado en sizes: 1280x720, 720x1280, 1024x1024
            'audio': False,
            'references': {
                'start_image': True,  # Soporta image-to-video
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
            'image_to_video': True,
            'duration': {'min': 4, 'max': 12, 'options': [4, 8, 12]},
            'aspect_ratio': ['16:9', '9:16', '1:1'],
            'resolution': ['720p', '1080p'],
            'audio': False,
            'references': {
                'start_image': True,  # Soporta image-to-video
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


    # ==================== Black Forest Labs (Flux) ====================
    'flux-pro/kontext/max/text-to-image': {
        'service': 'higgsfield',
        'name': 'Flux Pro Kontext Max',
        'description': 'Generación de imágenes de alta calidad a partir de texto (Flux Pro Kontext Max)',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['16:9', '4:3', '1:1', '3:4', '9:16'],
            'safety_tolerance': [1, 2, 3, 4, 5, 6],
            'seed': 'string',
        },
        'logo': '/static/img/logos/flux-ai.png',
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
        'description': 'Versión 2.1 mejorada con soporte para text-to-video e image-to-video',
        'type': 'video',
        'supports': {
            'text_to_video': True,  # Corregido: Kling v2.1 sí soporta text-to-video
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
            'duration': False,  # La duración la determina el script/audio
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
    
    # ==================== MANIM QUOTE ====================
    'manim-quote': {
        'service': 'manim',
        'name': 'Manim Quote',
        'description': 'Genera videos animados de citas con texto y autor opcional',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': False,
            'duration': {'min': 5, 'max': 12, 'variable': True},
            'aspect_ratio': ['16:9'],
            'resolution': False,
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'quality': ['l', 'm', 'h', 'k'],
            'author': True,
            'container_color': True,  # Color del contenedor (hex)
            'text_color': True,  # Color del texto (hex)
            'font_family': ['normal', 'bold', 'italic', 'bold_italic'],  # Tipo de fuente
        },
        'logo': '/static/img/logos/manim.png',
        'video_type': 'manim_quote',
    },
    
    # ==================== MANIM INTRO SLIDE ====================
    'manim-intro-slide': {
        'service': 'manim',
        'name': 'Manim Intro Slide',
        'description': 'Genera cortinillas de entrada estilo presentación educativa',
        'type': 'video',
        'supports': {
            'text_to_video': True,
            'image_to_video': False,
            'duration': {'min': 3, 'max': 10, 'variable': True},
            'aspect_ratio': ['16:9'],
            'resolution': False,
            'audio': False,
            'references': {
                'start_image': False,
                'end_image': False,
                'style_image': False,
                'asset_image': False,
            },
            'negative_prompt': False,
            'seed': False,
            'quality': ['l', 'm', 'h', 'k'],
            'title': True,  # Título de la cortinilla
            'central_text': True,  # Texto central (pregunta o mensaje principal)
            'footer': True,  # Footer (opcional)
            'bg_color': True,  # Color de fondo (hex)
            'title_color': True,  # Color del título (hex)
            'central_text_color': True,  # Color del texto central (hex)
            'footer_color': True,  # Color del footer (hex)
            'circle_color': True,  # Color del círculo sutil (hex)
        },
        'logo': '/static/img/logos/manim.png',
        'video_type': 'manim_intro_slide',
    },
    
    # ==================== GEMINI IMAGE ====================
    'gemini-2.5-flash-image': {
        'service': 'gemini image',
        'name': 'Nano Banana Flash',
        'description': 'Generación de imágenes con Gemini',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'],
        },
        'logo': '/static/img/logos/google.png',
    },
    'gemini-3-pro-image-preview': {
        'service': 'gemini image',
        'name': 'Nano Banana Pro',
        'description': 'Generación de imágenes con Nano Banana Pro',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'],
        },
        'logo': '/static/img/logos/google.png',
    },

    # ==================== SEEDREAM IMAGE ====================
    'seedream-4-5-251128': {
        'service': 'seedream',
        'name': 'SeeDream 4.5 Advanced',
        'description': 'Generación avanzada, edición y mezcla de imágenes (soporta multi-imagen).',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_image': True,     # Habilitado para edición avanzada (I2I)
            'multi_image': True,        # Habilitado para Multi-Imagen (Blending)
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '2:3', '3:2', '16:9', '9:16', '4:3', '21:9'],
        },
        'logo': '/static/img/logos/seedream.png',
    },
    
    'seedream-3-0-t2i-250415': {
        'service': 'seedream',
        'name': 'SeeDream 3.0 Standard',
        'description': 'Modelo estándar de generación (Text-to-Image) simple.',
        'type': 'image',
        'supports': {
            'text_to_image': True,      # <-- Activamos la generación simple (T2I)
            'image_to_image': False,    # <-- Desactivamos edición simple (si es solo T2I)
            'multi_image': False,
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '2:3', '3:2', '16:9', '9:16'],
        },
        'logo': '/static/img/logos/seedream.png',
    },
    
    # ==================== OPENAI GPT IMAGE ====================
    'gpt-image-1': {
        'service': 'openai_image',
        'name': 'GPT Image 1',
        'description': 'Generación de imágenes de alta calidad con OpenAI',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_image': True,  # Soportado vía Edits endpoint
            'multi_image': True,  # Soportado vía Edits endpoint con múltiples imágenes
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '16:9', '9:16'],
            'quality': ['low', 'medium', 'high', 'auto'],
            'format': ['png', 'jpeg', 'webp'],
            'background': ['transparent', 'opaque'],
            'input_fidelity': ['low', 'high'],
        },
        'logo': '/static/img/logos/openai.svg',
    },
    'gpt-image-1.5': {
        'service': 'openai_image',
        'name': 'GPT Image 1.5',
        'description': 'Modelo más avanzado, 4x más rápido que GPT Image 1',
        'type': 'image',
        'supports': {
            'text_to_image': True,
            'image_to_image': True,  # Soportado vía Edits endpoint
            'multi_image': True,  # Soportado vía Edits endpoint con múltiples imágenes
            'image_to_video': False,
            'text_to_video': False,
            'aspect_ratio': ['1:1', '16:9', '9:16'],
            'quality': ['low', 'medium', 'high', 'auto'],
            'format': ['png', 'jpeg', 'webp'],
            'background': ['transparent', 'opaque'],
            'input_fidelity': ['low', 'high'],
        },
        'logo': '/static/img/logos/openai.svg',
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
    
    # ==================== GOOGLE LYRIA ====================
    'lyria-002': {
        'service': 'google_lyria',
        'name': 'Lyria 2',
        'description': 'Generación de música instrumental de alta calidad',
        'type': 'audio',
        'supports': {
            'text_to_music': True,
            'prompt': True,
            'negative_prompt': True,
            'seed': True,
            'sample_count': True,
            'duration': {'fixed': 30},  # Siempre 30 segundos
            'format': 'wav',
            'sample_rate': 48000,
            'instrumental_only': True,
        },
        'logo': '/static/img/logos/google.png',
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
    if supports.get('text_to_video') or supports.get('text_to_image') or supports.get('text_to_speech') or supports.get('text_to_music'):
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
    
    # Campos específicos de música
    if supports.get('sample_count'):
        fields.append('sample_count')
    
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


def get_video_type_from_model_id(model_id: str) -> Optional[str]:
    """
    Convierte un ID de modelo a un tipo de video de la BD
    
    Args:
        model_id: ID del modelo (ej: 'veo-2.0-generate-001', 'sora-2')
    
    Returns:
        Tipo de video o None si no existe
    """
    # Primero buscar en MODEL_CAPABILITIES por el campo video_type
    if model_id in MODEL_CAPABILITIES:
        capabilities = MODEL_CAPABILITIES[model_id]
        video_type = capabilities.get('video_type')
        if video_type:
            return video_type
    
    # Si no está en MODEL_CAPABILITIES, buscar en el mapeo inverso
    for vtype, mid in VIDEO_TYPE_TO_MODEL_ID.items():
        if mid == model_id:
            return vtype
    
    # Fallback: intentar inferir del model_id
    if 'veo' in model_id:
        return 'gemini_veo'
    elif 'sora' in model_id:
        return 'sora'
    elif 'heygen' in model_id:
        return 'heygen_avatar_v2' if 'v2' in model_id else 'heygen_avatar_iv'
    elif 'kling' in model_id:
        return model_id.replace('-', '_')
    elif 'higgsfield' in model_id or 'seedance' in model_id:
        if 'dop/standard' in model_id:
            return 'higgsfield_dop_standard'
        elif 'dop/preview' in model_id:
            return 'higgsfield_dop_preview'
        elif 'seedance' in model_id:
            return 'higgsfield_seedance_v1_pro'
        elif 'kling-video' in model_id:
            return 'higgsfield_kling_v2_1_pro'
    elif 'vuela' in model_id:
        return 'vuela_ai'
    elif 'manim' in model_id:
        if 'intro-slide' in model_id or 'intro_slide' in model_id:
            return 'manim_intro_slide'
        return 'manim_quote'
    
    return None


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
        # Si model_key es un model_id directo (ej: 'veo-2.0-generate-exp'), usarlo directamente
        if model_key and model_key in MODEL_CAPABILITIES:
            model = MODEL_CAPABILITIES[model_key]
            return {
                'name': model.get('name', model_key),
                'logo': model.get('logo', '/static/img/logos/default.png'),
                'service': model.get('service', 'unknown'),
                'model_id': model_key
            }
        
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
        # model_key puede ser el model_id del config o image.type como fallback
        # Si model_key está en MODEL_CAPABILITIES, usarlo directamente
        if model_key and model_key in MODEL_CAPABILITIES:
            model = MODEL_CAPABILITIES[model_key]
            return {
                'name': model.get('name', 'Modelo desconocido'),
                'logo': model.get('logo', '/static/img/logos/default.png'),
                'service': model.get('service', 'unknown'),
                'model_id': model_key
            }
        # Fallback: Las imágenes por defecto usan Gemini
        return {
            'name': 'Gemini 2.5 Flash Image',
            'logo': '/static/img/logos/google.png',
            'service': 'gemini_image',
            'model_id': 'gemini-2.5-flash-image'
        }
    
    elif item_type == 'audio':
        # Si model_key está en MODEL_CAPABILITIES, usarlo directamente
        if model_key and model_key in MODEL_CAPABILITIES:
            model = MODEL_CAPABILITIES[model_key]
            return {
                'name': model.get('name', 'Modelo desconocido'),
                'logo': model.get('logo', '/static/img/logos/default.png'),
                'service': model.get('service', 'unknown'),
                'model_id': model_key
            }
        # Fallback: Audios por defecto usan ElevenLabs
        return {
            'name': 'ElevenLabs TTS',
            'logo': '/static/img/logos/elevenlabs.png',
            'service': 'elevenlabs',
            'model_id': 'elevenlabs'
        }
    
    return default_info

