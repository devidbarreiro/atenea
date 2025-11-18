"""
Factory para crear instancias de LLM
Soporta OpenAI y Gemini con fallback automático
"""

import logging
import os
from typing import Optional, Literal

try:
    from django.conf import settings
    # Verificar si Django está configurado
    try:
        _django_configured = settings.configured
        DJANGO_AVAILABLE = True
    except (RuntimeError, AttributeError):
        # Django no está configurado
        DJANGO_AVAILABLE = False
        settings = None
except (ImportError, RuntimeError):
    # Django no está disponible o no está configurado
    DJANGO_AVAILABLE = False
    settings = None

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory para crear instancias de LLM"""
    
    # Precios por 1M tokens (actualizados Enero 2025)
    PRICING = {
        'openai': {
            'gpt-4o': {'input': 2.50, 'output': 10.00},  # $2.50/$10 por 1M tokens
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
            'gpt-4': {'input': 30.00, 'output': 60.00},
        },
        'gemini': {
            'gemini-pro': {'input': 0.50, 'output': 1.50},  # $0.50/$1.50 por 1M tokens
            'gemini-pro-1.5': {'input': 1.25, 'output': 5.00},
        }
    }
    
    @staticmethod
    def create_openai_llm(
        model_name: str = 'gpt-4o',
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> ChatOpenAI:
        """
        Crea una instancia de OpenAI LLM
        
        Args:
            model_name: Nombre del modelo (gpt-4o, gpt-4-turbo, gpt-4)
            temperature: Temperatura para sampling
            max_tokens: Máximo de tokens de salida
            
        Returns:
            Instancia de ChatOpenAI
            
        Raises:
            ValueError: Si OPENAI_API_KEY no está configurada
        """
        # Intentar obtener API key de Django settings o variables de entorno
        api_key = None
        if DJANGO_AVAILABLE and settings and settings.configured:
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        # Fallback a variable de entorno si Django no está disponible
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError('OPENAI_API_KEY no está configurada. Debe estar en Django settings o variable de entorno OPENAI_API_KEY')
        
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )
    
    @staticmethod
    def create_gemini_llm(
        model_name: str = 'gemini-pro',
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> ChatGoogleGenerativeAI:
        """
        Crea una instancia de Gemini LLM
        
        Args:
            model_name: Nombre del modelo (gemini-pro, gemini-pro-1.5)
            temperature: Temperatura para sampling
            max_tokens: Máximo de tokens de salida
            
        Returns:
            Instancia de ChatGoogleGenerativeAI
            
        Raises:
            ValueError: Si GEMINI_API_KEY no está configurada
        """
        # Intentar obtener API key de Django settings o variables de entorno
        api_key = None
        if DJANGO_AVAILABLE and settings and settings.configured:
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
        
        # Fallback a variable de entorno si Django no está disponible
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError('GEMINI_API_KEY no está configurada. Debe estar en Django settings o variable de entorno GEMINI_API_KEY')
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=api_key,
        )
    
    @staticmethod
    def get_llm(
        provider: Literal['openai', 'gemini'] = 'openai',
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        fallback: bool = True
    ):
        """
        Obtiene una instancia de LLM con fallback automático
        
        Args:
            provider: Proveedor preferido ('openai' o 'gemini')
            model_name: Nombre del modelo específico (opcional)
            temperature: Temperatura para sampling
            max_tokens: Máximo de tokens de salida
            fallback: Si True, intenta fallback si el proveedor falla
            
        Returns:
            Instancia de LLM
            
        Raises:
            ValueError: Si ningún proveedor está disponible
        """
        # Modelos por defecto
        default_models = {
            'openai': 'gpt-4o',
            'gemini': 'gemini-pro'
        }
        
        if not model_name:
            model_name = default_models.get(provider)
        
        try:
            if provider == 'openai':
                return LLMFactory.create_openai_llm(
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            elif provider == 'gemini':
                return LLMFactory.create_gemini_llm(
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                raise ValueError(f"Proveedor no soportado: {provider}")
                
        except Exception as e:
            if fallback:
                logger.warning(f"Error al crear LLM {provider}: {e}. Intentando fallback...")
                # Intentar con el otro proveedor
                fallback_provider = 'gemini' if provider == 'openai' else 'openai'
                try:
                    return LLMFactory.get_llm(
                        provider=fallback_provider,
                        model_name=None,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        fallback=False  # No hacer fallback recursivo
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback también falló: {fallback_error}")
                    raise ValueError(f"No se pudo crear LLM. OpenAI error: {e}, Gemini error: {fallback_error}")
            else:
                raise
    
    @staticmethod
    def get_cost_estimate(
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estima el costo de una llamada al LLM
        
        Args:
            provider: 'openai' o 'gemini'
            model_name: Nombre del modelo
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            
        Returns:
            Costo estimado en USD
        """
        pricing = LLMFactory.PRICING.get(provider, {}).get(model_name)
        if not pricing:
            logger.warning(f"Pricing no encontrado para {provider}/{model_name}")
            return 0.0
        
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        
        return input_cost + output_cost


# Función helper para uso directo
def get_llm(provider: str = 'openai', **kwargs):
    """
    Helper function para obtener LLM fácilmente
    
    Usage:
        llm = get_llm('openai', model_name='gpt-4o')
        llm = get_llm('gemini')
    """
    return LLMFactory.get_llm(provider=provider, **kwargs)

