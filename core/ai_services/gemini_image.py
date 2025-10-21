"""Cliente para Gemini Image Generation API"""
import logging
from typing import Dict, Optional, List
from google import genai
from google.genai import types
from PIL import Image as PILImage
from io import BytesIO
import base64

logger = logging.getLogger(__name__)


class GeminiImageClient:
    """Cliente para generar imágenes con Gemini 2.5 Flash Image"""
    
    # Aspect ratios disponibles según la documentación
    ASPECT_RATIOS = {
        '1:1': {'width': 1024, 'height': 1024, 'tokens': 1290},
        '2:3': {'width': 832, 'height': 1248, 'tokens': 1290},
        '3:2': {'width': 1248, 'height': 832, 'tokens': 1290},
        '3:4': {'width': 864, 'height': 1184, 'tokens': 1290},
        '4:3': {'width': 1184, 'height': 864, 'tokens': 1290},
        '4:5': {'width': 896, 'height': 1152, 'tokens': 1290},
        '5:4': {'width': 1152, 'height': 896, 'tokens': 1290},
        '9:16': {'width': 768, 'height': 1344, 'tokens': 1290},
        '16:9': {'width': 1344, 'height': 768, 'tokens': 1290},
        '21:9': {'width': 1536, 'height': 672, 'tokens': 1290},
    }
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente de Gemini Image
        
        Args:
            api_key: API key de Google Gemini
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash-image"
        logger.info(f"[Gemini Image] Cliente inicializado con modelo: {self.model}")
    
    def generate_image_from_text(
        self,
        prompt: str,
        aspect_ratio: str = '1:1',
        response_modalities: Optional[List[str]] = None
    ) -> Dict:
        """
        Genera una imagen desde un prompt de texto (text-to-image)
        
        Args:
            prompt: Descripción textual de la imagen a generar
            aspect_ratio: Relación de aspecto (default: '1:1')
            response_modalities: Lista de modalidades ['Text', 'Image'] o ['Image']
        
        Returns:
            Dict con 'image_data' (bytes), 'text_response' (opcional), 'width', 'height'
        
        Raises:
            Exception si falla la generación
        """
        try:
            logger.info(f"[Gemini Image] Generando imagen text-to-image")
            logger.info(f"[Gemini Image] Prompt: {prompt[:100]}...")
            logger.info(f"[Gemini Image] Aspect ratio: {aspect_ratio}")
            
            # Configurar la solicitud
            config = types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            )
            
            # Agregar response_modalities si se especifica
            if response_modalities:
                config.response_modalities = response_modalities
            
            # Generar contenido
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=config
            )
            
            # Extraer resultados
            result = self._extract_response_data(response, aspect_ratio)
            
            logger.info(f"[Gemini Image] ✅ Imagen generada exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"[Gemini Image] ❌ Error al generar imagen: {str(e)}")
            raise
    
    def generate_image_from_image(
        self,
        prompt: str,
        input_image_data: bytes,
        aspect_ratio: str = '1:1',
        response_modalities: Optional[List[str]] = None
    ) -> Dict:
        """
        Edita una imagen existente con instrucciones de texto (image-to-image)
        
        Args:
            prompt: Instrucciones de edición (ej: "Add a wizard hat to the cat")
            input_image_data: Bytes de la imagen de entrada
            aspect_ratio: Relación de aspecto (default: '1:1')
            response_modalities: Lista de modalidades
        
        Returns:
            Dict con 'image_data' (bytes), 'text_response' (opcional), 'width', 'height'
        """
        try:
            logger.info(f"[Gemini Image] Generando imagen image-to-image (edición)")
            logger.info(f"[Gemini Image] Prompt: {prompt[:100]}...")
            logger.info(f"[Gemini Image] Aspect ratio: {aspect_ratio}")
            
            # Cargar imagen con PIL
            input_image = PILImage.open(BytesIO(input_image_data))
            
            # Configurar la solicitud
            config = types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            )
            
            if response_modalities:
                config.response_modalities = response_modalities
            
            # Generar contenido con imagen y prompt
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, input_image],
                config=config
            )
            
            # Extraer resultados
            result = self._extract_response_data(response, aspect_ratio)
            
            logger.info(f"[Gemini Image] ✅ Imagen editada exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"[Gemini Image] ❌ Error al editar imagen: {str(e)}")
            raise
    
    def generate_image_from_multiple_images(
        self,
        prompt: str,
        input_images_data: List[bytes],
        aspect_ratio: str = '1:1',
        response_modalities: Optional[List[str]] = None
    ) -> Dict:
        """
        Crea una imagen compuesta desde múltiples imágenes (composición/transferencia de estilo)
        
        Args:
            prompt: Instrucciones de composición (ej: "Combine these images into one scene")
            input_images_data: Lista de bytes de imágenes de entrada
            aspect_ratio: Relación de aspecto
            response_modalities: Lista de modalidades
        
        Returns:
            Dict con 'image_data' (bytes), 'text_response' (opcional), 'width', 'height'
        """
        try:
            logger.info(f"[Gemini Image] Generando imagen desde múltiples imágenes")
            logger.info(f"[Gemini Image] Número de imágenes: {len(input_images_data)}")
            logger.info(f"[Gemini Image] Prompt: {prompt[:100]}...")
            
            # Cargar imágenes con PIL
            images = []
            for i, img_data in enumerate(input_images_data):
                image = PILImage.open(BytesIO(img_data))
                images.append(image)
                logger.info(f"[Gemini Image] Imagen {i+1}: {image.size}")
            
            # Configurar la solicitud
            config = types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            )
            
            if response_modalities:
                config.response_modalities = response_modalities
            
            # Construir contenido: prompt + imágenes
            contents = [prompt] + images
            
            # Generar contenido
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            
            # Extraer resultados
            result = self._extract_response_data(response, aspect_ratio)
            
            logger.info(f"[Gemini Image] ✅ Imagen compuesta generada exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"[Gemini Image] ❌ Error al generar imagen compuesta: {str(e)}")
            raise
    
    def _extract_response_data(self, response, aspect_ratio: str) -> Dict:
        """
        Extrae datos de imagen y texto de la respuesta de Gemini
        
        Args:
            response: Respuesta de la API
            aspect_ratio: Aspect ratio usado
        
        Returns:
            Dict con image_data, text_response, width, height
        """
        result = {
            'image_data': None,
            'text_response': None,
            'width': None,
            'height': None,
            'aspect_ratio': aspect_ratio,
        }
        
        # Obtener dimensiones del aspect ratio
        if aspect_ratio in self.ASPECT_RATIOS:
            result['width'] = self.ASPECT_RATIOS[aspect_ratio]['width']
            result['height'] = self.ASPECT_RATIOS[aspect_ratio]['height']
        
        # Extraer partes de la respuesta
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                result['text_response'] = part.text
                logger.info(f"[Gemini Image] Texto de respuesta: {part.text[:100]}...")
            elif part.inline_data is not None:
                result['image_data'] = part.inline_data.data
                logger.info(f"[Gemini Image] Imagen generada: {len(part.inline_data.data)} bytes")
        
        if not result['image_data']:
            raise ValueError("No se recibió imagen en la respuesta de Gemini")
        
        return result
    
    @staticmethod
    def image_bytes_to_base64(image_bytes: bytes) -> str:
        """Convierte bytes de imagen a string base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    @staticmethod
    def base64_to_image_bytes(base64_string: str) -> bytes:
        """Convierte string base64 a bytes de imagen"""
        return base64.b64decode(base64_string)
    
    @staticmethod
    def validate_aspect_ratio(aspect_ratio: str) -> bool:
        """Valida si el aspect ratio es soportado"""
        return aspect_ratio in GeminiImageClient.ASPECT_RATIOS
    
    @classmethod
    def get_supported_aspect_ratios(cls) -> List[str]:
        """Retorna lista de aspect ratios soportados"""
        return list(cls.ASPECT_RATIOS.keys())
    
    @classmethod
    def get_aspect_ratio_dimensions(cls, aspect_ratio: str) -> Dict[str, int]:
        """Retorna dimensiones para un aspect ratio"""
        if aspect_ratio in cls.ASPECT_RATIOS:
            return {
                'width': cls.ASPECT_RATIOS[aspect_ratio]['width'],
                'height': cls.ASPECT_RATIOS[aspect_ratio]['height'],
            }
        return {'width': 1024, 'height': 1024}  # Default 1:1

