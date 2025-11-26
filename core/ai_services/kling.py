"""Cliente para Kling AI API"""
import logging
import time
from typing import Dict, Optional
import requests
import hmac
import hashlib
import base64
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Modelos disponibles de Kling
KLING_MODELS = {
    'kling-v1': {
        'name': 'Kling V1',
        'modes': ['std', 'pro'],
        'durations': [5, 10],
        'resolutions': {'std': '720p', 'pro': '720p'},
        'fps': 30,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'kling-v1-5': {
        'name': 'Kling V1.5',
        'modes': ['std', 'pro'],
        'durations': [5, 10],
        'resolutions': {'std': '720p', 'pro': '1080p'},
        'fps': 30,
        'supports_text_to_video': False,
        'supports_image_to_video': True,
    },
    'kling-v1-6': {
        'name': 'Kling V1.6',
        'modes': ['std', 'pro'],
        'durations': [5, 10],
        'resolutions': {'std': '720p', 'pro': '1080p'},
        'fps': 30,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'kling-v2-master': {
        'name': 'Kling V2 Master',
        'modes': [],  # No tiene modos STD/PRO
        'durations': [5, 10],
        'resolutions': {'default': '720p'},
        'fps': 24,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'kling-v2-1': {
        'name': 'Kling V2.1',
        'modes': ['std', 'pro'],
        'durations': [5, 10],
        'resolutions': {'std': '720p', 'pro': '1080p'},
        'fps': 24,
        'supports_text_to_video': False,
        'supports_image_to_video': True,
    },
    'kling-v2-5-turbo': {
        'name': 'Kling V2.5 Turbo',
        'modes': ['std', 'pro'],
        'durations': [5, 10],
        'resolutions': {'std': '1080p', 'pro': '1080p'},
        'fps': 24,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
}


class KlingClient:
    """Cliente para Kling AI API"""
    
    def __init__(self, access_key: str, secret_key: str):
        """
        Inicializa el cliente de Kling
        
        Args:
            access_key: Access Key de Kling
            secret_key: Secret Key de Kling
        """
        self.access_key = access_key
        self.secret_key = secret_key
        # Nota: La URL base puede variar según la documentación real de Kling
        self.base_url = "https://api.klingai.com"  # Ajustar según documentación real
        self.session = requests.Session()
        
        logger.info("Cliente Kling inicializado")
    
    def _sign_request(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """
        Firma una request usando HMAC-SHA256 (patrón común en APIs)
        
        Args:
            method: Método HTTP
            path: Path del endpoint
            params: Parámetros de query string
            body: Body de la request
        
        Returns:
            dict con headers firmados
        """
        # Construir string a firmar
        timestamp = str(int(time.time()))
        nonce = str(int(time.time() * 1000))
        
        # Construir query string ordenado
        query_string = ""
        if params:
            sorted_params = sorted(params.items())
            query_string = urlencode(sorted_params)
        
        # Construir string a firmar
        string_to_sign = f"{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}"
        if body:
            import json
            string_to_sign += f"\n{json.dumps(body, sort_keys=True)}"
        
        # Firmar con HMAC-SHA256
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'X-Access-Key': self.access_key,
            'X-Timestamp': timestamp,
            'X-Nonce': nonce,
            'X-Signature': signature,
        }
    
    def _get_headers(self, method: str = 'GET', path: str = '', params: dict = None, body: dict = None) -> dict:
        """Retorna los headers para las peticiones"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Añadir firma si tenemos secret_key
        if self.secret_key:
            signed_headers = self._sign_request(method, path, params, body)
            headers.update(signed_headers)
        else:
            # Fallback: usar access_key directamente
            headers['Authorization'] = f'Bearer {self.access_key}'
        
        return headers
    
    def generate_video(
        self,
        model_name: str,
        prompt: str = None,
        image_url: str = None,
        mode: str = 'std',
        duration: int = 5,
        aspect_ratio: str = "16:9",
        **kwargs
    ) -> dict:
        """
        Genera un video con Kling
        
        Args:
            model_name: Nombre del modelo (ej: 'kling-v1')
            prompt: Descripción del video (requerido para text-to-video)
            image_url: URL de la imagen de entrada (requerido para image-to-video)
            mode: Modo 'std' o 'pro' (solo para modelos que lo soportan)
            duration: Duración en segundos (5 o 10)
            aspect_ratio: Relación de aspecto ("16:9", "9:16", "1:1")
            **kwargs: Parámetros adicionales específicos del modelo
        
        Returns:
            dict con task_id y estado
        
        Raises:
            ValueError: Si los parámetros no son válidos
            Exception: Si falla la generación
        """
        # Validar modelo
        if model_name not in KLING_MODELS:
            raise ValueError(f"Modelo no soportado: {model_name}. Opciones: {list(KLING_MODELS.keys())}")
        
        model_info = KLING_MODELS[model_name]
        
        # Validar duración
        if duration not in model_info['durations']:
            raise ValueError(f"Duración {duration}s no válida. Opciones: {model_info['durations']}")
        
        # Validar modo si el modelo lo requiere
        if model_info['modes'] and mode not in model_info['modes']:
            raise ValueError(f"Modo '{mode}' no válido. Opciones: {model_info['modes']}")
        
        # Validar que haya prompt o image_url según el tipo
        if not prompt and not image_url:
            raise ValueError("Se requiere 'prompt' para text-to-video o 'image_url' para image-to-video")
        
        if model_info['supports_text_to_video'] and not prompt:
            raise ValueError(f"El modelo {model_name} requiere 'prompt' para text-to-video")
        
        if model_info['supports_image_to_video'] and image_url and not prompt:
            # Para image-to-video, el prompt describe el movimiento
            raise ValueError("Se requiere 'prompt' para describir el movimiento deseado")
        
        logger.info(f"🎬 Generando video con Kling")
        logger.info(f"   Modelo: {model_name} - {model_info['name']}")
        logger.info(f"   Modo: {mode if model_info['modes'] else 'N/A'}")
        logger.info(f"   Prompt: {prompt[:100] if prompt else 'N/A'}...")
        logger.info(f"   Duración: {duration}s, Aspect Ratio: {aspect_ratio}")
        
        try:
            # Nota: El endpoint puede variar según la documentación real
            endpoint = f"{self.base_url}/v1/video/generate"
            path = "/v1/video/generate"
            
            payload = {
                "model_name": model_name,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }
            
            # Añadir modo si el modelo lo soporta
            if model_info['modes']:
                payload["mode"] = mode
            
            # Añadir prompt
            if prompt:
                payload["prompt"] = prompt
            
            # Añadir image_url para image-to-video
            if image_url:
                payload["image_url"] = image_url
            
            # Añadir parámetros adicionales
            payload.update(kwargs)
            
            logger.info(f"📤 Enviando request a: {endpoint}")
            
            headers = self._get_headers('POST', path, body=payload)
            
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            logger.info(f"📥 Response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                task_id = data.get('task_id') or data.get('id') or data.get('request_id')
                
                logger.info(f"✅ Video creado exitosamente!")
                logger.info(f"   Task ID: {task_id}")
                logger.info(f"   Status: {data.get('status', 'queued')}")
                
                return {
                    'task_id': task_id,
                    'status': data.get('status', 'queued'),
                    'model_name': model_name,
                    'mode': mode,
                    'duration': duration,
                    'prompt': prompt,
                    'raw_response': data
                }
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error al crear video: {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Kling API: {str(e)}")
            raise Exception(f"Error de conexión: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}")
            raise
    
    def get_video_status(self, task_id: str) -> dict:
        """
        Obtiene el estado de una generación de video
        
        Args:
            task_id: ID de la tarea
        
        Returns:
            dict con el estado y datos del video si está completo
        """
        try:
            logger.info(f"Consultando estado de task: {task_id}")
            
            # Nota: El endpoint puede variar según la documentación real
            endpoint = f"{self.base_url}/v1/video/status/{task_id}"
            path = f"/v1/video/status/{task_id}"
            
            headers = self._get_headers('GET', path)
            
            response = self.session.get(
                endpoint,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                logger.info(f"📊 Status: {status}")
                
                result = {
                    'task_id': task_id,
                    'status': status,
                    'raw_response': data
                }
                
                if status == 'completed' or status == 'success':
                    logger.info(f"✅ Video completado!")
                    
                    # Extraer URL del video
                    video_url = data.get('video_url') or data.get('url') or data.get('result', {}).get('video_url')
                    result['video_url'] = video_url
                    
                elif status == 'failed' or status == 'error':
                    logger.error(f"❌ Video falló")
                    result['error'] = data.get('error') or data.get('message', 'Unknown error')
                
                return result
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error consultando estado: {error_msg}")
                return {
                    'task_id': task_id,
                    'status': 'error',
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Error al consultar estado: {str(e)}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }
    
    def wait_for_completion(
        self,
        task_id: str,
        max_wait_seconds: int = 600,
        poll_interval: int = 10
    ) -> dict:
        """
        Espera a que un video se complete con polling
        
        Args:
            task_id: ID de la tarea
            max_wait_seconds: Máximo tiempo de espera (default: 10 min)
            poll_interval: Intervalo entre consultas en segundos (default: 10s)
        
        Returns:
            dict con el estado final del video
        """
        logger.info(f"⏳ Esperando a que el task {task_id} se complete...")
        logger.info(f"   Tiempo máximo: {max_wait_seconds}s, Intervalo: {poll_interval}s")
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                logger.error(f"❌ Timeout esperando video después de {elapsed:.1f}s")
                return {
                    'task_id': task_id,
                    'status': 'timeout',
                    'error': f'Timeout after {elapsed:.1f}s'
                }
            
            status_data = self.get_video_status(task_id)
            status = status_data.get('status')
            
            if status in ['completed', 'success']:
                logger.info(f"✅ Video completado en {elapsed:.1f}s!")
                return status_data
            elif status in ['failed', 'error']:
                logger.error(f"❌ Video falló después de {elapsed:.1f}s")
                return status_data
            elif status in ['queued', 'processing', 'in_progress']:
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
                error_obj = error_data['error']
                if isinstance(error_obj, dict):
                    return error_obj.get('message', str(error_obj))
                return str(error_obj)
            if 'message' in error_data:
                return str(error_data['message'])
            return error_data.get('detail', response.text)
        except:
            return f"HTTP {response.status_code}: {response.text[:200]}"

