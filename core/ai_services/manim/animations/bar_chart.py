"""
Animación de Gráfico de Barras con Manim
"""
from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation


@register_animation('bar_chart')
class BarChartAnimation(BaseManimAnimation):
    """Animación de gráfico de barras personalizable"""
    
    def get_animation_type(self) -> str:
        return 'bar_chart'
    
    def construct(self):
        import json
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG-BARCHART] Starting construct. Config: {self._config}")
        
        # 1. Obtener datos del prompt (JSON)
        prompt_text = self._get_config_value('text', '{}')
        try:
            # Intentar parsear JSON
            data_config = json.loads(prompt_text) if prompt_text.strip() else {}
        except json.JSONDecodeError:
            # Fallback si no es JSON válido: tratar como texto simple o usar default
            data_config = {}
            if prompt_text:
                # Si el usuario escribió texto plano, intentar inferir (ej: "A,10;B,20")
                # Por ahora, usar default
                pass
        
        # 2. Configuración predeterminada / Merge de JSON
        # Prioridad: data_config (lo que viene del sidebar actualmente) > settings de base
        
        # --- ROBUST INPUT HANDLING ---
        # Retrieve raw values first
        raw_values = data_config.get('values', self._get_config_value('values', [10, 20, 30, 40]))
        
        # Validate/Coerce values to float/int
        if not isinstance(raw_values, list):
            # If it's a string (e.g. "10,20,30"), try to split (though JSON load should handle standard lists)
            if isinstance(raw_values, str):
                try:
                    raw_values = [float(x.strip()) for x in raw_values.split(',') if x.strip()]
                except ValueError:
                    raw_values = []
            else:
                raw_values = [] # Unrecognized format

        # Filter out non-numeric entries (just in case) and convert
        clean_values = []
        for v in raw_values:
            try:
                clean_values.append(float(v))
            except (ValueError, TypeError):
                continue
                
        # Handle empty or invalid values list (Avoid Manim crash on empty chart)
        if not clean_values:
            logger.warning("[BARCHART] No valid numeric values found. Using default placeholder.")
            clean_values = [0]
            
        values = clean_values
        
        # Sync labels length with validated values
        raw_labels = data_config.get('labels', self._get_config_value('labels', ["Q1", "Q2", "Q3", "Q4"]))
        if not isinstance(raw_labels, list):
             raw_labels = [str(raw_labels)]
             
        # Labels should match values count. If fewer labels, cycle or use blank? 
        # Better: use what we have, fill rest with empty, or truncate.
        # Original logic was truncating. Let's truncate or extend safely.
        
        labels = []
        for i in range(len(values)):
            if i < len(raw_labels):
                labels.append(str(raw_labels[i]))
            else:
                labels.append(f"Label {i+1}")
                
        title_str = data_config.get('title', self._get_config_value('title', ' '))
        y_label = data_config.get('y_axis_label', data_config.get('y_label', 'Valores')) # Support both keys
        x_label = data_config.get('x_axis_label', data_config.get('x_label', 'Categorías')) # Support both keys
        
        # Si bar_colors viene como lista de hex strings en JSON, Manim los aceptará directamente
        bar_colors = data_config.get('bar_colors', self._get_config_value('bar_colors', [BLUE, GREEN, YELLOW, RED]))
        if isinstance(bar_colors, str):
            bar_colors = [bar_colors]
        if not bar_colors: # If empty list
             bar_colors = [BLUE]
        
        # --- Configuración de Fuente ---
        font_family = self._get_config_value('font_family', 'Arial')
        font_style = self._get_config_value('font_style', 'normal')
        
        # Mapeo de estilos a constantes de Manim (si es posible) o kwargs
        # Nota: Manim usa weight y slant.
        text_kwargs = {'font': font_family}
        
        if font_style == 'bold':
            text_kwargs['weight'] = BOLD
        elif font_style == 'italic':
            text_kwargs['slant'] = ITALIC
        elif font_style == 'bold_italic':
            text_kwargs['weight'] = BOLD
            text_kwargs['slant'] = ITALIC
            
        # Color de texto global
        text_color_hex = self._get_config_value('text_color', '#FFFFFF')
        text_kwargs['color'] = text_color_hex
        
        # 4. Crear Gráfico
        bar_width = data_config.get('bar_width', self._get_config_value('bar_width', 0.8))
        
        chart = BarChart(
            values=values,
            bar_names=labels,
            y_range=[0, max(values) * 1.2, max(values) // 5 or 1],
            y_length=6,
            x_length=10,
            x_axis_config={"font_size": 24, "label_constructor": Text, "color": text_color_hex},
            y_axis_config={"label_constructor": Text, "color": text_color_hex},
            bar_colors=bar_colors,  # Cycle colors
            bar_width=bar_width,
        )
        
        # Forzar estilos en las etiquetas de los ejes si es necesario
        # (Esto es complejo en Manim pre-renderizado, pero intentamos con kwargs arriba)

        # Título
        title = Text(title_str, font_size=48, **text_kwargs).to_edge(UP)
        
        # Axis Labels Manuales (si los usas aparte, heredar diseño)
        x_axis_label = Text(x_label, font_size=24, **text_kwargs).next_to(chart.x_axis, DOWN)
        # Rotar label Y pero mantener estilo
        y_axis_label = Text(y_label, font_size=24, **text_kwargs).rotate(PI/2).next_to(chart.y_axis, LEFT)
        
        # 5. Animación
        bg_color = self._get_config_value('container_color', '#ECEFF1')
        self.camera.background_color = bg_color # Usar cámara directamente o setup_background
        
        # Intro
        self.play(Write(title))
        self.play(Create(chart), run_time=2)
        self.play(FadeIn(x_axis_label), FadeIn(y_axis_label))
        
        # Mostrar valores encima de las barras (opcional)
        show_labels = data_config.get('show_labels', self._get_config_value('show_labels', True))
        bar_top_texts = data_config.get('top_texts', self._get_config_value('top_texts', []))
        
        if show_labels:
            if any(bar_top_texts):
                # Texto personalizado superior
                anims = []
                for i, txt in enumerate(bar_top_texts):
                    if i < len(chart.bars) and txt:
                        # Usar mismo estilo de fuente, quizás color distinto (negro por defecto en barras claras? o text_color?)
                        # User pidió "labels bonitos" con color de texto. Usaremos text_color global.
                        t = Text(str(txt), font_size=24, **text_kwargs).next_to(chart.bars[i], UP)
                        anims.append(Write(t))
                if anims:
                    self.play(*anims)
            else:
                # get_bar_labels retorna mobjects.
                # IMPORTANTE: Forzar label_constructor=Text para evitar dependencia de LaTeX/MathTex
                try:
                    bar_labels = chart.get_bar_labels(label_constructor=Text, font_size=24)
                    # Aplicar color manualmente si es posible
                    bar_labels.set_color(text_color_hex)
                    self.play(Write(bar_labels))
                except Exception as e:
                    logger.error(f"Error al animar etiquetas por defecto: {e}")
        
        self.wait(2)

