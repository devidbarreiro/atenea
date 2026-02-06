"""
Cliente para Pixabay Stock Content API
https://pixabay.com/api/docs/
"""
import requests
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PixabayImageType(Enum):
    """Tipos de imagen"""
    ALL = 'all'
    PHOTO = 'photo'
    ILLUSTRATION = 'illustration'
    VECTOR = 'vector'


class PixabayCategory(Enum):
    """Categorías de búsqueda"""
    BACKGROUNDS = 'backgrounds'
    FASHION = 'fashion'
    NATURE = 'nature'
    SCIENCE = 'science'
    EDUCATION = 'education'
    FEELINGS = 'feelings'
    HEALTH = 'health'
    PEOPLE = 'people'
    RELIGION = 'religion'
    PLACES = 'places'
    ANIMALS = 'animals'
    INDUSTRY = 'industry'
    COMPUTER = 'computer'
    FOOD = 'food'
    SPORTS = 'sports'
    TRANSPORTATION = 'transportation'
    TRAVEL = 'travel'
    BUILDINGS = 'buildings'
    BUSINESS = 'business'
    MUSIC = 'music'


class PixabayOrientation(Enum):
    """Orientaciones de búsqueda"""
    ALL = 'all'
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'


class PixabayOrder(Enum):
    """Orden de resultados"""
    POPULAR = 'popular'
    LATEST = 'latest'


