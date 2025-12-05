"""
Servicio para validar recursos de HeyGen antes de usar
Evita errores de voz/avatar no encontrados
"""

import logging
from typing import Dict, Optional, List
from django.core.cache import cache

from core.services import APIService, ServiceException, ValidationException

logger = logging.getLogger(__name__)


class VoiceValidator:
    """Valida recursos de HeyGen antes de usar"""
    
    # TTL del caché de validaciones (5 minutos)
    VALIDATION_CACHE_TTL = 300
    
    @staticmethod
    def validate_voice(voice_id: str, force_refresh: bool = False) -> Dict:
        """
        Valida que una voz existe en HeyGen
        
        Args:
            voice_id: ID de la voz a validar
            force_refresh: Si True, fuerza refresh del caché de voces
        
        Returns:
            {
                'valid': bool,
                'voice_id': str,
                'fallback_voice_id': str | None,
                'fallback_voice_name': str | None,
                'message': str,
                'used_fallback': bool
            }
        """
        if not voice_id:
            raise ValidationException('voice_id es requerido')
        
        # Verificar caché de validación
        cache_key = f'voice_validation:{voice_id}'
        if not force_refresh:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Usando validación en caché para voz {voice_id}")
                return cached_result
        
        try:
            # Obtener lista de voces (con refresh si es necesario)
            api_service = APIService()
            voices = api_service.list_voices(use_cache=not force_refresh)
            
            # Buscar la voz en la lista
            voice_ids = []
            voice_map = {}  # voice_id -> voice_data
            
            for voice in voices:
                vid = voice.get('voice_id') or voice.get('id')
                if vid:
                    voice_ids.append(vid)
                    voice_map[vid] = voice
            
            is_valid = voice_id in voice_ids
            
            result = {
                'valid': is_valid,
                'voice_id': voice_id,
                'fallback_voice_id': None,
                'fallback_voice_name': None,
                'message': '',
                'used_fallback': False
            }
            
            if is_valid:
                result['message'] = f'Voz {voice_id} válida'
                logger.info(f"✓ Voz {voice_id} validada correctamente")
            else:
                result['message'] = f'Voz {voice_id} no encontrada en HeyGen'
                logger.warning(f"⚠ Voz {voice_id} no encontrada. Buscando fallback...")
                
                # Buscar fallback: misma lengua/género si es posible
                # Por ahora, usar la primera voz disponible
                if voice_ids:
                    fallback_voice_id = voice_ids[0]
                    fallback_voice = voice_map.get(fallback_voice_id, {})
                    result['fallback_voice_id'] = fallback_voice_id
                    result['fallback_voice_name'] = fallback_voice.get('name', 'Voz por defecto')
                    result['message'] = f'Voz no encontrada. Usando fallback: {result["fallback_voice_name"]}'
                    logger.info(f"✓ Fallback encontrado: {fallback_voice_id} ({result['fallback_voice_name']})")
                else:
                    result['message'] = 'Voz no encontrada y no hay voces disponibles'
                    logger.error(f"❌ No hay voces disponibles para fallback")
            
            # Guardar en caché
            cache.set(cache_key, result, VoiceValidator.VALIDATION_CACHE_TTL)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al validar voz {voice_id}: {e}")
            # En caso de error, asumir que no es válida pero no bloquear
            return {
                'valid': False,
                'voice_id': voice_id,
                'fallback_voice_id': None,
                'fallback_voice_name': None,
                'message': f'Error al validar voz: {str(e)}',
                'used_fallback': False
            }
    
    @staticmethod
    def validate_avatar(avatar_id: str, force_refresh: bool = False) -> Dict:
        """
        Valida que un avatar existe en HeyGen
        
        Args:
            avatar_id: ID del avatar a validar
            force_refresh: Si True, fuerza refresh del caché de avatares
        
        Returns:
            {
                'valid': bool,
                'avatar_id': str,
                'fallback_avatar_id': str | None,
                'fallback_avatar_name': str | None,
                'message': str,
                'used_fallback': bool
            }
        """
        if not avatar_id:
            raise ValidationException('avatar_id es requerido')
        
        # Verificar caché de validación
        cache_key = f'avatar_validation:{avatar_id}'
        if not force_refresh:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Usando validación en caché para avatar {avatar_id}")
                return cached_result
        
        try:
            # Obtener lista de avatares (con refresh si es necesario)
            api_service = APIService()
            avatars = api_service.list_avatars(use_cache=not force_refresh)
            
            # Buscar el avatar en la lista
            avatar_ids = []
            avatar_map = {}  # avatar_id -> avatar_data
            
            for avatar in avatars:
                aid = avatar.get('avatar_id') or avatar.get('id')
                if aid:
                    avatar_ids.append(aid)
                    avatar_map[aid] = avatar
            
            is_valid = avatar_id in avatar_ids
            
            result = {
                'valid': is_valid,
                'avatar_id': avatar_id,
                'fallback_avatar_id': None,
                'fallback_avatar_name': None,
                'message': '',
                'used_fallback': False
            }
            
            if is_valid:
                result['message'] = f'Avatar {avatar_id} válido'
                logger.info(f"✓ Avatar {avatar_id} validado correctamente")
            else:
                result['message'] = f'Avatar {avatar_id} no encontrado en HeyGen'
                logger.warning(f"⚠ Avatar {avatar_id} no encontrado. Buscando fallback...")
                
                # Buscar fallback: mismo género si es posible
                # Por ahora, usar el primer avatar disponible
                if avatar_ids:
                    fallback_avatar_id = avatar_ids[0]
                    fallback_avatar = avatar_map.get(fallback_avatar_id, {})
                    result['fallback_avatar_id'] = fallback_avatar_id
                    result['fallback_avatar_name'] = fallback_avatar.get('name', 'Avatar por defecto')
                    result['message'] = f'Avatar no encontrado. Usando fallback: {result["fallback_avatar_name"]}'
                    logger.info(f"✓ Fallback encontrado: {fallback_avatar_id} ({result['fallback_avatar_name']})")
                else:
                    result['message'] = 'Avatar no encontrado y no hay avatares disponibles'
                    logger.error(f"❌ No hay avatares disponibles para fallback")
            
            # Guardar en caché
            cache.set(cache_key, result, VoiceValidator.VALIDATION_CACHE_TTL)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al validar avatar {avatar_id}: {e}")
            # En caso de error, asumir que no es válida pero no bloquear
            return {
                'valid': False,
                'avatar_id': avatar_id,
                'fallback_avatar_id': None,
                'fallback_avatar_name': None,
                'message': f'Error al validar avatar: {str(e)}',
                'used_fallback': False
            }
    
    @staticmethod
    def get_valid_voice(voice_id: str, script_default_voice_id: Optional[str] = None, 
                       force_refresh: bool = False) -> Dict:
        """
        Obtiene una voz válida, usando fallbacks si es necesario
        
        Args:
            voice_id: ID de la voz a validar
            script_default_voice_id: Voz por defecto del script (si existe)
            force_refresh: Si True, fuerza refresh del caché
        
        Returns:
            {
                'voice_id': str,  # Voz válida a usar
                'voice_name': str,
                'used_fallback': bool,
                'fallback_reason': str
            }
        """
        # Validar voz solicitada
        validation = VoiceValidator.validate_voice(voice_id, force_refresh)
        
        if validation['valid']:
            # Voz válida, usar la solicitada
            voice_data = {
                'voice_id': voice_id,
                'voice_name': None,  # Se puede obtener de la lista si es necesario
                'used_fallback': False,
                'fallback_reason': None
            }
            
            # Intentar obtener nombre de la voz
            try:
                api_service = APIService()
                voices = api_service.list_voices(use_cache=True)
                for voice in voices:
                    vid = voice.get('voice_id') or voice.get('id')
                    if vid == voice_id:
                        voice_data['voice_name'] = voice.get('name', 'Voz desconocida')
                        break
            except Exception as e:
                logger.debug(f"No se pudo obtener nombre de voz {voice_id}: {e}")
            
            return voice_data
        
        # Voz no válida, buscar fallback
        fallback_voice_id = None
        fallback_reason = None
        
        # 1. Intentar voz por defecto del script
        if script_default_voice_id and script_default_voice_id != voice_id:
            script_validation = VoiceValidator.validate_voice(script_default_voice_id, force_refresh)
            if script_validation['valid']:
                fallback_voice_id = script_default_voice_id
                fallback_reason = 'Voz por defecto del script'
                logger.info(f"Usando voz por defecto del script: {script_default_voice_id}")
        
        # 2. Intentar fallback de la validación
        if not fallback_voice_id and validation.get('fallback_voice_id'):
            fallback_voice_id = validation['fallback_voice_id']
            fallback_reason = 'Primera voz disponible'
            logger.info(f"Usando fallback de validación: {fallback_voice_id}")
        
        # 3. Usar voz por defecto del sistema
        if not fallback_voice_id:
            from decouple import config
            system_voice_id = config('ELEVENLABS_DEFAULT_VOICE_ID', default='pFZP5JQG7iQjIQuC4Bku')
            system_validation = VoiceValidator.validate_voice(system_voice_id, force_refresh)
            if system_validation['valid']:
                fallback_voice_id = system_voice_id
                fallback_reason = 'Voz por defecto del sistema'
                logger.info(f"Usando voz por defecto del sistema: {system_voice_id}")
        
        if not fallback_voice_id:
            raise ValidationException(
                f'Voz {voice_id} no válida y no se encontró fallback disponible. '
                f'Por favor, selecciona una voz válida.'
            )
        
        # Obtener nombre de la voz fallback
        fallback_voice_name = validation.get('fallback_voice_name') or 'Voz por defecto'
        try:
            api_service = APIService()
            voices = api_service.list_voices(use_cache=True)
            for voice in voices:
                vid = voice.get('voice_id') or voice.get('id')
                if vid == fallback_voice_id:
                    fallback_voice_name = voice.get('name', fallback_voice_name)
                    break
        except Exception as e:
            logger.debug(f"No se pudo obtener nombre de voz fallback {fallback_voice_id}: {e}")
        
        return {
            'voice_id': fallback_voice_id,
            'voice_name': fallback_voice_name,
            'used_fallback': True,
            'fallback_reason': fallback_reason
        }

