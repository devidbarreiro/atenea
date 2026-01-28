"""
Tool para buscar contenido en servicios de stock (Freepik, Pexels, Unsplash, Pixabay, FreeSound)
"""

from langchain.tools import tool
from typing import Dict, List, Optional, Any
from core.services.stock_service import StockService
import logging

logger = logging.getLogger(__name__)

@tool
def search_stock_tool(
    user_id: int,
    query: str,
    media_type: str = 'image',  # 'image', 'video', 'audio'
    limit: int = 10,
    orientation: Optional[str] = None,  # 'horizontal', 'vertical', 'square'
    sources: Optional[List[str]] = None
) -> Dict:
    """
    Busca contenido de stock (imágenes, videos, audio) en múltiples proveedores.

    Args:
        user_id: ID del usuario (requerido para contexto)
        query: Texto a buscar (ej: "paisaje montaña", "música épica")
        media_type: Tipo de medio: 'image', 'video', 'audio' (default: 'image')
        limit: Número máximo de resultados (default: 10)
        orientation: Orientación (opcional): 'horizontal', 'vertical', 'square'
        sources: Lista de fuentes específicas (opcional).
                 Para image: ['freepik', 'pexels', 'unsplash', 'pixabay']
                 Para video: ['freepik', 'pexels', 'pixabay']
                 Para audio: ['pixabay', 'freesound']

    Returns:
        Dict con resultados encontrados:
            - status: 'success' o 'error'
            - items: Lista de items encontrados
            - total: Total encontrados
            - message: Mensaje descriptivo
    """
    try:
        stock_service = StockService()

        # Validar media_type
        if media_type not in ['image', 'video', 'audio']:
            return {'status': 'error', 'message': f'Tipo de medio no válido: {media_type}. Usa image, video o audio.'}

        results = {}

        if media_type == 'image':
            results = stock_service.search_images(
                query=query,
                sources=sources,
                orientation=orientation,
                per_page=limit
            )
        elif media_type == 'video':
            results = stock_service.search_videos(
                query=query,
                sources=sources,
                orientation=orientation,
                per_page=limit
            )
        elif media_type == 'audio':
            # Intentar detectar si busca música o efectos
            audio_type = 'all'
            if 'musica' in query.lower() or 'music' in query.lower():
                audio_type = 'music'
            elif 'efecto' in query.lower() or 'sound' in query.lower() or 'fx' in query.lower():
                audio_type = 'sound_effects'

            results = stock_service.search_audio(
                query=query,
                sources=sources,
                audio_type=audio_type,
                per_page=limit
            )

        # Formatear resultados para el agente
        items = results.get('results', [])
        formatted_items = []

        for item in items:
            formatted_item = {
                'id': item.get('id'),
                'title': item.get('title', 'Sin título'),
                'source': item.get('source'),
                'url': item.get('preview') or item.get('url'), # Preferir preview para mostrar
                'download_url': item.get('download_url'),
                'thumbnail': item.get('thumbnail'),
                'type': media_type
            }

            # Añadir campos específicos
            if media_type == 'audio':
                formatted_item['duration'] = item.get('duration')

            formatted_items.append(formatted_item)

        return {
            'status': 'success',
            'items': formatted_items,
            'total': results.get('total', 0),
            'sources_searched': results.get('sources_searched', []),
            'message': f"Se encontraron {len(formatted_items)} resultados de stock para '{query}'"
        }

    except Exception as e:
        logger.error(f"Error en search_stock_tool: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Error al buscar contenido de stock: {str(e)}',
            'items': [],
            'count': 0
        }
