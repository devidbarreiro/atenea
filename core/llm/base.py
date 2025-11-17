"""
Clase base para clientes LLM
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Clase base abstracta para clientes LLM"""
    
    def __init__(self, model_name: str, temperature: float = 0.7):
        self.model_name = model_name
        self.temperature = temperature
    
    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Invoca el LLM con un prompt
        
        Args:
            prompt: Texto del prompt
            **kwargs: Argumentos adicionales
            
        Returns:
            Respuesta del LLM como string
        """
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Cuenta tokens en un texto
        
        Args:
            text: Texto a contar
            
        Returns:
            Número de tokens
        """
        pass
    
    @abstractmethod
    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estima el costo de una llamada
        
        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            
        Returns:
            Costo estimado en USD
        """
        pass

