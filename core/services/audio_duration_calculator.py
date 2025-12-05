"""
Servicio para calcular duración estimada de audio TTS
y validar que el texto encaja en la duración del video
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AudioDurationCalculator:
    """Calcula duración estimada de audio TTS"""
    
    # Palabras por segundo según idioma y velocidad
    WORDS_PER_SECOND = {
        'es': {
            'normal': 2.5,   # Español: velocidad normal de narración
            'fast': 3.0,      # Velocidad rápida (+20%)
            'slow': 2.0,      # Velocidad lenta (-20%)
        },
        'en': {
            'normal': 2.3,    # Inglés: velocidad normal
            'fast': 2.8,
            'slow': 1.8,
        },
        'fr': {
            'normal': 2.4,
            'fast': 2.9,
            'slow': 1.9,
        },
        'de': {
            'normal': 2.2,
            'fast': 2.7,
            'slow': 1.7,
        },
        # Default para otros idiomas
        'default': {
            'normal': 2.3,
            'fast': 2.8,
            'slow': 1.8,
        }
    }
    
    @staticmethod
    def count_words(text: str) -> int:
        """
        Cuenta palabras en un texto
        
        Args:
            text: Texto a contar
        
        Returns:
            Número de palabras
        """
        if not text:
            return 0
        
        # Limpiar y dividir por espacios
        words = text.strip().split()
        return len(words)
    
    @staticmethod
    def estimate_duration(text: str, language: str = 'es', speed: float = 1.0) -> float:
        """
        Estima duración de audio TTS en segundos
        
        Args:
            text: Texto a convertir a voz
            language: Código de idioma ('es', 'en', 'fr', etc.)
            speed: Factor de velocidad (1.0 = normal, 1.2 = rápido, 0.8 = lento)
        
        Returns:
            Duración estimada en segundos
        """
        word_count = AudioDurationCalculator.count_words(text)
        
        # Obtener palabras por segundo según idioma
        lang_config = AudioDurationCalculator.WORDS_PER_SECOND.get(
            language, 
            AudioDurationCalculator.WORDS_PER_SECOND['default']
        )
        
        # Determinar velocidad base
        if speed >= 1.15:
            wps = lang_config['fast']
        elif speed <= 0.85:
            wps = lang_config['slow']
        else:
            wps = lang_config['normal']
        
        # Calcular duración base
        base_duration = word_count / wps
        
        # Aplicar factor de velocidad
        estimated_duration = base_duration / speed
        
        logger.debug(
            f"Estimación de duración: {word_count} palabras, "
            f"{wps} palabras/segundo, velocidad {speed}x = {estimated_duration:.2f}s"
        )
        
        return estimated_duration
    
    @staticmethod
    def validate_text_length(text: str, duration_sec: int, language: str = 'es', 
                            speed: float = 1.0, tolerance: float = 0.1) -> Dict:
        """
        Valida que el texto encaja en la duración del video
        
        Args:
            text: Texto a validar
            duration_sec: Duración del video en segundos
            language: Código de idioma
            speed: Factor de velocidad
            tolerance: Tolerancia permitida (0.1 = 10% de margen)
        
        Returns:
            {
                'valid': bool,
                'estimated_duration': float,
                'target_duration': int,
                'difference': float,  # diferencia en segundos
                'difference_percent': float,  # diferencia en porcentaje
                'recommendation': str,
                'words_count': int,
                'words_per_second': float
            }
        """
        word_count = AudioDurationCalculator.count_words(text)
        estimated_duration = AudioDurationCalculator.estimate_duration(text, language, speed)
        
        difference = estimated_duration - duration_sec
        difference_percent = (difference / duration_sec) * 100 if duration_sec > 0 else 0
        
        # Obtener palabras por segundo usado
        lang_config = AudioDurationCalculator.WORDS_PER_SECOND.get(
            language,
            AudioDurationCalculator.WORDS_PER_SECOND['default']
        )
        if speed >= 1.15:
            wps = lang_config['fast']
        elif speed <= 0.85:
            wps = lang_config['slow']
        else:
            wps = lang_config['normal']
        
        # Determinar si es válido (dentro de la tolerancia)
        max_duration = duration_sec * (1 + tolerance)
        is_valid = estimated_duration <= max_duration
        
        # Generar recomendación
        recommendation = ''
        if is_valid:
            if abs(difference_percent) < 5:
                recommendation = 'Texto perfectamente ajustado'
            else:
                recommendation = f'Texto ajustado (diferencia: {difference_percent:.1f}%)'
        else:
            if difference_percent > 20:
                recommendation = (
                    f'Texto demasiado largo. Reducir {word_count - int(duration_sec * wps / speed)} palabras '
                    f'o aumentar velocidad a {speed * (estimated_duration / duration_sec):.2f}x'
                )
            elif difference_percent > 10:
                recommendation = (
                    f'Texto ligeramente largo. Reducir {word_count - int(duration_sec * wps / speed)} palabras '
                    f'o aumentar velocidad a {speed * (estimated_duration / duration_sec):.2f}x'
                )
            else:
                recommendation = (
                    f'Texto ligeramente largo. Aumentar velocidad a '
                    f'{speed * (estimated_duration / duration_sec):.2f}x'
                )
        
        return {
            'valid': is_valid,
            'estimated_duration': estimated_duration,
            'target_duration': duration_sec,
            'difference': difference,
            'difference_percent': difference_percent,
            'recommendation': recommendation,
            'words_count': word_count,
            'words_per_second': wps / speed
        }
    
    @staticmethod
    def get_optimal_word_count(duration_sec: int, language: str = 'es', 
                               speed: float = 1.0) -> Dict:
        """
        Calcula el número óptimo de palabras para una duración
        
        Args:
            duration_sec: Duración deseada en segundos
            language: Código de idioma
            speed: Factor de velocidad
        
        Returns:
            {
                'min_words': int,
                'max_words': int,
                'optimal_words': int,
                'words_per_second': float
            }
        """
        lang_config = AudioDurationCalculator.WORDS_PER_SECOND.get(
            language,
            AudioDurationCalculator.WORDS_PER_SECOND['default']
        )
        
        if speed >= 1.15:
            wps = lang_config['fast']
        elif speed <= 0.85:
            wps = lang_config['slow']
        else:
            wps = lang_config['normal']
        
        # Aplicar factor de velocidad
        effective_wps = wps * speed
        
        # Calcular palabras óptimas
        optimal_words = int(duration_sec * effective_wps)
        
        # Rango recomendado (±10%)
        min_words = int(optimal_words * 0.9)
        max_words = int(optimal_words * 1.1)
        
        return {
            'min_words': min_words,
            'max_words': max_words,
            'optimal_words': optimal_words,
            'words_per_second': effective_wps
        }


