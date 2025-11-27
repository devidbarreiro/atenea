"""
Script único para crear animaciones de citas con Manim
Soporta texto solo o texto + autor

Uso:
    python create_quote.py "Tu frase aquí"
    python create_quote.py "Tu frase aquí" "Nombre del Autor"
    python create_quote.py "Tu frase aquí" "Autor" --duration 10

NOTA: Este archivo también puede ser ejecutado directamente por Manim:
    manim -pql create_quote.py QuoteAnimation
"""
import sys
import subprocess
from pathlib import Path

# Intentar importar manim - si falla, se usará cuando manim importe el módulo
_manim_imported = False
try:
    from manim import *
    _manim_imported = True
except ImportError:
    # Si no está disponible ahora, manim lo importará cuando renderice
    # Crear stubs para que el código no falle
    class Scene:
        pass
    class RoundedRectangle:
        pass
    class Text:
        pass
    BLUE_E = "#1C2833"
    BLUE_C = "#3498DB"
    WHITE = "#FFFFFF"
    UP = (0, 1, 0)
    LEFT = (-1, 0, 0)
    RIGHT = (1, 0, 0)
    NORMAL = "normal"
    ITALIC = "italic"


# Variables globales que se establecerán antes de renderizar
# También se pueden leer de variables de entorno
import os

