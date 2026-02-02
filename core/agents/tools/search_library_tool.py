"""
Tool para buscar contenido en la biblioteca del usuario
Permite buscar videos, imágenes, audios y guiones por texto
"""

from langchain.tools import tool
from typing import Dict, List, Optional, Any
from django.contrib.auth.models import User
from django.db.models import Q
from core.models import Video, Image, Audio, Script
from core.storage.gcs import gcs_storage
import logging

logger = logging.getLogger(__name__)

@tool
def search_library_tool(
    user_id: int,
    query: str,
    item_type: Optional[str] = None,  # 'video', 'image', 'audio', 'script', None para todos
    limit: int = 5
) -> Dict:
    """
    Busca contenido en la biblioteca del usuario (videos, imágenes, audios, guiones).

    Args:
        user_id: ID del usuario (requerido)
        query: Texto a buscar (en título, prompt, script, etc.)
        item_type: Filtrar por tipo ('video', 'image', 'audio', 'script') o None para todos
        limit: Número máximo de resultados (default: 5)

    Returns:
        Dict con resultados encontrados:
            - status: 'success' o 'error'
            - items: Lista de items encontrados
            - count: Total encontrados
            - message: Mensaje descriptivo
    """
    try:
        if not user_id:
            return {'status': 'error', 'message': 'user_id es requerido'}

        if not query:
            return {'status': 'error', 'message': 'query es requerido'}

        if item_type is not None and item_type not in ['video', 'image', 'audio', 'script']:
            return {'status': 'error', 'message': 'item_type inválido'}

        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
            MAX_LIMIT = 50
            if limit > MAX_LIMIT:
                limit = MAX_LIMIT
        except (ValueError, TypeError):
             return {'status': 'error', 'message': 'limit debe ser un entero positivo'}

        # Validar usuario
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {'status': 'error', 'message': f'Usuario {user_id} no encontrado'}

        items = []

        # Helper para procesar resultados
        def process_item(item, type_name):
            # Determinar campos comunes
            title = getattr(item, 'title', 'Sin título') or 'Sin título'
            uuid_val = str(getattr(item, 'uuid', getattr(item, 'id', '')) or '')
            created_at = item.created_at.isoformat() if hasattr(item, 'created_at') else None
            status = getattr(item, 'status', 'unknown')

            # Campos específicos
            content = ""
            raw_content = None
            
            if type_name == 'video':
                raw_content = getattr(item, 'script', '')
            elif type_name == 'image':
                raw_content = getattr(item, 'prompt', '')
            elif type_name == 'audio':
                raw_content = getattr(item, 'text', '') or getattr(item, 'prompt', '')
            elif type_name == 'script':
                raw_content = getattr(item, 'original_script', '')
            
            content = str(raw_content) if raw_content is not None else ""

            # Generar URL de preview si tiene gcs_path
            preview_url = None
            if hasattr(item, 'gcs_path') and item.gcs_path:
                try:
                    preview_url = gcs_storage.get_signed_url(item.gcs_path)
                except Exception as e:
                    logger.warning(f"Error generando signed URL para {type_name} {uuid_val}: {e}")

            # Generar URL de detalle
            detail_url = None
            if uuid_val:
                if type_name == 'video':
                    detail_url = f'/videos/{uuid_val}/'
                elif type_name == 'image':
                    detail_url = f'/images/{uuid_val}/'
                elif type_name == 'audio':
                    detail_url = f'/audios/{uuid_val}/'
                elif type_name == 'script':
                    detail_url = f'/scripts/{uuid_val}/'

            return {
                'id': uuid_val,
                'type': type_name,
                'title': title,
                'content_snippet': content[:100] + '...' if len(content) > 100 else content,
                'status': status,
                'created_at': created_at,
                'preview_url': preview_url,
                'url': preview_url, # Alias para consistencia
                'detail_url': detail_url
            }

        # 1. Buscar VIDEOS
        if not item_type or item_type == 'video':
            videos = Video.objects.filter(
                created_by=user
            ).filter(
                Q(title__icontains=query) | Q(script__icontains=query)
            ).order_by('-created_at')[:limit]

            for v in videos:
                items.append(process_item(v, 'video'))

        # 2. Buscar IMÁGENES
        if not item_type or item_type == 'image':
            # Si ya tenemos suficientes items y no estamos filtrando solo por imágenes, podríamos optimizar
            # Pero como el límite es global, seguiremos buscando y luego recortaremos
            images = Image.objects.filter(
                created_by=user
            ).filter(
                Q(title__icontains=query) | Q(prompt__icontains=query)
            ).order_by('-created_at')[:limit]

            for img in images:
                items.append(process_item(img, 'image'))

        # 3. Buscar AUDIOS
        if not item_type or item_type == 'audio':
            audios = Audio.objects.filter(
                created_by=user
            ).filter(
                Q(title__icontains=query) | Q(text__icontains=query) | Q(prompt__icontains=query)
            ).order_by('-created_at')[:limit]

            for a in audios:
                items.append(process_item(a, 'audio'))

        # 4. Buscar SCRIPTS
        if not item_type or item_type == 'script':
            scripts = Script.objects.filter(
                created_by=user
            ).filter(
                Q(title__icontains=query) | Q(original_script__icontains=query)
            ).order_by('-created_at')[:limit]

            for s in scripts:
                items.append(process_item(s, 'script'))

        # Ordenar todos los resultados por fecha (más reciente primero) y aplicar límite global
        items.sort(key=lambda x: x['created_at'] or '', reverse=True)
        items = items[:limit]

        return {
            'status': 'success',
            'items': items,
            'count': len(items),
            'message': f'Se encontraron {len(items)} resultados para "{query}"'
        }

    except Exception as e:
        logger.error(f"Error en search_library_tool: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Error al buscar en biblioteca: {str(e)}',
            'items': [],
            'count': 0
        }