class PixabayClient:
    """Cliente para interactuar con Pixabay API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Pixabay
        
        Args:
            api_key: API key de Pixabay
        """
        self.api_key = api_key
        self.base_url = 'https://pixabay.com/api'
        self.session = requests.Session()
        logger.info("PixabayClient inicializado")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API de Pixabay
        
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
        
        # Pixabay usa query params para la API key
        params = kwargs.pop('params', {})
        params['key'] = self.api_key
        
        logger.info(f"Pixabay API Request: {method} {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=30,
                **kwargs
            )
            
            logger.info(f"Pixabay API Response Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            if 'hits' in result:
                logger.info(f"Pixabay API: Encontrados {len(result['hits'])} resultados")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error en Pixabay API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Pixabay API: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Error al parsear respuesta JSON de Pixabay: {str(e)}")
            raise
    
    def search_images(
        self,
        query: str,
        image_type: Optional[PixabayImageType] = None,
        category: Optional[PixabayCategory] = None,
        orientation: Optional[PixabayOrientation] = None,
        order: Optional[PixabayOrder] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        colors: Optional[str] = None,
        safesearch: bool = True,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Busca imágenes en Pixabay
        
        Args:
            query: Término de búsqueda
            image_type: Tipo de imagen
            category: Categoría
            orientation: Orientación deseada
            order: Orden de resultados
            min_width: Ancho mínimo
            min_height: Alto mínimo
            colors: Colores (grayscale, transparent, red, orange, yellow, green, turquoise, blue, lilac, pink, white, gray, black, brown)
            safesearch: Filtrar contenido inapropiado
            page: Número de página
            per_page: Resultados por página (max 200)
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'q': query,
            'page': page,
            'per_page': min(per_page, 200),
            'safesearch': 'true' if safesearch else 'false'
        }
        
        if image_type:
            params['image_type'] = image_type.value
        if category:
            params['category'] = category.value
        if orientation:
            params['orientation'] = orientation.value
        if order:
            params['order'] = order.value
        if min_width:
            params['min_width'] = min_width
        if min_height:
            params['min_height'] = min_height
        if colors:
            params['colors'] = colors
        
        logger.info(f"Buscando imágenes en Pixabay con parámetros: {params}")
        return self._make_request('GET', '/', params=params)
    
    def search_audio(
        self,
        query: str,
        audio_type: str = 'all',  # 'all', 'music', 'sound_effects'
        category: Optional[PixabayCategory] = None,
        safesearch: bool = True,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Busca audios en Pixabay
        
        Args:
            query: Término de búsqueda
            audio_type: Tipo de audio ('all', 'music', 'sound_effects')
            category: Categoría
            safesearch: Filtrar contenido inapropiado
            page: Número de página
            per_page: Resultados por página (max 200)
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'q': query,
            'audio_type': audio_type,
            'page': page,
            'per_page': min(per_page, 200),
            'safesearch': 'true' if safesearch else 'false'
        }
        
        if category:
            params['category'] = category.value
        
        logger.info(f"Buscando audios en Pixabay con parámetros: {params}")
        return self._make_request('GET', '/audio/', params=params)
    
    def search_videos(
        self,
        query: str,
        video_type: str = 'all',  # 'all', 'film', 'animation'
        category: Optional[PixabayCategory] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        safesearch: bool = True,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """
        Busca videos en Pixabay
        
        Args:
            query: Término de búsqueda
            video_type: Tipo de video ('all', 'film', 'animation')
            category: Categoría
            min_width: Ancho mínimo
            min_height: Alto mínimo
            safesearch: Filtrar contenido inapropiado
            page: Número de página
            per_page: Resultados por página (max 200)
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'q': query,
            'video_type': video_type,
            'page': page,
            'per_page': min(per_page, 200),
            'safesearch': 'true' if safesearch else 'false'
        }
        
        if category:
            params['category'] = category.value
        if min_width:
            params['min_width'] = min_width
        if min_height:
            params['min_height'] = min_height
        
        logger.info(f"Buscando videos en Pixabay con parámetros: {params}")
        response = self._make_request('GET', '/videos/', params=params)
        logger.debug(f"Pixabay Video Response Keys: {list(response.keys())}")
        if 'hits' in response:
             logger.debug(f"Pixabay Video Hits: {len(response['hits'])}")
             if len(response['hits']) > 0:
                 logger.debug(f"First Hit Sample: {response['hits'][0]}")
        return response
    
    def parse_images(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de imágenes
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de imágenes simplificadas
        """
        if 'hits' not in results:
            logger.warning("No se encontró 'hits' en resultados de Pixabay")
            return []
        
        parsed = []
        for image in results['hits']:
            # Validar user_id antes de construir URL
            user = image.get('user', '')
            user_id = image.get('user_id')
            photographer_url = ''
            if user and user_id:
                photographer_url = f"https://pixabay.com/users/{user}-{user_id}/"
            
            parsed_item = {
                'id': str(image.get('id', '')),
                'title': image.get('tags', 'Sin título'),
                'type': 'photo',
                'source': 'pixabay',
                'thumbnail': image.get('previewURL', ''),
                'preview': image.get('webformatURL', ''),
                'download_url': image.get('largeImageURL', ''),
                'width': image.get('imageWidth', 0),
                'height': image.get('imageHeight', 0),
                'orientation': self._determine_orientation(
                    image.get('imageWidth', 0),
                    image.get('imageHeight', 0)
                ),
                'photographer': user,
                'photographer_url': photographer_url,
                'url': image.get('pageURL', ''),
                'is_premium': False  # Pixabay es siempre gratuito
            }
            
            if parsed_item['thumbnail'] or parsed_item['preview']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de Pixabay")
        return parsed
    
    def parse_videos(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de videos
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de videos simplificados
        """
        if 'hits' not in results:
            logger.warning("No se encontró 'hits' en resultados de videos de Pixabay")
            return []
        
        parsed = []
        for video in results['hits']:
            # Obtener la mejor calidad disponible
            videos = video.get('videos', {}) or {}
            best_quality = videos.get('large') or videos.get('medium') or videos.get('small') or {}
            
            # Validar user_id antes de construir URL
            user = video.get('user', '')
            user_id = video.get('user_id')
            photographer_url = ''
            if user and user_id:
                photographer_url = f"https://pixabay.com/users/{user}-{user_id}/"
            
            # Construir URL de thumbnail desde picture_id
            # Pixabay usa Vimeo CDN para thumbnails de videos
            thumbnail_url = ''
            picture_id = video.get('picture_id')
            if picture_id:
                # Construir URL de thumbnail usando el formato de Pixabay/Vimeo CDN
                thumbnail_url = f"https://i.vimeocdn.com/video/{picture_id}_640x360.jpg"
            
            parsed_item = {
                'id': str(video.get('id', '')),
                'title': video.get('tags', 'Sin título'),
                'type': 'video',
                'source': 'pixabay',
                'thumbnail': thumbnail_url,
                'preview': best_quality.get('url', '') if best_quality else '',
                'download_url': best_quality.get('url', '') if best_quality else '',
                'width': best_quality.get('width', 0) if best_quality else 0,
                'height': best_quality.get('height', 0) if best_quality else 0,
                'duration': video.get('duration', 0),
                'orientation': self._determine_orientation(
                    best_quality.get('width', 0) if best_quality else 0,
                    best_quality.get('height', 0) if best_quality else 0
                ),
                'photographer': user,
                'photographer_url': photographer_url,
                'url': video.get('pageURL', ''),
                'is_premium': False  # Pixabay es siempre gratuito
            }
            
            # Solo agregar si tiene URL de descarga o preview válida
            if parsed_item['preview'] or parsed_item['download_url']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de videos de Pixabay")
        return parsed
    
    def parse_audio(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de audios
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de audios simplificados
        """
        if 'hits' not in results:
            logger.warning("No se encontró 'hits' en resultados de audio de Pixabay")
            return []
        
        parsed = []
        for audio in results['hits']:
            # Validar user_id antes de construir URL
            user = audio.get('user', '')
            user_id = audio.get('user_id')
            author_url = ''
            if user and user_id:
                author_url = f"https://pixabay.com/users/{user}-{user_id}/"
            
            parsed_item = {
                'id': str(audio.get('id', '')),
                'title': audio.get('title', 'Sin título'),
                'description': audio.get('tags', ''),
                'type': 'audio',
                'source': 'pixabay',
                'thumbnail': '',  # Pixabay audio puede no tener thumbnail
                'preview': audio.get('url', ''),
                'download_url': audio.get('url', ''),  # Pixabay permite descarga directa
                'duration': audio.get('duration', 0),
                'bitrate': audio.get('bitrate', 0),
                'sample_rate': audio.get('sample_rate', 0),
                'author': user,
                'author_url': author_url,
                'url': audio.get('pageURL', ''),
                'is_premium': False  # Pixabay es siempre gratuito
            }
            
            if parsed_item['preview'] or parsed_item['download_url']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de audio de Pixabay")
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

