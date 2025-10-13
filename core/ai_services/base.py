"""
Clase base para clientes de APIs de IA
"""
import requests
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """Clase base abstracta para clientes de APIs de IA"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_headers(self) -> dict:
        """Retorna los headers por defecto para las peticiones"""
        return {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key
        }
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Realiza una petición HTTP"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update(self.get_headers())
        
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
            logger.error(f"Error en petición a {url}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Respuesta: {e.response.text}")
            raise
    
    @abstractmethod
    def generate_video(self, **kwargs) -> dict:
        """Método abstracto para generar video"""
        pass
    
    @abstractmethod
    def get_video_status(self, video_id: str) -> dict:
        """Método abstracto para obtener el estado de un video"""
        pass

