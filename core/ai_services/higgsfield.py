"""Cliente para Higgsfield API"""
import logging
import time
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)

# Modelos disponibles de Higgsfield
HIGGSFIELD_MODELS = {
    # Image-to-Video models
    'higgsfield-ai/dop/standard': {
        'name': 'DoP Standard',
        'description': 'Generación de video de alta calidad a partir de imágenes',
        'type': 'image_to_video',
        'supports_text_to_video': False,
        'supports_image_to_video': True,
        'credits_per_generation': 7,
        'typical_duration': 3,  # segundos
        'resolution': '720p',
    },
    'higgsfield-ai/dop/preview': {
        'name': 'DoP Preview',
        'description': 'Generación rápida de video a partir de imágenes',
        'type': 'image_to_video',
        'supports_text_to_video': False,
        'supports_image_to_video': True,
        'credits_per_generation': 3,
        'typical_duration': 3,  # segundos
        'resolution': '720p',
    },
    'bytedance/seedance/v1/pro/image-to-video': {
        'name': 'Seedance V1 Pro',
        'description': 'Generación profesional de video a partir de imágenes (ByteDance)',
        'type': 'image_to_video',
        'supports_text_to_video': False,
        'supports_image_to_video': True,
        'credits_per_generation': 400,
        'typical_duration': 5,  # segundos
        'resolution': '1080p',
    },
    'kling-video/v2.1/pro/image-to-video': {
        'name': 'Kling V2.1 Pro (via Higgsfield)',
        'description': 'Generación avanzada de video a partir de imágenes',
        'type': 'image_to_video',
        'supports_text_to_video': False,
        'supports_image_to_video': True,
        'credits_per_generation': 35,
        'typical_duration': 5,  # segundos
        'resolution': '1080p',
    },
    # Text-to-Image models
    'higgsfield-ai/soul/standard': {
        'name': 'Soul Standard',
        'description': 'Generación de imágenes de alta calidad a partir de texto',
        'type': 'text_to_image',
        'supports_text_to_video': False,
        'supports_image_to_video': False,
        'supports_text_to_image': True,
    },
    'reve/text-to-image': {
        'name': 'Reve Text-to-Image',
        'description': 'Generación versátil de imágenes a partir de texto',
        'type': 'text_to_image',
        'supports_text_to_video': False,
        'supports_image_to_video': False,
        'supports_text_to_image': True,
    },
    'flux-pro/kontext/max/text-to-image': {
        'name': 'Flux Pro Kontext Max Text-to-Image',
        'description': 'Generación de imágenes de alta calidad a partir de texto (Flux Pro Kontext Max)',
        'type': 'text_to_image',
        'aspect_ratio': ['16:9', '4:3', '1:1', '3:4', '9:16'],
        'safety_tolerance': [1, 2, 3, 4, 5, 6],
        'seed': 'string',
        'supports_text_to_video': False,
        'supports_image_to_video': False,
        'supports_text_to_image': True,
    },
}


