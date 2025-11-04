"""
Cliente para Freepik Stock Content API
https://docs.freepik.com/introduction
"""
import requests
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class FreepikContentType(Enum):
    """Tipos de contenido disponibles en Freepik"""
    PHOTO = 'photo'
    VECTOR = 'vector'
    PSD = 'psd'
    ICON = 'icon'
    VIDEO = 'video'


class FreepikOrientation(Enum):
    """Orientaciones de búsqueda"""
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'
    SQUARE = 'square'


class FreepikClient:
    """Cliente para interactuar con Freepik Stock Content API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Freepik
        
        Args:
            api_key: API key de Freepik
        """
        self.api_key = api_key
        self.base_url = 'https://api.freepik.com/v1'
        self.session = requests.Session()
        logger.info("FreepikClient inicializado")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna los headers para las peticiones"""
        return {
            'x-freepik-api-key': self.api_key,
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API de Freepik
        
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
        
        # Log de parámetros
        params = kwargs.get('params', {})
        logger.info(f"Freepik API Request: {method} {url}")
        logger.info(f"Freepik API Params: {params}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )
            
            # Log de respuesta
            logger.info(f"Freepik API Response Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            # Log de cantidad de resultados
            if 'data' in result:
                logger.info(f"Freepik API: Encontrados {len(result['data'])} resultados")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error en Freepik API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Freepik API: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Error al parsear respuesta JSON de Freepik: {str(e)}")
            raise
    
    # ==================
    # BÚSQUEDA DE RECURSOS
    # ==================
    
    def search_resources(
        self,
        query: str,
        content_types: Optional[List[FreepikContentType]] = None,
        orientation: Optional[FreepikOrientation] = None,
        page: int = 1,
        limit: int = 20,
        order: str = 'latest',
        license_filter: str = 'all'
    ) -> Dict:
        """
        Busca recursos en Freepik (imágenes, videos, vectores, etc.)
        
        Args:
            query: Término de búsqueda
            content_types: Lista de tipos de contenido a buscar
            orientation: Orientación deseada
            page: Número de página
            limit: Límite de resultados por página (max 200)
            order: Orden de resultados ('latest', 'popular', 'random')
            
        Returns:
            Dict con resultados de búsqueda:
            {
                'data': [...],  # Lista de recursos
                'meta': {...},  # Metadata de paginación
            }
        """
        params = {
            'term': query,  # Usar 'term' según la documentación oficial de Freepik
            'page': page,
            'limit': min(limit, 200),
            'order': order
        }
        
        # Filtrar por tipo de contenido - debe ser array según la API
        if content_types:
            # La API requiere arrays para los filtros
            content_type_values = [ct.value for ct in content_types]
            for i, val in enumerate(content_type_values):
                params[f'filters[content_type][{i}]'] = val
        
        # Filtrar por orientación - debe ser array según la API
        if orientation:
            # Enviar como array con un solo elemento
            params['filters[orientation][0]'] = orientation.value
        
        # Filtrar por licencia si se especifica
        if license_filter == 'free':
            # Solo recursos gratuitos (freemium)
            params['filters[license][0]'] = 'freemium'
        elif license_filter == 'premium':
            # Solo recursos Premium - filtramos excluyendo freemium
            # Nota: Freepik API no tiene un filtro directo para "solo premium"
            # así que esto lo filtraremos post-procesamiento en parse_search_results
            pass
        # Si es 'all', no agregamos filtro de licencia
        
        logger.info(f"Buscando en Freepik con parámetros: {params} (license_filter={license_filter})")
        return self._make_request('GET', '/resources', params=params)
    
    def search_images(
        self,
        query: str,
        orientation: Optional[FreepikOrientation] = None,
        page: int = 1,
        limit: int = 20,
        license_filter: str = 'all'
    ) -> Dict:
        """
        Busca imágenes (fotos y vectores) en Freepik
        
        Args:
            query: Término de búsqueda
            orientation: Orientación deseada
            page: Número de página
            limit: Límite de resultados
            
        Returns:
            Dict con resultados de búsqueda
        """
        return self.search_resources(
            query=query,
            content_types=[FreepikContentType.PHOTO, FreepikContentType.VECTOR],
            orientation=orientation,
            page=page,
            limit=limit,
            license_filter=license_filter
        )
    
    def search_videos(
        self,
        query: str,
        orientation: Optional[FreepikOrientation] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """
        Busca videos en Freepik
        
        Args:
            query: Término de búsqueda
            orientation: Orientación deseada
            page: Número de página
            limit: Límite de resultados
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'term': query,  # Usar 'term' según la documentación oficial
            'page': page,
            'limit': min(limit, 200)
        }
        
        # Filtrar por orientación - debe ser array según la API
        if orientation:
            params['filters[orientation][0]'] = orientation.value
        
        logger.info(f"Buscando videos en Freepik con parámetros: {params}")
        return self._make_request('GET', '/videos', params=params)
    
    def search_icons(
        self,
        query: str,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """
        Busca iconos en Freepik
        
        Args:
            query: Término de búsqueda
            page: Número de página
            limit: Límite de resultados
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'term': query,  # Usar 'term' según la documentación oficial
            'page': page,
            'limit': min(limit, 200)
        }
        
        logger.info(f"Buscando iconos en Freepik con parámetros: {params}")
        return self._make_request('GET', '/icons', params=params)
    
    # ==================
    # DETALLES Y DESCARGA
    # ==================
    
    def get_resource_details(self, resource_id: str) -> Dict:
        """
        Obtiene detalles de un recurso específico
        
        Args:
            resource_id: ID del recurso en Freepik
            
        Returns:
            Dict con detalles del recurso
        """
        return self._make_request('GET', f'/resources/{resource_id}')
    
    def get_download_url(self, resource_id: str, image_size: str = 'large') -> Dict:
        """
        Obtiene URL de descarga para un recurso usando el endpoint oficial de download
        
        Args:
            resource_id: ID del recurso
            image_size: Tamaño de imagen ('small', 'medium', 'large', 'original')
            
        Returns:
            Dict con información de descarga incluyendo URL firmada
            
        Note:
            Esta es la forma oficial de descargar recursos de Freepik
        """
        params = {}
        if image_size:
            params['image_size'] = image_size
        
        logger.info(f"Obteniendo URL de descarga para recurso {resource_id} (size={image_size})")
        return self._make_request('GET', f'/resources/{resource_id}/download', params=params)
    
    # ==================
    # UTILIDADES
    # ==================
    
    def parse_search_results(self, results: Dict, license_filter: str = 'all') -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de recursos simplificados:
            [
                {
                    'id': str,
                    'title': str,
                    'thumbnail': str (URL),
                    'preview': str (URL),
                    'download_url': str (URL),
                    'type': str,
                    'orientation': str,
                    'width': int,
                    'height': int,
                }
            ]
        """
        if 'data' not in results:
            logger.warning("No se encontró 'data' en resultados de Freepik")
            return []
        
        parsed = []
        for item in results['data']:
            # Log del item raw para debugging
            item_id = item.get('id', 'unknown')
            
            # Extraer tipo de licencia para saber si es Premium
            # Según la API de Freepik, el campo 'premium' está directamente en el objeto
            is_premium = item.get('premium', False)  # False por defecto (gratis)
            
            # Log detallado para las primeras 3 imágenes
            if len(parsed) < 3:
                logger.info(f"  RAW Item {item_id}: premium={item.get('premium')}, licenses={item.get('licenses', [])}")
            
            logger.debug(f"  Item {item_id} - premium field: {is_premium} (type: {type(is_premium).__name__})")
            
            parsed_item = {
                'id': str(item.get('id', '')),
                'title': item.get('title', 'Sin título'),
                'type': item.get('type', ''),
                'thumbnail': '',
                'preview': '',
                'download_url': '',
                'orientation': '',
                'width': 0,
                'height': 0,
                'is_premium': is_premium
            }
            
            # Extraer thumbnail - puede estar en diferentes lugares
            if 'thumbnails' in item and item['thumbnails']:
                if isinstance(item['thumbnails'], list) and len(item['thumbnails']) > 0:
                    thumb = item['thumbnails'][0]
                    if isinstance(thumb, dict):
                        parsed_item['thumbnail'] = thumb.get('url', '')
                    elif isinstance(thumb, str):
                        parsed_item['thumbnail'] = thumb
            elif 'thumbnail' in item:
                thumb = item['thumbnail']
                if isinstance(thumb, dict):
                    parsed_item['thumbnail'] = thumb.get('url', '')
                elif isinstance(thumb, str):
                    parsed_item['thumbnail'] = thumb
            
            # Extraer preview/imagen principal según la estructura de la API
            # La estructura es: image.source.url
            if 'image' in item:
                img_data = item['image']
                if isinstance(img_data, dict):
                    # La URL está en image.source.url según la documentación
                    if 'source' in img_data and isinstance(img_data['source'], dict):
                        parsed_item['preview'] = img_data['source'].get('url', '')
                        # Intentar obtener dimensiones de size (ej: "128x128")
                        size_str = img_data['source'].get('size', '')
                        if 'x' in size_str:
                            try:
                                w, h = size_str.split('x')
                                parsed_item['width'] = int(w)
                                parsed_item['height'] = int(h)
                            except:
                                pass
                    # Fallback: intentar otras ubicaciones
                    if not parsed_item['preview']:
                        parsed_item['preview'] = (
                            img_data.get('url') or 
                            img_data.get('source') or 
                            ''
                        )
                    
                    # Obtener orientación si está disponible
                    if 'orientation' in img_data:
                        parsed_item['orientation'] = img_data['orientation']
                    
                elif isinstance(img_data, str):
                    parsed_item['preview'] = img_data
            
            # Alternativa: 'images' (array)
            if not parsed_item['preview'] and 'images' in item:
                images_data = item['images']
                if isinstance(images_data, list) and len(images_data) > 0:
                    img = images_data[0]
                    if isinstance(img, dict):
                        parsed_item['preview'] = (
                            img.get('url') or 
                            img.get('source') or 
                            img.get('preview') or 
                            ''
                        )
                    elif isinstance(img, str):
                        parsed_item['preview'] = img
            
            # Si no hay preview, usar thumbnail
            if not parsed_item['preview'] and parsed_item['thumbnail']:
                parsed_item['preview'] = parsed_item['thumbnail']
            
            # URL de descarga - Freepik puede usar varios campos
            if 'download_url' in item:
                parsed_item['download_url'] = item['download_url']
            elif 'url' in item:
                parsed_item['download_url'] = item['url']
            elif 'source' in item:
                parsed_item['download_url'] = item['source']
            
            # Si no hay download_url, usar preview como fallback
            if not parsed_item['download_url']:
                parsed_item['download_url'] = parsed_item['preview']
                logger.debug(f"  Using preview as download_url fallback for item {parsed_item['id']}")
            
            # Determinar orientación
            if parsed_item['width'] and parsed_item['height']:
                ratio = parsed_item['width'] / parsed_item['height']
                if ratio > 1.2:
                    parsed_item['orientation'] = 'horizontal'
                elif ratio < 0.8:
                    parsed_item['orientation'] = 'vertical'
                else:
                    parsed_item['orientation'] = 'square'
            
            # Asegurar que todos sean strings válidos
            def safe_string(value):
                """Convierte un valor a string seguro o retorna string vacío"""
                if not value:
                    return ''
                if isinstance(value, str):
                    return value
                if isinstance(value, dict):
                    # Si es un dict, intentar extraer 'url'
                    return value.get('url', '')
                return str(value) if value else ''
            
            parsed_item['thumbnail'] = safe_string(parsed_item['thumbnail'])
            parsed_item['preview'] = safe_string(parsed_item['preview'])
            parsed_item['download_url'] = safe_string(parsed_item['download_url'])
            
            # Log URLs para debugging
            thumb_str = parsed_item['thumbnail'][:50] if parsed_item['thumbnail'] else 'None'
            preview_str = parsed_item['preview'][:50] if parsed_item['preview'] else 'None'
            download_str = parsed_item['download_url'][:50] if parsed_item['download_url'] else 'None'
            
            logger.debug(f"  Thumbnail: {thumb_str} (type: {type(parsed_item['thumbnail']).__name__})")
            logger.debug(f"  Preview: {preview_str} (type: {type(parsed_item['preview']).__name__})")
            logger.debug(f"  Download URL: {download_str} (type: {type(parsed_item['download_url']).__name__})")
            
            # Filtrar por licencia si es necesario
            if license_filter == 'premium' and not is_premium:
                logger.debug(f"  Skipping item {parsed_item['id']} - not premium (filter: premium only)")
                continue
            elif license_filter == 'free' and is_premium:
                logger.debug(f"  Skipping item {parsed_item['id']} - premium (filter: free only)")
                continue
            
            # Solo agregar si tiene al menos un preview o thumbnail
            if parsed_item['thumbnail'] or parsed_item['preview']:
                parsed.append(parsed_item)
            else:
                logger.warning(f"  Skipping item {parsed_item['id']} - no images found")
        
        logger.info(f"Parseados {len(parsed)} resultados de Freepik (de {len(results['data'])} totales, filter={license_filter})")
        return parsed

