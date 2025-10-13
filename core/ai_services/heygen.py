"""Cliente para HeyGen API"""
import logging
from typing import List, Dict, Optional
from .base import BaseAIClient

logger = logging.getLogger(__name__)


class HeyGenClient(BaseAIClient):
    """Cliente para interactuar con HeyGen API"""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url='https://api.heygen.com'
        )
    
    def list_avatars(self) -> List[Dict]:
        """Lista todos los avatares disponibles"""
        try:
            response = self.make_request('GET', '/v2/avatars')
            return response.get('data', {}).get('avatars', [])
        except Exception as e:
            logger.error(f"Error al obtener avatares: {str(e)}")
            raise
    
    def list_voices(self) -> List[Dict]:
        """Lista todas las voces disponibles"""
        try:
            response = self.make_request('GET', '/v2/voices')
            return response.get('data', {}).get('voices', [])
        except Exception as e:
            logger.error(f"Error al obtener voces: {str(e)}")
            raise
    
    def generate_video(
        self,
        script: str,
        avatar_id: str,
        voice_id: str,
        title: str = "Untitled Video",
        has_background: bool = False,
        background_url: Optional[str] = None,
        dimension: Dict[str, int] = None,
        aspect_ratio: str = "16:9",
        caption: bool = True,
        voice_speed: float = 1.0,
        voice_pitch: int = 50,
        voice_emotion: str = "Excited",
        **kwargs
    ) -> dict:
        """Genera un video con avatar en HeyGen"""
        if dimension is None:
            dimension = {"width": 1280, "height": 720}
        
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                        "scale": 1.0
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id,
                        "speed": voice_speed,
                        "pitch": voice_pitch,
                        "emotion": voice_emotion
                    }
                }
            ],
            "dimension": dimension,
            "aspect_ratio": aspect_ratio,
            "caption": str(caption).lower(),
            "title": title
        }
        
        if has_background and background_url:
            payload["video_inputs"][0]["background"] = {
                "type": "image",
                "url": background_url
            }
        
        try:
            logger.info(f"Generando video en HeyGen: {title}")
            response = self.make_request('POST', '/v2/video/generate', json=payload)
            logger.info(f"Video creado. ID: {response.get('data', {}).get('video_id')}")
            return response
        except Exception as e:
            logger.error(f"Error al generar video: {str(e)}")
            raise
    
    def get_video_status(self, video_id: str) -> dict:
        """Obtiene el estado de un video"""
        try:
            response = self.make_request('GET', f'/v1/video_status.get?video_id={video_id}')
            return response.get('data', {})
        except Exception as e:
            logger.error(f"Error al obtener estado: {str(e)}")
            raise
    
    def get_video_url(self, video_id: str) -> Optional[str]:
        """Obtiene la URL del video completado"""
        try:
            status = self.get_video_status(video_id)
            if status.get('status') == 'completed':
                return status.get('video_url')
            return None
        except Exception as e:
            logger.error(f"Error al obtener URL: {str(e)}")
            return None

