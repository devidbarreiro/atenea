"""
Cliente para Unsplash Stock Content API
https://unsplash.com/developers
"""
import requests
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class UnsplashOrientation(Enum):
    """Orientaciones de búsqueda"""
    LANDSCAPE = 'landscape'
    PORTRAIT = 'portrait'
    SQUARISH = 'squarish'


class UnsplashOrderBy(Enum):
    """Orden de resultados"""
    LATEST = 'latest'
    OLDEST = 'oldest'
    POPULAR = 'popular'
    RELEVANT = 'relevant'


class UnsplashClient:
    """Cliente para interactuar con Unsplash API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Unsplash
        
        Args:
            api_key: API key de Unsplash (Access Key)
        """
        self.api_key = api_key
        self.base_url = 'https://api.unsplash.com'
        self.session = requests.Session()
        logger.info("UnsplashClient inicializado")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna los headers para las peticiones"""
        return {
            'Authorization': f'Client-ID {self.api_key}',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API de Unsplash
        
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
        
        logger.info(f"Unsplash API Request: {method} {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )
            
            logger.info(f"Unsplash API Response Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, list):
                logger.info(f"Unsplash API: Encontrados {len(result)} resultados")
            elif 'results' in result:
                logger.info(f"Unsplash API: Encontrados {len(result['results'])} resultados")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error en Unsplash API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Unsplash API: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Error al parsear respuesta JSON de Unsplash: {str(e)}")
            raise
    
    def search_photos(
        self,
        query: str,
        orientation: Optional[UnsplashOrientation] = None,
        order_by: Optional[UnsplashOrderBy] = None,
        page: int = 1,
        per_page: int = 20,
        color: Optional[str] = None
    ) -> Dict:
        """
        Busca fotos en Unsplash
        
        Args:
            query: Término de búsqueda
            orientation: Orientación deseada
            order_by: Orden de resultados
            page: Número de página
            per_page: Resultados por página (max 30)
            color: Filtrar por color (black_and_white, black, white, yellow, orange, red, purple, magenta, green, teal, blue)
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'query': query,
            'page': page,
            'per_page': min(per_page, 30)
        }
        
        if orientation:
            params['orientation'] = orientation.value
        if order_by:
            params['order_by'] = order_by.value
        if color:
            params['color'] = color
        
        logger.info(f"Buscando fotos en Unsplash con parámetros: {params}")
        return self._make_request('GET', '/search/photos', params=params)
    
    def parse_photos(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de fotos
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de fotos simplificadas
        """
        if 'results' not in results:
            logger.warning("No se encontró 'results' en resultados de Unsplash")
            return []
        
        parsed = []
        for photo in results['results']:
            urls = photo.get('urls', {})
            parsed_item = {
                'id': str(photo.get('id', '')),
                'title': photo.get('description') or photo.get('alt_description', 'Sin título'),
                'type': 'photo',
                'source': 'unsplash',
                'thumbnail': urls.get('thumb', ''),
                'preview': urls.get('regular', ''),
                'download_url': urls.get('full', ''),
                'width': photo.get('width', 0),
                'height': photo.get('height', 0),
                'orientation': photo.get('orientation', 'unknown'),
                'photographer': photo.get('user', {}).get('name', ''),
                'photographer_url': photo.get('user', {}).get('links', {}).get('html', ''),
                'url': photo.get('links', {}).get('html', ''),
                'is_premium': False  # Unsplash es siempre gratuito
            }
            
            if parsed_item['thumbnail'] or parsed_item['preview']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de Unsplash")
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

