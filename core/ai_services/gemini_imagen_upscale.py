"""Cliente para Google Vertex AI Imagen Upscale API"""
import logging
import json
from typing import Dict, Optional
import requests
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class GeminiImagenUpscaleClient:
    """Cliente para Vertex AI Imagen Upscale (imagen-4.0-upscale-preview)"""
    
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        """
        Inicializa el cliente de Imagen Upscale
        
        Args:
            project_id: ID del proyecto de Google Cloud (si None, se obtiene de settings)
            location: Región del endpoint (us-central1, europe-west4, etc.)
        """
        from django.conf import settings
        
        self.project_id = project_id or getattr(settings, 'GCS_PROJECT_ID', None)
        if not self.project_id:
            raise ValueError("project_id es requerido. Configura GCS_PROJECT_ID en settings.")
        
        self.location = location
        self.base_url = f"https://{location}-aiplatform.googleapis.com/v1"
        self.model_name = "imagen-4.0-upscale-preview"
        
        # Obtener credenciales con los scopes correctos para Vertex AI
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        self.credentials, _ = default(scopes=scopes)
        
        logger.info(f"Cliente Imagen Upscale inicializado: {self.project_id} @ {location}")
        logger.info(f"Modelo: {self.model_name}")
    
    def _get_access_token(self) -> str:
        """Obtiene un access token válido de Google Cloud"""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token
    
    def upscale_image(
        self,
        input_gcs_uri: str,
        output_gcs_directory: str,
        upscale_factor: str = "x4",
        output_mime_type: str = "image/png"
    ) -> Dict:
        """
        Escala una imagen usando Vertex AI Imagen Upscale
        
        Args:
            input_gcs_uri: URI completa de GCS de la imagen de entrada (gs://bucket/path/image.jpg)
            output_gcs_directory: Directorio de GCS donde guardar la imagen escalada (gs://bucket/output/)
            upscale_factor: Factor de escalado ("x2", "x3", "x4")
            output_mime_type: Tipo MIME de salida ("image/png", "image/jpeg")
        
        Returns:
            dict con información del resultado:
            {
                'output_gcs_uri': 'gs://bucket/output/filename.png',
                'status': 'completed',
                ...
            }
        
        Raises:
            Exception: Si falla la petición o el procesamiento
        """
        if upscale_factor not in ["x2", "x3", "x4"]:
            raise ValueError(f"upscale_factor debe ser 'x2', 'x3' o 'x4', recibido: {upscale_factor}")
        
        endpoint = f"{self.base_url}/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}:predict"
        
        headers = {
            'Authorization': f'Bearer {self._get_access_token()}',
            'Content-Type': 'application/json'
        }
        
        # Construir el body según la documentación oficial
        # Asegurar que el directorio termine con /
        if not output_gcs_directory.endswith('/'):
            output_gcs_directory = output_gcs_directory + '/'
        
        # Construir outputOptions (solo mimeType y compressionQuality)
        # storageUri va en el nivel de parameters, NO dentro de outputOptions
        output_options = {
            "mimeType": output_mime_type
        }
        
        # Si es JPEG, agregar compressionQuality (opcional)
        if output_mime_type == "image/jpeg":
            output_options["compressionQuality"] = 95
        
        body = {
            "instances": [
                {
                    "image": {
                        "gcsUri": input_gcs_uri
                    }
                }
            ],
            "parameters": {
                "mode": "upscale",
                "storageUri": output_gcs_directory,  # Directorio de salida (nivel de parameters)
                "upscaleConfig": {
                    "upscaleFactor": upscale_factor
                },
                "outputOptions": output_options  # Solo mimeType y compressionQuality
            }
        }
        
        logger.info(f"Request body: {json.dumps(body, indent=2)}")
        
        logger.info(f"📤 Enviando request de upscale a Vertex AI")
        logger.info(f"   Input: {input_gcs_uri}")
        logger.info(f"   Output directory: {output_gcs_directory}")
        logger.info(f"   Factor: {upscale_factor}")
        
        try:
            response = requests.post(
                endpoint,
                json=body,
                headers=headers,
                timeout=300  # 5 minutos timeout (upscale puede tardar)
            )
            
            logger.info(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Vertex AI devuelve el resultado en predictions[0]
                predictions = result.get('predictions', [])
                if not predictions:
                    raise Exception("No se recibieron predicciones en la respuesta")
                
                prediction = predictions[0]
                
                # El output URI está en la respuesta
                output_gcs_uri = prediction.get('gcsUri') or prediction.get('outputGcsUri')
                
                logger.info(f"✅ Upscale completado exitosamente!")
                logger.info(f"   Output URI: {output_gcs_uri}")
                
                return {
                    'output_gcs_uri': output_gcs_uri,
                    'status': 'completed',
                    'upscale_factor': upscale_factor,
                    'raw_response': result
                }
            else:
                error_msg = self._parse_error(response)
                logger.error(f"❌ Error al hacer upscale: {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión al hacer upscale: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado al hacer upscale: {str(e)}")
            raise
    
    def _parse_error(self, response: requests.Response) -> str:
        """Parsea el error de la respuesta de Vertex AI"""
        try:
            error_data = response.json()
            error_info = error_data.get('error', {})
            message = error_info.get('message', 'Error desconocido')
            code = error_info.get('code', 'UNKNOWN')
            return f"[{code}] {message}"
        except Exception:
            return f"Error HTTP {response.status_code}: {response.text[:500]}"

