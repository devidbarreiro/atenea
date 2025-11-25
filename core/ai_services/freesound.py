"""
Cliente para FreeSound API
https://freesound.org/docs/api/

Para obtener un token de API:
1. Ve a https://freesound.org/apiv2/apply/
2. Inicia sesión en tu cuenta de FreeSound
3. Completa el formulario de aplicación API
4. Copia el "API Key" (token) que aparece después de crear la aplicación
5. Configúralo en tu .env como FREESOUND_API_KEY

Nota: El token se usa para búsquedas básicas. Para descargas de archivos originales
se requiere OAuth2 (no implementado aún).
"""
import requests
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class FreeSoundFilter(Enum):
    """Filtros de búsqueda"""
    DURATION = 'duration'
    CREATED = 'created'
    DOWNLOADS = 'downloads'
    RATING = 'rating'


class FreeSoundSort(Enum):
    """Orden de resultados"""
    SCORE = 'score'
    DURATION_ASC = 'duration_asc'
    DURATION_DESC = 'duration_desc'
    CREATED_ASC = 'created_asc'
    CREATED_DESC = 'created_desc'
    DOWNLOADS_ASC = 'downloads_asc'
    DOWNLOADS_DESC = 'downloads_desc'
    RATING_ASC = 'rating_asc'
    RATING_DESC = 'rating_desc'


class FreeSoundClient:
    """Cliente para interactuar con FreeSound API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de FreeSound
        
        Args:
            api_key: API key de FreeSound (Token de acceso)
        """
        self.api_key = api_key
        self.base_url = 'https://freesound.org/apiv2'
        self.session = requests.Session()
        logger.info("FreeSoundClient inicializado")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna los headers para las peticiones"""
        # FreeSound API v2 usa "Token {api_key}" donde api_key es el "Client secret/Api key"
        # de la tabla de aplicaciones en https://freesound.org/apiv2/apply/
        return {
            'Authorization': f'Token {self.api_key}',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API de FreeSound
        
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
        
        logger.info(f"FreeSound API Request: {method} {url}")
        # Log parcial del token para debugging (solo si es necesario)
        if logger.isEnabledFor(logging.DEBUG):
            masked_token = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
            logger.debug(f"FreeSound usando token: {masked_token}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )
            
            logger.info(f"FreeSound API Response Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            if 'results' in result:
                logger.info(f"FreeSound API: Encontrados {len(result['results'])} resultados")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error en FreeSound API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response Body: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a FreeSound API: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Error al parsear respuesta JSON de FreeSound: {str(e)}")
            raise
    
    def search_sounds(
        self,
        query: str,
        filter_query: Optional[str] = None,
        sort: Optional[FreeSoundSort] = None,
        page: int = 1,
        page_size: int = 20,
        fields: Optional[str] = None
    ) -> Dict:
        """
        Busca sonidos en FreeSound
        
        Args:
            query: Término de búsqueda
            filter_query: Filtros adicionales (ej: "duration:[1 TO 10]")
            sort: Orden de resultados
            page: Número de página
            page_size: Resultados por página (max 150)
            fields: Campos a retornar (ej: "id,name,previews,duration")
            
        Returns:
            Dict con resultados de búsqueda
        """
        params = {
            'query': query,
            'page': page,
            'page_size': min(page_size, 150)
        }
        
        if filter_query:
            params['filter'] = filter_query
        
        if sort:
            params['sort'] = sort.value
        
        # Campos por defecto si no se especifican
        if fields is None:
            fields = 'id,name,description,previews,duration,downloads,license,username,tags,created'
        params['fields'] = fields
        
        logger.info(f"Buscando sonidos en FreeSound con parámetros: {params}")
        return self._make_request('GET', '/search/text/', params=params)
    
    def get_sound_details(self, sound_id: int) -> Dict:
        """
        Obtiene detalles completos de un sonido
        
        Args:
            sound_id: ID del sonido
            
        Returns:
            Dict con detalles del sonido
        """
        return self._make_request('GET', f'/sounds/{sound_id}/')
    
    def parse_sounds(self, results: Dict) -> List[Dict]:
        """
        Parsea y simplifica los resultados de búsqueda de sonidos
        
        Args:
            results: Resultados crudos de la API
            
        Returns:
            Lista de sonidos simplificados
        """
        if 'results' not in results:
            logger.warning("No se encontró 'results' en resultados de FreeSound")
            return []
        
        parsed = []
        for sound in results['results']:
            # Obtener preview URL (preferir preview-hq-mp3, luego preview-mp3)
            preview_url = ''
            if 'previews' in sound:
                previews = sound['previews']
                preview_url = (
                    previews.get('preview-hq-mp3', '') or
                    previews.get('preview-mp3', '') or
                    previews.get('preview-ogg', '') or
                    ''
                )
            
            # Obtener download URL
            # NOTA: FreeSound requiere autenticación OAuth2 para descargar archivos originales.
            # El endpoint de descarga requiere un token de acceso válido en el header Authorization.
            # Por ahora, marcamos como None ya que requiere autenticación adicional del usuario.
            # Los usuarios pueden usar la URL de preview para escuchar el audio.
            download_url = None
            # Si en el futuro se implementa autenticación OAuth2, descomentar:
            # download_url = f"https://freesound.org/apiv2/sounds/{sound.get('id')}/download/"
            
            parsed_item = {
                'id': str(sound.get('id', '')),
                'title': sound.get('name', 'Sin título'),
                'description': sound.get('description', '')[:200] if sound.get('description') else '',
                'type': 'audio',
                'source': 'freesound',
                'thumbnail': '',  # FreeSound no tiene thumbnails de imágenes
                'preview': preview_url,
                'download_url': download_url,  # None - requiere autenticación OAuth2
                'duration': sound.get('duration', 0),
                'downloads': sound.get('downloads', 0),
                'license': sound.get('license', ''),
                'author': sound.get('username', ''),
                'tags': sound.get('tags', []),
                'created': sound.get('created', ''),
                'is_premium': False  # FreeSound es siempre gratuito
            }
            
            # Solo agregar si tiene preview (download_url puede ser None)
            if parsed_item['preview']:
                parsed.append(parsed_item)
        
        logger.info(f"Parseados {len(parsed)} resultados de FreeSound")
        return parsed

