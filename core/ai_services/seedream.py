"""Cliente para SeaDream Image Generation API - Simulación REST Autocontenida"""
import logging
from typing import Dict, Optional, List
from io import BytesIO
import base64
import requests 

logger = logging.getLogger(__name__)

# --- Configuraciones y Dimensiones (Añadidas/Corregidas) ---

# Dimensiones recomendadas por la documentación de BytePlus/SeaDream
RECOMMENDED_RESOLUTIONS = {
    '4.5': { # Para seedream-4.5new
        '1:1': '2048x2048',
        '16:9': '2560x1440',
        '9:16': '1440x2560',
        '4:3': '2304x1728',
    },
    '3.0-t2i': { # Para seedream-3.0-t2i
        '1:1': '1024x1024',
        '16:9': '1280x720',
        '9:16': '720x1280',
        '4:3': '1152x864',
    },
}

# Configuración de Modelos de Imagen de SeaDream (Integrada)
SEADREAM_IMAGE_MODELS: Dict[str, Dict] = {
    # ==================== SEADREAM 4.5 (T-t-I) ====================
    'seedream-4-5-251128': {
        'version': 'SeeDream 4.5',
        'description': 'Modelo estándar de generación Text-to-Image (T2I)',
        'resolutions': RECOMMENDED_RESOLUTIONS['4.5'],
    },
    # ==================== SEADREAM 3.0 (T-t-I) ====================
    'seedream-3-0-t2i-250415': {
        'version': 'SeeDream 3.0',
        'description': 'Modelo de Text-to-Image (T2I) más rápido',
        'resolutions': RECOMMENDED_RESOLUTIONS['3.0-t2i'],
    },
    # Nota: Los modelos I2I (seededit-3.0-i2i) usarían 'adaptive' en el parámetro 'size'
}


