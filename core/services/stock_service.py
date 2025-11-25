"""
Servicio unificado para búsqueda de contenido stock
Integra múltiples APIs: Freepik, Pexels, Unsplash, Pixabay
"""
import logging
from typing import Dict, List, Optional, Set
from django.conf import settings
from core.ai_services.freepik import FreepikClient, FreepikContentType, FreepikOrientation
from core.ai_services.pexels import PexelsClient, PexelsOrientation
from core.ai_services.unsplash import UnsplashClient, UnsplashOrientation
from core.ai_services.pixabay import PixabayClient, PixabayOrientation, PixabayImageType
from core.ai_services.freesound import FreeSoundClient, FreeSoundSort

logger = logging.getLogger(__name__)


class StockService:
    """Servicio unificado para búsqueda de contenido stock"""
    
    # Mapeo de orientaciones entre servicios
    ORIENTATION_MAP = {
        'horizontal': {
            'freepik': FreepikOrientation.HORIZONTAL,
            'pexels': PexelsOrientation.LANDSCAPE,
            'unsplash': UnsplashOrientation.LANDSCAPE,
            'pixabay': PixabayOrientation.HORIZONTAL,
        },
        'vertical': {
            'freepik': FreepikOrientation.VERTICAL,
            'pexels': PexelsOrientation.PORTRAIT,
            'unsplash': UnsplashOrientation.PORTRAIT,
            'pixabay': PixabayOrientation.VERTICAL,
        },
        'square': {
            'freepik': FreepikOrientation.SQUARE,
            'pexels': PexelsOrientation.SQUARE,
            'unsplash': UnsplashOrientation.SQUARISH,
            'pixabay': None,  # Pixabay no tiene square específico
        }
    }
    
    def __init__(self):
        """Inicializa los clientes de las APIs disponibles"""
        self.clients = {}
        
        # Freepik
        if hasattr(settings, 'FREEPIK_API_KEY') and settings.FREEPIK_API_KEY:
            try:
                self.clients['freepik'] = FreepikClient(settings.FREEPIK_API_KEY)
                logger.info("Freepik client inicializado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Freepik client: {e}")
        
        # Pexels
        if hasattr(settings, 'PEXELS_API_KEY') and settings.PEXELS_API_KEY:
            try:
                self.clients['pexels'] = PexelsClient(settings.PEXELS_API_KEY)
                logger.info("Pexels client inicializado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Pexels client: {e}")
        
        # Unsplash
        if hasattr(settings, 'UNSPLASH_ACCESS_KEY') and settings.UNSPLASH_ACCESS_KEY:
            try:
                self.clients['unsplash'] = UnsplashClient(settings.UNSPLASH_ACCESS_KEY)
                logger.info("Unsplash client inicializado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Unsplash client: {e}")
        
        # Pixabay
        if hasattr(settings, 'PIXABAY_API_KEY') and settings.PIXABAY_API_KEY:
            try:
                self.clients['pixabay'] = PixabayClient(settings.PIXABAY_API_KEY)
                logger.info("Pixabay client inicializado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Pixabay client: {e}")
        
        # FreeSound
        if hasattr(settings, 'FREESOUND_API_KEY') and settings.FREESOUND_API_KEY:
            try:
                self.clients['freesound'] = FreeSoundClient(settings.FREESOUND_API_KEY.strip())
                logger.info("FreeSound client inicializado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar FreeSound client: {e}")
        
        logger.info(f"StockService inicializado con {len(self.clients)} clientes disponibles")
    
    def search_images(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        orientation: Optional[str] = None,
        license_filter: str = 'all',
        page: int = 1,
        per_page: int = 20,
        max_results_per_source: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Busca imágenes en múltiples fuentes de stock
        
        Args:
            query: Término de búsqueda
            sources: Lista de fuentes a buscar (None = todas las disponibles)
            orientation: Orientación ('horizontal', 'vertical', 'square')
            license_filter: Filtro de licencia ('all', 'free', 'premium')
            page: Número de página
            per_page: Resultados totales deseados
            max_results_per_source: Máximo de resultados por fuente
            
        Returns:
            Dict con resultados agrupados por fuente y totales
        """
        if sources is None:
            sources = list(self.clients.keys())
        
        # Validar que haya fuentes disponibles
        if not sources:
            return {
                'query': query,
                'total': 0,
                'sources_searched': [],
                'results_by_source': {},
                'results': [],
                'page': page,
                'per_page': per_page
            }
        
        if max_results_per_source is None:
            # Distribuir resultados equitativamente entre fuentes
            max_results_per_source = (per_page // len(sources)) + 5  # Buffer extra
        
        results_by_source = {}
        all_results = []
        
        for source in sources:
            if source not in self.clients:
                logger.warning(f"Fuente '{source}' no disponible, saltando...")
                continue
            
            try:
                client = self.clients[source]
                source_results = self._search_images_in_source(
                    client=client,
                    source=source,
                    query=query,
                    orientation=orientation,
                    license_filter=license_filter,
                    page=page,
                    limit=max_results_per_source
                )
                
                # Asegurar que todos los resultados tengan el campo 'source'
                for result in source_results:
                    if 'source' not in result:
                        result['source'] = source
                
                results_by_source[source] = source_results
                all_results.extend(source_results)
                
            except Exception as e:
                logger.error(f"Error buscando en {source}: {e}")
                results_by_source[source] = []
        
        # Ordenar todos los resultados (por relevancia, fecha, etc.)
        # Por ahora los dejamos en el orden que vienen
        
        # Limitar resultados totales
        all_results = all_results[:per_page]
        
        return {
            'query': query,
            'total': len(all_results),
            'sources_searched': sources,
            'results_by_source': results_by_source,
            'results': all_results,
            'page': page,
            'per_page': per_page
        }
    
    def _search_images_in_source(
        self,
        client,
        source: str,
        query: str,
        orientation: Optional[str],
        license_filter: str,
        page: int,
        limit: int
    ) -> List[Dict]:
        """Busca imágenes en una fuente específica"""
        
        try:
            if source == 'freepik':
                # Mapear orientación
                freepik_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    freepik_orientation = self.ORIENTATION_MAP[orientation]['freepik']
                
                # Buscar en Freepik
                results = client.search_images(
                    query=query,
                    orientation=freepik_orientation,
                    page=page,
                    limit=limit,
                    license_filter=license_filter
                )
                return client.parse_search_results(results, license_filter=license_filter)
            
            elif source == 'pexels':
                # Mapear orientación
                pexels_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    pexels_orientation = self.ORIENTATION_MAP[orientation]['pexels']
                
                # Buscar en Pexels
                results = client.search_photos(
                    query=query,
                    orientation=pexels_orientation,
                    page=page,
                    per_page=limit
                )
                return client.parse_photos(results)
            
            elif source == 'unsplash':
                # Mapear orientación
                unsplash_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    unsplash_orientation = self.ORIENTATION_MAP[orientation]['unsplash']
                
                # Buscar en Unsplash
                results = client.search_photos(
                    query=query,
                    orientation=unsplash_orientation,
                    page=page,
                    per_page=limit
                )
                return client.parse_photos(results)
            
            elif source == 'pixabay':
                # Mapear orientación
                pixabay_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    pixabay_orientation = self.ORIENTATION_MAP[orientation]['pixabay']
                
                # Buscar en Pixabay
                results = client.search_images(
                    query=query,
                    orientation=pixabay_orientation,
                    page=page,
                    per_page=limit
                )
                return client.parse_images(results)
            
            else:
                logger.warning(f"Fuente '{source}' no soportada")
                return []
        
        except Exception as e:
            logger.error(f"Error buscando imágenes en {source}: {e}")
            return []
    
    def search_videos(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        orientation: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        max_results_per_source: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Busca videos en múltiples fuentes de stock
        
        Args:
            query: Término de búsqueda
            sources: Lista de fuentes a buscar (None = todas las disponibles)
            orientation: Orientación ('horizontal', 'vertical', 'square')
            page: Número de página
            per_page: Resultados totales deseados
            max_results_per_source: Máximo de resultados por fuente
            
        Returns:
            Dict con resultados agrupados por fuente y totales
        """
        if sources is None:
            sources = list(self.clients.keys())
        
        # Validar que haya fuentes disponibles
        if not sources:
            return {
                'query': query,
                'total': 0,
                'sources_searched': [],
                'results_by_source': {},
                'results': [],
                'page': page,
                'per_page': per_page
            }
        
        if max_results_per_source is None:
            max_results_per_source = (per_page // len(sources)) + 5
        
        results_by_source = {}
        all_results = []
        
        for source in sources:
            if source not in self.clients:
                logger.warning(f"Fuente '{source}' no disponible, saltando...")
                continue
            
            try:
                client = self.clients[source]
                source_results = self._search_videos_in_source(
                    client=client,
                    source=source,
                    query=query,
                    orientation=orientation,
                    page=page,
                    limit=max_results_per_source
                )
                
                # Asegurar que todos los resultados tengan el campo 'source'
                for result in source_results:
                    if 'source' not in result:
                        result['source'] = source
                
                results_by_source[source] = source_results
                all_results.extend(source_results)
                
            except Exception as e:
                logger.error(f"Error buscando videos en {source}: {e}")
                results_by_source[source] = []
        
        all_results = all_results[:per_page]
        
        return {
            'query': query,
            'total': len(all_results),
            'sources_searched': sources,
            'results_by_source': results_by_source,
            'results': all_results,
            'page': page,
            'per_page': per_page
        }
    
    def _search_videos_in_source(
        self,
        client,
        source: str,
        query: str,
        orientation: Optional[str],
        page: int,
        limit: int
    ) -> List[Dict]:
        """Busca videos en una fuente específica"""
        
        try:
            if source == 'freepik':
                freepik_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    freepik_orientation = self.ORIENTATION_MAP[orientation]['freepik']
                
                results = client.search_videos(
                    query=query,
                    orientation=freepik_orientation,
                    page=page,
                    limit=limit
                )
                # Freepik videos usa el mismo parser que imágenes
                return client.parse_search_results(results)
            
            elif source == 'pexels':
                pexels_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    pexels_orientation = self.ORIENTATION_MAP[orientation]['pexels']
                
                results = client.search_videos(
                    query=query,
                    orientation=pexels_orientation,
                    page=page,
                    per_page=limit
                )
                return client.parse_videos(results)
            
            elif source == 'pixabay':
                pixabay_orientation = None
                if orientation and orientation in self.ORIENTATION_MAP:
                    pixabay_orientation = self.ORIENTATION_MAP[orientation]['pixabay']
                
                results = client.search_videos(
                    query=query,
                    page=page,
                    per_page=limit
                )
                return client.parse_videos(results)
            
            else:
                logger.warning(f"Fuente '{source}' no soporta videos o no está implementada")
                return []
        
        except Exception as e:
            logger.error(f"Error buscando videos en {source}: {e}")
            return []
    
    def search_audio(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        audio_type: Optional[str] = None,  # 'music', 'sound_effects', 'all'
        page: int = 1,
        per_page: int = 20,
        max_results_per_source: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Busca audios en múltiples fuentes de stock
        
        Args:
            query: Término de búsqueda
            sources: Lista de fuentes a buscar (None = todas las disponibles)
            audio_type: Tipo de audio ('music', 'sound_effects', 'all')
            page: Número de página
            per_page: Resultados totales deseados
            max_results_per_source: Máximo de resultados por fuente
            
        Returns:
            Dict con resultados agrupados por fuente y totales
        """
        # Fuentes que soportan audio
        audio_sources = ['pixabay', 'freesound']
        
        if sources is None:
            sources = [s for s in audio_sources if s in self.clients.keys()]
        else:
            # Filtrar solo fuentes que soportan audio
            sources = [s for s in sources if s in audio_sources and s in self.clients.keys()]
        
        if not sources:
            return {
                'query': query,
                'total': 0,
                'sources_searched': [],
                'results_by_source': {},
                'results': [],
                'page': page,
                'per_page': per_page
            }
        
        if max_results_per_source is None:
            max_results_per_source = (per_page // len(sources)) + 5
        
        results_by_source = {}
        all_results = []
        
        for source in sources:
            try:
                client = self.clients[source]
                source_results = self._search_audio_in_source(
                    client=client,
                    source=source,
                    query=query,
                    audio_type=audio_type,
                    page=page,
                    limit=max_results_per_source
                )
                
                # Asegurar que todos los resultados tengan el campo 'source'
                for result in source_results:
                    if 'source' not in result:
                        result['source'] = source
                
                results_by_source[source] = source_results
                all_results.extend(source_results)
                
                if source_results:
                    logger.info(f"✓ {source}: {len(source_results)} resultados encontrados")
                
            except Exception as e:
                error_msg = str(e)
                # Detectar errores de autenticación específicos
                if '401' in error_msg or 'Unauthorized' in error_msg or 'Invalid token' in error_msg:
                    logger.warning(f"⚠ {source}: Error de autenticación - API key/token inválido o no configurado")
                elif '400' in error_msg or 'Bad Request' in error_msg or 'Invalid or missing API key' in error_msg:
                    logger.warning(f"⚠ {source}: Error de API key - clave inválida o no configurada")
                else:
                    logger.error(f"✗ {source}: Error buscando audio: {e}")
                results_by_source[source] = []
        
        all_results = all_results[:per_page]
        
        # Log resumen de búsqueda
        successful_sources = [s for s, results in results_by_source.items() if results]
        failed_sources = [s for s in sources if s not in successful_sources]
        
        if successful_sources:
            logger.info(f"✓ Búsqueda de audio exitosa: {len(all_results)} resultados de {len(successful_sources)} fuente(s): {', '.join(successful_sources)}")
        else:
            logger.warning(f"⚠ Búsqueda de audio sin resultados: todas las fuentes fallaron ({', '.join(failed_sources)})")
        
        return {
            'query': query,
            'total': len(all_results),
            'sources_searched': sources,
            'sources_successful': successful_sources,
            'sources_failed': failed_sources,
            'results_by_source': results_by_source,
            'results': all_results,
            'page': page,
            'per_page': per_page
        }
    
    def _search_audio_in_source(
        self,
        client,
        source: str,
        query: str,
        audio_type: Optional[str],
        page: int,
        limit: int
    ) -> List[Dict]:
        """Busca audios en una fuente específica"""
        
        try:
            if source == 'pixabay':
                # Mapear audio_type
                pixabay_audio_type = 'all'
                if audio_type == 'music':
                    pixabay_audio_type = 'music'
                elif audio_type == 'sound_effects':
                    pixabay_audio_type = 'sound_effects'
                
                results = client.search_audio(
                    query=query,
                    audio_type=pixabay_audio_type,
                    page=page,
                    per_page=limit
                )
                return client.parse_audio(results)
            
            elif source == 'freesound':
                # FreeSound no tiene filtro directo de tipo, pero podemos usar filtros
                filter_query = None
                if audio_type == 'music':
                    # Intentar filtrar por tags comunes de música
                    filter_query = 'tag:music OR tag:musical'
                elif audio_type == 'sound_effects':
                    # Filtrar efectos de sonido (excluir música)
                    filter_query = 'NOT tag:music'
                
                results = client.search_sounds(
                    query=query,
                    filter_query=filter_query,
                    page=page,
                    page_size=limit
                )
                return client.parse_sounds(results)
            
            else:
                logger.warning(f"Fuente '{source}' no soporta audio o no está implementada")
                return []
        
        except Exception as e:
            error_msg = str(e)
            # Detectar errores de autenticación específicos para logging más detallado
            if '401' in error_msg or 'Unauthorized' in error_msg:
                logger.warning(f"⚠ {source}: Error de autenticación (401) - verificar API key/token")
            elif '400' in error_msg and ('API key' in error_msg or 'Bad Request' in error_msg):
                logger.warning(f"⚠ {source}: API key inválida o no configurada (400)")
            else:
                logger.error(f"✗ Error buscando audio en {source}: {e}")
            return []
    
    def get_available_sources(self) -> List[str]:
        """Retorna lista de fuentes disponibles"""
        return list(self.clients.keys())

