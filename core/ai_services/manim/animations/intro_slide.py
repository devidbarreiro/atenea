"""
Animación de cortinilla de entrada (intro slide)
Crea slides minimalistas estilo presentación educativa
"""
from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation


@register_animation('intro_slide')
class IntroSlideAnimation(BaseManimAnimation):
    """Animación de cortinilla de entrada profesional"""
    
    
    def get_animation_type(self) -> str:
        return 'intro_slide'

    @classmethod
    def get_parameters(cls) -> dict:
        return {
            "title": {
                "type": "string",
                "description": "Título principal (parte superior)",
                "required": True
            },
            "central_text": {
                "type": "string",
                "description": "Texto central destacado",
                "default": ""
            },
            "footer": {
                "type": "string",
                "description": "Texto al pie (parte inferior)",
                "default": ""
            },
            "bg_color": {
                "type": "string",
                "description": "Color de fondo principal (hex)",
                "default": "#E5E5E5"
            },
            "title_color": {
                "type": "string",
                "description": "Color del título (hex)",
                "default": "#1A1A1A"
            },
            "central_text_color": {
                "type": "string",
                "description": "Color del texto central (hex)",
                "default": "#1A1A1A"
            }
        }
    
    def construct(self):
        # Obtener datos desde configuración
        title = self._get_config_value('title', '')
        central_text = self._get_config_value('central_text', '')
        footer = self._get_config_value('footer', '')
        duration = self._get_config_value('duration', 5.0)
        display_time = self._get_config_value('display_time')
        
        # Validar y reparar encoding
        if not title or not title.strip():
            raise ValueError("El título no puede estar vacío")
        
        title = self._fix_encoding(title)
        if central_text:
            central_text = self._fix_encoding(central_text)
        if footer:
            footer = self._fix_encoding(footer)
        
        # Validar duración
        if isinstance(duration, str):
            try:
                duration = float(duration)
            except ValueError:
                duration = 5.0
        if duration <= 0:
            duration = 5.0
        
        # Validar display_time
        if display_time is not None:
            if isinstance(display_time, str):
                try:
                    display_time = float(display_time)
                except ValueError:
                    display_time = None
            if display_time is not None and display_time <= 0:
                display_time = None
        
        # Colores personalizables
        bg_color = self._get_config_value('bg_color', '#E5E5E5')  # Gris claro
        title_color = self._get_config_value('title_color', '#1A1A1A')  # Casi negro
        central_text_color = self._get_config_value('central_text_color', '#1A1A1A')
        footer_color = self._get_config_value('footer_color', '#666666')  # Gris medio
        circle_color = self._get_config_value('circle_color', '#D0D0D0')  # Gris muy claro
        
        # Configurar fondo con gradiente sutil
        self.setup_background(bg_color)
        
        # Crear gradiente radial sutil (simulado con círculos superpuestos)
        gradient_center = Circle(
            radius=8,
            fill_opacity=0.15,
            stroke_width=0,
            fill_color=WHITE
        )
        gradient_center.move_to(ORIGIN)
        
        gradient_outer = Circle(
            radius=10,
            fill_opacity=0.05,
            stroke_width=0,
            fill_color=WHITE
        )
        gradient_outer.move_to(ORIGIN)
        
        # Crear título (arriba)
        title_text = Text(
            title,
            font_size=42,
            color=title_color,
            weight='BOLD',
            font='Arial'
        )
        title_text.move_to(UP * 2.8)
        
        # Crear texto central con círculo sutil alrededor
        if central_text:
            central_text_obj = Text(
                central_text,
                font_size=36,
                color=central_text_color,
                weight='NORMAL',
                font='Arial'
            )
            central_text_obj.move_to(ORIGIN)
            
            # Círculo sutil alrededor del texto central
            # Calcular tamaño del círculo basado en el texto
            text_width = central_text_obj.width
            text_height = central_text_obj.height
            circle_radius = max(text_width, text_height) * 0.6 + 0.8
            
            central_circle = Circle(
                radius=circle_radius,
                stroke_width=2,
                stroke_color=circle_color,
                stroke_opacity=0.3,
                fill_opacity=0
            )
            central_circle.move_to(central_text_obj.get_center())
        else:
            central_text_obj = None
            central_circle = None
        
        # Crear footer (abajo)
        footer_text = None
        if footer:
            footer_text = Text(
                footer,
                font_size=24,
                color=footer_color,
                weight='NORMAL',
                font='Arial'
            )
            footer_text.move_to(DOWN * 2.8)
        
        # === ANIMACIONES ===
        # Fade in del gradiente de fondo
        self.play(
            FadeIn(gradient_outer),
            FadeIn(gradient_center),
            run_time=0.8,
            rate_func=smooth
        )
        
        # Entrada del título (desde arriba)
        title_text.shift(UP * 0.5)
        self.play(
            title_text.animate.shift(DOWN * 0.5),
            FadeIn(title_text),
            run_time=0.6,
            rate_func=smooth
        )
        
        self.wait(0.2)
        
        # Entrada del texto central con círculo
        if central_text_obj and central_circle:
            # Escalar desde el centro
            central_circle.scale(0.3)
            central_text_obj.set_opacity(0)
            
            self.play(
                GrowFromCenter(central_circle),
                FadeIn(central_text_obj),
                run_time=0.8,
                rate_func=smooth
            )
        
        self.wait(0.2)
        
        # Entrada del footer (desde abajo)
        if footer_text:
            footer_text.shift(DOWN * 0.3)
            self.play(
                footer_text.animate.shift(UP * 0.3),
                FadeIn(footer_text),
                run_time=0.5,
                rate_func=smooth
            )
        
        # Calcular tiempo de visualización
        animation_time = 0.8 + 0.6 + 0.2 + 0.8 + 0.2 + 0.5  # Suma de todas las animaciones
        if display_time is not None:
            wait_time = display_time
        else:
            wait_time = max(2.0, duration - animation_time)
        
        # Tiempo de visualización en pantalla
        self.wait(wait_time)
        
        # Salida suave (fade out de todos los elementos)
        fade_out_objects = [title_text, gradient_center, gradient_outer]
        if central_text_obj:
            fade_out_objects.append(central_text_obj)
        if central_circle:
            fade_out_objects.append(central_circle)
        if footer_text:
            fade_out_objects.append(footer_text)
        
        self.play(
            *[FadeOut(obj) for obj in fade_out_objects],
            run_time=0.8,
            rate_func=smooth
        )

