"""Cliente para OpenAI Image Generation API - GPT Image models"""
import logging
from typing import Dict, Optional, List
from openai import OpenAI
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

# --- Configuración de Modelos de Imagen de OpenAI GPT Image ---

OPENAI_IMAGE_MODELS = {
    'gpt-image-1': {
        'version': 'GPT Image 1',
        'description': 'Modelo estándar de generación de imágenes de alta calidad',
        'resolutions': {
            '1:1': {'width': 1024, 'height': 1024},
            '16:9': {'width': 1536, 'height': 1024},  # landscape
            '9:16': {'width': 1024, 'height': 1536},  # portrait
        }
    },
    'gpt-image-1.5': {
        'version': 'GPT Image 1.5',
        'description': 'Modelo más avanzado, 4x más rápido que GPT Image 1',
        'resolutions': {
            '1:1': {'width': 1024, 'height': 1024},
            '16:9': {'width': 1536, 'height': 1024},  # landscape
            '9:16': {'width': 1024, 'height': 1536},  # portrait
        }
    },
}


class OpenAIImageClient:
    """Cliente para generar imágenes con modelos GPT Image de OpenAI"""
    
    MODEL_CONFIGS = OPENAI_IMAGE_MODELS
    
    def __init__(self, api_key: str, model_name: str = "gpt-image-1"):
        """
        Inicializa el cliente de OpenAI Image
        
        Args:
            api_key: API key de OpenAI
            model_name: Nombre del modelo ('gpt-image-1' o 'gpt-image-1.5')
        """
        if model_name not in self.MODEL_CONFIGS:
            raise ValueError(f"Modelo {model_name} no configurado en OpenAI Image.")
        
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model = model_name
        self.model_config = self.MODEL_CONFIGS[model_name]
        logger.info(f"[OpenAI Image] Cliente inicializado con modelo: {self.model} ({self.model_config['version']})")
    
    def generate_image_from_text(
        self,
        prompt: str,
        aspect_ratio: str = '1:1',
        size: Optional[str] = None,
        quality: Optional[str] = None,
        format: Optional[str] = None,
        background: Optional[str] = None,
        n: int = 1,
        **kwargs
    ) -> Dict:
        """
        Genera una imagen desde un prompt de texto (text-to-image)
        
        Args:
            prompt: Descripción de la imagen a generar
            aspect_ratio: Aspect ratio ('1:1', '16:9', '9:16')
            size: Tamaño específico ('1024x1024', '1536x1024', '1024x1536', o 'auto')
            quality: Calidad ('low', 'medium', 'high', o 'auto')
            format: Formato de salida ('png', 'jpeg', 'webp')
            background: Fondo ('transparent' u 'opaque')
            n: Número de imágenes a generar (default: 1)
            **kwargs: Parámetros adicionales
        
        Returns:
            Dict con image_data (bytes), width, height, aspect_ratio
        """
        # Validar aspect ratio
        if aspect_ratio not in self.model_config['resolutions']:
            raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
        
        # Obtener dimensiones
        dims = self.model_config['resolutions'][aspect_ratio]
        
        # Construir tamaño si no se proporciona
        if not size:
            size = f"{dims['width']}x{dims['height']}"
        
        try:
            logger.info(f"[OpenAI Image] Generando imagen text-to-image ({self.model})")
            
            # Preparar parámetros
            params = {
                'model': self.model,
                'prompt': prompt,
                'n': n,
                'size': size,
                'response_format': 'b64_json',  # Siempre usar base64 para consistencia
            }
            
            # Agregar parámetros opcionales
            if quality:
                params['quality'] = quality
            if format:
                params['format'] = format
            if background:
                params['background'] = background
            
            # Agregar kwargs adicionales
            params.update(kwargs)
            
            # Generar imagen
            response = self.client.images.generate(**params)
            
            # Extraer la primera imagen (si n=1) o todas
            if n == 1:
                image_base64 = response.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)
                
                result = {
                    'image_data': image_bytes,
                    'width': dims['width'],
                    'height': dims['height'],
                    'aspect_ratio': aspect_ratio,
                }
            else:
                # Múltiples imágenes - retornar la primera por ahora
                # TODO: Considerar retornar todas las imágenes
                image_base64 = response.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)
                
                result = {
                    'image_data': image_bytes,
                    'width': dims['width'],
                    'height': dims['height'],
                    'aspect_ratio': aspect_ratio,
                    'all_images': [base64.b64decode(img.b64_json) for img in response.data],
                }
            
            logger.info(f"[OpenAI Image] ✅ Imagen generada exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"[OpenAI Image] ❌ Error al generar imagen: {str(e)}")
            raise
    
    def generate_image_from_image(
        self,
        prompt: str,
        input_image_data: bytes,
        aspect_ratio: str = '1:1',
        mask_data: Optional[bytes] = None,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        format: Optional[str] = None,
        input_fidelity: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Edita una imagen existente con instrucciones de texto (image-to-image)
        Usa el endpoint de Edits de OpenAI
        
        Args:
            prompt: Instrucciones para editar la imagen
            input_image_data: Bytes de la imagen de entrada
            aspect_ratio: Aspect ratio deseado
            mask_data: Bytes de la máscara (opcional, para inpainting)
            size: Tamaño específico
            quality: Calidad ('low', 'medium', 'high', o 'auto')
            format: Formato de salida ('png', 'jpeg', 'webp')
            input_fidelity: Fidelidad de entrada ('low' o 'high')
            **kwargs: Parámetros adicionales
        
        Returns:
            Dict con image_data (bytes), width, height, aspect_ratio
        """
        # Validar aspect ratio
        if aspect_ratio not in self.model_config['resolutions']:
            raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
        
        # Obtener dimensiones
        dims = self.model_config['resolutions'][aspect_ratio]
        
        # Construir tamaño si no se proporciona
        if not size:
            size = f"{dims['width']}x{dims['height']}"
        
        try:
            logger.info(f"[OpenAI Image] Editando imagen image-to-image ({self.model})")
            
            # Preparar parámetros
            params = {
                'model': self.model,
                'image': BytesIO(input_image_data),
                'prompt': prompt,
                'size': size,
                'response_format': 'b64_json',
            }
            
            # Agregar máscara si se proporciona
            if mask_data:
                params['mask'] = BytesIO(mask_data)
            
            # Agregar parámetros opcionales
            if quality:
                params['quality'] = quality
            if format:
                params['format'] = format
            if input_fidelity:
                params['input_fidelity'] = input_fidelity
            
            # Agregar kwargs adicionales
            params.update(kwargs)
            
            # Editar imagen
            response = self.client.images.edit(**params)
            
            # Extraer imagen
            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)
            
            result = {
                'image_data': image_bytes,
                'width': dims['width'],
                'height': dims['height'],
                'aspect_ratio': aspect_ratio,
            }
            
            logger.info(f"[OpenAI Image] ✅ Imagen editada exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"[OpenAI Image] ❌ Error al editar imagen: {str(e)}")
            raise
    
    def generate_image_from_multiple_images(
        self,
        prompt: str,
        input_images_data: List[bytes],
        aspect_ratio: str = '1:1',
        size: Optional[str] = None,
        quality: Optional[str] = None,
        format: Optional[str] = None,
        input_fidelity: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Crea una imagen compuesta desde múltiples imágenes usando el endpoint de Edits
        Usa múltiples imágenes como referencia
        
        Args:
            prompt: Descripción de la imagen a generar usando las referencias
            input_images_data: Lista de bytes de imágenes de entrada
            aspect_ratio: Aspect ratio deseado
            size: Tamaño específico
            quality: Calidad ('low', 'medium', 'high', o 'auto')
            format: Formato de salida ('png', 'jpeg', 'webp')
            input_fidelity: Fidelidad de entrada ('low' o 'high')
            **kwargs: Parámetros adicionales
        
        Returns:
            Dict con image_data (bytes), width, height, aspect_ratio
        """
        if len(input_images_data) < 1:
            raise ValueError("Se requiere al menos una imagen de entrada para multi-image.")
        
        # Validar aspect ratio
        if aspect_ratio not in self.model_config['resolutions']:
            raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
        
        # Obtener dimensiones
        dims = self.model_config['resolutions'][aspect_ratio]
        
        # Construir tamaño si no se proporciona
        if not size:
            size = f"{dims['width']}x{dims['height']}"
        
        try:
            logger.info(f"[OpenAI Image] Generando imagen compuesta desde {len(input_images_data)} imágenes ({self.model})")
            
            # Preparar parámetros
            # OpenAI Edits acepta múltiples imágenes como lista de BytesIO
            image_files = [BytesIO(img_data) for img_data in input_images_data]
            
            params = {
                'model': self.model,
                'image': image_files,  # Lista de imágenes
                'prompt': prompt,
                'size': size,
                'response_format': 'b64_json',
            }
            
            # Agregar parámetros opcionales
            if quality:
                params['quality'] = quality
            if format:
                params['format'] = format
            if input_fidelity:
                params['input_fidelity'] = input_fidelity
            
            # Agregar kwargs adicionales
            params.update(kwargs)
            
            # Generar imagen compuesta
            response = self.client.images.edit(**params)
            
            # Extraer imagen
            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)
            
            result = {
                'image_data': image_bytes,
                'width': dims['width'],
                'height': dims['height'],
                'aspect_ratio': aspect_ratio,
            }
            
            logger.info(f"[OpenAI Image] ✅ Imagen compuesta generada exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"[OpenAI Image] ❌ Error al generar imagen compuesta: {str(e)}")
            raise
    
    # --- Métodos de utilidad ---
    @staticmethod
    def image_bytes_to_base64(image_bytes: bytes) -> str:
        """Convierte bytes de imagen a string base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    @staticmethod
    def base64_to_image_bytes(base64_string: str) -> bytes:
        """Convierte string base64 a bytes de imagen"""
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        return base64.b64decode(base64_string)
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Retorna lista de modelos soportados"""
        return list(cls.MODEL_CONFIGS.keys())
    
    @classmethod
    def get_supported_aspect_ratios(cls, model_name: str) -> List[str]:
        """Retorna lista de aspect ratios soportados por un modelo"""
        if model_name in cls.MODEL_CONFIGS and 'resolutions' in cls.MODEL_CONFIGS[model_name]:
            return list(cls.MODEL_CONFIGS[model_name]['resolutions'].keys())
        return []
