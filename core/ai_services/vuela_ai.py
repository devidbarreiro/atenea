"""
Cliente para Vuela.ai Video Generation API
https://vuela.ai/docs/api (documentación proporcionada)
"""
import requests
import logging
from typing import Dict, List, Optional, Literal
from enum import Enum

logger = logging.getLogger(__name__)


class VuelaMode(Enum):
    """Modos de generación de video"""
    SINGLE_VOICE = 'single_voice'  # Video con una sola voz
    SCENES = 'scenes'  # Video multi-escena con múltiples voces
    AVATAR = 'avatar'  # Video con avatar


class VuelaQualityTier(Enum):
    """Niveles de calidad"""
    BASIC = 'basic'
    PREMIUM = 'premium'


class VuelaAnimationType(Enum):
    """Tipos de animación"""
    MOVING_IMAGE = 'moving_image'  # Efecto Ken Burns
    AI_VIDEO = 'ai_video'  # Animación generada por IA


class VuelaMediaType(Enum):
    """Tipos de media"""
    AI_IMAGE = 'ai_image'  # Imágenes generadas por IA
    GOOGLE_IMAGE = 'google_image'  # Imágenes de Google
    CUSTOM_IMAGE = 'custom_image'  # Imágenes subidas por el usuario


class VuelaVoiceStyle(Enum):
    """Estilos de voz"""
    NARRATIVE = 'narrative'
    EXPRESSIVE = 'expressive'
    DYNAMIC = 'dynamic'


