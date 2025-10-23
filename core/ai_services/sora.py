"""Cliente para OpenAI Sora API"""
import logging
import time
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


# Modelos disponibles de Sora
SORA_MODELS = {
    'sora-2': {
        'name': 'Sora 2',
        'description': 'Velocidad y flexibilidad para exploración y redes sociales',
        'use_case': 'Prototipos, contenido social, iteración rápida',
        'quality': 'estándar',
        'speed': 'rápido'
    },
    'sora-2-pro': {
        'name': 'Sora 2 Pro',
        'description': 'Alta calidad para producción profesional',
        'use_case': 'Marketing, cine, precisión visual crítica',
        'quality': 'alta',
        'speed': 'lento'
    }
}

# Duraciones permitidas
SORA_DURATIONS = [4, 8, 12]  # Duraciones en segundos

# Tamaños soportados
SORA_SIZES = [
    '720x1280',   # Vertical (9:16)
    '1280x720',   # Horizontal (16:9)
    '1024x1024'   # Cuadrado (1:1)
]


class SoraClient:
    """Cliente para OpenAI Sora API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Sora
        
        Args:
            api_key: API Key de OpenAI
        """
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.session = requests.Session()
        
        logger.info("Cliente Sora inicializado")
    
    def _get_headers(self) -> dict:
        """Retorna los headers para las peticiones"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def generate_video(
        self,
        prompt: str,
        model: str = "sora-2",
        seconds: int = 8,
        size: str = "1280x720"
    ) -> dict:
        """
        Genera un video con Sora
        
        Args:
            prompt: Descripción del video a generar
            model: Modelo a usar ("sora-2" o "sora-2-pro")
            seconds: Duración en segundos (4, 8 o 12, default: 8)
                    Nota: Se convierte automáticamente a string para la API
            size: Resolución del video (default: "1280x720")
        
        Returns:
            dict con datos del video creado
        
        Raises:
            ValueError: Si los parámetros no son válidos
            Exception: Si falla la generación
        """
        # Validaciones
        if model not in SORA_MODELS:
            raise ValueError(f"Modelo no soportado: {model}. Opciones: {list(SORA_MODELS.keys())}")
        
        # Duraciones permitidas: 4, 8, 12 segundos
        if seconds not in SORA_DURATIONS:
            raise ValueError(f"Duración debe ser 4, 8 o 12 segundos. Valor recibido: {seconds}")
        
        if size not in SORA_SIZES:
            raise ValueError(f"Tamaño no soportado: {size}. Opciones: {SORA_SIZES}")
        
        logger.info(f"🎬 Generando video con Sora")
        logger.info(f"   Modelo: {model} - {SORA_MODELS[model]['name']}")
        logger.info(f"   Prompt: {prompt[:100]}...")
        logger.info(f"   Duración: {seconds}s, Tamaño: {size}")
        
        try:
            endpoint = f"{self.base_url}/videos"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "seconds": str(seconds),  # API espera string, no int
                "size": size
            }
            
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
                video_id = data.get('id')
                
                logger.info(f"✅ Video creado exitosamente!")
                logger.info(f"   Video ID: {video_id}")
                logger.info(f"   Status: {data.get('status', 'unknown')}")
                
                return {
                    'video_id': video_id,
                    'status': data.get('status', 'queued'),
                    'model': model,
                    'prompt': prompt,
                    'seconds': seconds,
                    'size': size,
                    'created_at': data.get('created_at'),
                    'raw_response': data
                }
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error al crear video: {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Sora API: {str(e)}")
            raise Exception(f"Error de conexión: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}")
            raise
    
    def generate_video_with_image(
        self,
        prompt: str,
        input_reference_path: str,
        model: str = "sora-2-pro",
        seconds: int = 8,
        size: str = "1280x720"
    ) -> dict:
        """
        Genera un video con imagen de referencia (multipart/form-data)
        
        Args:
            prompt: Descripción del video a generar
            input_reference_path: Ruta al archivo de imagen (JPEG, PNG, WEBP)
            model: Modelo a usar
            seconds: Duración en segundos (4, 8 o 12)
                    Nota: Se convierte automáticamente a string para la API
            size: Resolución del video
        
        Returns:
            dict con datos del video creado
            
        Note:
            ⚠️ IMPORTANTE: La imagen debe tener exactamente las mismas dimensiones
            que el tamaño del video especificado (size parameter).
            Ejemplo: Si size='1280x720', la imagen debe ser 1280x720 píxeles.
        """
        logger.info(f"🎬 Generando video con imagen de referencia")
        logger.info(f"   Imagen: {input_reference_path}")
        logger.info(f"   ⚠️  IMPORTANTE: La imagen debe ser exactamente {size} píxeles")
        
        try:
            endpoint = f"{self.base_url}/videos"
            
            # Headers sin Content-Type (requests lo añadirá automáticamente para multipart)
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # Preparar multipart form data
            with open(input_reference_path, 'rb') as img_file:
                files = {
                    'input_reference': img_file
                }
                
                data = {
                    'model': model,
                    'prompt': prompt,
                    'seconds': str(seconds),  # API espera string, no int
                    'size': size
                }
                
                logger.info(f"📤 Enviando request con imagen...")
                
                response = self.session.post(
                    endpoint,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=120
                )
            
            logger.info(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                video_id = data.get('id')
                
                logger.info(f"✅ Video con imagen creado exitosamente!")
                logger.info(f"   Video ID: {video_id}")
                
                return {
                    'video_id': video_id,
                    'status': data.get('status', 'queued'),
                    'model': model,
                    'prompt': prompt,
                    'seconds': seconds,
                    'size': size,
                    'created_at': data.get('created_at'),
                    'has_input_reference': True,
                    'raw_response': data
                }
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error al crear video con imagen: {error_msg}")
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"❌ Error al generar video con imagen: {str(e)}")
            raise
    
    def get_video_status(self, video_id: str) -> dict:
        """
        Obtiene el estado de un video
        
        Args:
            video_id: ID del video
        
        Returns:
            dict con el estado y datos del video
        """
        try:
            logger.info(f"Consultando estado del video: {video_id}")
            
            endpoint = f"{self.base_url}/videos/{video_id}"
            
            response = self.session.get(
                endpoint,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Accept': 'application/json'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                logger.info(f"📊 Status: {status}")
                
                result = {
                    'video_id': video_id,
                    'status': status,
                    'progress': data.get('progress', 0),
                    'model': data.get('model'),
                    'seconds': data.get('seconds'),
                    'size': data.get('size'),
                    'created_at': data.get('created_at'),
                    'completed_at': data.get('completed_at'),
                    'expires_at': data.get('expires_at'),
                    'error': data.get('error'),
                    'raw_response': data
                }
                
                if status == 'completed':
                    logger.info(f"✅ Video completado!")
                    logger.info(f"   Expira en: {data.get('expires_at')}")
                elif status == 'failed':
                    logger.error(f"❌ Video falló: {data.get('error')}")
                
                return result
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error consultando estado: {error_msg}")
                return {
                    'video_id': video_id,
                    'status': 'error',
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Error al consultar estado: {str(e)}")
            return {
                'video_id': video_id,
                'status': 'error',
                'error': str(e)
            }
    
    def download_video(self, video_id: str, output_path: str) -> bool:
        """
        Descarga el contenido del video
        
        Args:
            video_id: ID del video
            output_path: Ruta donde guardar el video
        
        Returns:
            True si se descargó correctamente
        """
        try:
            logger.info(f"📥 Descargando video: {video_id}")
            logger.info(f"   Destino: {output_path}")
            
            endpoint = f"{self.base_url}/videos/{video_id}/content"
            
            response = self.session.get(
                endpoint,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Accept': 'application/octet-stream'
                },
                stream=True,
                timeout=300
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"✅ Video descargado exitosamente!")
                return True
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error descargando video: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al descargar video: {str(e)}")
            return False
    
    def download_thumbnail(self, video_id: str, output_path: str) -> bool:
        """
        Descarga el thumbnail del video
        
        Args:
            video_id: ID del video
            output_path: Ruta donde guardar el thumbnail
        
        Returns:
            True si se descargó correctamente
        """
        try:
            logger.info(f"📥 Descargando thumbnail: {video_id}")
            
            endpoint = f"{self.base_url}/videos/{video_id}/content?variant=thumbnail"
            
            response = self.session.get(
                endpoint,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Accept': 'application/octet-stream'
                },
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"✅ Thumbnail descargado exitosamente!")
                return True
            else:
                logger.warning(f"⚠️  No se pudo descargar thumbnail: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al descargar thumbnail: {str(e)}")
            return False
    
    def wait_for_completion(
        self,
        video_id: str,
        max_wait_seconds: int = 600,
        poll_interval: int = 10
    ) -> dict:
        """
        Espera a que un video se complete con polling
        
        Args:
            video_id: ID del video
            max_wait_seconds: Máximo tiempo de espera (default: 10 min)
            poll_interval: Intervalo entre consultas en segundos (default: 10s)
        
        Returns:
            dict con el estado final del video
        """
        logger.info(f"⏳ Esperando a que el video {video_id} se complete...")
        logger.info(f"   Tiempo máximo: {max_wait_seconds}s, Intervalo: {poll_interval}s")
        
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                logger.error(f"❌ Timeout esperando video después de {elapsed:.1f}s")
                return {
                    'video_id': video_id,
                    'status': 'timeout',
                    'error': f'Timeout after {elapsed:.1f}s'
                }
            
            status_data = self.get_video_status(video_id)
            status = status_data.get('status')
            progress = status_data.get('progress', 0)
            
            if status == 'completed':
                logger.info(f"✅ Video completado en {elapsed:.1f}s!")
                return status_data
            elif status == 'failed':
                logger.error(f"❌ Video falló después de {elapsed:.1f}s")
                return status_data
            elif status in ['queued', 'in_progress']:
                logger.info(f"⏳ Progreso: {progress}% ({elapsed:.1f}s transcurridos)")
                time.sleep(poll_interval)
            else:
                logger.warning(f"⚠️  Estado desconocido: {status}")
                time.sleep(poll_interval)
    
    def _parse_error(self, response: requests.Response) -> str:
        """Parsea el mensaje de error de la API"""
        try:
            error_data = response.json()
            
            # OpenAI usa estructura: { "error": { "message": "...", "type": "...", "code": "..." } }
            if 'error' in error_data:
                error_obj = error_data['error']
                if isinstance(error_obj, dict):
                    code = error_obj.get('code') or error_obj.get('type', 'unknown_error')
                    message = error_obj.get('message', 'Unknown error')
                    return f"[{code}] {message}"
                else:
                    return str(error_obj)
            
            return error_data.get('message', response.text)
        except:
            return f"HTTP {response.status_code}: {response.text[:200]}"
    
    def list_videos(self, limit: int = 20, after: Optional[str] = None, order: str = "desc") -> dict:
        """
        Lista videos creados
        
        Args:
            limit: Número máximo de videos a retornar (default: 20)
            after: ID del video para paginación
            order: Orden ("asc" o "desc", default: "desc")
        
        Returns:
            dict con lista de videos
        """
        try:
            endpoint = f"{self.base_url}/videos"
            params = {
                'limit': limit,
                'order': order
            }
            
            if after:
                params['after'] = after
            
            response = self.session.get(
                endpoint,
                params=params,
                headers={
                    'Authorization': f'Bearer {self.api_key}'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error listando videos: {response.status_code}")
                return {'data': []}
                
        except Exception as e:
            logger.error(f"Error al listar videos: {str(e)}")
            return {'data': []}
    
    def delete_video(self, video_id: str) -> bool:
        """
        Elimina un video
        
        Args:
            video_id: ID del video a eliminar
        
        Returns:
            True si se eliminó correctamente
        """
        try:
            endpoint = f"{self.base_url}/videos/{video_id}"
            
            response = self.session.delete(
                endpoint,
                headers={
                    'Authorization': f'Bearer {self.api_key}'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Video {video_id} eliminado")
                return True
            else:
                logger.error(f"Error eliminando video: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error al eliminar video: {str(e)}")
            return False

