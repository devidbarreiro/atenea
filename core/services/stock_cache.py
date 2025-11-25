"""
Sistema de caché para búsquedas de contenido stock
"""
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class StockCache:
    """Sistema de caché para búsquedas de stock"""
    
    CACHE_PREFIX = 'stock_search:'
    DEFAULT_TTL = 3600  # 1 hora por defecto
    
    @staticmethod
    def get_cache_key(
        query: str,
        content_type: str,  # 'image', 'video' o 'audio'
        sources: Optional[list] = None,
        orientation: Optional[str] = None,
        license_filter: str = 'all',
        audio_type: Optional[str] = None,  # Para audio: 'music', 'sound_effects', 'all'
        page: int = 1,
        per_page: int = 20
    ) -> str:
        """
        Genera una clave de caché única basada en los parámetros de búsqueda
        
        Args:
            query: Término de búsqueda
            content_type: Tipo de contenido ('image' o 'video')
            sources: Lista de fuentes
            orientation: Orientación
            license_filter: Filtro de licencia
            page: Número de página
            per_page: Resultados por página
            
        Returns:
            Clave de caché
        """
        # Normalizar query (lowercase, strip)
        normalized_query = query.lower().strip()
        
        # Crear hash del contenido
        # Normalizar sources: None y [] son equivalentes para evitar colisiones
        normalized_sources = sorted(sources) if sources else []
        
        cache_data = {
            'query': normalized_query,
            'type': content_type,
            'sources': normalized_sources,
            'orientation': orientation,
            'license': license_filter,
            'audio_type': audio_type,
            'page': page,
            'per_page': per_page
        }
        
        content_str = json.dumps(cache_data, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        
        return f"{StockCache.CACHE_PREFIX}{content_hash}"
    
    @staticmethod
    def get(
        query: str,
        content_type: str,
        sources: Optional[list] = None,
        orientation: Optional[str] = None,
        license_filter: str = 'all',
        audio_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene resultados del caché si existen
        
        Args:
            query: Término de búsqueda
            content_type: Tipo de contenido ('image' o 'video')
            sources: Lista de fuentes
            orientation: Orientación
            license_filter: Filtro de licencia
            page: Número de página
            per_page: Resultados por página
            
        Returns:
            Resultados cacheados o None
        """
        cache_key = StockCache.get_cache_key(
            query=query,
            content_type=content_type,
            sources=sources,
            orientation=orientation,
            license_filter=license_filter,
            audio_type=audio_type,
            page=page,
            per_page=per_page
        )
        
        cached = cache.get(cache_key)
        
        if cached:
            logger.info(f"Stock Cache HIT para '{query}' (hash: {cache_key[-8:]})")
            return cached
        else:
            logger.debug(f"Stock Cache MISS para '{query}' (hash: {cache_key[-8:]})")
            return None
    
    @staticmethod
    def set(
        query: str,
        content_type: str,
        results: Dict[str, Any],
        sources: Optional[list] = None,
        orientation: Optional[str] = None,
        license_filter: str = 'all',
        audio_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        ttl: Optional[int] = None
    ):
        """
        Guarda resultados en caché
        
        Args:
            query: Término de búsqueda
            content_type: Tipo de contenido ('image' o 'video')
            results: Resultados a cachear
            sources: Lista de fuentes
            orientation: Orientación
            license_filter: Filtro de licencia
            page: Número de página
            per_page: Resultados por página
            ttl: Time to live en segundos (default: 1 hora)
        """
        cache_key = StockCache.get_cache_key(
            query=query,
            content_type=content_type,
            sources=sources,
            orientation=orientation,
            license_filter=license_filter,
            audio_type=audio_type,
            page=page,
            per_page=per_page
        )
        
        if ttl is None:
            ttl = getattr(settings, 'STOCK_CACHE_TTL', StockCache.DEFAULT_TTL)
        
        cache.set(cache_key, results, ttl)
        logger.info(f"Resultados guardados en caché (hash: {cache_key[-8:]}, TTL: {ttl}s)")
    
    @staticmethod
    def invalidate(
        query: str,
        content_type: str,
        sources: Optional[list] = None,
        orientation: Optional[str] = None,
        license_filter: str = 'all',
        audio_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ):
        """
        Invalida una entrada del caché
        
        Args:
            query: Término de búsqueda
            content_type: Tipo de contenido ('image' o 'video')
            sources: Lista de fuentes
            orientation: Orientación
            license_filter: Filtro de licencia
            page: Número de página
            per_page: Resultados por página
        """
        cache_key = StockCache.get_cache_key(
            query=query,
            content_type=content_type,
            sources=sources,
            orientation=orientation,
            license_filter=license_filter,
            audio_type=audio_type,
            page=page,
            per_page=per_page
        )
        
        cache.delete(cache_key)
        logger.info(f"Caché invalidado (hash: {cache_key[-8:]})")
    
    @staticmethod
    def invalidate_all():
        """Invalida todo el caché de stock (usar con precaución)"""
        # Esto requeriría acceso directo a Redis o usar un patrón de prefijo
        # Por ahora, solo logueamos
        logger.warning("Invalidación completa de caché de stock solicitada (no implementada)")
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché
        
        Returns:
            Dict con estadísticas
        """
        return {
            'cache_enabled': True,
            'cache_prefix': StockCache.CACHE_PREFIX,
            'default_ttl': StockCache.DEFAULT_TTL
        }

