"""
Módulo Manim para generar videos animados
Arquitectura escalable para múltiples tipos de animaciones

Uso básico:
    from core.ai_services.manim import ManimClient
    
    client = ManimClient()
    result = client.generate_video(
        animation_type='quote',
        config={'text': 'Mi cita', 'author': 'Autor'},
        quality='k'
    )
"""
# Importar animaciones para que se registren automáticamente
from . import animations  # noqa: F401

from .client import ManimClient
from .base import BaseManimAnimation
from .registry import AnimationRegistry, register_animation

__all__ = [
    'ManimClient',
    'BaseManimAnimation',
    'AnimationRegistry',
    'register_animation',
]

