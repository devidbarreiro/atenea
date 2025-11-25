"""
Tool para listar avatares de HeyGen
Permite filtrar por género, letra inicial del nombre, etc.
"""

from langchain.tools import tool
from typing import Dict, List, Optional
from django.contrib.auth.models import User

from core.services import APIService, ValidationException


@tool
def list_avatars_tool(
    user_id: int = None,
    gender: Optional[str] = None,  # 'male', 'female', None para todos
    starts_with: Optional[str] = None,  # Letra o texto inicial del nombre
    limit: Optional[int] = None  # Límite de resultados
) -> Dict:
    """
    Lista avatares disponibles de HeyGen con opciones de filtrado.
    
    Args:
        user_id: ID del usuario (requerido para validación)
        gender: Filtrar por género ('male', 'female') o None para todos
        starts_with: Filtrar avatares cuyo nombre empiece con esta letra/texto
        limit: Número máximo de resultados a retornar
    
    Returns:
        Dict con:
            - status: 'success' o 'error'
            - avatars: Lista de avatares con avatar_id, avatar_name, gender, etc.
            - count: Número total de avatares encontrados
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
        
        # Listar avatares usando el servicio existente (con caché)
        avatars = api_service.list_avatars(use_cache=True)
        
        # Aplicar filtros
        filtered_avatars = avatars
        
        if gender:
            gender_lower = gender.lower()
            filtered_avatars = [
                a for a in filtered_avatars
                if a.get('gender', '').lower() == gender_lower
            ]
        
        if starts_with:
            starts_with_lower = starts_with.lower()
            filtered_avatars = [
                a for a in filtered_avatars
                if a.get('avatar_name', '').lower().startswith(starts_with_lower)
            ]
        
        # Aplicar límite
        if limit and limit > 0:
            filtered_avatars = filtered_avatars[:limit]
        
        # Formatear respuesta
        result = {
            'status': 'success',
            'avatars': filtered_avatars,
            'count': len(filtered_avatars),
            'total_available': len(avatars),
            'message': f'Se encontraron {len(filtered_avatars)} avatares'
        }
        
        if gender:
            result['message'] += f' (género: {gender})'
        if starts_with:
            result['message'] += f' (empiezan con: {starts_with})'
        
        return result

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error al listar avatares: {str(e)}',
            'avatars': [],
            'count': 0
        }

