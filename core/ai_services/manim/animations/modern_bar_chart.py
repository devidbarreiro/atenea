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
    
    def construct(self):
        # 1. Obtener datos
        prompt_text = self._get_config_value('text', '{}')
        logger.info(f"[DEBUG-MODERN-BARCHART] prompt_text recibido: {prompt_text[:200] if prompt_text else 'None'}")
        try:
            data_config = json.loads(prompt_text) if prompt_text.strip() else {}
            logger.info(f"[DEBUG-MODERN-BARCHART] data_config parseado: {data_config}")
        except json.JSONDecodeError as e:
            logger.error(f"[DEBUG-MODERN-BARCHART] Error parseando JSON: {e}")
            data_config = {}
            
        values = data_config.get('values', [60, 80, 45, 90])
        labels = data_config.get('labels', ["A", "B", "C", "D"])
        title_str = data_config.get('title', '')
        bar_colors = data_config.get('bar_colors', ["#3B82F6", "#6366F1", "#8B5CF6", "#EC4899"])
        show_labels = data_config.get('show_labels', True)
        top_texts = data_config.get('top_texts', [])
        
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
        max_val = max(values) if values else 1
        
        # Espaciado
        user_bar_width = data_config.get('bar_width', self._get_config_value('bar_width', 0.8))
        bar_spacing = chart_width / (n_bars + 1)
        bar_width = min(0.9, bar_spacing * user_bar_width)
        
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
            x_pos = -chart_width/2 + (i + 1) * bar_spacing
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
            Create(bars, run_time=1.5, lag_ratio=0.2),
            FadeIn(bar_labels, shift=UP * 0.3, run_time=1),
        )
        
        if show_labels:
            self.play(FadeIn(bar_values, scale=1.2))
            
        self.wait(3)
