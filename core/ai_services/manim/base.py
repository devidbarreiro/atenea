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
    
    Los parámetros se pasan al constructor para evitar problemas de concurrencia
    con variables de entorno compartidas.
    """
    
    def __init__(self, config: dict = None, **kwargs):
        """
        Inicializa la animación con configuración
        
        Args:
            config: Dict con la configuración de la animación
            **kwargs: Argumentos adicionales para Scene
        """
        super().__init__(**kwargs)
        self._config = config or {}
    
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
    
    def _get_config_value(self, key: str, default=None):
        """
        Obtiene un valor de configuración desde self._config
        
        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe
        
        Returns:
            Valor de configuración o default
        """
        return self._config.get(key, default)
    
    def _get_config(self) -> dict:
        """
        Obtiene toda la configuración de la animación
        
        Returns:
            Dict con la configuración
        """
        return self._config.copy()
    
    # Métodos legacy para compatibilidad (deprecated)
    def _get_env_var(self, key: str, default=None, decode_base64: bool = False):
        """
        DEPRECATED: Usa _get_config_value() en su lugar.
        
        Mantenido para compatibilidad temporal. Lee desde self._config
        en lugar de variables de entorno para evitar problemas de concurrencia.
        """
        # Mapear nombres de variables de entorno a claves de config
        config_key = key.replace('QUOTE_ANIMATION_', '').lower()
        
        # Si no está en config, intentar desde env (fallback legacy)
        value = self._config.get(config_key, os.environ.get(key, default))
        
        if decode_base64 and value and value != "None":
            # Verificar si está codificado
            encoded_key = f'{key}_ENCODED'
            is_encoded = self._config.get(f'{config_key}_encoded', False) or os.environ.get(encoded_key, '0') == '1'
            if is_encoded:
                try:
                    value = base64.b64decode(value.encode('ascii')).decode('utf-8')
                except:
                    pass
        
        if value == "None":
            return None
        
        return value
    
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

