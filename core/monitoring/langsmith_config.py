"""
Configuración de LangSmith para observabilidad
"""

import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def setup_langsmith():
    """
    Configura LangSmith para trazabilidad completa del agente.
    LangSmith permite ver todas las llamadas al LLM, prompts, respuestas, y métricas.
    """
    langsmith_api_key = getattr(settings, 'LANGSMITH_API_KEY', None)
    langsmith_project = getattr(settings, 'LANGSMITH_PROJECT', 'atenea-script-agent')
    
    if langsmith_api_key:
        os.environ['LANGCHAIN_TRACING_V2'] = 'true'
        os.environ['LANGCHAIN_API_KEY'] = langsmith_api_key
        os.environ['LANGCHAIN_PROJECT'] = langsmith_project
        
        logger.info(f"LangSmith configurado (proyecto: {langsmith_project})")
    else:
        logger.warning("LANGSMITH_API_KEY no configurada. LangSmith deshabilitado.")
        logger.info("Para habilitar LangSmith, agrega LANGSMITH_API_KEY a tu .env")
        logger.info("Obtén tu API key en: https://smith.langchain.com/")

