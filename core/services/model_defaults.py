"""
Servicio para manejar defaults inteligentes de modelos según tipo de video
"""

import logging
from typing import Dict, Optional
from decouple import config

logger = logging.getLogger(__name__)


class ModelDefaults:
    """Defaults inteligentes según tipo de video"""
    
    # Defaults por tipo de video
    DEFAULTS_BY_VIDEO_TYPE = {
        'ultra': {
            'gemini_veo': 'veo-3.1-generate-preview',
            'sora': 'sora-2',
        },
        'avatar': {
            'heygen': 'heygen_v2',
        },
        'general': {
            'gemini_veo': 'veo-3.1-generate-preview',
            'sora': 'sora-2',
            'heygen': 'heygen_v2',
        }
    }
    
    # Estrategias de duración según formato de video
    # IMPORTANTE: Veo solo acepta 4, 6, u 8 segundos
    DURATION_STRATEGIES = {
        'social': {
            'heygen': {'min': 15, 'max': 25, 'preferred': 20},
            'veo': {'min': 4, 'max': 6, 'preferred': 4},  # Solo 4, 6, 8 válidos
            'sora': {'min': 4, 'max': 8, 'preferred': 4},
            'description': 'Escenas cortas y dinámicas para redes sociales'
        },
        'educational': {
            'heygen': {'min': 30, 'max': 45, 'preferred': 35},
            'veo': {'min': 4, 'max': 8, 'preferred': 6},  # Solo 4, 6, 8 válidos
            'sora': {'min': 8, 'max': 12, 'preferred': 8},
            'description': 'Escenas medianas para contenido educativo'
        },
        'longform': {
            'heygen': {'min': 45, 'max': 60, 'preferred': 50},
            'veo': {'min': 6, 'max': 8, 'preferred': 8},  # Solo 4, 6, 8 válidos
            'sora': {'min': 8, 'max': 12, 'preferred': 12},
            'description': 'Escenas largas para contenido extenso'
        }
    }
    
    @staticmethod
    def get_duration_strategy(video_format: str) -> Dict:
        """
        Obtiene estrategia de duración según formato
        
        Args:
            video_format: Formato de video ('social', 'educational', 'longform')
        
        Returns:
            Dict con estrategias de duración por servicio
        """
        return ModelDefaults.DURATION_STRATEGIES.get(
            video_format,
            ModelDefaults.DURATION_STRATEGIES['educational']  # Default
        )
    
    @staticmethod
    def get_defaults(video_type: Optional[str] = None) -> Dict[str, str]:
        """
        Retorna defaults según tipo de video
        
        Args:
            video_type: Tipo de video ('ultra', 'avatar', 'general')
        
        Returns:
            Dict con defaults de modelos
        """
        if not video_type:
            video_type = 'general'
        
        defaults = ModelDefaults.DEFAULTS_BY_VIDEO_TYPE.get(
            video_type,
            ModelDefaults.DEFAULTS_BY_VIDEO_TYPE['general']
        ).copy()
        
        # Agregar defaults del sistema si no están
        if 'default_voice_id' not in defaults:
            defaults['default_voice_id'] = config(
                'ELEVENLABS_DEFAULT_VOICE_ID',
                default='pFZP5JQG7iQjIQuC4Bku'
            )
            defaults['default_voice_name'] = config(
                'ELEVENLABS_DEFAULT_VOICE_NAME',
                default='Aria'
            )
        
        return defaults
    
    @staticmethod
    def apply_defaults(script) -> Dict[str, str]:
        """
        Aplica defaults inteligentes a un script
        
        Si script.model_preferences está vacío, aplica defaults según video_type.
        Si tiene preferencias, las completa con defaults faltantes.
        
        Args:
            script: Objeto Script
        
        Returns:
            Dict con preferencias completas (user preferences + defaults)
        """
        # Si ya tiene preferencias, usarlas como base
        if script.model_preferences:
            preferences = script.model_preferences.copy()
        else:
            preferences = {}
        
        # Obtener defaults según video_type
        defaults = ModelDefaults.get_defaults(script.video_type)
        
        # Completar preferencias con defaults faltantes
        for key, default_value in defaults.items():
            if key not in preferences or not preferences[key]:
                preferences[key] = default_value
        
        return preferences
    
    @staticmethod
    def get_available_models(service: str) -> list:
        """
        Obtiene lista de modelos disponibles para un servicio
        
        Args:
            service: Nombre del servicio ('gemini_veo', 'sora', 'heygen')
        
        Returns:
            Lista de modelos disponibles
        """
        from core.ai_services.model_config import MODEL_CAPABILITIES
        
        models = []
        for model_id, model_data in MODEL_CAPABILITIES.items():
            # Filtrar por servicio
            if service == 'gemini_veo' and 'veo' in model_id.lower():
                models.append({
                    'id': model_id,
                    'name': model_data.get('name', model_id),
                    'description': model_data.get('description', ''),
                    'version': model_data.get('version', ''),
                })
            elif service == 'sora' and 'sora' in model_id.lower():
                models.append({
                    'id': model_id,
                    'name': model_data.get('name', model_id),
                    'description': model_data.get('description', ''),
                    'version': model_data.get('version', ''),
                })
            elif service == 'heygen':
                # HeyGen no está en MODEL_CAPABILITIES, usar valores hardcodeados
                if model_id == 'heygen_v2':
                    models.append({
                        'id': 'heygen_v2',
                        'name': 'HeyGen Avatar V2',
                        'description': 'Avatar V2 con mejor calidad',
                    })
                elif model_id == 'heygen_avatar_iv':
                    models.append({
                        'id': 'heygen_avatar_iv',
                        'name': 'HeyGen Avatar IV',
                        'description': 'Avatar IV con imagen personalizada',
                    })
        
        # Si es heygen y no hay modelos, agregar defaults
        if service == 'heygen' and not models:
            models = [
                {
                    'id': 'heygen_v2',
                    'name': 'HeyGen Avatar V2',
                    'description': 'Avatar V2 con mejor calidad',
                },
                {
                    'id': 'heygen_avatar_iv',
                    'name': 'HeyGen Avatar IV',
                    'description': 'Avatar IV con imagen personalizada',
                }
            ]
        
        return models

