"""
Sistema de registro de animaciones Manim
Permite registrar y obtener clases de animación por tipo
"""
from typing import Dict, Type, Optional
from .base import BaseManimAnimation


class AnimationRegistry:
    """
    Registro centralizado de todas las animaciones disponibles
    """
    _animations: Dict[str, Type[BaseManimAnimation]] = {}
    
    @classmethod
    def register(cls, animation_type: str, animation_class: Type[BaseManimAnimation]):
        """
        Registra una clase de animación
        
        Args:
            animation_type: Tipo de animación (ej: 'quote', 'bar_chart')
            animation_class: Clase que hereda de BaseManimAnimation
        """
        if not issubclass(animation_class, BaseManimAnimation):
            raise ValueError(f"{animation_class.__name__} debe heredar de BaseManimAnimation")
        
        cls._animations[animation_type] = animation_class
    
    @classmethod
    def get(cls, animation_type: str) -> Optional[Type[BaseManimAnimation]]:
        """
        Obtiene una clase de animación por tipo
        
        Args:
            animation_type: Tipo de animación
        
        Returns:
            Clase de animación o None si no existe
        """
        return cls._animations.get(animation_type)
    
    @classmethod
    def list_types(cls) -> list:
        """
        Lista todos los tipos de animaciones registradas
        
        Returns:
            Lista de tipos de animaciones
        """
        return list(cls._animations.keys())
    
    @classmethod
    def is_registered(cls, animation_type: str) -> bool:
        """
        Verifica si un tipo de animación está registrado
        
        Args:
            animation_type: Tipo de animación
        
        Returns:
            True si está registrado, False en caso contrario
        """
        return animation_type in cls._animations


def register_animation(animation_type: str):
    """
    Decorador para registrar una clase de animación
    
    Uso:
        @register_animation('quote')
        class QuoteAnimation(BaseManimAnimation):
            ...
    
    Args:
        animation_type: Tipo de animación
    """
    def decorator(cls: Type[BaseManimAnimation]):
        AnimationRegistry.register(animation_type, cls)
        return cls
    return decorator

