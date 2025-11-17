"""
Clase base para agentes
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Clase base abstracta para agentes"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa la entrada y retorna resultado
        
        Args:
            input_data: Datos de entrada
            
        Returns:
            Resultado procesado
        """
        pass
    
    def log_metrics(self, metrics: Dict[str, Any]):
        """Log métricas del agente"""
        self.logger.info(f"Métricas: {metrics}")