class VuelaAIClient:
    """Cliente para interactuar con Vuela.ai Video Generation API"""
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Vuela.ai
        
        Args:
            api_key: API key (Bearer token) de Vuela.ai
        """
        self.api_key = api_key
        self.base_url = 'https://api.vuela.ai'
        self.session = requests.Session()
        logger.info("VuelaAIClient inicializado")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna los headers para las peticiones"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Realiza una petición a la API de Vuela.ai
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API (sin base_url)
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Respuesta JSON de la API
            
        Raises:
            requests.exceptions.RequestException: Si falla la petición
        """
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update(self._get_headers())
        
        try:
            logger.info(f"Vuela.ai API: {method} {url}")
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=60,  # Los videos pueden tardar
                **kwargs
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Vuela.ai API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise
    
    # ==================
    # VALIDACIÓN
    # ==================
    
    def validate_token(self) -> Dict:
        """
        Valida que el token API esté configurado correctamente
        
        Returns:
            Dict con resultado de validación:
            {
                'valid': bool,
                'message': str,
                ...
            }
        """
        return self._make_request('POST', '/generate/validate-token')
    
    # ==================
    # GENERACIÓN DE VIDEO
    # ==================
    
    def generate_video(
        self,
        mode: VuelaMode,
        video_script: str,
        aspect_ratio: Literal['16:9', '9:16'] = '16:9',
        animation_type: VuelaAnimationType = VuelaAnimationType.MOVING_IMAGE,
        quality_tier: VuelaQualityTier = VuelaQualityTier.PREMIUM,
        language: str = 'es',
        country: str = 'ES',
        # Parámetros de voz
        voice_id: Optional[str] = None,
        voice_style: VuelaVoiceStyle = VuelaVoiceStyle.EXPRESSIVE,
        voice_speed: Literal['standard', 'fast', 'very_fast'] = 'standard',
        voices: Optional[List[Dict[str, str]]] = None,
        # Parámetros de media
        media_type: VuelaMediaType = VuelaMediaType.AI_IMAGE,
        style: Optional[str] = 'photorealistic',
        style_id: Optional[str] = None,
        images_per_minute: int = 8,
        custom_images_urls: Optional[List[str]] = None,
        # Parámetros de avatar
        avatar_id: Optional[str] = None,
        avatar_layout: Optional[Literal['full_screen', 'combined']] = None,
        avatar_layout_style: Optional[str] = None,
        avatar_layout_options: Optional[Dict] = None,
        # Subtítulos
        add_subtitles: bool = False,
        caption_font: Optional[str] = 'Roboto',
        caption_alignment: Optional[str] = 'bottom',
        subtitle_highlight_color: Optional[str] = None,
        subtitle_stroke_width: int = 0,
        subtitle_highlight_mode: Optional[str] = None,
        caption_font_url: Optional[str] = None,
        # Música de fondo
        add_background_music: bool = False,
        background_music_id: Optional[str] = None
    ) -> Dict:
        """
        Genera un video con Vuela.ai
        
        Args:
            mode: Modo de generación (single_voice, scenes, avatar)
            video_script: Guión del video (usar \n para saltos de línea)
            aspect_ratio: Relación de aspecto ('16:9' o '9:16')
            animation_type: Tipo de animación
            quality_tier: Nivel de calidad
            language: Código de idioma (2 caracteres)
            country: Código de país (2 caracteres)
            
            voice_id: ID de voz (requerido para single_voice y avatar)
            voice_style: Estilo de voz
            voice_speed: Velocidad de narración
            voices: Lista de voces para modo scenes: [{'character': 'NAME', 'voice_id': 'ID'}]
            
            media_type: Tipo de medio (ai_image, google_image, custom_image)
            style: Estilo visual para ai_image
            style_id: ID de estilo personalizado
            images_per_minute: Imágenes por minuto (8-40)
            custom_images_urls: URLs de imágenes personalizadas
            
            avatar_id: ID del avatar (requerido para modo avatar)
            avatar_layout: Disposición del avatar
            avatar_layout_style: Estilo de disposición
            avatar_layout_options: Opciones adicionales
            
            add_subtitles: Si se deben añadir subtítulos
            caption_font: Fuente para subtítulos
            caption_alignment: Alineación de subtítulos
            subtitle_highlight_color: Color de resaltado
            subtitle_stroke_width: Grosor del contorno
            subtitle_highlight_mode: Modo de resaltado
            caption_font_url: URL de fuente personalizada
            
            add_background_music: Si se debe añadir música de fondo
            background_music_id: ID de la pista de música
            
        Returns:
            Dict con información del video generado:
            {
                'status': str,
                'video_id': str,
                'message': str,
                ...
            }
        """
        # Construir payload base
        payload = {
            'mode': mode.value,
            'video_script': video_script,
            'aspect_ratio': aspect_ratio,
            'animation_type': animation_type.value,
            'quality_tier': quality_tier.value,
            'language': language,
            'country': country
        }
        
        # Configuración de voz
        if mode in [VuelaMode.SINGLE_VOICE, VuelaMode.AVATAR]:
            if not voice_id:
                raise ValueError(f"voice_id es requerido para modo {mode.value}")
            payload['voice_id'] = voice_id
            payload['voice_style'] = voice_style.value
            payload['voice_speed'] = voice_speed
        elif mode == VuelaMode.SCENES:
            if not voices or len(voices) == 0:
                raise ValueError("voices es requerido para modo scenes")
            if len(voices) > 8:
                raise ValueError("Máximo 8 personajes permitidos")
            payload['voices'] = voices
        
        # Configuración de media
        if mode != VuelaMode.AVATAR or (mode == VuelaMode.AVATAR and avatar_layout == 'combined'):
            payload['media_type'] = media_type.value
            
            if media_type == VuelaMediaType.AI_IMAGE:
                if style == 'custom' and not style_id:
                    raise ValueError("style_id es requerido cuando style es 'custom'")
                payload['style'] = style
                if style_id:
                    payload['style_id'] = style_id
                if media_type != VuelaMediaType.CUSTOM_IMAGE:
                    payload['images_per_minute'] = images_per_minute
            elif media_type == VuelaMediaType.CUSTOM_IMAGE:
                if not custom_images_urls:
                    raise ValueError("custom_images_urls es requerido para custom_image")
                payload['custom_images_urls'] = custom_images_urls
        
        # Configuración de avatar
        if mode == VuelaMode.AVATAR:
            if not avatar_id:
                raise ValueError("avatar_id es requerido para modo avatar")
            if not avatar_layout:
                raise ValueError("avatar_layout es requerido para modo avatar")
            
            payload['avatar_id'] = avatar_id
            payload['avatar_layout'] = avatar_layout
            
            if avatar_layout == 'combined':
                if not avatar_layout_style:
                    raise ValueError("avatar_layout_style es requerido para layout combined")
                payload['avatar_layout_style'] = avatar_layout_style
            
            if avatar_layout_style == 'presentation' and avatar_layout_options:
                payload['avatar_layout_options'] = avatar_layout_options
        
        # Subtítulos
        if add_subtitles:
            payload['add_subtitles'] = True
            payload['caption_font'] = caption_font
            payload['caption_alignment'] = caption_alignment
            
            if caption_font == 'custom' and caption_font_url:
                payload['caption_font_url'] = caption_font_url
            
            if subtitle_highlight_color:
                payload['subtitle_highlight_color'] = subtitle_highlight_color
            
            payload['subtitle_stroke_width'] = subtitle_stroke_width
            
            if subtitle_highlight_mode:
                payload['subtitle_highlight_mode'] = subtitle_highlight_mode
        
        # Música de fondo
        if add_background_music:
            if not background_music_id:
                raise ValueError("background_music_id es requerido cuando add_background_music es True")
            payload['add_background_music'] = True
            payload['background_music_id'] = background_music_id
        
        return self._make_request('POST', '/generate/video', json=payload)
    
    # ==================
    # LISTAR Y OBTENER VIDEOS
    # ==================
    
    def list_videos(
        self,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None
    ) -> Dict:
        """
        Lista los videos generados
        
        Args:
            page: Número de página
            limit: Número de videos por página
            search: Término de búsqueda
            
        Returns:
            Dict con lista de videos y metadata de paginación
        """
        params = {
            'page': page,
            'limit': limit
        }
        
        if search:
            params['search'] = search
        
        return self._make_request('GET', '/my-videos', params=params)
    
    def get_video_details(self, video_id: str) -> Dict:
        """
        Obtiene detalles de un video específico
        
        Args:
            video_id: ID del video
            
        Returns:
            Dict con detalles del video:
            {
                'video_id': str,
                'status': str,  # 'creating', 'completed', 'failed'
                'video_url': str,  # URL del video completado
                ...
            }
        """
        return self._make_request('GET', f'/my-videos/{video_id}')
    
    # ==================
    # UTILIDADES
    # ==================
    
    def format_script_for_scenes(
        self,
        scenes: List[Dict[str, str]]
    ) -> str:
        """
        Formatea un guión para el modo 'scenes' de Vuela.ai
        
        Args:
            scenes: Lista de escenas con formato:
            [
                {'character': 'Personaje1', 'text': 'Texto de la escena'},
                {'character': 'Personaje2', 'text': 'Texto de la escena'},
                ...
            ]
            
        Returns:
            String formateado para Vuela.ai:
            [characters]
            Personaje1, Personaje2
            [end]
            
            [scene: Personaje1]
            Texto de la escena
            [end]
            
            [scene: Personaje2]
            Texto de la escena
            [end]
        """
        # Extraer personajes únicos
        characters = list(set([scene['character'] for scene in scenes]))
        
        # Construir guión
        script_parts = []
        
        # Bloque de personajes
        script_parts.append('[characters]')
        script_parts.append(', '.join(characters))
        script_parts.append('[end]')
        script_parts.append('')
        
        # Bloques de escenas
        for scene in scenes:
            script_parts.append(f"[scene: {scene['character']}]")
            script_parts.append(scene['text'])
            script_parts.append('[end]')
            script_parts.append('')
        
        return '\n'.join(script_parts)

