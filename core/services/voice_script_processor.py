"""
Procesador de guiones con tags de voz para ElevenLabs TTS
Convierte tags de voice-acting a formato optimizado para ElevenLabs
"""
import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class VoiceScriptProcessor:
    """
    Procesa guiones con tags de voz y los convierte a formato optimizado para ElevenLabs.
    
    Soporta:
    - Tags de emoción: [Confident], [Whisper], etc.
    - Tags de pausa: [Pause: 0.4s] -> convertidos a puntos suspensivos o saltos de línea
    - Tags de interpretación: [Storytelling], [Energetic], etc.
    """
    
    # Mapeo de emociones a instrucciones naturales
    EMOTION_MAP = {
        'confident': 'con confianza',
        'casual': 'de forma casual',
        'storytelling': 'como narrando una historia',
        'sarcastic': 'con sarcasmo',
        'energetic': 'con energía',
        'proud': 'con orgullo',
        'reflective': 'reflexivo',
        'soft': 'suave',
        'whisper': 'en susurro',
        'low': 'en tono bajo',
        'bold': 'con firmeza',
        'playful': 'juguetón',
        'warm': 'cálido',
        'sharp': 'directo',
        'futuristic': 'futurista',
        'passionate': 'apasionado',
        'empowering': 'empoderador',
        'inspirational': 'inspirador',
        'competitive': 'competitivo',
        'hype': 'emocionante',
        'victorious': 'victorioso',
        'champion': 'como un campeón',
        'smooth': 'suave',
        'dreamy': 'soñador',
        'aesthetic': 'estético',
        'mocking': 'burlón',
        'laugh': 'riendo',
        'smirk': 'con sonrisa',
        'smiling': 'sonriendo',
    }
    
    @staticmethod
    def process_script(text: str, use_ssml: bool = False) -> Dict[str, any]:
        """
        Procesa un guión con tags de voz y lo convierte a formato optimizado.
        
        Args:
            text: Texto con tags de voz (ej: [Confident] texto [Pause: 0.4s])
            use_ssml: Si True, genera SSML (requiere API v1 con soporte SSML)
        
        Returns:
            Dict con:
                - 'processed_text': Texto procesado listo para ElevenLabs
                - 'metadata': Información sobre tags encontrados
                - 'has_emotions': Si tiene tags emocionales
                - 'has_pauses': Si tiene pausas
        """
        if not text:
            return {
                'processed_text': '',
                'metadata': {},
                'has_emotions': False,
                'has_pauses': False
            }
        
        original_text = text
        metadata = {
            'emotions_found': [],
            'pauses_found': [],
            'original_length': len(text),
            'processed_length': 0
        }
        
        # Extraer y procesar tags de pausa
        pause_pattern = r'\[Pause:\s*([\d.]+)s?\]'
        pauses = re.findall(pause_pattern, text)
        metadata['pauses_found'] = [float(p) for p in pauses]
        
        # Convertir pausas a formato natural
        if use_ssml:
            # Usar SSML para pausas exactas
            text = re.sub(pause_pattern, lambda m: f'<break time="{m.group(1)}s"/>', text)
        else:
            # Convertir a puntos suspensivos o saltos de línea según duración
            def pause_replacer(match):
                duration = float(match.group(1))
                if duration >= 0.6:
                    return '\n\n'  # Pausa larga: doble salto de línea
                elif duration >= 0.4:
                    return '... '  # Pausa media: puntos suspensivos
                else:
                    return '... '  # Pausa corta: puntos suspensivos
            
            text = re.sub(pause_pattern, pause_replacer, text)
        
        # Extraer y procesar tags de emoción/interpretación
        emotion_pattern = r'\[([^\]]+)\]'
        emotions = re.findall(emotion_pattern, text)
        
        # Filtrar emociones (excluir pausas que ya procesamos)
        valid_emotions = [e for e in emotions if not e.startswith('Pause:')]
        metadata['emotions_found'] = valid_emotions
        
        # Convertir tags de emoción a texto natural o instrucciones
        def emotion_replacer(match):
            tag_content = match.group(1)
            
            # Si es una pausa, ya la procesamos antes
            if tag_content.startswith('Pause:'):
                return match.group(0)  # Mantener el tag original (ya procesado)
            
            # Procesar emociones compuestas (ej: [Confident, casual])
            emotions_in_tag = [e.strip().lower() for e in tag_content.split(',')]
            
            # Convertir a instrucciones naturales
            instructions = []
            for emotion in emotions_in_tag:
                # Limpiar modificadores (ej: "subtle", "huge")
                emotion_clean = re.sub(r'\s*(subtle|huge|slight|strong)\s*:', '', emotion)
                emotion_clean = emotion_clean.strip()
                
                if emotion_clean in VoiceScriptProcessor.EMOTION_MAP:
                    instructions.append(VoiceScriptProcessor.EMOTION_MAP[emotion_clean])
            
            # Si hay instrucciones, agregarlas como comentario natural
            if instructions:
                return f"({', '.join(instructions)}) "
            
            # Si no hay mapeo, mantener el tag como guía
            return f"({tag_content.lower()}) "
        
        text = re.sub(emotion_pattern, emotion_replacer, text)
        
        # Limpiar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Máximo 2 saltos de línea
        text = text.strip()
        
        metadata['processed_length'] = len(text)
        
        return {
            'processed_text': text,
            'metadata': metadata,
            'has_emotions': len(valid_emotions) > 0,
            'has_pauses': len(metadata['pauses_found']) > 0
        }
    
    @staticmethod
    def enhance_for_elevenlabs(text: str, use_natural_pauses: bool = True) -> str:
        """
        Versión simplificada que mejora el texto para ElevenLabs sin tags.
        Convierte pausas y emociones a formato natural.
        
        Args:
            text: Texto con o sin tags
            use_natural_pauses: Si True, usa puntos suspensivos para pausas
        
        Returns:
            Texto optimizado para ElevenLabs
        """
        result = VoiceScriptProcessor.process_script(text, use_ssml=False)
        return result['processed_text']
    
    @staticmethod
    def add_voice_guidance(text: str, emotion: str = None, pace: str = 'normal') -> str:
        """
        Añade guía de voz al texto sin usar tags complejos.
        Útil cuando quieres mejorar un texto sin tags.
        
        Args:
            text: Texto original
            emotion: Emoción general (confident, casual, energetic, etc.)
            pace: Ritmo (slow, normal, fast)
        
        Returns:
            Texto con guía natural añadida
        """
        guidance_parts = []
        
        if emotion and emotion.lower() in VoiceScriptProcessor.EMOTION_MAP:
            guidance_parts.append(VoiceScriptProcessor.EMOTION_MAP[emotion.lower()])
        
        if pace != 'normal':
            pace_map = {
                'slow': 'hablando despacio',
                'fast': 'hablando rápido',
                'very_slow': 'hablando muy despacio',
                'very_fast': 'hablando muy rápido'
            }
            if pace in pace_map:
                guidance_parts.append(pace_map[pace])
        
        if guidance_parts:
            # Añadir guía al inicio como contexto
            guidance = f"({', '.join(guidance_parts)}): "
            return guidance + text
        
        return text


# Ejemplo de uso
if __name__ == '__main__':
    sample_script = """
    [Confident, casual]
    ¿La IA es el final de la creatividad humana? Nah.
    
    [Pause: 0.4s]
    
    [Storytelling, slightly sarcastic]
    Cuando llegaron apps como Instagram o TikTok, todos decían lo mismo:
    
    [Pause: 0.2s]
    
    [Impersonation, mocking tone]
    "la gente ya no va a crear, todo va a ser copia".
    
    [Laugh, subtle: 0.3s]
    Y míranos:
    
    [Pause: 0.2s]
    
    [Energetic, proud]
    Creando trends legendarios cada semana.
    """
    
    processor = VoiceScriptProcessor()
    result = processor.process_script(sample_script)
    
    print("Texto original:")
    print(sample_script)
    print("\n" + "="*50 + "\n")
    print("Texto procesado:")
    print(result['processed_text'])
    print("\n" + "="*50 + "\n")
    print("Metadata:")
    print(f"Emociones encontradas: {result['metadata']['emotions_found']}")
    print(f"Pausas encontradas: {result['metadata']['pauses_found']}")

