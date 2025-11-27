"""
Utilidades para trabajar con capacidades de modelos
"""

from typing import Dict, List, Optional
from ..ai_services.model_config import (
    MODEL_CAPABILITIES,
    get_models_by_type,
    get_model_capabilities,
    get_supported_fields,
    get_model_id_from_video_type,
)


def get_models_by_service(service: str) -> List[Dict]:
    """
    Retorna todos los modelos de un servicio específico
    
    Args:
        service: Nombre del servicio (ej: 'gemini_veo', 'openai', 'higgsfield')
    
    Returns:
        Lista de diccionarios con información de modelos
    """
    return [
        {**model, 'id': model_id}
        for model_id, model in MODEL_CAPABILITIES.items()
        if model.get('service') == service
    ]


def get_models_grouped_by_service(item_type: str = None) -> Dict[str, List[Dict]]:
    """
    Retorna modelos agrupados por servicio
    
    Args:
        item_type: Opcional, filtrar por tipo ('video', 'image', 'audio')
    
    Returns:
        Diccionario con servicio como clave y lista de modelos como valor
    """
    models = MODEL_CAPABILITIES.items()
    
    if item_type:
        models = [(mid, m) for mid, m in models if m.get('type') == item_type]
    
    grouped = {}
    for model_id, model in models:
        service = model.get('service', 'unknown')
        if service not in grouped:
            grouped[service] = []
        grouped[service].append({**model, 'id': model_id})
    
    return grouped


def validate_model_supports_field(model_id: str, field: str) -> bool:
    """
    Valida si un modelo soporta un campo específico
    
    Args:
        model_id: ID del modelo
        field: Nombre del campo a validar
    
    Returns:
        True si el modelo soporta el campo, False en caso contrario
    """
    supported_fields = get_supported_fields(model_id)
    return field in supported_fields


def get_default_values_for_model(model_id: str) -> Dict:
    """
    Retorna valores por defecto para un modelo
    
    Args:
        model_id: ID del modelo
    
    Returns:
        Diccionario con valores por defecto
    """
    model = get_model_capabilities(model_id)
    if not model:
        return {}
    
    supports = model.get('supports', {})
    defaults = {}
    
    # Duración por defecto
    if 'duration' in supports:
        duration_config = supports['duration']
        if 'options' in duration_config:
            defaults['duration'] = duration_config['options'][0]
        elif 'min' in duration_config:
            defaults['duration'] = duration_config['min']
        elif 'fixed' in duration_config:
            defaults['duration'] = duration_config['fixed']
    
    # Aspect ratio por defecto
    if 'aspect_ratio' in supports and supports['aspect_ratio']:
        defaults['aspect_ratio'] = supports['aspect_ratio'][0]
    
    # Resolution por defecto
    if 'resolution' in supports and supports['resolution']:
        if isinstance(supports['resolution'], list):
            defaults['resolution'] = supports['resolution'][0]
    
    # Audio por defecto
    if 'audio' in supports:
        defaults['audio'] = supports['audio']
    
    # Mode por defecto (para Kling)
    if 'modes' in supports and supports['modes']:
        defaults['mode'] = supports['modes'][0]
    
    return defaults


def get_required_fields_for_model(model_id: str) -> List[str]:
    """
    Retorna lista de campos requeridos para un modelo
    
    Args:
        model_id: ID del modelo
    
    Returns:
        Lista de nombres de campos requeridos
    """
    model = get_model_capabilities(model_id)
    if not model:
        return []
    
    supports = model.get('supports', {})
    required = []
    
    # Prompt siempre requerido si soporta text-to-video o text-to-image
    if supports.get('text_to_video') or supports.get('text_to_image') or supports.get('text_to_speech'):
        required.append('prompt')
    
    # Start image requerido si solo soporta image-to-video
    if supports.get('image_to_video') and not supports.get('text_to_video'):
        required.append('start_image')
    
    # Avatar ID requerido para HeyGen
    if supports.get('avatar_id') and model.get('service') == 'heygen':
        required.append('avatar_id')
    
    # Voice ID requerido para HeyGen y Vuela.ai
    if supports.get('voice_id') and model.get('service') in ['heygen', 'vuela_ai']:
        required.append('voice_id')
    
    return required

