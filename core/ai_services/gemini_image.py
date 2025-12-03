"""Cliente para Gemini Image Generation API - Todos los modelos"""
import logging
from typing import Dict, Optional, List
from google import genai
from google.genai import types
from PIL import Image as PILImage
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

# --- Configuración de Modelos de Imagen de Gemini ---

GEMINI_IMAGE_MODELS = {
    # ==================== GEMINI 2.5 FLASH IMAGE ====================
    'gemini-2.5-flash-image': {
        'version': '2.5 Flash (1K Max)',
        'max_images': 3,
        'description': 'Generación rápida y eficiente (hasta 1K)',
        # Dimensiones para 2.5 Flash
        'resolutions': {
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
    },
    
    # ==================== GEMINI 3 PRO IMAGE PREVIEW ====================
    'gemini-3-pro-image-preview': {
        'version': '3.0 Pro Preview (1K Implícito)',
        'max_images': 14,
        'supports_grounding': True,
        'description': 'Generación y edición avanzada (forzada a 1K para evitar error SDK)',
        # Usamos la resolución 1K por defecto del Pro (aunque internamente el modelo soporta más)
        'resolutions': {
            '1:1': {'width': 1024, 'height': 1024, 'tokens': 1210}, 
            '2:3': {'width': 848, 'height': 1264, 'tokens': 1210}, 
            '3:2': {'width': 1264, 'height': 848, 'tokens': 1210}, 
            '3:4': {'width': 896, 'height': 1200, 'tokens': 1210},
            '4:3': {'width': 1200, 'height': 896, 'tokens': 1210},
            '4:5': {'width': 928, 'height': 1152, 'tokens': 1210},
            '5:4': {'width': 1152, 'height': 928, 'tokens': 1210},
            '16:9': {'width': 1376, 'height': 768, 'tokens': 1210}, 
            '9:16': {'width': 768, 'height': 1376, 'tokens': 1210}, 
        }
    }
}


class GeminiImageClient:
    """Cliente para generar imágenes con múltiples modelos de Gemini"""
    
    # Se usa el diccionario centralizado para los modelos
    MODEL_CONFIGS = GEMINI_IMAGE_MODELS
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-image"):
        """
        Inicializa el cliente de Gemini Image
        """
        if model_name not in self.MODEL_CONFIGS:
            raise ValueError(f"Modelo de imagen no soportado: {model_name}. Modelos disponibles: {list(self.MODEL_CONFIGS.keys())}")
            
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = model_name
        self.model_config = self.MODEL_CONFIGS[model_name]
        logger.info(f"[Gemini Image] Cliente inicializado con modelo: {self.model} ({self.model_config['version']})")
    
    
    def generate_image_from_text(
        self,
        prompt: str,
        aspect_ratio: str = '1:1',
        response_modalities: Optional[List[str]] = None,
        enable_grounding: bool = False, # Nuevo para 3 Pro
    ) -> Dict:
        """
        Genera una imagen desde un prompt de texto (text-to-image)
        """
        
        # Validación de aspect ratio (simplificado)
        if aspect_ratio not in self.model_config['resolutions']:
             raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
        
        try:
            logger.info(f"[Gemini Image] Generando imagen text-to-image ({self.model})")
            
            # Construir image_config
            image_config_args = {"aspect_ratio": aspect_ratio}
            
            
            image_config = types.ImageConfig(**image_config_args)
            
            # Construir config
            config_args = {"image_config": image_config}
            if response_modalities:
                config_args["response_modalities"] = response_modalities
            
            # Agregar Grounding (Búsqueda de Google) si está soportado y habilitado
            if enable_grounding and self.model_config.get('supports_grounding'):
                config_args['tools'] = [{"google_search": {}}]
                logger.info("[Gemini Image] Grounding con Búsqueda de Google habilitado.")
            
            config = types.GenerateContentConfig(**config_args)
            
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
        response_modalities: Optional[List[str]] = None,
        enable_grounding: bool = False,
    ) -> Dict:
        """
        Edita una imagen existente con instrucciones de texto (image-to-image)
        """
        
        if aspect_ratio not in self.model_config['resolutions']:
             raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")

        try:
            logger.info(f"[Gemini Image] Generando imagen image-to-image (edición) con {self.model}")
            
            # Cargar imagen con PIL
            input_image = PILImage.open(BytesIO(input_image_data))
            
            # Construir image_config
            image_config_args = {"aspect_ratio": aspect_ratio}
                
            image_config = types.ImageConfig(**image_config_args)
            
            # Construir config
            config_args = {"image_config": image_config}
            if response_modalities:
                config_args["response_modalities"] = response_modalities
            
            if enable_grounding and self.model_config.get('supports_grounding'):
                config_args['tools'] = [{"google_search": {}}]
            
            config = types.GenerateContentConfig(**config_args)
            
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
        response_modalities: Optional[List[str]] = None,
        enable_grounding: bool = False,
    ) -> Dict:
        """
        Crea una imagen compuesta desde múltiples imágenes (composición/transferencia de estilo)
        """
        
        # Validación de límites de imágenes
        if len(input_images_data) > self.model_config['max_images']:
            logger.warning(f"[Gemini Image] El modelo {self.model} soporta hasta {self.model_config['max_images']} imágenes. Se usará el límite.")
            # Nota: La API de Gemini manejará el recorte/límite si se pasan más de 14.
            
        if aspect_ratio not in self.model_config['resolutions']:
             raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
            
        try:
            logger.info(f"[Gemini Image] Generando compuesta ({self.model}). Imágenes: {len(input_images_data)}")
            
            # Cargar imágenes con PIL
            images = [PILImage.open(BytesIO(img_data)) for img_data in input_images_data]
            
            # Construir image_config
            image_config_args = {"aspect_ratio": aspect_ratio}
                
            image_config = types.ImageConfig(**image_config_args)
            
            # Construir config
            config_args = {"image_config": image_config}
            if response_modalities:
                config_args["response_modalities"] = response_modalities
                
            if enable_grounding and self.model_config.get('supports_grounding'):
                config_args['tools'] = [{"google_search": {}}]
            
            config = types.GenerateContentConfig(**config_args)
            
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
        Extrae datos de imagen y texto de la respuesta de Gemini, determinando
        las dimensiones basado en el modelo y el size/ratio.
        """
        result = {
            'image_data': None,
            'text_response': None,
            'width': None,
            'height': None,
            'aspect_ratio': aspect_ratio,
        }
        
        # --- Obtener dimensiones ---
        try:
            resolutions = self.model_config['resolutions']
            
            # Lógica simplificada: Usar el diccionario de resoluciones directamente
            # Ahora resolutions[aspect_ratio] es {width, height, tokens} para AMBOS modelos
            dims = resolutions[aspect_ratio] 

            result['width'] = dims['width']
            result['height'] = dims['height']
        except (KeyError, TypeError):
            logger.warning(f"[Gemini Image] No se encontraron dimensiones exactas para {self.model}/{aspect_ratio}. Usando 1024x1024.")
            result['width'] = 1024
            result['height'] = 1024
        
        # --- Extracción de contenido de la respuesta (se mantiene) ---
        if not response.candidates:
            raise ValueError("Gemini no devolvió candidatos en la respuesta. Contenido bloqueado.")
        
        candidate = response.candidates[0]
        if not candidate.content:
            raise ValueError(f"Gemini bloqueó la generación. Motivo: {candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'desconocido'}")
        
        for part in candidate.content.parts:
            if part.text is not None:
                result['text_response'] = part.text
            elif part.inline_data is not None:
                result['image_data'] = part.inline_data.data
        
        if not result['image_data']:
            raise ValueError("No se recibió imagen en la respuesta de Gemini")
        
        return result
    
    
    # --- Métodos de utilidad (se mantienen igual) ---
    @staticmethod
    def image_bytes_to_base64(image_bytes: bytes) -> str:
        """Convierte bytes de imagen a string base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    @staticmethod
    def base64_to_image_bytes(base64_string: str) -> bytes:
        """Convierte string base64 a bytes de imagen"""
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
    
    @classmethod
    def get_supported_resolutions(cls, model_name: str) -> List[str]:
        """Retorna lista de resoluciones (ELIMINADO - siempre vacío)"""
        return []