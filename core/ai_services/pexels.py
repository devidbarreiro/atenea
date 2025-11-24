"""
Cliente para Pexels Stock Content API
https://www.pexels.com/api/
"""
import requests
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PexelsOrientation(Enum):
    """Orientaciones de búsqueda"""
    LANDSCAPE = 'landscape'
    PORTRAIT = 'portrait'
    SQUARE = 'square'


class PexelsSize(Enum):
    """Tamaños de imagen"""
    LARGE = 'large'
    MEDIUM = 'medium'
    SMALL = 'small'
    ORIGINAL = 'original'


class PexelsColor(Enum):
    """Colores para filtrar"""
    RED = 'red'
    ORANGE = 'orange'
    YELLOW = 'yellow'
    GREEN = 'green'
    TURQUOISE = 'turquoise'
    BLUE = 'blue'
    VIOLET = 'violet'
    PINK = 'pink'
    BROWN = 'brown'
    BLACK = 'black'
    GRAY = 'gray'
    WHITE = 'white'


class PexelsClient:
    """Cliente para interactuar con Pexels API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Pexels
        
        Args:
            api_key: API key de Pexels
        """
        self.api_key = api_key
        self.base_url = 'https://api.pexels.com/v1'
        self.session = requests.Session()
        logger.info("PexelsClient inicializado")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna los headers para las peticiones"""
        return {
            'Authorization': self.api_key,
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API de Pexels
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API (sin base_url)
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Respuesta JSON de la API
            
        Raises:
            requests.exceptions.RequestException: Si falla la petición
        """
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update(self._get_headers())
        
        logger.info(f"Pexels API Request: {method} {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )
            
            logger.info(f"Pexels API Response Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            if 'photos' in result:
                logger.info(f"Pexels API: Encontradas {len(result['photos'])} fotos")
            elif 'videos' in result:
                logger.info(f"Pexels API: Encontrados {len(result['videos'])} videos")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error en Pexels API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Pexels API: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Error al parsear respuesta JSON de Pexels: {str(e)}")
            raise
    
    def search_photos(
        self,
        query: str,
        orientation: Optional[PexelsOrientation] = None,
        size: Optional[PexelsSize] = None,
        color: Optional[PexelsColor] = None,
        locale: str = 'es-ES',
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Busca fotos en Pexels
        
        Args:
            query: Término de búsqueda
            orientation: Orientación deseada
            size: Tamaño mínimo de imagen
            color: Color dominante
            locale: Idioma de la búsqueda
            page: Número de página
            per_page: Resultados por página (max 80)
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'query': query,
            'page': page,
            'per_page': min(per_page, 80),
            'locale': locale
        }
        
        if orientation:
            params['orientation'] = orientation.value
        if size:
            params['size'] = size.value
        if color:
            params['color'] = color.value
        
        logger.info(f"Buscando fotos en Pexels con parámetros: {params}")
        return self._make_request('GET', '/search', params=params)
    
    def search_videos(
        self,
        query: str,
        orientation: Optional[PexelsOrientation] = None,
        size: Optional[PexelsSize] = None,
        locale: str = 'es-ES',
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Busca videos en Pexels
        
        Args:
            query: Término de búsqueda
            orientation: Orientación deseada
            size: Tamaño mínimo de video
            locale: Idioma de la búsqueda
            page: Número de página
            per_page: Resultados por página (max 80)
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'query': query,
            'page': page,
            'per_page': min(per_page, 80),
            'locale': locale
        }
        
        if orientation:
            params['orientation'] = orientation.value
        if size:
            params['size'] = size.value
        
        logger.info(f"Buscando videos en Pexels con parámetros: {params}")
        return self._make_request('GET', '/videos/search', params=params)
    
    def parse_photos(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de fotos
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de fotos simplificadas
        """
        if 'photos' not in results:
            logger.warning("No se encontró 'photos' en resultados de Pexels")
            return []
        
        parsed = []
        for photo in results['photos']:
            parsed_item = {
                'id': str(photo.get('id', '')),
                'title': photo.get('alt', 'Sin título'),
                'type': 'photo',
                'source': 'pexels',
                'thumbnail': photo.get('src', {}).get('medium', ''),
                'preview': photo.get('src', {}).get('large', ''),
                'download_url': photo.get('src', {}).get('original', ''),
                'width': photo.get('width', 0),
                'height': photo.get('height', 0),
                'orientation': self._determine_orientation(
                    photo.get('width', 0),
                    photo.get('height', 0)
                ),
                'photographer': photo.get('photographer', ''),
                'photographer_url': photo.get('photographer_url', ''),
                'url': photo.get('url', ''),
                'is_premium': False  # Pexels es siempre gratuito
            }
            
            if parsed_item['thumbnail'] or parsed_item['preview']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de Pexels")
        return parsed
    
    def parse_videos(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de videos
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de videos simplificados
        """
        if 'videos' not in results:
            logger.warning("No se encontró 'videos' en resultados de Pexels")
            return []
        
        parsed = []
        for video in results['videos']:
            # Obtener la mejor calidad disponible
            video_files = video.get('video_files', [])
            best_quality = max(
                video_files,
                key=lambda x: x.get('width', 0) * x.get('height', 0),
                default={}
            )
            
            parsed_item = {
                'id': str(video.get('id', '')),
                'title': video.get('alt', 'Sin título'),
                'type': 'video',
                'source': 'pexels',
                'thumbnail': video.get('image', ''),
                'preview': best_quality.get('link', ''),
                'download_url': best_quality.get('link', ''),
                'width': best_quality.get('width', 0),
                'height': best_quality.get('height', 0),
                'duration': video.get('duration', 0),
                'orientation': self._determine_orientation(
                    best_quality.get('width', 0),
                    best_quality.get('height', 0)
                ),
                'photographer': video.get('user', {}).get('name', ''),
                'photographer_url': video.get('user', {}).get('url', ''),
                'url': video.get('url', ''),
                'is_premium': False  # Pexels es siempre gratuito
            }
            
            if parsed_item['thumbnail'] or parsed_item['preview']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de videos de Pexels")
        return parsed
    
    @staticmethod
    def _determine_orientation(width: int, height: int) -> str:
        """Determina la orientación basada en dimensiones"""
        if width == 0 or height == 0:
            return 'unknown'
        ratio = width / height
        if ratio > 1.2:
            return 'horizontal'
        elif ratio < 0.8:
            return 'vertical'
        else:
            return 'square'

