"""
Clase base para todas las animaciones de Manim
Proporciona funcionalidades comunes y estructura estándar
"""
import os
import base64
from abc import ABC, abstractmethod

# Intentar importar manim - si falla, se usará cuando manim importe el módulo
try:
    from manim import *
except ImportError:
    # Stubs para que el código no falle si manim no está disponible
    class Scene:
        pass
    NORMAL = "normal"
    ITALIC = "italic"
    UP = (0, 1, 0)
    LEFT = (-1, 0, 0)
    RIGHT = (1, 0, 0)


class BaseManimAnimation(Scene, ABC):
    """
    Clase base abstracta para todas las animaciones de Manim
    
    Todas las animaciones deben heredar de esta clase e implementar:
    - construct(): Método principal que define la animación
    - get_animation_type(): Retorna el tipo de animación (ej: 'quote', 'bar_chart')
    """
    
    def _fix_encoding(self, text):
        """Repara caracteres mal codificados comunes"""
        if not text:
            return text
        
        fixes = {
            'Ã±': 'ñ', 'Ã³': 'ó', 'Ã¡': 'á', 'Ã©': 'é', 
            'Ã­': 'í', 'Ãº': 'ú', 'Ã': 'Á', 'Ã': 'É',
            'Ã': 'Í', 'Ã': 'Ó', 'Ã': 'Ú', 'Ã': 'Ñ'
        }
        
        result = text
        for wrong, correct in fixes.items():
            result = result.replace(wrong, correct)
        
        if '' in result:
            try:
                result = result.encode('latin-1').decode('utf-8')
            except:
                pass
        
        return result
    
    def _get_env_var(self, key: str, default=None, decode_base64: bool = False):
        """
        Obtiene una variable de entorno, opcionalmente decodificando desde base64
        
        Args:
            key: Nombre de la variable de entorno
            default: Valor por defecto si no existe
            decode_base64: Si True, intenta decodificar desde base64
        
        Returns:
            Valor de la variable de entorno o default
        """
        value = os.environ.get(key, default)
        
        if decode_base64 and value and value != "None":
            is_encoded = os.environ.get(f'{key}_ENCODED', '0') == '1'
            if is_encoded:
                try:
                    value = base64.b64decode(value.encode('ascii')).decode('utf-8')
                except:
                    pass
        
        if value == "None":
            return None
        
        return value
    
    def _get_config(self) -> dict:
        """
        Obtiene la configuración de la animación desde variables de entorno
        
        Returns:
            Dict con la configuración
        """
        animation_type = self.get_animation_type()
        prefix = f'{animation_type.upper()}_ANIMATION'
        
        config = {}
        
        # Leer todas las variables de entorno con el prefijo
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key.replace(f'{prefix}_', '').lower()
                config[config_key] = value
        
        return config
    
    @abstractmethod
    def construct(self):
        """
        Método principal que define la animación
        Debe ser implementado por cada tipo de animación
        """
        pass
    
    @abstractmethod
    def get_animation_type(self) -> str:
        """
        Retorna el tipo de animación (ej: 'quote', 'bar_chart', 'histogram')
        
        Returns:
            String con el tipo de animación
        """
        pass
    
    def setup_background(self, color: str = "#D3D3D3"):
        """Configura el color de fondo de la escena"""
        self.camera.background_color = color

