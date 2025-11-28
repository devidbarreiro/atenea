"""
EJEMPLO: Cómo crear una nueva animación Manim

Este archivo muestra la estructura para crear nuevas animaciones.
Copia este archivo y renómbralo según tu tipo de animación (ej: histogram.py, bar_chart.py)

Pasos:
1. Copia este archivo y renómbralo
2. Cambia el nombre de la clase
3. Implementa get_animation_type() retornando el tipo único
4. Implementa construct() con tu lógica de animación
5. Usa @register_animation('tipo') para registrarla
6. Importa el módulo en animations/__init__.py
"""

from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation


@register_animation('example')  # Cambia 'example' por tu tipo único (ej: 'histogram', 'bar_chart')
class ExampleAnimation(BaseManimAnimation):
    """
    Descripción de tu animación
    
    Ejemplo: Animación de histograma que muestra distribución de datos
    """
    
    def get_animation_type(self) -> str:
        """Retorna el tipo único de esta animación"""
        return 'example'  # Cambia por tu tipo
    
    def construct(self):
        """
        Método principal que define la animación
        Aquí va toda la lógica de tu animación
        """
        # Obtener configuración desde variables de entorno
        # Las variables estarán con el prefijo: {TIPO}_ANIMATION_{PARAMETRO}
        # Ejemplo para 'histogram': HISTOGRAM_ANIMATION_DATA, HISTOGRAM_ANIMATION_TITLE, etc.
        
        # Ejemplo: obtener datos
        data_str = self._get_env_var('EXAMPLE_ANIMATION_DATA', '[]')
        title = self._get_env_var('EXAMPLE_ANIMATION_TITLE', 'Título', decode_base64=True)
        color = self._get_env_var('EXAMPLE_ANIMATION_COLOR', '#3498DB')
        
        # Configurar fondo
        self.setup_background("#FFFFFF")
        
        # === TU LÓGICA DE ANIMACIÓN AQUÍ ===
        # Ejemplo básico:
        text = Text(title, font_size=48)
        text.move_to(ORIGIN)
        
        self.play(Write(text))
        self.wait(2)
        self.play(FadeOut(text))
        
        # === FIN DE TU ANIMACIÓN ===
    
    # Puedes añadir métodos auxiliares privados aquí
    # Ejemplo:
    # def _create_chart(self, data):
    #     """Crea un gráfico a partir de datos"""
    #     pass


# NOTAS IMPORTANTES:
# 
# 1. REGISTRO AUTOMÁTICO:
#    - El decorador @register_animation() registra automáticamente tu animación
#    - Asegúrate de importar el módulo en animations/__init__.py
#
# 2. VARIABLES DE ENTORNO:
#    - Usa self._get_env_var() para obtener configuración
#    - Para strings con caracteres especiales, usa decode_base64=True
#    - El prefijo será {TIPO}_ANIMATION_ (ej: HISTOGRAM_ANIMATION_TITLE)
#
# 3. MÉTODOS ÚTILES DE BaseManimAnimation:
#    - self._fix_encoding(text): Repara encoding de texto
#    - self._get_env_var(key, default, decode_base64): Obtiene variables de entorno
#    - self._get_config(): Obtiene toda la configuración como dict
#    - self.setup_background(color): Configura el color de fondo
#
# 4. USO DESDE ManimClient:
#    client = ManimClient()
#    result = client.generate_video(
#        animation_type='example',  # Tu tipo único
#        config={
#            'data': [1, 2, 3, 4, 5],
#            'title': 'Mi Gráfico',
#            'color': '#3498DB',
#        },
#        quality='k'
#    )
#
# 5. INTEGRACIÓN CON VideoService:
#    - En core/services.py, añade un caso en _generate_manim_quote_video()
#    - O crea un método genérico que use ManimClient.generate_video()
#
# 6. TESTING:
#    - Puedes probar tu animación directamente:
#      MANIM_ANIMATION_TYPE=example python -m manim core/ai_services/manim/render_wrapper.py ExampleAnimation
#    - O usando el cliente:
#      from core.ai_services.manim import ManimClient
#      client = ManimClient()
#      client.generate_video('example', {'title': 'Test'})