class HiggsfieldClient:
    """Cliente para Higgsfield API"""
    
    def __init__(self, api_key_id: str, api_key_secret: str):
        """
        Inicializa el cliente de Higgsfield
        
        Args:
            api_key_id: API Key ID de Higgsfield
            api_key_secret: API Key Secret de Higgsfield
        """
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        self.base_url = "https://platform.higgsfield.ai"
        self.session = requests.Session()
        
        logger.info("Cliente Higgsfield inicializado")
    
    def _get_headers(self) -> dict:
        """Retorna los headers para las peticiones"""
        auth_string = f"Key {self.api_key_id}:{self.api_key_secret}"
        return {
            'Authorization': auth_string,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def generate_video(
        self,
        model_id: str,
        prompt: str,
        image_url: str = None,
        aspect_ratio: str = None,
        resolution: str = None,
        duration: int = None
    ) -> dict:
        """
        Genera un video con Higgsfield
        
        Args:
            model_id: ID del modelo (ej: 'higgsfield-ai/dop/standard')
            prompt: Descripción del movimiento/animación deseada
            image_url: URL de la imagen de entrada (requerido para image-to-video)
            aspect_ratio: Relación de aspecto ("16:9", "9:16", "1:1") - opcional
            resolution: Resolución ("720p", "1080p") - opcional
            duration: Duración en segundos - opcional (algunos modelos lo requieren)
        
        Returns:
            dict con request_id y URLs de estado
        
        Raises:
            ValueError: Si los parámetros no son válidos
            Exception: Si falla la generación
        """
        # Validar modelo
        if model_id not in HIGGSFIELD_MODELS:
            raise ValueError(f"Modelo no soportado: {model_id}. Opciones: {list(HIGGSFIELD_MODELS.keys())}")
        
        model_info = HIGGSFIELD_MODELS[model_id]
        
        # Validar que image_url esté presente para image-to-video
        if model_info['supports_image_to_video'] and not image_url:
            raise ValueError(f"El modelo {model_id} requiere image_url para image-to-video")
        
        logger.info(f"🎬 Generando video con Higgsfield")
        logger.info(f"   Modelo: {model_id} - {model_info['name']}")
        logger.info(f"   Prompt: {prompt[:100]}...")
        logger.info(f"   Duración: {duration}s, Resolución: {resolution}, Aspect Ratio: {aspect_ratio}")
        
        try:
            endpoint = f"{self.base_url}/{model_id}"
            
            # Payload mínimo requerido
            payload = {
                "prompt": prompt,
            }
            
            # Añadir image_url si está presente (requerido para image-to-video)
            if image_url:
                payload["image_url"] = image_url
            
            # Añadir parámetros opcionales solo si se proporcionan
            if aspect_ratio:
                payload["aspect_ratio"] = aspect_ratio
            
            if resolution:
                payload["resolution"] = resolution
            
            if duration:
                payload["duration"] = duration
            
            logger.info(f"📤 Enviando request a: {endpoint}")
            
            response = self.session.post(
                endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=60
            )
            
            logger.info(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                request_id = data.get('request_id')
                
                logger.info(f"✅ Video creado exitosamente!")
                logger.info(f"   Request ID: {request_id}")
                logger.info(f"   Status: {data.get('status', 'queued')}")
                
                return {
                    'request_id': request_id,
                    'status': data.get('status', 'queued'),
                    'status_url': data.get('status_url'),
                    'cancel_url': data.get('cancel_url'),
                    'model_id': model_id,
                    'prompt': prompt,
                    'raw_response': data
                }
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error al crear video: {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Higgsfield API: {str(e)}")
            raise Exception(f"Error de conexión: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}")
            raise
    
    def get_request_status(self, request_id: str) -> dict:
        """
        Obtiene el estado de una solicitud de generación
        
        Args:
            request_id: ID de la solicitud
        
        Returns:
            dict con el estado y datos del video si está completo
        """
        try:
            logger.info(f"Consultando estado de request: {request_id}")
            
            endpoint = f"{self.base_url}/requests/{request_id}/status"
            
            response = self.session.get(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                logger.info(f"📊 Status: {status}")
                
                result = {
                    'request_id': request_id,
                    'status': status,
                    'status_url': data.get('status_url'),
                    'cancel_url': data.get('cancel_url'),
                    'raw_response': data
                }
                
                if status == 'completed':
                    logger.info(f"✅ Video completado!")
                    
                    # Extraer URLs de video e imágenes
                    video_url = None
                    image_urls = []
                    
                    if 'video' in data and data['video']:
                        video_url = data['video'].get('url')
                    
                    if 'images' in data and data['images']:
                        image_urls = [img.get('url') for img in data['images'] if img.get('url')]
                    
                    result['video_url'] = video_url
                    result['image_urls'] = image_urls
                    
                elif status == 'failed':
                    logger.error(f"❌ Video falló")
                    result['error'] = data.get('error', 'Unknown error')
                elif status == 'nsfw':
                    logger.warning(f"⚠️  Contenido bloqueado por moderación")
                    result['error'] = 'Content failed moderation checks'
                
                return result
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error consultando estado: {error_msg}")
                return {
                    'request_id': request_id,
                    'status': 'error',
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Error al consultar estado: {str(e)}")
            return {
                'request_id': request_id,
                'status': 'error',
                'error': str(e)
            }
    
    def cancel_request(self, request_id: str) -> bool:
        """
        Cancela una solicitud pendiente
        
        Args:
            request_id: ID de la solicitud
        
        Returns:
            True si se canceló exitosamente
        """
        try:
            logger.info(f"Cancelando request: {request_id}")
            
            endpoint = f"{self.base_url}/requests/{request_id}/cancel"
            
            response = self.session.post(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 202:
                logger.info(f"✅ Request cancelado exitosamente")
                return True
            else:
                logger.warning(f"⚠️  No se pudo cancelar request: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al cancelar request: {str(e)}")
            return False
    
    def wait_for_completion(
        self,
        request_id: str,
        max_wait_seconds: int = 600,
        poll_interval: int = 10
    ) -> dict:
        """
        Espera a que un video se complete con polling
        
        Args:
            request_id: ID de la solicitud
            max_wait_seconds: Máximo tiempo de espera (default: 10 min)
            poll_interval: Intervalo entre consultas en segundos (default: 10s)
        
        Returns:
            dict con el estado final del video
        """
        logger.info(f"⏳ Esperando a que el request {request_id} se complete...")
        logger.info(f"   Tiempo máximo: {max_wait_seconds}s, Intervalo: {poll_interval}s")
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                logger.error(f"❌ Timeout esperando video después de {elapsed:.1f}s")
                return {
                    'request_id': request_id,
                    'status': 'timeout',
                    'error': f'Timeout after {elapsed:.1f}s'
                }
            
            status_data = self.get_request_status(request_id)
            status = status_data.get('status')
            
            if status == 'completed':
                logger.info(f"✅ Video completado en {elapsed:.1f}s!")
                return status_data
            elif status in ['failed', 'nsfw']:
                logger.error(f"❌ Video falló después de {elapsed:.1f}s")
                return status_data
            elif status in ['queued', 'in_progress']:
                logger.info(f"⏳ Procesando... ({elapsed:.1f}s transcurridos)")
                time.sleep(poll_interval)
            else:
                logger.warning(f"⚠️  Estado desconocido: {status}")
                time.sleep(poll_interval)
    
    def _parse_error(self, response: requests.Response) -> str:
        """Parsea el mensaje de error de la API"""
        try:
            error_data = response.json()
            if 'error' in error_data:
                return str(error_data['error'])
            if 'message' in error_data:
                return str(error_data['message'])
            return error_data.get('detail', response.text)
        except (json.JSONDecodeError, KeyError, TypeError):
            return f"HTTP {response.status_code}: {response.text[:200]}"

def generate_image(
    self,
    model_id: str,
    prompt: str,
    aspect_ratio: str = None,
    resolution: str = None,
    output_format: str = None,
    image_url: str = None,
    wait_for_completion: bool = True,
    poll_interval: int = 5,
    max_wait_seconds: int = 300
) -> dict:
    """
    Genera una imagen con Higgsfield (o edita una existente).
    
    Args:
        model_id: ID del modelo (ej: 'nano-banana-pro' o 'nano-banana-pro/edit')
        prompt: Texto descriptivo de la imagen
        aspect_ratio: Relación de aspecto (ej: '1:1', '4:3', etc.)
        resolution: Resolución ('1k', '2k', '4k')
        output_format: Formato de salida ('png', 'jpeg')
        image_url: URL de imagen de entrada (solo para edición)
        wait_for_completion: Si True, espera a que la imagen esté lista
        poll_interval: Intervalo de polling en segundos
        max_wait_seconds: Tiempo máximo de espera en segundos
    
    Returns:
        dict con información de la solicitud y URLs de imágenes generadas
    """
    model_info = HIGGSFIELD_MODELS.get(model_id)
    if not model_info:
        raise ValueError(f"Modelo no soportado: {model_id}")
    
    if model_info['type'] not in ['text_to_image', 'image_edit']:
        raise ValueError(f"El modelo {model_id} no es de generación de imágenes")
    
    # Para modelos de edición, image_url es obligatorio
    if model_info['type'] == 'image_edit' and not image_url:
        raise ValueError(f"El modelo {model_id} requiere image_url para editar la imagen")
    
    payload = {"prompt": prompt}
    
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if resolution:
        payload["resolution"] = resolution
    if output_format:
        payload["output_format"] = output_format
    if image_url:
        payload["image_url"] = image_url
    
    endpoint = f"{self.base_url}/{model_id}"
    
    logger.info(f"📤 Enviando request a: {endpoint}")
    logger.info(f"   Payload: {payload}")
    
    response = self.session.post(
        endpoint,
        json=payload,
        headers=self._get_headers(),
        timeout=60
    )
    
    if response.status_code != 200:
        error_msg = self._parse_error(response)
        logger.error(f"❌ Error al crear imagen: {error_msg}")
        raise Exception(error_msg)
    
    data = response.json()
    request_id = data.get('request_id')
    
    result = {
        'request_id': request_id,
        'status': data.get('status', 'queued'),
        'status_url': data.get('status_url'),
        'cancel_url': data.get('cancel_url'),
        'model_id': model_id,
        'prompt': prompt,
        'image_urls': [],
        'raw_response': data
    }
    
    if wait_for_completion:
        start_time = time.time()
        while True:
            status_data = self.get_request_status(request_id)
            status = status_data.get('status')
            
            if status == 'completed':
                result['status'] = 'completed'
                result['image_urls'] = [img.get('url') for img in status_data.get('images', []) if img.get('url')]
                break
            elif status in ['failed', 'nsfw']:
                result.update(status_data)
                break
            
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                result['status'] = 'timeout'
                result['error'] = f"Timeout después de {elapsed:.1f}s"
                break
            
            time.sleep(poll_interval)
    
    return result
