"""
Tool para contar palabras y validar longitud de texto vs duración
"""

from langchain.tools import tool
from typing import Dict
import re

# Guía de palabras por duración (basado en velocidad de lectura promedio)
WORDS_PER_DURATION = {
    4: (8, 10),      # 8-10 palabras para 4s
    5: (10, 12),     # 10-12 palabras para 5s
    8: (16, 18),     # 16-18 palabras para 8s
    12: (22, 25),    # 22-25 palabras para 12s
    30: (60, 75),    # 60-75 palabras para 30s
    45: (90, 110),   # 90-110 palabras para 45s
    60: (120, 150),  # 120-150 palabras para 60s
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
        # Estimar basado en velocidad promedio (15 palabras/segundo)
        estimated_words = duration_sec * 15
        min_words = int(estimated_words * 0.8)
        max_words = int(estimated_words * 1.2)
    
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

