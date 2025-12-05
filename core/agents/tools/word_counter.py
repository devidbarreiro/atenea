"""
Tool para contar palabras y validar longitud de texto vs duración
"""

from langchain.tools import tool
from typing import Dict
import re

# Velocidad de narración: 2.5 palabras por segundo (español)
WORDS_PER_SECOND = 2.5

# Guía de palabras por duración (basado en velocidad de narración: 2.5 palabras/segundo)
# Formato: duración_segundos: (mínimo_palabras, máximo_palabras)
WORDS_PER_DURATION = {
    4: (8, 11),      # 8-11 palabras para 4s (10 palabras ideal)
    5: (10, 14),     # 10-14 palabras para 5s (12-13 palabras ideal)
    6: (13, 17),     # 13-17 palabras para 6s (15 palabras ideal)
    7: (15, 19),     # 15-19 palabras para 7s (17-18 palabras ideal)
    8: (18, 22),     # 18-22 palabras para 8s (20 palabras ideal)
    12: (27, 32),    # 27-32 palabras para 12s (30 palabras ideal)
    15: (34, 40),    # 34-40 palabras para 15s (37 palabras ideal)
    20: (45, 52),    # 45-52 palabras para 20s (50 palabras ideal)
    25: (58, 65),    # 58-65 palabras para 25s (62 palabras ideal)
    30: (68, 80),    # 68-80 palabras para 30s (75 palabras ideal)
    35: (80, 90),    # 80-90 palabras para 35s (87 palabras ideal)
    45: (103, 117),  # 103-117 palabras para 45s (112 palabras ideal)
    50: (115, 130),  # 115-130 palabras para 50s (125 palabras ideal)
    60: (138, 155),  # 138-155 palabras para 60s (150 palabras ideal)
}


@tool
def count_words(text: str) -> int:
    """
    Cuenta el número de palabras en un texto.
    
    Args:
        text: Texto a contar
        
    Returns:
        Número de palabras
    """
    # Remover espacios múltiples y dividir
    words = re.findall(r'\b\w+\b', text.lower())
    return len(words)


@tool
def validate_text_length_for_duration(text: str, duration_sec: int) -> Dict[str, any]:
    """
    Valida que el texto tenga una longitud apropiada para la duración.
    
    Args:
        text: Texto a validar
        duration_sec: Duración en segundos
        
    Returns:
        Dict con 'valid' (bool), 'word_count' (int), 'expected_range' (tuple), 'message' (str)
    """
    word_count = count_words.invoke({'text': text})
    
    # Obtener rango esperado
    if duration_sec in WORDS_PER_DURATION:
        min_words, max_words = WORDS_PER_DURATION[duration_sec]
    else:
        # Estimar basado en velocidad de narración (2.5 palabras/segundo)
        estimated_words = duration_sec * WORDS_PER_SECOND
        min_words = int(estimated_words * 0.9)  # 10% de margen inferior
        max_words = int(estimated_words * 1.1)  # 10% de margen superior
    
    is_valid = min_words <= word_count <= max_words
    
    if is_valid:
        message = f'Longitud de texto apropiada ({word_count} palabras para {duration_sec}s)'
    else:
        if word_count < min_words:
            message = f'Texto muy corto: {word_count} palabras (esperado: {min_words}-{max_words})'
        else:
            message = f'Texto muy largo: {word_count} palabras (esperado: {min_words}-{max_words})'
    
    return {
        'valid': is_valid,
        'word_count': word_count,
        'expected_range': (min_words, max_words),
        'message': message
    }

