"""
Clase base para clientes de APIs de IA
"""
import requests
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """Clase base abstracta para clientes de APIs de IA"""
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_headers(self, method: str = 'GET') -> dict:
        """
        Retorna los headers por defecto para las peticiones
        
        Args:
            method: Método HTTP (GET, POST, etc) para determinar headers apropiados
        """
        headers = {
            'accept': 'application/json',
            'x-api-key': self.api_key
        }
        
        # Para POST/PUT/PATCH, también agregar Content-Type
        if method.upper() in ('POST', 'PUT', 'PATCH'):
            headers['Content-Type'] = 'application/json'
        
        return headers
    
    def make_request(
        self, 
        method: str, 
        endpoint: str, 
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> dict:
        """
        Realiza una petición HTTP con retry logic para errores temporales
        
        Args:
            method: Método HTTP (GET, POST, etc)
            endpoint: Endpoint de la API
            max_retries: Número máximo de reintentos para errores temporales (default: 3)
            retry_delay: Delay inicial entre reintentos en segundos (default: 1.0)
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            dict: Respuesta JSON de la API
            
        Raises:
            requests.exceptions.RequestException: Si la petición falla después de todos los reintentos
        """
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update(self.get_headers(method))
        
        # Establecer timeout si no se proporciona
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        # Códigos de error temporales que justifican retry
        RETRY_STATUS_CODES = {502, 503, 504, 429}  # Bad Gateway, Service Unavailable, Gateway Timeout, Too Many Requests
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                
                # Verificar si es un error temporal que justifica retry
                should_retry = False
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    if status_code in RETRY_STATUS_CODES:
                        should_retry = True
                        logger.warning(
                            f"Error temporal {status_code} en petición a {url}. "
                            f"Reintento {attempt + 1}/{max_retries} en {retry_delay}s..."
                        )
                    else:
                        # Error no temporal (4xx client error, etc), no reintentar
                        logger.error(f"Error en petición a {url}: {str(e)}")
                        if hasattr(e.response, 'text'):
                            logger.error(f"Respuesta: {e.response.text}")
                        raise
                else:
                    # Error de conexión/timeout, reintentar
                    should_retry = True
                    logger.warning(
                        f"Error de conexión a {url}: {str(e)}. "
                        f"Reintento {attempt + 1}/{max_retries} en {retry_delay}s..."
                    )
                
                # Si es el último intento, lanzar la excepción
                if attempt == max_retries - 1:
                    logger.error(f"Error en petición a {url} después de {max_retries} intentos: {str(e)}")
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        logger.error(f"Respuesta: {e.response.text}")
                    raise
                
                # Si debemos reintentar, esperar con exponential backoff
                if should_retry:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        
        # Esto no debería alcanzarse, pero por seguridad
        if last_exception:
            raise last_exception
    
    @abstractmethod
    def generate_video(self, **kwargs) -> dict:
        """Método abstracto para generar video"""
        pass
    
    @abstractmethod
    def get_video_status(self, video_id: str) -> dict:
        """Método abstracto para obtener el estado de un video"""
        pass

