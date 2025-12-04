"""
Base Agent - Clase base para todos los agentes especializados
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional
from core.agents.production_house.shared_state import SharedState

logger = logging.getLogger(__name__)

# Timeout por defecto para llamadas LLM (en segundos)
DEFAULT_LLM_TIMEOUT = 120


class BaseAgent(ABC):
    """
    Clase base para todos los agentes especializados.
    Cada agente debe implementar process() y puede tener su propio LLM.
    """
    
    def __init__(
        self,
        name: str,
        llm_provider: str = 'openai',
        llm_model: str = None,
        temperature: float = 0.7,
        timeout: int = DEFAULT_LLM_TIMEOUT
    ):
        """
        Inicializa el agente base
        
        Args:
            name: Nombre del agente (para logging)
            llm_provider: Proveedor LLM ('openai' o 'gemini')
            llm_model: Modelo específico (None = default)
            temperature: Temperatura para sampling
            timeout: Timeout para llamadas LLM en segundos
        """
        self.name = name
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.temperature = temperature
        self.timeout = timeout
        self.llm = None  # Se inicializa cuando se necesite
        
        logger.info(f"{self.name} Agent inicializado (provider: {llm_provider}, model: {llm_model})")
    
    def get_llm(self):
        """Obtiene el LLM (lazy loading)"""
        if self.llm is None:
            from core.llm.factory import LLMFactory
            self.llm = LLMFactory.get_llm(
                provider=self.llm_provider,
                model_name=self.llm_model,
                temperature=self.temperature
            )
        return self.llm
    
    def validate_state(self, state: SharedState) -> bool:
        """
        Valida que el estado tenga los campos necesarios.
        Sobrescribir en agentes específicos si necesitan validación extra.
        
        Args:
            state: Estado a validar
            
        Returns:
            True si es válido
            
        Raises:
            ValueError si hay problemas de validación
        """
        if not state.script_text:
            raise ValueError(f"{self.name}: script_text está vacío")
        if state.duration_seconds <= 0:
            raise ValueError(f"{self.name}: duration_seconds debe ser > 0")
        return True
    
    @abstractmethod
    def process(self, state: SharedState) -> SharedState:
        """
        Procesa el estado compartido y lo modifica.
        
        Args:
            state: Estado compartido actual
            
        Returns:
            Estado compartido modificado
        """
        pass
    
    def log(self, state: SharedState, message: str):
        """Añade un log al estado"""
        state.add_log(self.name, message)
        logger.info(f"[{self.name}] {message}")
    
    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parsea JSON de una respuesta LLM de forma robusta.
        Maneja markdown code blocks, texto antes/después del JSON, etc.
        
        Args:
            response_text: Texto de respuesta del LLM
            
        Returns:
            Dict parseado
            
        Raises:
            ValueError si no se puede parsear
        """
        import json
        import re
        
        # Intentar extraer JSON de markdown code block primero
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Intentar encontrar JSON directo
        start_idx = response_text.find('{')
        if start_idx == -1:
            raise ValueError("No se encontró JSON en la respuesta")
        
        # Encontrar el cierre balanceado de llaves
        depth = 0
        end_idx = start_idx
        for i, char in enumerate(response_text[start_idx:], start_idx):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
        
        if depth != 0:
            # Fallback: usar rfind
            end_idx = response_text.rfind('}') + 1
        
        json_str = response_text[start_idx:end_idx]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.error(f"JSON string: {json_str[:500]}...")
            raise ValueError(f"Error parseando JSON: {str(e)}")