class QuoteAnimation(Scene):
    """Animación de cita profesional"""
    
    def _fix_encoding(self, text):
        """Repara caracteres mal codificados"""
        if not text:
            return text
        
        # Reemplazos directos de caracteres comunes mal codificados
        fixes = {
            'Ã±': 'ñ', 'Ã³': 'ó', 'Ã¡': 'á', 'Ã©': 'é', 
            'Ã­': 'í', 'Ãº': 'ú', 'Ã': 'Á', 'Ã': 'É',
            'Ã': 'Í', 'Ã': 'Ó', 'Ã': 'Ú', 'Ã': 'Ñ'
        }
        
        result = text
        for wrong, correct in fixes.items():
            result = result.replace(wrong, correct)
        
        # Intentar reparar otros caracteres si quedan problemas
        if '' in result:
            try:
                # Intentar como si fuera latin-1 mal interpretado como UTF-8
                result = result.encode('latin-1').decode('utf-8')
            except:
                pass
        
        return result
    
    def construct(self):
        import base64
        
        # Leer de variables de entorno (establecidas antes de renderizar)
        # Verificar si está codificado en base64
        is_encoded = os.environ.get('QUOTE_ANIMATION_ENCODED', '0') == '1'
        
        if is_encoded:
            # Decodificar desde base64
            quote_encoded = os.environ.get('QUOTE_ANIMATION_TEXT', '')
            try:
                quote = base64.b64decode(quote_encoded.encode('ascii')).decode('utf-8')
            except:
                quote = quote_encoded  # Fallback si falla la decodificación
            
            author_encoded = os.environ.get('QUOTE_ANIMATION_AUTHOR', 'None')
            author_is_encoded = os.environ.get('QUOTE_ANIMATION_AUTHOR_ENCODED', '0') == '1'
            
            if author_is_encoded and author_encoded != "None":
                try:
                    author = base64.b64decode(author_encoded.encode('ascii')).decode('utf-8')
                except:
                    author = author_encoded
            else:
                author = author_encoded if author_encoded != "None" else None
        else:
            # Método antiguo (sin codificación)
            quote = os.environ.get('QUOTE_ANIMATION_TEXT', '')
            author = os.environ.get('QUOTE_ANIMATION_AUTHOR', None)
            
            # Si no hay en variables de entorno, intentar variables globales
            if not quote:
                try:
                    import create_quote
                    quote = getattr(create_quote, '_QUOTE', '')
                    author = getattr(create_quote, '_AUTHOR', None)
                except:
                    pass
            
            # Reparar encoding si es necesario
            quote = self._fix_encoding(quote)
            if author and author != "None":
                author = self._fix_encoding(author)
        
        duration_str = os.environ.get('QUOTE_ANIMATION_DURATION', None)
        
        # Si aún no hay nada, usar valores por defecto
        if not quote:
            quote = "Texto de ejemplo"
        
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
        container_color = os.environ.get('QUOTE_ANIMATION_CONTAINER_COLOR', '#0066CC')
        text_color = os.environ.get('QUOTE_ANIMATION_TEXT_COLOR', '#FFFFFF')
        font_family = os.environ.get('QUOTE_ANIMATION_FONT_FAMILY', 'normal')
        
        background_color = "#D3D3D3"
        card_width = 13
        card_height = 5
        card_corner_radius = 0.8
        
        # Configurar fondo gris claro
        self.camera.background_color = background_color
        
        # === CREAR TARJETA CON COLOR PERSONALIZADO ===
        # Container con esquinas redondeadas
        card = RoundedRectangle(
            corner_radius=card_corner_radius,
            width=card_width,
            height=card_height,
            fill_opacity=1.0,
            stroke_width=0
        )
        
        # Aplicar color personalizado del contenedor
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
            # Con autor: texto centrado arriba, autor abajo derecha
            quote_text.move_to(card.get_center() + UP * 0.6)
            
            # Posicionar autor en esquina inferior derecha
            card_bottom = card.get_bottom()
            card_right = card.get_right()
            author_margin_x = 0.5
            author_margin_y = 0.4
            
            author_x = card_right[0] - author_text.width/2 - author_margin_x
            author_y = card_bottom[1] + author_text.height/2 + author_margin_y
            author_text.move_to([author_x, author_y, 0])
            
            # Ajustar para que todo quepa
            self._ensure_text_fits(card, quote_text, author_text, card_width, card_height)
        else:
            # Sin autor: texto completamente centrado
            quote_text.move_to(card.get_center())
            
            # Ajustar solo el texto principal
            self._ensure_text_only(card, quote_text, card_width, card_height)
        
        # === CALCULAR DURACIÓN AUTOMÁTICA ===
        if duration is None:
            # Duración automática basada en longitud del texto
            text_length = len(quote.replace('\n', '').replace(' ', ''))
            base_duration = 8.0  # Duración base
            char_duration = 0.05  # Segundos por carácter
            auto_duration = base_duration + (text_length * char_duration)
            # Mínimo 8 segundos, máximo 15 segundos
            duration = max(8.0, min(15.0, auto_duration))
        
        # Calcular tiempos de animación proporcionales
        total_time = duration
        card_fade_time = 0.3
        card_move_time = min(1.5, total_time * 0.15)
        text_write_time = min(4.0, total_time * 0.35)
        author_write_time = 1.2 if has_author else 0
        wait_before_read = 0.7
        read_time = max(2.0, total_time * 0.25)
        fade_out_time = min(1.5, total_time * 0.15)
        
        # Ajustar tiempos si la duración total es muy corta
        if total_time < 10:
            # Escalar proporcionalmente
            scale = total_time / 10.0
            text_write_time *= scale
            read_time *= scale
            fade_out_time *= scale
        
        # === ANIMACIONES ===
        
        # 1. Container aparece con fade in
        card.shift(LEFT * 15)
        self.play(
            FadeIn(card),
            run_time=card_fade_time
        )
        
        # 2. Container se mueve a su posición
        self.play(
            card.animate.shift(RIGHT * 15),
            run_time=card_move_time,
            rate_func=smooth
        )
        
        self.wait(0.5)
        
        # 3. Texto aparece letra por letra
        self.play(
            AddTextLetterByLetter(quote_text),
            run_time=text_write_time,
            rate_func=linear
        )
        
        self.wait(wait_before_read)
        
        # 4. Autor aparece (si existe)
        if has_author:
            self.play(
                Write(author_text),
                run_time=author_write_time
            )
        
        # 5. Pausa para leer
        self.wait(read_time)
        
        # 6. Todo desaparece
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
        """Crea el texto de la cita con ajuste automático y encoding UTF-8"""
        max_line_length = 45
        
        # Asegurar que el texto sea un string Unicode válido (UTF-8)
        # Intentar reparar encoding si es necesario
        quote_clean = quote
        
        # Si el texto tiene caracteres mal codificados, intentar arreglarlos
        if 'Ã±' in quote_clean:
            quote_clean = quote_clean.replace('Ã±', 'ñ')
        if 'Ã³' in quote_clean:
            quote_clean = quote_clean.replace('Ã³', 'ó')
        if 'Ã¡' in quote_clean:
            quote_clean = quote_clean.replace('Ã¡', 'á')
        if 'Ã©' in quote_clean:
            quote_clean = quote_clean.replace('Ã©', 'é')
        if 'Ã­' in quote_clean:
            quote_clean = quote_clean.replace('Ã­', 'í')
        if 'Ãº' in quote_clean:
            quote_clean = quote_clean.replace('Ãº', 'ú')
        if 'Ã' in quote_clean and 'Ã±' not in quote_clean and 'Ã³' not in quote_clean:
            # Intentar reparar otros caracteres mal codificados
            try:
                quote_clean = quote_clean.encode('latin-1').decode('utf-8')
            except:
                pass
        
        # Verificar que el texto no esté vacío
        if not quote_clean or not quote_clean.strip():
            quote_clean = quote  # Usar el original si el limpio está vacío
        
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
        
        # Asegurar que hay líneas
        if not lines:
            lines = [quote_clean] if quote_clean else ["Texto"]
        
        # Ajustar tamaño de fuente
        if len(lines) == 1:
            font_size = 48
        elif len(lines) == 2:
            font_size = 42
        elif len(lines) == 3:
            font_size = 38
        elif len(lines) == 4:
            font_size = 34
        else:
            font_size = 32
        
        # Ajustar si es muy largo
        total_chars = len(quote_clean.replace('\n', ''))
        if total_chars > 80:
            font_size = max(30, font_size - 4)
        
        # Crear texto - Manim maneja UTF-8 correctamente
        # Asegurar que el texto se pasa como string Unicode
        text_content = '\n'.join(lines)
        
        # Mapear font_family a parámetros de Manim
        font_weight = NORMAL
        font_slant = NORMAL
        
        if font_family.lower() == 'bold':
            font_weight = "bold"
        elif font_family.lower() == 'italic':
            font_slant = ITALIC
        elif font_family.lower() == 'bold_italic':
            font_weight = "bold"
            font_slant = ITALIC
        
        quote_text = Text(
            text_content,
            font_size=font_size,
            color=text_color,
            line_spacing=1.2,
            weight=font_weight,
            slant=font_slant
        )
        
        return quote_text
    
    def _create_author_text(self, author, text_color="#FFFFFF", font_family="normal"):
        """Crea el texto del autor con encoding UTF-8"""
        # Mapear font_family a parámetros de Manim
        font_weight = NORMAL
        font_slant = ITALIC  # Por defecto el autor es itálico
        
        if font_family.lower() == 'bold':
            font_weight = "bold"
            font_slant = ITALIC  # Mantener itálico para autor
        elif font_family.lower() == 'italic':
            font_slant = ITALIC
        elif font_family.lower() == 'bold_italic':
            font_weight = "bold"
            font_slant = ITALIC
        
        author_text = Text(
            author,
            font_size=28,
            color=text_color,
            slant=font_slant,
            weight=font_weight
        )
        return author_text
    
    def _ensure_text_fits(self, card, quote_text, author_text, card_width, card_height):
        """Asegura que texto y autor quepan en el container"""
        margin_x = 0.5
        margin_y = 0.5
        
        # Verificar ancho del texto
        if quote_text.width > card_width - margin_x * 2:
            scale_factor = (card_width - margin_x * 2) / quote_text.width
            quote_text.scale(scale_factor * 0.95)
        
        # Verificar altura total
        text_height = quote_text.get_top()[1] - quote_text.get_bottom()[1]
        card_top = card.get_top()[1]
        card_bottom = card.get_bottom()[1]
        available_height = card_top - card_bottom
        
        author_height = author_text.height
        needed_height = text_height + author_height + margin_y * 3
        
        if needed_height > available_height:
            scale_factor = (available_height - margin_y * 3 - author_height) / text_height
            quote_text.scale(min(scale_factor * 0.95, 1.0))
        
        # Reposicionar
        quote_text.move_to(card.get_center() + UP * 0.4)
        
        # Reposicionar autor
        card_bottom = card.get_bottom()
        card_right = card.get_right()
        author_margin_x = 0.5
        author_margin_y = 0.4
        
        author_x = card_right[0] - author_text.width/2 - author_margin_x
        author_y = card_bottom[1] + author_text.height/2 + author_margin_y
        author_text.move_to([author_x, author_y, 0])
        
        # Verificar que autor no se salga
        if author_text.get_left()[0] < card.get_left()[0] + 0.3:
            author_text.move_to([
                card.get_center()[0],
                card_bottom[1] + author_text.height/2 + author_margin_y,
                0
            ])
        
        # Verificar superposición
        if author_text.get_top()[1] > quote_text.get_bottom()[1] - 0.3:
            quote_text.shift(UP * 0.3)
        
        return quote_text, author_text
    
    def _ensure_text_only(self, card, quote_text, card_width, card_height):
        """Asegura que solo el texto quepa en el container"""
        margin = 0.6
        
        # Verificar ancho
        if quote_text.width > card_width - margin * 2:
            scale_factor = (card_width - margin * 2) / quote_text.width
            quote_text.scale(scale_factor * 0.95)
        
        # Verificar altura
        text_height = quote_text.get_top()[1] - quote_text.get_bottom()[1]
        available_height = card_height - margin * 2
        
        if text_height > available_height:
            scale_factor = available_height / text_height
            quote_text.scale(scale_factor * 0.95)
        
        # Centrar
        quote_text.move_to(card.get_center())
        
        return quote_text


