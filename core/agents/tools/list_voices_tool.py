"""
Tool para listar voces de HeyGen
Permite filtrar por género, idioma, etc.
"""

from langchain.tools import tool
from typing import Dict, List, Optional
from django.contrib.auth.models import User

from core.services import APIService, ValidationException


@tool
def list_voices_tool(
    user_id: int = None,
    gender: Optional[str] = None,  # 'male', 'female', None para todos
    language: Optional[str] = None,  # Código de idioma (ej: 'es', 'en')
    limit: Optional[int] = None  # Límite de resultados
) -> Dict:
    """
    Lista voces disponibles de HeyGen con opciones de filtrado.
    
    Args:
        user_id: ID del usuario (requerido para validación)
        gender: Filtrar por género ('male', 'female') o None para todos
        language: Filtrar por idioma (código de idioma como 'es', 'en')
        limit: Número máximo de resultados a retornar
    
    Returns:
        Dict con:
            - status: 'success' o 'error'
            - voices: Lista de voces con voice_id, voice_name, gender, language, etc.
            - count: Número total de voces encontradas
            - message: Mensaje descriptivo
    """
    try:
        if not user_id:
            return {'status': 'error', 'message': 'user_id es requerido'}

        # Validar usuario
        try:
            User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {'status': 'error', 'message': f'Usuario {user_id} no encontrado'}

        # Obtener servicio
        api_service = APIService()
        
        # Listar voces usando el servicio existente (con caché)
        voices = api_service.list_voices(use_cache=True)
        
        # Aplicar filtros
        filtered_voices = voices
        
        if gender:
            gender_lower = gender.lower()
            filtered_voices = [
                v for v in filtered_voices
                if v.get('gender', '').lower() == gender_lower
            ]
        
        if language:
            language_lower = language.lower()
            filtered_voices = [
                v for v in filtered_voices
                if v.get('language', '').lower() == language_lower or
                   v.get('language_code', '').lower() == language_lower
            ]
        
        # Aplicar límite
        if limit and limit > 0:
            filtered_voices = filtered_voices[:limit]
        
        # Formatear respuesta
        result = {
            'status': 'success',
            'voices': filtered_voices,
            'count': len(filtered_voices),
            'total_available': len(voices),
            'message': f'Se encontraron {len(filtered_voices)} voces'
        }
        
        if gender:
            result['message'] += f' (género: {gender})'
        if language:
            result['message'] += f' (idioma: {language})'
        
        return result

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error al listar voces: {str(e)}',
            'voices': [],
            'count': 0
        }

