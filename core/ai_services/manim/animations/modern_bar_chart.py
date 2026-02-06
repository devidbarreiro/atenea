"""
Animación de Gráfico de Barras Moderno (Card style) con Manim
"""
from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation
import json
import logging

logger = logging.getLogger(__name__)

@register_animation('modern_bar_chart')
class ModernBarChartAnimation(BaseManimAnimation):
    """Gráfico de barras minimalista sin ejes, estilo tarjeta"""
    
    
    def get_animation_type(self) -> str:
        return 'modern_bar_chart'

    @classmethod
    def get_parameters(cls) -> dict:
        return {
            "title": {
                "type": "string",
                "description": "Título del gráfico",
                "default": ""
            },
            "values": {
                "type": "list<float>",
                "description": "Lista de valores numéricos para las barras",
                "default": [60, 80, 45, 90],
                "required": True
            },
            "labels": {
                "type": "list<string>",
                "description": "Etiquetas inferiores (A, B, C...)",
                "default": ["A", "B", "C", "D"]
            },
            "bar_colors": {
                "type": "list<string>",
                "description": "Lista de colores hex para las barras",
                "default": ["#3B82F6", "#6366F1", "#8B5CF6", "#EC4899"]
            },
            "show_labels": {
                "type": "boolean",
                "description": "Mostrar valores numéricos sobre las barras",
                "default": True
            },
            "top_texts": {
                "type": "list<string>",
                "description": "Textos personalizados sobre las barras (opcional)",
                "default": []
            },
            "bar_width": {
                "type": "float",
                "description": "Ancho relativo de las barras (0.1 a 1.0)",
                "default": 0.8
            },
            "container_color": {
                "type": "string",
                "description": "Color de fondo (hex)",
                "default": "#1E293B"
            },
            "text_color": {
                "type": "string",
                "description": "Color del texto (hex)",
                "default": "#FFFFFF"
            }
        }
    
    def construct(self):
        # 1. Obtener datos
        prompt_text = self._get_config_value('text', '{}')
        try:
            data_config = json.loads(prompt_text) if prompt_text and prompt_text.strip() and prompt_text.strip().startswith('{') else {}
        except (json.JSONDecodeError, AttributeError):
            data_config = {}
            
        # Helper para obtener parámetros (prioridad: config directo > json en text > default)
        def get_param(key, default=None):
            val = self._get_config_value(key)
            if val is not None:
                return val
            return data_config.get(key, default)
            
        raw_values = get_param('values', [60, 80, 45, 90])
        
        # Validate/Coerce values to numeric
        values = []
        if isinstance(raw_values, list):
            for v in raw_values:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    continue
        
        if not values:
            logger.warning("[MODERN_BARCHART] No valid numeric values found. Using defaults.")
            values = [60, 80, 45, 90]

        labels = get_param('labels', ["A", "B", "C", "D"])
        title_str = get_param('title', '')
        bar_colors = get_param('bar_colors', ["#3B82F6", "#6366F1", "#8B5CF6", "#EC4899"])
        show_labels = get_param('show_labels', True)
        top_texts = get_param('top_texts', [])
        user_bar_width = get_param('bar_width', 0.8)
        
        # Colores y fuentes
        bg_color = self._get_config_value('container_color', '#1E293B')
        text_color = self._get_config_value('text_color', '#FFFFFF')
        font_family = self._get_config_value('font_family', 'Arial')
        
        self.camera.background_color = bg_color
        
        # 2. Configurar contenedores
        # Tarjeta principal (opcional, si queremos un recuadro interno)
        card = RoundedRectangle(
            corner_radius=0.3, 
            height=6.5, 
            width=11, 
            fill_color=bg_color, 
            fill_opacity=1, 
            stroke_color=WHITE, 
            stroke_opacity=0.1
        )
        
        # 3. Dibujar Barras
        n_bars = len(values)
        if n_bars == 0: return

        chart_height = 4.5
        chart_width = 9
        
        # --- Safeguards ---
        max_val = max(values) if values else 1
        if max_val == 0:
            max_val = 1 # Prevent division by zero if all values are 0
            
        # Ensure bar_colors is a valid non-empty list
        if isinstance(bar_colors, str):
            bar_colors = [bar_colors]
        if not bar_colors or not isinstance(bar_colors, list):
            bar_colors = ["#3B82F6", "#6366F1", "#8B5CF6", "#EC4899"] # Default Palette
        
        # Espaciado
        user_bar_width = data_config.get('bar_width', self._get_config_value('bar_width', 0.8))
        bar_spacing = chart_width / max(1, n_bars)
        bar_width = bar_spacing * user_bar_width
        
        bars = VGroup()
        bar_labels = VGroup()
        bar_values = VGroup()
        
        for i, val in enumerate(values):
            # Color
            color = bar_colors[i % len(bar_colors)]
            
            # Altura proporcional
            h = (val / max_val) * chart_height
            
            # Crear Barra
            rect = RoundedRectangle(
                corner_radius=0.1,
                height=h,
                width=bar_width,
                fill_color=color,
                fill_opacity=1,
                stroke_width=0
            )
            
            # Posicionar (alinear base abajo)
            x_pos = -chart_width/2 + (i + 0.5) * bar_spacing
            rect.move_to([x_pos, -chart_height/2 + h/2, 0])
            bars.add(rect)
            
            # Etiqueta inferior
            if i < len(labels):
                lbl = Text(labels[i], font=font_family, font_size=20, color=text_color, weight="BOLD")
                lbl.next_to(rect, DOWN, buff=0.3)
                bar_labels.add(lbl)
            
            # Valor superior
            if show_labels:
                display_val = top_texts[i] if (i < len(top_texts) and top_texts[i]) else str(val)
                v_lbl = Text(display_val, font=font_family, font_size=24, color=text_color, weight="NORMAL")
                v_lbl.next_to(rect, UP, buff=0.2)
                bar_values.add(v_lbl)

        # 4. Título
        title = Text(title_str, font=font_family, font_size=40, color=text_color, weight="BOLD")
        title.to_edge(UP, buff=0.6)
        
        # 5. Animación
        self.add(card)
        if title_str:
            self.play(Write(title))
        
        self.play(
            AnimationGroup(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0, run_time=1.5),
            FadeIn(bar_labels, shift=UP * 0.3, run_time=1),
        )
        
        if show_labels:
            self.play(FadeIn(bar_values, scale=1.2))
            
        self.wait(3)
