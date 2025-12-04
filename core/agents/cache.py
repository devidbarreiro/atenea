"""
Sistema de caché para respuestas del agente
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class AgentCache:
    """Sistema de caché para respuestas del agente"""
    
    CACHE_PREFIX = 'agent_response:'
    DEFAULT_TTL = 86400  # 24 horas
    
    @staticmethod
    def get_cache_key(script_text: str, duration_min: float) -> str:
        """
        Genera una clave de caché única basada en el contenido del guión
        
        Args:
            script_text: Texto del guión
            duration_min: Duración en minutos (puede ser decimal, ej: 1.5)
            
        Returns:
            Clave de caché
        """
        # Crear hash del contenido - normalizar duración a 2 decimales para consistencia
        content = f"{script_text}:{duration_min:.2f}"
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        return f"{AgentCache.CACHE_PREFIX}{content_hash}"
    
    @staticmethod
    def get(script_text: str, duration_min: float) -> Optional[Dict[str, Any]]:
        """
        Obtiene respuesta del caché si existe
        
        Args:
            script_text: Texto del guión
            duration_min: Duración en minutos (puede ser decimal)
            
        Returns:
            Respuesta cacheada o None
        """
        cache_key = AgentCache.get_cache_key(script_text, duration_min)
        cached = cache.get(cache_key)
        
        if cached:
            logger.info(f"Cache HIT para guión (hash: {cache_key[-8:]})")
            return cached
        else:
            logger.debug(f"Cache MISS para guión (hash: {cache_key[-8:]})")
            return None
    
    @staticmethod
    def set(
        script_text: str,
        duration_min: float,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Guarda respuesta en caché
        
        Args:
            script_text: Texto del guión
            duration_min: Duración en minutos (puede ser decimal)
            response: Respuesta a cachear
            ttl: Time to live en segundos (default: 24 horas)
        """
        cache_key = AgentCache.get_cache_key(script_text, duration_min)
        
        if ttl is None:
            ttl = getattr(settings, 'AGENT_CACHE_TTL', AgentCache.DEFAULT_TTL)
        
        cache.set(cache_key, response, ttl)
        logger.info(f"Respuesta guardada en caché (hash: {cache_key[-8:]}, TTL: {ttl}s)")
    
    @staticmethod
    def invalidate(script_text: str, duration_min: float):
        """
        Invalida una entrada del caché
        
        Args:
            script_text: Texto del guión
            duration_min: Duración en minutos (puede ser decimal)
        """
        cache_key = AgentCache.get_cache_key(script_text, duration_min)
        cache.delete(cache_key)
        logger.info(f"Caché invalidado (hash: {cache_key[-8:]})")
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché (requiere Redis con INFO command)
        
        Returns:
            Dict con estadísticas
        """
        # Esto requeriría acceso directo a Redis
        # Por ahora retornamos estructura básica
        return {
            'cache_enabled': True,
            'cache_prefix': AgentCache.CACHE_PREFIX,
            'default_ttl': AgentCache.DEFAULT_TTL
        }