def render_animation(quote, author=None, duration=None, quality="k"):
    """
    Renderiza la animación directamente
    
    Args:
        quote: Texto de la cita (UTF-8)
        author: Nombre del autor (opcional, UTF-8)
        duration: Duración en segundos (opcional)
        quality: Calidad de renderizado (l/m/h/k)
    """
    import base64
    
    # Codificar en base64 para preservar caracteres especiales
    # Esto evita problemas de encoding en variables de entorno
    quote_encoded = base64.b64encode(quote.encode('utf-8')).decode('ascii')
    os.environ['QUOTE_ANIMATION_TEXT'] = quote_encoded
    os.environ['QUOTE_ANIMATION_ENCODED'] = '1'  # Indicador de que está codificado
    
    if author and author.strip():
        author_encoded = base64.b64encode(author.encode('utf-8')).decode('ascii')
        os.environ['QUOTE_ANIMATION_AUTHOR'] = author_encoded
        os.environ['QUOTE_ANIMATION_AUTHOR_ENCODED'] = '1'
    else:
        os.environ['QUOTE_ANIMATION_AUTHOR'] = "None"
        os.environ['QUOTE_ANIMATION_AUTHOR_ENCODED'] = '0'
    
    if duration is not None:
        os.environ['QUOTE_ANIMATION_DURATION'] = str(duration)
    else:
        os.environ['QUOTE_ANIMATION_DURATION'] = "None"
    
    # También establecer variables globales como fallback
    import create_quote as this_module
    this_module._QUOTE = quote
    this_module._AUTHOR = author if author and author.strip() else None
    this_module._DURATION = duration
    
    # Renderizar usando el Python del venv
    script_dir = Path(__file__).parent
    venv_python = script_dir / "venv" / "Scripts" / "python.exe"
    
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable
    
    # Renderizar el módulo actual
    cmd = [
        python_cmd,
        "-m", "manim",
        f"-pq{quality}",
        str(Path(__file__).absolute()),
        "QuoteAnimation"
    ]
    
    print(f"[*] Renderizando animación...")
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print()
        print(f"[OK] Animación completada!")
        script_name = Path(__file__).stem
        # Determinar la carpeta según la calidad
        quality_folder = {
            "l": "480p15",
            "m": "720p30", 
            "h": "1080p60",
            "k": "2160p60"
        }.get(quality, "2160p60")
        print(f"[OK] Video: media/videos/{script_name}/{quality_folder}/QuoteAnimation.mp4")
    else:
        print()
        print(f"[ERROR] Error al renderizar")
    
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Crear Animación de Cita con Manim")
        print("=" * 60)
        print("\nUso:")
        print('  python create_quote.py "Tu frase aquí"')
        print('  python create_quote.py "Tu frase aquí" "Nombre del Autor"')
        print('  python create_quote.py "Tu frase" "Autor" --duration 10')
        print("\nEjemplos:")
        print('  python create_quote.py "La estrategia no se diseña en un despacho, se descubre en la acción" "David Barreiro"')
        print('  python create_quote.py "Solo texto sin autor"')
        print('  python create_quote.py "Texto" "Autor" --duration 12')
        print("\nOpciones:")
        print("  --duration N       Duración total en segundos (opcional, se calcula automáticamente)")
        print("  --quality l|m|h|k  Calidad (default: k=4K máxima calidad, l=baja, m=media, h=alta)")
        print("\n" + "=" * 60)
        sys.exit(1)
    
    # Asegurar encoding UTF-8 para los argumentos
    # En Windows, los argumentos pueden venir con encoding incorrecto
    if sys.platform == 'win32':
        # En Windows, asegurar que la consola use UTF-8
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass
        
        # Decodificar argumentos correctamente si es necesario
        try:
            # Intentar decodificar desde UTF-8 si viene mal codificado
            quote_raw = sys.argv[1]
            # Si el texto tiene caracteres mal codificados, intentar arreglarlo
            if 'Ã' in quote_raw or 'Ã±' in quote_raw or 'Ã³' in quote_raw:
                # Parece que viene con encoding incorrecto, intentar repararlo
                try:
                    # Intentar como si fuera latin-1 mal interpretado como UTF-8
                    quote = quote_raw.encode('latin-1').decode('utf-8')
                except:
                    quote = quote_raw
            else:
                quote = quote_raw
        except:
            quote = sys.argv[1]
    else:
        quote = sys.argv[1]
    author = None
    quality = "k"  # Máxima calidad (4K) por defecto
    duration = None
    
    # Parsear argumentos
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--duration" and i + 1 < len(sys.argv):
            try:
                duration = float(sys.argv[i + 1])
            except ValueError:
                print(f"[ERROR] Duración inválida: {sys.argv[i + 1]}")
                sys.exit(1)
            i += 2
        elif arg == "--quality" and i + 1 < len(sys.argv):
            quality = sys.argv[i + 1]
            i += 2
        elif not arg.startswith('--') and author is None:
            # Segundo argumento sin -- es el autor
            author_raw = arg
            # Arreglar encoding del autor si es necesario
            if sys.platform == 'win32':
                try:
                    if 'Ã' in author_raw:
                        author = author_raw.encode('latin-1').decode('utf-8')
                    else:
                        author = author_raw
                except:
                    author = author_raw
            else:
                author = author_raw
            i += 1
        else:
            i += 1
    
    print("=" * 60)
    print("Creando animación de cita...")
    print("=" * 60)
    print(f"Frase: {quote}")
    if author:
        print(f"Autor: {author}")
    else:
        print("Autor: (ninguno)")
    if duration:
        print(f"Duración: {duration} segundos")
    else:
        print("Duración: automática")
    print(f"Calidad: {quality}")
    print("=" * 60)
    print()
    
    render_animation(quote, author, duration, quality)
