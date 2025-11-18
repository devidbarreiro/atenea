"""
Métricas y tracking del agente
"""

import logging
import time
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class AgentMetrics:
    """Clase para trackear métricas del agente"""
    
    CACHE_PREFIX = 'agent_metrics:'
    CACHE_TTL = 86400  # 24 horas
    
    @staticmethod
    def track_request(
        script_id: Optional[int],
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        errors: Optional[list] = None
    ):
        """
        Trackea una request del agente
        
        Args:
            script_id: ID del script procesado
            provider: Proveedor LLM ('openai', 'gemini')
            model: Modelo usado
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            latency_ms: Latencia en milisegundos
            success: Si la request fue exitosa
            errors: Lista de errores (si los hay)
        """
        metrics = {
            'script_id': script_id,
            'provider': provider,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'latency_ms': latency_ms,
            'success': success,
            'errors': errors or [],
            'timestamp': time.time()
        }
        
        # Calcular costo estimado
        try:
            from core.llm.factory import LLMFactory
            cost = LLMFactory.get_cost_estimate(
                provider=provider,
                model_name=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            metrics['cost_usd'] = cost
        except Exception as e:
            logger.warning(f"Error al calcular costo: {e}")
            metrics['cost_usd'] = 0.0
        
        # Guardar en caché (para estadísticas)
        if script_id:
            cache_key = f"{AgentMetrics.CACHE_PREFIX}script_{script_id}"
            cache.set(cache_key, metrics, AgentMetrics.CACHE_TTL)
        
        # Log estructurado
        logger.info(f"Agent Metrics: {metrics}")
        
        # Incrementar contadores globales
        AgentMetrics._increment_counters(provider, model, success)
        
        return metrics
    
    @staticmethod
    def _increment_counters(provider: str, model: str, success: bool):
        """Incrementa contadores globales en caché"""
        today = time.strftime('%Y-%m-%d')
        
        # Contador total de requests
        total_key = f"{AgentMetrics.CACHE_PREFIX}total:{today}"
        try:
            cache.incr(total_key)
        except (ValueError, TypeError):
            cache.set(total_key, 1, timeout=AgentMetrics.CACHE_TTL)
        
        # Contador por proveedor
        provider_key = f"{AgentMetrics.CACHE_PREFIX}provider:{provider}:{today}"
        try:
            cache.incr(provider_key)
        except (ValueError, TypeError):
            cache.set(provider_key, 1, timeout=AgentMetrics.CACHE_TTL)
        
        # Contador de éxito/error
        status_key = f"{AgentMetrics.CACHE_PREFIX}status:{'success' if success else 'error'}:{today}"
        try:
            cache.incr(status_key)
        except (ValueError, TypeError):
            cache.set(status_key, 1, timeout=AgentMetrics.CACHE_TTL)
    
    @staticmethod
    def get_daily_stats(date: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas del día
        
        Args:
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            Dict con estadísticas
        """
        if not date:
            date = time.strftime('%Y-%m-%d')
        
        total = cache.get(f"{AgentMetrics.CACHE_PREFIX}total:{date}", 0)
        success = cache.get(f"{AgentMetrics.CACHE_PREFIX}status:success:{date}", 0)
        errors = cache.get(f"{AgentMetrics.CACHE_PREFIX}status:error:{date}", 0)
        
        openai_count = cache.get(f"{AgentMetrics.CACHE_PREFIX}provider:openai:{date}", 0)
        gemini_count = cache.get(f"{AgentMetrics.CACHE_PREFIX}provider:gemini:{date}", 0)
        
        return {
            'date': date,
            'total_requests': total,
            'successful': success,
            'errors': errors,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'by_provider': {
                'openai': openai_count,
                'gemini': gemini_count
            }
        }
    
    @staticmethod
    def get_script_metrics(script_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene métricas de un script específico
        
        Args:
            script_id: ID del script
            
        Returns:
            Dict con métricas o None si no existe
        """
        cache_key = f"{AgentMetrics.CACHE_PREFIX}script_{script_id}"
        return cache.get(cache_key)

