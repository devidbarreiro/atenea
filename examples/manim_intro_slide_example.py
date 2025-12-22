"""
Ejemplo de uso de la animación IntroSlide (cortinilla de entrada)

Este ejemplo muestra cómo generar una cortinilla de entrada estilo presentación
usando Manim.
"""
from core.ai_services.manim import ManimClient

def example_intro_slide():
    """Ejemplo básico de cortinilla de entrada"""
    client = ManimClient()
    
    # Configuración básica
    config = {
        'title': 'Tema 1 - LA ESTRATEGIA Y LA DIRECCIÓN ESTRATÉGICA',
        'central_text': '¿Qué es la estrategia y por qué es esencial en la empresa?',
        'footer': 'Avatar y lección original de Ana Martínez - EDITADO CON IA',
        'duration': 6.0,  # Duración total del video en segundos
    }
    
    result = client.generate_video(
        animation_type='intro_slide',
        config=config,
        quality='k'  # Calidad: l (low), m (medium), h (high), k (4K)
    )
    
    print(f"Video generado en: {result['video_path']}")
    return result


def example_intro_slide_custom_colors():
    """Ejemplo con colores personalizados"""
    client = ManimClient()
    
    config = {
        'title': 'Módulo 2 - Marketing Digital',
        'central_text': '¿Cómo crear una estrategia de contenido efectiva?',
        'footer': 'Curso de Marketing - 2025',
        'duration': 5.0,
        # Colores personalizados
        'bg_color': '#F5F5F5',  # Fondo más claro
        'title_color': '#2C3E50',  # Azul oscuro
        'central_text_color': '#34495E',  # Gris oscuro
        'footer_color': '#7F8C8D',  # Gris medio
        'circle_color': '#BDC3C7',  # Gris claro para el círculo
    }
    
    result = client.generate_video(
        animation_type='intro_slide',
        config=config,
        quality='h'  # Alta calidad
    )
    
    print(f"Video generado en: {result['video_path']}")
    return result


def example_intro_slide_minimal():
    """Ejemplo minimalista solo con título"""
    client = ManimClient()
    
    config = {
        'title': 'Bienvenido al Curso',
        'central_text': None,  # Sin texto central
        'footer': None,  # Sin footer
        'duration': 3.0,
    }
    
    result = client.generate_video(
        animation_type='intro_slide',
        config=config,
        quality='m'
    )
    
    print(f"Video generado en: {result['video_path']}")
    return result


if __name__ == '__main__':
    print("Generando cortinilla de entrada básica...")
    example_intro_slide()
    
    print("\nGenerando cortinilla con colores personalizados...")
    example_intro_slide_custom_colors()
    
    print("\nGenerando cortinilla minimalista...")
    example_intro_slide_minimal()

