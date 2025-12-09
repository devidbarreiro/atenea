"""Cliente para HeyGen API"""
import logging
import requests
import imghdr
from typing import List, Dict, Optional
from .base import BaseAIClient

logger = logging.getLogger(__name__)


def detect_image_type(image_data: bytes) -> str:
    """
    Detecta el tipo real de una imagen basándose en su contenido
    
    Args:
        image_data: Bytes de la imagen
        
    Returns:
        Content-Type apropiado (image/jpeg, image/png, image/webp)
    """
    # Detectar por magic bytes (primeros bytes del archivo)
    if image_data.startswith(b'\xFF\xD8\xFF'):
        return 'image/jpeg'
    elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
        return 'image/webp'
    elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
        return 'image/gif'
    else:
        # Fallback: intentar con imghdr
        img_type = imghdr.what(None, h=image_data)
        if img_type == 'jpeg':
            return 'image/jpeg'
        elif img_type == 'png':
            return 'image/png'
        elif img_type == 'webp':
            return 'image/webp'
        else:
            # Por defecto, asumir JPEG
            logger.warning(f"No se pudo detectar el tipo de imagen, usando image/jpeg por defecto")
            return 'image/jpeg'


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
    
    def list_assets(self, file_type: str = None, limit: int = 100) -> List[Dict]:
        """
        Lista los assets (imágenes, videos, audio) disponibles en HeyGen
        
        Args:
            file_type: Filtrar por tipo ('image', 'video', 'audio')
            limit: Número máximo de resultados por página
            
        Returns:
            List de assets disponibles
        """
        try:
            params = {'limit': str(limit)}
            if file_type:
                params['file_type'] = file_type
            
            # Construir URL con parámetros
            param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
            endpoint = f'/v1/asset/list?{param_str}'
            
            logger.info(f"Listando assets de HeyGen (tipo: {file_type or 'todos'})")
            response = self.make_request('GET', endpoint)
            
            assets = response.get('data', {}).get('assets', [])
            logger.info(f"Se encontraron {len(assets)} assets")
            
            return assets
        except Exception as e:
            logger.error(f"Error al listar assets: {str(e)}")
            raise
    
    def list_image_assets(self, limit: int = 100) -> List[Dict]:
        """Lista solo los assets de tipo imagen"""
        return self.list_assets(file_type='image', limit=limit)
    
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
            # Según la documentación de HeyGen V2, el background debe usar:
            # - type: "image" o "color"
            # - src: URL de la imagen (para type: "image")
            # - value: color hex/rgba (para type: "color")
            
            # Verificar si es una URL o un color
            if background_url.startswith('http://') or background_url.startswith('https://'):
                # Es una URL de imagen - usar directamente con "src"
                logger.info(f"Usando imagen de fondo desde URL: {background_url}")
                payload["video_inputs"][0]["background"] = {
                    "type": "image",
                    "src": background_url
                }
            elif background_url.startswith('#') or background_url.startswith('rgb'):
                # Es un color
                logger.info(f"Usando color de fondo: {background_url}")
                payload["video_inputs"][0]["background"] = {
                    "type": "color",
                    "value": background_url
                }
            else:
                # Podría ser un asset_id de HeyGen - intentar subirlo primero o usar como URL
                # Si es un asset_id, HeyGen podría requerir subirlo como asset primero
                logger.warning(f"background_url no es una URL válida ni un color: {background_url}")
                logger.info(f"Intentando usar como URL directa...")
                # Intentar construir una URL o usar como está
                payload["video_inputs"][0]["background"] = {
                    "type": "image",
                    "src": background_url if background_url.startswith('http') else f"https://{background_url}"
                }
        
        try:
            logger.info(f"Generando video en HeyGen: {title}")
            logger.info(f"Payload completo: {payload}")
            if has_background and background_url:
                logger.info(f"Background configurado: {payload['video_inputs'][0].get('background', {})}")
            response = self.make_request('POST', '/v2/video/generate', json=payload)
            logger.info(f"Video creado. ID: {response.get('data', {}).get('video_id')}")
            return response
        except Exception as e:
            logger.error(f"Error al generar video: {str(e)}")
            raise
    
    def get_video_status(self, video_id: str) -> dict:
        """Obtiene el estado de un video"""
        try:
            logger.info(f"[POLLING] Consultando estado del video HeyGen: {video_id}")
            response = self.make_request('GET', f'/v1/video_status.get?video_id={video_id}')
            
            # Log completo de la respuesta
            logger.info(f"[POLLING] Respuesta completa de HeyGen: {response}")
            
            status_data = response.get('data', {})
            status = status_data.get('status', 'unknown')
            
            logger.info(f"[POLLING] Video {video_id} - Estado: {status}")
            logger.info(f"[POLLING] Data completa: {status_data}")
            
            # Log específico si está completado
            if status == 'completed':
                logger.info(f"[POLLING] ✅ VIDEO COMPLETADO!")
                logger.info(f"[POLLING] video_url: {status_data.get('video_url')}")
                logger.info(f"[POLLING] duration: {status_data.get('duration')}")
                logger.info(f"[POLLING] thumbnail_url: {status_data.get('thumbnail_url')}")
            elif status == 'failed':
                logger.error(f"[POLLING] ❌ VIDEO FALLÓ!")
                logger.error(f"[POLLING] error: {status_data.get('error')}")
            elif status == 'processing':
                logger.info(f"[POLLING] ⏳ Video aún procesando...")
            elif status == 'pending':
                logger.info(f"[POLLING] ⏸️ Video en cola esperando...")
            
            return status_data
        except Exception as e:
            logger.error(f"[POLLING] Error al obtener estado de {video_id}: {str(e)}")
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
    
    def upload_asset_from_file(self, file_path: str, content_type: str = 'image/jpeg') -> str:
        """
        Sube una imagen a HeyGen desde un archivo y retorna el image_key
        
        Args:
            file_path: Ruta al archivo de imagen
            content_type: Tipo MIME del archivo (image/jpeg o image/png)
            
        Returns:
            str: image_key para usar en Avatar IV
        """
        try:
            logger.info(f"Subiendo asset a HeyGen desde archivo: {file_path}")
            
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Usar el método from_bytes que ya tiene mejor logging
            return self.upload_asset_from_bytes(file_data, content_type)
            
        except Exception as e:
            logger.error(f"Error al subir asset desde archivo: {str(e)}")
            raise
    
    def upload_asset_from_bytes(self, file_content: bytes, content_type: str = None) -> str:
        """
        Sube una imagen desde memoria a HeyGen y retorna el image_key
        
        Args:
            file_content: Contenido del archivo en bytes
            content_type: Tipo MIME del archivo (si es None, se detecta automáticamente)
            
        Returns:
            str: image_key para usar en Avatar IV
        """
        url = "https://upload.heygen.com/v1/asset"
        
        try:
            # Detectar tipo real del archivo si no se especifica
            if content_type is None:
                content_type = detect_image_type(file_content)
                logger.info(f"Tipo de imagen detectado automáticamente: {content_type}")
            
            logger.info(f"Subiendo asset a HeyGen desde memoria ({len(file_content)} bytes, tipo: {content_type})")
            
            headers = {
                'Content-Type': content_type,
                'X-Api-Key': self.api_key
            }
            
            response = requests.post(url, headers=headers, data=file_content)
            
            # Log de respuesta antes de raise_for_status
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:500]}")  # Primeros 500 chars
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Response JSON completo: {data}")
            
            # Intentar obtener image_key de diferentes ubicaciones
            image_key = None
            if 'data' in data:
                image_key = data['data'].get('image_key') or data['data'].get('id')
            elif 'image_key' in data:
                image_key = data.get('image_key')
            elif 'id' in data:
                image_key = data.get('id')
            
            if not image_key:
                raise ValueError(f"No se recibió image_key de HeyGen. Response: {data}")
            
            logger.info(f"Asset subido exitosamente. Image key: {image_key}")
            return image_key
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error al subir asset: {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Error al subir asset: {str(e)}")
            raise
    
    def upload_asset_from_url(self, image_url: str, content_type: str = None) -> str:
        """
        Descarga una imagen desde URL y la sube a HeyGen
        
        Args:
            image_url: URL de la imagen a subir
            content_type: Tipo MIME del archivo (si es None, se detecta automáticamente)
            
        Returns:
            str: image_key para usar en Avatar IV
        """
        try:
            logger.info(f"Descargando imagen desde: {image_url}")
            
            # Descargar imagen desde URL
            response = requests.get(image_url)
            response.raise_for_status()
            file_content = response.content
            
            logger.info(f"Imagen descargada ({len(file_content)} bytes), subiendo a HeyGen...")
            
            # Subir a HeyGen (detectará el tipo automáticamente si content_type es None)
            return self.upload_asset_from_bytes(file_content, content_type)
            
        except Exception as e:
            logger.error(f"Error al subir asset desde URL: {str(e)}")
            raise
    
    def generate_avatar_iv_video(
        self,
        script: str,
        image_key: str,
        voice_id: str,
        title: str = "Untitled Video",
        video_orientation: str = "portrait",
        fit: str = "cover",
        **kwargs
    ) -> dict:
        """
        Genera un video Avatar IV en HeyGen
        
        Args:
            script: Texto que dirá el avatar
            image_key: Image key obtenido del upload de asset
            voice_id: ID de la voz a usar
            title: Título del video
            video_orientation: Orientación del video (portrait, landscape)
            fit: Cómo ajustar el avatar (cover, contain)
            
        Returns:
            dict: Respuesta de la API con el video_id
        """
        # Estructura correcta para Avatar IV según documentación
        payload = {
            "image_key": image_key,
            "video_title": title,
            "script": script,
            "voice_id": voice_id,
            "video_orientation": video_orientation,
            "fit": fit
        }
        
        try:
            logger.info(f"Generando video Avatar IV en HeyGen: {title}")
            logger.info(f"Payload: image_key={image_key}, voice_id={voice_id}, orientation={video_orientation}")
            response = self.make_request('POST', '/v2/video/av4/generate', json=payload)
            logger.info(f"Video Avatar IV creado. ID: {response.get('data', {}).get('video_id')}")
            return response
        except Exception as e:
            logger.error(f"Error al generar video Avatar IV: {str(e)}")
            raise