class SeaDreamImageClient:
    """Cliente para generar imágenes con la API de SeaDream (Simulación REST)"""
    
    MODEL_CONFIGS = SEADREAM_IMAGE_MODELS
    # Endpoint de BytePlus que detectaste
    BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3/images/generations" 
    
    def __init__(self, api_key: str, model_name: str = "seedream-4-5-251128"):
        """
        Inicializa el cliente de SeaDream Image.
        """ 
        if model_name not in self.MODEL_CONFIGS:
             raise ValueError(f"Modelo {model_name} no configurado en SeaDream.")
             
        self.api_key = api_key
        # Advertencia: verify=False se utiliza para solucionar problemas de SSL locales. 
        # Es altamente recomendable usar 'verify=True' en producción y solucionar el SSL en el host.
        self.session = requests.Session() 
        self.model = model_name
        self.model_config = self.MODEL_CONFIGS[model_name]
        logger.info(f"[SeaDream Image] Cliente inicializado: {self.model}")
    
    
    def _get_headers(self) -> dict:
        """Retorna los headers para las peticiones de autenticación"""
        # Nota: La autenticación de BytePlus puede ser más compleja (ej. SigV4). 
        # Asumimos 'Bearer' por ahora, pero esto es un punto de posible falla 400/401.
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    
    def generate_image_from_text(
        self,
        prompt: str,
        aspect_ratio: str = '1:1',
        **kwargs 
    ) -> Dict:
        """Genera una imagen desde un prompt de texto (Text-to-Image)."""
        
        # 1. Validación de Aspect Ratio y Obtención de Dimensión
        resolutions = self.model_config.get('resolutions', {})
        if aspect_ratio not in resolutions:
             raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
             
        size_str = resolutions[aspect_ratio] # Ejemplo: '2048x2048'

        # 2. Construcción del Payload (AÑADIDOS: model, size, response_format)
        payload = {
            "model": self.model,         # Clave 'model' requerida por la API
            "prompt": prompt,
            "size": size_str,            # Clave 'size' requerida
            "response_format": "b64_json", # Para obtener la imagen directamente
            "watermark": False,          # Opcional, para evitar marca de agua
            **kwargs 
        }
        
        try:
            logger.info(f"[SeaDream Image] Llamando API Text-to-Image ({self.model}) con size={size_str}")
            
            # Usar verify=False para bypass temporal del SSL local (si se necesita)
            response = self.session.post(self.BASE_URL, headers=self._get_headers(), json=payload, verify=False) 
            response.raise_for_status() 
            api_data = response.json()
            
            result = self._extract_response_data(api_data, aspect_ratio)
            
            logger.info(f"[SeaDream Image] ✅ Imagen generada exitosamente")
            return result
            
        except requests.exceptions.RequestException as e:
            # Captura MaxRetryError, Timeout, y el 400 de raise_for_status()
            error_details = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"[SeaDream Image] ❌ Error de red o API: {error_details}")
            raise ValueError(f"Error en la API de SeaDream: {error_details}")
        except Exception as e:
            logger.error(f"[SeaDream Image] ❌ Error desconocido: {str(e)}")
            raise
    
    
    def generate_image_from_image(
        self,
        prompt: str,
        input_image_data: bytes, 
        aspect_ratio: str = '1:1',
        **kwargs
    ) -> Dict:
        """Edita una imagen existente con instrucciones de texto (Image-to-Image)."""
        
        # Simulación simplificada para I2I, la lógica real requeriría usar 'seededit-3.0-i2i'
        # y manejar el parámetro 'size' con 'adaptive' o dimensiones exactas.
        
        # 1. Validación de Aspect Ratio
        resolutions = self.model_config.get('resolutions', {})
        if aspect_ratio not in resolutions:
             raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
             
        # Para el modelo I2I, si no usas adaptive, el tamaño debe ser específico
        size_str = resolutions[aspect_ratio] 
        
        # Convertir bytes de imagen de entrada a Base64 (formato requerido por la documentación)
        input_image_base64 = self.image_bytes_to_base64(input_image_data)
        
        # Construcción del Payload
        payload = {
            "model": "seededit-3.0-i2i", 
            "prompt": prompt,
            "image": [input_image_base64], # La documentación sugiere que 'image' es un array de strings Base64
            "size": size_str,
            "response_format": "b64_json",
            **kwargs 
        }
        
        try:
            logger.info(f"[SeaDream Image] Llamando API Image-to-Image ({self.model})")
            
            response = self.session.post(self.BASE_URL, headers=self._get_headers(), json=payload, verify=False)
            response.raise_for_status() 
            api_data = response.json()
            
            result = self._extract_response_data(api_data, aspect_ratio)
            
            logger.info(f"[SeaDream Image] ✅ Imagen editada exitosamente")
            return result
            
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"[SeaDream Image] ❌ Error de red o API: {error_details}")
            raise ValueError(f"Error en la API de SeaDream: {error_details}")
        except Exception as e:
            logger.error(f"[SeaDream Image] ❌ Error desconocido: {str(e)}")
            raise
    
    
    def generate_image_from_multiple_images(
        self,
        prompt: str,
        input_images_data: List[bytes],
        aspect_ratio: str = '1:1',
        **kwargs
    ) -> Dict:
        """Crea una imagen compuesta desde múltiples imágenes (Multi-Image Blending)."""
        
        if len(input_images_data) < 2:
            raise ValueError("Se requieren al menos dos imágenes de entrada para 'multi-image'.")
        
        # Convertir todas las imágenes a Base64
        image_base64_array = [self.image_bytes_to_base64(img_data) for img_data in input_images_data]

        resolutions = self.model_config.get('resolutions', RECOMMENDED_RESOLUTIONS['4.5'])
        if aspect_ratio not in resolutions:
             raise ValueError(f"Aspect ratio {aspect_ratio} no válido para {self.model}.")
        size_str = resolutions[aspect_ratio] 

        # El modelo 'seedream-4-5-251128' (o 4.0) soporta multi-image blending
        payload = {
            "model": "seedream-4-5-251128", 
            "prompt": prompt,
            "image": image_base64_array, # Array de strings Base64
            "size": size_str,
            "response_format": "b64_json",
            **kwargs 
        }
        
        try:
            logger.info(f"[SeaDream Image] Llamando API Multi-Image Blending ({self.model})")
            
            response = self.session.post(self.BASE_URL, headers=self._get_headers(), json=payload, verify=False)
            response.raise_for_status() 
            api_data = response.json()
            
            result = self._extract_response_data(api_data, aspect_ratio)
            
            logger.info(f"[SeaDream Image] ✅ Imagen compuesta generada exitosamente")
            return result
            
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"[SeaDream Image] ❌ Error de red o API: {error_details}")
            raise ValueError(f"Error en la API de SeaDream: {error_details}")
        except Exception as e:
            logger.error(f"[SeaDream Image] ❌ Error desconocido: {str(e)}")
            raise
    
    
    def _extract_response_data(self, api_data: Dict, aspect_ratio: str) -> Dict:
        """
        Extrae datos de imagen y texto de la respuesta de SeaDream.
        """
        
        # La documentación muestra que 'data' es un array de objetos Image information object.
        if 'data' not in api_data or not api_data['data']:
             # Si no hay 'data', verifica si hay un error global
             error_obj = api_data.get('error', {})
             if error_obj:
                 raise ValueError(f"Error de la API: {error_obj.get('message', 'Error desconocido')}")
             raise ValueError("Respuesta de API de SeaDream incompleta o vacía.")

        # Tomamos el primer resultado (asumiendo generación de una sola imagen)
        first_data = api_data['data'][0] 
        
        # Extraer Base64 y Prompt
        image_base64 = first_data.get('b64_json') 
        
        # El prompt original debe venir del config del objeto Image, no de la API
        text_response = api_data.get('usage', {}).get('prompt_used') # Intenta obtener el prompt usado
        
        # Si la API devolvió 'size', úsalo, sino calculamos aproximado de la tabla.
        size_str = first_data.get('size')
        if size_str:
            width, height = map(int, size_str.split('x'))
        else:
            # Fallback (asume que la resolución fue la recomendada)
            res_map = self.MODEL_CONFIGS.get(self.model, {}).get('resolutions', {})
            size_str = res_map.get(aspect_ratio, '1024x1024')
            width, height = map(int, size_str.split('x'))


        if not image_base64:
             # Si no hay b64_json, pero hay un error de imagen individual:
             error_details = first_data.get('error', {}).get('message', 'Imagen individual falló.')
             raise ValueError(f"Error de generación (código 400): {error_details}")

        return {
            'image_data': self.base64_to_image_bytes(image_base64),
            'text_response': text_response,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio,
        }
    # --- Métodos de utilidad (se mantienen igual que en Gemini) ---

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