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
    
    def construct(self):
        # Obtener datos desde variables de entorno
        quote = self._get_env_var('QUOTE_ANIMATION_TEXT', '', decode_base64=True)
        author = self._get_env_var('QUOTE_ANIMATION_AUTHOR', None, decode_base64=True)
        duration_str = self._get_env_var('QUOTE_ANIMATION_DURATION', None)
        
        # Reparar encoding si es necesario
        quote = self._fix_encoding(quote) if quote else "Texto de ejemplo"
        if author:
            author = self._fix_encoding(author)
        
        # Parsear duración
        duration = None
        if duration_str and duration_str != "None":
            try:
                duration = float(duration_str)
            except:
                duration = None
        
        # Si author es "None" como string, convertirlo
        if author == "None" or author == "":
            author = None
        
        has_author = author is not None and author.strip() != ""
        
        # Leer parámetros de personalización desde variables de entorno
        container_color = self._get_env_var('QUOTE_ANIMATION_CONTAINER_COLOR', '#0066CC')
        text_color = self._get_env_var('QUOTE_ANIMATION_TEXT_COLOR', '#FFFFFF')
        font_family = self._get_env_var('QUOTE_ANIMATION_FONT_FAMILY', 'normal')
        
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
        
        # === CALCULAR DURACIÓN AUTOMÁTICA ===
        if duration is None:
            text_length = len(quote.replace('\n', '').replace(' ', ''))
            base_duration = 8.0
            char_duration = 0.05
            auto_duration = base_duration + (text_length * char_duration)
            duration = max(8.0, min(15.0, auto_duration))
        
        # Calcular tiempos de animación
        total_time = duration
        card_fade_time = 0.3
        card_move_time = min(1.5, total_time * 0.15)
        text_write_time = min(4.0, total_time * 0.35)
        author_write_time = 1.2 if has_author else 0
        wait_before_read = 0.7
        read_time = max(2.0, total_time * 0.25)
        fade_out_time = min(1.5, total_time * 0.15)
        
        if total_time < 10:
            scale = total_time / 10.0
            text_write_time *= scale
            read_time *= scale
            fade_out_time *= scale
        
        # === ANIMACIONES ===
        card.shift(LEFT * 15)
        self.play(FadeIn(card), run_time=card_fade_time)
        
        self.play(
            card.animate.shift(RIGHT * 15),
            run_time=card_move_time,
            rate_func=smooth
        )
        
        self.wait(0.5)
        
        self.play(
            AddTextLetterByLetter(quote_text),
            run_time=text_write_time,
            rate_func=linear
        )
        
        self.wait(wait_before_read)
        
        if has_author:
            self.play(Write(author_text), run_time=author_write_time)
        
        self.wait(read_time)
        
        if has_author:
            self.play(
                FadeOut(card, shift=UP),
                FadeOut(quote_text, shift=UP),
                FadeOut(author_text, shift=UP),
                run_time=fade_out_time,
                rate_func=smooth
            )
        else:
            self.play(
                FadeOut(card, shift=UP),
                FadeOut(quote_text, shift=UP),
                run_time=fade_out_time,
                rate_func=smooth
            )
        
        self.wait(0.5)
    
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
        
        if quote_text.width > card_width - margin_x * 2:
            scale_factor = (card_width - margin_x * 2) / quote_text.width
            quote_text.scale(scale_factor * 0.95)
        
        text_height = quote_text.get_top()[1] - quote_text.get_bottom()[1]
        card_top = card.get_top()[1]
        card_bottom = card.get_bottom()[1]
        available_height = card_top - card_bottom
        
        author_height = author_text.height
        needed_height = text_height + author_height + margin_y * 3
        
        if needed_height > available_height:
            scale_factor = (available_height - margin_y * 3 - author_height) / text_height
            quote_text.scale(min(scale_factor * 0.95, 1.0))
        
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
        
        if quote_text.width > card_width - margin * 2:
            scale_factor = (card_width - margin * 2) / quote_text.width
            quote_text.scale(scale_factor * 0.95)
        
        text_height = quote_text.get_top()[1] - quote_text.get_bottom()[1]
        available_height = card_height - margin * 2
        
        if text_height > available_height:
            scale_factor = available_height / text_height
            quote_text.scale(scale_factor * 0.95)
        
        quote_text.move_to(card.get_center())
        return quote_text

