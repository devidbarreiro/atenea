from langchain.tools import tool
try:
    from langchain_community.tools import DuckDuckGoSearchRun
except ImportError:
    # Fallback or stub if not available, but usually is in langchain-community
    DuckDuckGoSearchRun = None
    
import logging

logger = logging.getLogger(__name__)

@tool
def search_web_tool(query: str, user_id: int = None) -> str:
    """
    Busca información en internet (DuckDuckGo).
    Úsalo para encontrar datos reales, estadísticas o valores cuando el usuario
    pide un gráfico pero no da los números (ej: "tasa de natalidad en España").
    
    Args:
        query: La consulta de búsqueda (ej: "birth rate Spain execution 2023")
        user_id: ID del usuario (opcional, por compatibilidad)
    """
    if DuckDuckGoSearchRun is None:
        return "Error: DuckDuckGoSearchRun library not found."
        
    try:
        logger.info(f"Searching web for: {query}")
        search = DuckDuckGoSearchRun()
        result = search.invoke(query)
        logger.info(f"Search result length: {len(result)}")
        print(f"[DEBUG TOOL] Search result: {result[:200]}...") # Force print to stdout
        return result
    except Exception as e:
        logger.error(f"Error searching web: {e}", exc_info=True)
        return f"Error searching web: {str(e)}"
