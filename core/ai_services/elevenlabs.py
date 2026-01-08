"""
Cliente para ElevenLabs Text-to-Speech API
"""

import requests
import logging
import base64
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ElevenLabsClient:
    """Cliente para interactuar con ElevenLabs API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io"
        self.session = requests.Session()
        self.session.headers.update({
            'xi-api-key': api_key,
            'Content-Type': 'application/json'
        })
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Realiza una petición a la API de ElevenLabs
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API (ej: '/v1/voices')
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Respuesta JSON de la API
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Si la respuesta es JSON, devolverla
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            
            # Si es audio u otro contenido binario, devolver el contenido
            return {
                'content': response.content,
                'content_type': response.headers.get('Content-Type'),
                'status_code': response.status_code
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from ElevenLabs API: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Error making request to ElevenLabs: {e}")
            raise
    
    def list_voices(self) -> List[Dict]:
        """
        Lista TODAS las voces disponibles de una sola vez (Endpoint V1).
        Esto permite alimentar el modal con el catálogo completo para filtrar en el frontend.
        """
        try:
            logger.info("Listando catálogo completo de voces ElevenLabs (API V1)...")
            
            # Usamos /v1/voices porque devuelve la lista completa sin forzar paginación estricta
            response = self.make_request('GET', '/v1/voices')
            
            # La respuesta suele venir en la clave 'voices'
            voices = response.get('voices', [])
            logger.info(f"Se encontraron {len(voices)} voces en total.")
            
            simplified_voices = []
            for voice in voices:
                # Extraemos etiquetas para facilitar el filtrado en el frontend
                labels = voice.get('labels', {})
                
                # Normalizamos un poco los datos antes de enviarlos
                simplified_voices.append({
                    'voice_id': voice.get('voice_id'),
                    'name': voice.get('name'),
                    'category': voice.get('category'), # 'premade', 'cloned', 'generated'
                    'labels': labels,                  # Aquí suelen venir 'gender', 'accent', etc.
                    'description': voice.get('description', ''),
                    'preview_url': voice.get('preview_url'),
                    'settings': voice.get('settings', {}),
                    
                    # Extraemos género explícitamente si existe para facilitar al JS
                    'gender': labels.get('gender', 'unknown'),
                })
            
            return simplified_voices
            
        except Exception as e:
            logger.error(f"Error al listar voces de ElevenLabs: {e}")
            raise

    def get_voice(self, voice_id: str) -> Dict:
        """
        Obtiene información de una voz específica
        
        Args:
            voice_id: ID de la voz
            
        Returns:
            Diccionario con información de la voz
        """
        try:
            logger.info(f"Obteniendo información de la voz: {voice_id}")
            response = self.make_request('GET', f'/v1/voices/{voice_id}')
            return response
        except Exception as e:
            logger.error(f"Error al obtener voz {voice_id}: {e}")
            raise
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_turbo_v2_5",
        language_code: str = "es",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        speed: float = 1.0,
        **kwargs
    ) -> bytes:
        """
        Convierte texto a voz
        
        Args:
            text: Texto para convertir
            voice_id: ID de la voz a usar
            model_id: Modelo de ElevenLabs
            language_code: Código de idioma (ISO 639-1)
            output_format: Formato de salida (mp3_44100_128, etc.)
            stability: Estabilidad de la voz (0.0-1.0)
            similarity_boost: Similitud con la voz original (0.0-1.0)
            style: Estilo de la voz (0.0-1.0)
            speed: Velocidad de la voz (0.25-4.0)
            
        Returns:
            Audio en bytes
        """
        try:
            logger.info(f"Generando TTS con voz {voice_id}")
            logger.info(f"  Texto: {text[:100]}{'...' if len(text) > 100 else ''}")
            logger.info(f"  Modelo: {model_id}")
            logger.info(f"  Idioma: {language_code}")
            
            payload = {
                "text": text,
                "model_id": model_id,
                "language_code": language_code,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "speed": speed
                }
            }
            
            # Agregar parámetros opcionales
            for key in ['seed', 'previous_text', 'next_text']:
                if key in kwargs and kwargs[key] is not None:
                    payload[key] = kwargs[key]
            
            endpoint = f'/v1/text-to-speech/{voice_id}?output_format={output_format}'
            response = self.make_request('POST', endpoint, json=payload)
            
            # La respuesta es el audio en bytes
            audio_bytes = response.get('content')
            logger.info(f"✓ Audio generado ({len(audio_bytes)} bytes)")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error al generar TTS: {e}")
            raise
    
    def text_to_speech_with_timestamps(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_turbo_v2_5",
        language_code: str = "es",
        output_format: str = "mp3_44100_128",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        speed: float = 1.0,
        **kwargs
    ) -> Dict:
        """
        Convierte texto a voz con timestamps carácter por carácter
        
        Args:
            text: Texto para convertir
            voice_id: ID de la voz a usar
            model_id: Modelo de ElevenLabs
            language_code: Código de idioma (ISO 639-1)
            output_format: Formato de salida
            stability: Estabilidad de la voz (0.0-1.0)
            similarity_boost: Similitud con la voz original (0.0-1.0)
            style: Estilo de la voz (0.0-1.0)
            speed: Velocidad de la voz (0.25-4.0)
            
        Returns:
            Dict con 'audio_base64', 'alignment' y 'normalized_alignment'
        """
        try:
            logger.info(f"Generando TTS con timestamps para voz {voice_id}")
            
            payload = {
                "text": text,
                "model_id": model_id,
                "language_code": language_code,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                    "speed": speed
                }
            }
            
            # Agregar parámetros opcionales
            for key in ['seed', 'previous_text', 'next_text']:
                if key in kwargs and kwargs[key] is not None:
                    payload[key] = kwargs[key]
            
            endpoint = f'/v1/text-to-speech/{voice_id}/with-timestamps?output_format={output_format}'
            response = self.make_request('POST', endpoint, json=payload)
            
            logger.info(f"✓ Audio con timestamps generado")
            
            return response
            
        except Exception as e:
            logger.error(f"Error al generar TTS con timestamps: {e}")
            raise

