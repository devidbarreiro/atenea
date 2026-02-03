"""
Animación de Gráfico de Línea Minimalista con Manim
"""
from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation
import json
import logging

logger = logging.getLogger(__name__)

@register_animation('line_chart')
class LineChartAnimation(BaseManimAnimation):
    """Gráfico de líneas elegante y minimalista"""
    
    def get_animation_type(self) -> str:
        return 'line_chart'
    
    def construct(self):
        # 1. Obtener y procesar datos
        prompt_text = self._get_config_value('text', '{}')
        try:
            data_config = json.loads(prompt_text) if prompt_text.strip() else {}
        except json.JSONDecodeError:
            data_config = {}
            
        # Datos por defecto si no hay input válido
        raw_values = data_config.get('values', [20, 55, 40, 75, 60, 90])
        labels = data_config.get('labels', ["Ene", "Feb", "Mar", "Abr", "May", "Jun"])
        title_str = data_config.get('title', 'Evolución Mensual')
        line_color = data_config.get('line_color', "#000000") # Negro
        point_color = data_config.get('point_color', "#FFFFFF")
        point_radius = data_config.get('point_radius', 0.1) # Default bigger than dot
        line_width = data_config.get('line_width', 4)
        
        # Validar valores numéricos
        values = []
        for v in raw_values:
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                continue
                
        if not values:
            values = [20, 55, 40, 75, 60, 90]

        # Configuración visual
        bg_color = self._get_config_value('container_color', '#1E293B')
        text_color = self._get_config_value('text_color', '#FFFFFF')
        font_family = self._get_config_value('font_family', 'Arial')
        
        self.camera.background_color = bg_color

        # 2. Configurar dimensiones y escalas
        chart_width = 10
        chart_height = 5
        
        max_val = max(values) if values else 100
        min_val = min(values) if values else 0
        val_range = max_val - min_val if max_val != min_val else 10
        
        # Ajustar rango para que no toque los bordes exactos (margen vertical 10%)
        y_bottom = 0 # Asumimos base 0 para visualización más limpia, o min_val si queremos zoom
        y_top = max_val * 1.1
        
        # Función para mapear valor a coordenada Y local
        def get_y(val):
            # Mapea 0..y_top a -height/2..height/2
            ratio = val / y_top
            return -chart_height/2 + (ratio * chart_height)

        # Espaciado horizontal
        n_points = len(values)
        x_step = chart_width / (n_points + 1) if n_points > 0 else 1
        
        def get_x(index):
            return -chart_width/2 + (index + 1) * x_step

        # 3. Crear Elementos
        
        # Ejes o línea base (solo horizontal para minimalismo)
        # base_line removido a petición de usuario ("eliminar ejes")
        
        # Puntos y Línea conectora
        points = []
        dots = VGroup()
        
        for i, val in enumerate(values):
            x = get_x(i)
            y = get_y(val)
            point = [x, y, 0]
            points.append(point)
            
            # Punto visual
            dot = Dot(point, color=point_color, radius=point_radius)
            dot.set_stroke(color=line_color, width=line_width/2) # Anillo proporcional
            dots.add(dot)
            
            # Etiqueta X (Labels)
            if i < len(labels):
                lbl = Text(labels[i], font=font_family, font_size=20, color=text_color, weight="BOLD")
                lbl.next_to([x, -chart_height/2, 0], DOWN, buff=0.3)
                self.add(lbl) # Añadir directo o agrupar para animar
        
        # Crear la línea suave (polilínea)
        if len(points) > 1:
            line_graph = VMobject()
            line_graph.set_points_as_corners(points)
            # Opcional: hacerla curva con .make_smooth() pero a veces distorsiona datos precisos
            # line_graph.make_smooth() 
            line_graph.set_color(line_color)
            line_graph.set_stroke(width=line_width)
        else:
            line_graph = VGroup() # Vacío si solo hay 1 punto

        # Área bajo la curva (opcional para efecto "chart elegante")
        area = VGroup()
        if len(points) > 1:
            # Crear polígono para cerrar el área
            area_points = points.copy()
            area_points.append([points[-1][0], -chart_height/2, 0]) # Bajar al eje
            area_points.append([points[0][0], -chart_height/2, 0])  # Volver al inicio eje
            
            area_poly = Polygon(*area_points)
            area_poly.set_stroke(width=0)
            area_poly.set_fill(line_color, opacity=0.15)
            area.add(area_poly)

        # Título
        title = Text(title_str, font=font_family, font_size=40, color=text_color, weight="BOLD")
        title.to_edge(UP, buff=0.8)

        # 4. Animación
        self.play(Write(title))
        
        # Animar la línea dibujándose de izq a derecha
        self.play(
            Create(line_graph, run_time=2, rate_func=linear),
            FadeIn(area, run_time=2),
            lag_ratio=0
        )
        
        # Mostrar puntos uno por uno siguiendo la línea o de golpe
        self.play(
            FadeIn(dots, scale=0.5, lag_ratio=0.1, run_time=1)
        )
        
        self.wait(2)
