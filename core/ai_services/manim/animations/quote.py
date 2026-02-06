"""
Animación de citas con Manim
Muestra texto con autor opcional en una tarjeta animada
"""
from manim import *
from ..base import BaseManimAnimation
from ..registry import register_animation


@register_animation('quote')
class QuoteAnimation(BaseManimAnimation):
    """Animación de cita profesional"""
    
    
    def get_animation_type(self) -> str:
        return 'quote'

    @classmethod
    def get_parameters(cls) -> dict:
        return {
            "text": {
                "type": "string",
                "description": "Texto principal de la cita",
                "required": True
            },
            "author": {
                "type": "string",
                "description": "Autor de la cita (opcional)",
                "default": None
            },
            "container_color": {
                "type": "string",
                "description": "Color de fondo de la tarjeta (hex)",
                "default": "#0066CC"
            },
            "text_color": {
                "type": "string",
                "description": "Color del texto (hex)",
                "default": "#FFFFFF"
            },
            "font_family": {
                "type": "string",
                "description": "Estilo de fuente ('normal', 'bold', 'italic', 'bold_italic')",
                "default": "normal"
            }
        }
    
    def construct(self):
        # Obtener datos desde configuración (pasada al constructor)
        quote = self._get_config_value('text', '')
        author = self._get_config_value('author')
        duration = self._get_config_value('duration')
        display_time = self._get_config_value('display_time')
        
        # Validar y reparar encoding si es necesario
        if not quote or not quote.strip():
            raise ValueError("El texto de la cita no puede estar vacío")
        
        quote = self._fix_encoding(quote)
        if author:
            author = self._fix_encoding(author)
        
        # Validar duración si se proporciona
        if duration is not None:
            if isinstance(duration, str):
                try:
                    duration = float(duration)
                except ValueError:
                    duration = None
            if duration is not None and duration <= 0:
                raise ValueError(f"Duración debe ser positiva, recibido: {duration}")
        
        # Validar display_time si se proporciona
        if display_time is not None:
            if isinstance(display_time, str):
                try:
                    display_time = float(display_time)
                except ValueError:
                    display_time = None
            if display_time is not None and display_time <= 0:
                display_time = None
        
        # Si author es None o string vacío, convertirlo
        if author == "None" or author == "" or not author:
            author = None
        
        has_author = author is not None and author.strip() != ""
        
        # Leer parámetros de personalización desde configuración
        container_color = self._get_config_value('container_color', '#0066CC')
        text_color = self._get_config_value('text_color', '#FFFFFF')
        font_family = self._get_config_value('font_family', 'normal')
        
        # Validar colores hex
        def _is_valid_hex_color(color: str) -> bool:
            """Valida formato de color hex (#RRGGBB)"""
            if not color or not color.startswith('#'):
                return False
            if len(color) != 7:
                return False
            try:
                int(color[1:], 16)
                return True
            except ValueError:
                return False
        
        if not _is_valid_hex_color(container_color):
            raise ValueError(f"Color de contenedor inválido: '{container_color}'. Debe ser formato hex (#RRGGBB)")
        
        if not _is_valid_hex_color(text_color):
            raise ValueError(f"Color de texto inválido: '{text_color}'. Debe ser formato hex (#RRGGBB)")
        
        # Validar font_family
        valid_fonts = ['normal', 'bold', 'italic', 'bold_italic']
        if font_family not in valid_fonts:
            # Usar 'normal' como fallback seguro
            font_family = 'normal'
        
        background_color = "#D3D3D3"
        card_width = 13
        card_height = 5
        card_corner_radius = 0.8
        
        # Configurar fondo
        self.setup_background(background_color)
        
        # === CREAR TARJETA CON COLOR PERSONALIZADO ===
        card = RoundedRectangle(
            corner_radius=card_corner_radius,
            width=card_width,
            height=card_height,
            fill_opacity=1.0,
            stroke_width=0
        )
        
        card.set_fill(color=container_color, opacity=1.0)
        card.set_stroke(width=0)
        
        # === CREAR TEXTO DE LA CITA ===
        quote_text = self._create_quote_text(quote, text_color=text_color, font_family=font_family)
        
        # === CREAR AUTOR (si existe) ===
        author_text = None
        if has_author:
            author_text = self._create_author_text(author, text_color=text_color, font_family=font_family)
        
        # === POSICIONAR ELEMENTOS ===
        if has_author:
            quote_text.move_to(card.get_center() + UP * 0.6)
            
            card_bottom = card.get_bottom()
            card_right = card.get_right()
            author_margin_x = 0.5
            author_margin_y = 0.4
            
            author_x = card_right[0] - author_text.width/2 - author_margin_x
            author_y = card_bottom[1] + author_text.height/2 + author_margin_y
            author_text.move_to([author_x, author_y, 0])
            
            self._ensure_text_fits(card, quote_text, author_text, card_width, card_height)
        else:
            quote_text.move_to(card.get_center())
            self._ensure_text_only(card, quote_text, card_width, card_height)
        
        # === CALCULAR TIEMPOS DE ANIMACIÓN ===
        text_length = len(quote.replace('\n', '').replace(' ', ''))
        
        # Tiempo de entrada: escalado desde esquina inferior izquierda
        card_scale_time = 0.8
        
        # Tiempo de escritura del texto (basado en longitud)
        text_write_time = min(4.0, max(1.5, text_length * 0.04))
        
        # Tiempo de escritura del autor
        author_write_time = 1.2 if has_author else 0
        
        # Pequeña pausa antes de mostrar el autor
        wait_before_author = 0.3
        
        # === CALCULAR TIEMPO DE VISUALIZACIÓN ===
        if display_time is not None:
            # Si se especificó display_time, usarlo directamente
            read_time = display_time
        elif duration is not None:
            # Si se especificó duración total, calcular read_time como el resto
            time_used = card_scale_time + 0.2 + text_write_time + wait_before_author + author_write_time
            read_time = max(1.0, duration - time_used)
        else:
            # Cálculo automático basado en longitud del texto
            base_read_time = 3.0
            char_read_time = 0.03
            read_time = max(2.0, min(8.0, base_read_time + (text_length * char_read_time)))
        
        # === ANIMACIONES ===
        # Entrada: escalado desde esquina inferior izquierda
        scale_point = card.get_corner(DOWN + LEFT)
        self.play(
            GrowFromPoint(card, scale_point),
            run_time=card_scale_time,
            rate_func=smooth
        )
        
        self.wait(0.2)
        
        # Escritura del texto letra por letra
        self.play(
            AddTextLetterByLetter(quote_text),
            run_time=text_write_time,
            rate_func=linear
        )
        
        self.wait(wait_before_author)
        
        # Escritura del autor si existe
        if has_author:
            self.play(Write(author_text), run_time=author_write_time)
        
        # Tiempo de visualización en pantalla
        self.wait(read_time)
        
        # Salida: corte directo (sin animación, el video simplemente termina)
    
    def _create_quote_text(self, quote, text_color="#FFFFFF", font_family="normal"):
        """Crea el texto de la cita con ajuste automático"""
        max_line_length = 45
        quote_clean = self._fix_encoding(quote)
        
        if not quote_clean or not quote_clean.strip():
            quote_clean = quote
        
        # Dividir en líneas
        if '\n' in quote_clean:
            lines = [line.strip() for line in quote_clean.split('\n') if line.strip()]
        else:
            words = quote_clean.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 <= max_line_length:
                    current_line += (" " + word if current_line else word)
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
        
        if not lines:
            lines = [quote_clean] if quote_clean else ["Texto"]
        
        # Ajustar tamaño de fuente
        font_sizes = {1: 48, 2: 42, 3: 38, 4: 34}
        font_size = font_sizes.get(len(lines), 32)
        
        total_chars = len(quote_clean.replace('\n', ''))
        if total_chars > 80:
            font_size = max(30, font_size - 4)
        
        text_content = '\n'.join(lines)
        
        # Mapear font_family
        # Manim espera weight como string ('NORMAL', 'BOLD'), no objeto Weight
        font_weight = 'NORMAL'
        font_slant = NORMAL
        
        if font_family.lower() in ['bold', 'bold_italic']:
            font_weight = 'BOLD'
        
        if font_family.lower() in ['italic', 'bold_italic']:
            font_slant = ITALIC
        
        text_params = {
            'text': text_content,
            'font_size': font_size,
            'color': text_color,
            'line_spacing': 1.2,
            'slant': font_slant,
            'weight': font_weight  # Manim espera string, no objeto Weight
        }
        
        return Text(**text_params)
    
    def _create_author_text(self, author, text_color="#FFFFFF", font_family="normal"):
        """Crea el texto del autor"""
        font_weight = 'NORMAL'
        font_slant = ITALIC  # Por defecto el autor es itálico
        
        if font_family.lower() in ['bold', 'bold_italic']:
            font_weight = 'BOLD'
        
        if font_family.lower() == 'bold_italic':
            font_slant = ITALIC  # Ya es ITALIC por defecto, pero lo mantenemos explícito
        
        text_params = {
            'text': author,
            'font_size': 28,
            'color': text_color,
            'slant': font_slant,
            'weight': font_weight  # Manim espera string, no objeto Weight
        }
        
        return Text(**text_params)
    
    def _ensure_text_fits(self, card, quote_text, author_text, card_width, card_height):
        """Asegura que texto y autor quepan en el container"""
        margin_x = 0.5
        margin_y = 0.5
        
        # Validar que los objetos existen y tienen dimensiones válidas
        if not quote_text or not author_text:
            return quote_text, author_text
        
        # Escalar horizontalmente si es necesario
        if quote_text.width > card_width - margin_x * 2:
            scale_factor = (card_width - margin_x * 2) / quote_text.width
            # Limitar el factor de escala para evitar texto demasiado pequeño
            scale_factor = max(0.3, scale_factor * 0.95)
            quote_text.scale(scale_factor)
        
        # Calcular altura disponible
        text_height = abs(quote_text.get_top()[1] - quote_text.get_bottom()[1])
        card_top = card.get_top()[1]
        card_bottom = card.get_bottom()[1]
        available_height = abs(card_top - card_bottom)
        
        # Verificar si cabe verticalmente
        author_height = abs(author_text.height) if hasattr(author_text, 'height') else 0.5
        needed_height = text_height + author_height + margin_y * 3
        
        if needed_height > available_height and text_height > 0:
            # Escalar para que quepa verticalmente
            scale_factor = (available_height - margin_y * 3 - author_height) / text_height
            # Limitar el factor de escala para evitar texto demasiado pequeño
            scale_factor = max(0.3, min(scale_factor * 0.95, 1.0))
            quote_text.scale(scale_factor)
        
        quote_text.move_to(card.get_center() + UP * 0.4)
        
        card_bottom = card.get_bottom()
        card_right = card.get_right()
        author_margin_x = 0.5
        author_margin_y = 0.4
        
        author_x = card_right[0] - author_text.width/2 - author_margin_x
        author_y = card_bottom[1] + author_text.height/2 + author_margin_y
        author_text.move_to([author_x, author_y, 0])
        
        if author_text.get_left()[0] < card.get_left()[0] + 0.3:
            author_text.move_to([
                card.get_center()[0],
                card_bottom[1] + author_text.height/2 + author_margin_y,
                0
            ])
        
        if author_text.get_top()[1] > quote_text.get_bottom()[1] - 0.3:
            quote_text.shift(UP * 0.3)
        
        return quote_text, author_text
    
    def _ensure_text_only(self, card, quote_text, card_width, card_height):
        """Asegura que solo el texto quepa en el container"""
        margin = 0.6
        
        if not quote_text:
            return quote_text
        
        # Escalar horizontalmente si es necesario
        if quote_text.width > card_width - margin * 2:
            scale_factor = (card_width - margin * 2) / quote_text.width
            # Limitar el factor de escala para evitar texto demasiado pequeño
            scale_factor = max(0.3, scale_factor * 0.95)
            quote_text.scale(scale_factor)
        
        # Escalar verticalmente si es necesario
        text_height = abs(quote_text.get_top()[1] - quote_text.get_bottom()[1])
        available_height = card_height - margin * 2
        
        if text_height > available_height and text_height > 0:
            scale_factor = available_height / text_height
            # Limitar el factor de escala para evitar texto demasiado pequeño
            scale_factor = max(0.3, min(scale_factor * 0.95, 1.0))
            quote_text.scale(scale_factor)
        
        quote_text.move_to(card.get_center())
        return quote_text

