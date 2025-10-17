"""Cliente para Gemini Veo 2 API (Vertex AI)"""
import logging
from typing import Dict, Optional
import requests
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class GeminiVeoClient:
    """Cliente para Gemini Veo 2 (Vertex AI Video Generation)"""
    
    def __init__(self, api_key: str = None, project_id: str = "proeduca-472312", location: str = "us-central1"):
        """
        Inicializa el cliente de Veo 2
        
        Args:
            api_key: No se usa, mantiene compatibilidad con la interfaz
            project_id: ID del proyecto de Google Cloud
            location: Región del endpoint (us-central1, europe-west4, etc.)
        """
        self.project_id = project_id
        self.location = location
        self.base_url = f"https://{location}-aiplatform.googleapis.com/v1"
        self.model_name = "veo-2.0-generate-001"
        
        # Obtener credenciales con los scopes correctos para Vertex AI
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        self.credentials, _ = default(scopes=scopes)
        
        logger.info(f"Cliente Veo 2 inicializado: {project_id} @ {location}")
        logger.info(f"Scopes configurados: {scopes}")
    
    def _get_access_token(self) -> str:
        """Obtiene un access token válido de Google Cloud"""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token
    
    def generate_video(
        self,
        prompt: str,
        title: str = "Untitled Video",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        **kwargs
    ) -> dict:
        """
        Genera un video usando Gemini Veo 2
        
        Args:
            prompt: Descripción del video a generar
            title: Título del video (para referencia local)
            duration: Duración en segundos (5-8)
            aspect_ratio: Relación de aspecto (16:9, 9:16, 1:1)
        
        Returns:
            dict con 'video_id' (operation name) y otros metadatos
        """
        try:
            logger.info(f"Generando video con Gemini Veo 2: {title}")
            logger.info(f"Prompt: {prompt[:100]}...")
            logger.info(f"Duración: {duration}s, Aspect Ratio: {aspect_ratio}")
            
            # Endpoint para predictLongRunning
            endpoint = (
                f"{self.base_url}/projects/{self.project_id}/"
                f"locations/{self.location}/publishers/google/"
                f"models/{self.model_name}:predictLongRunning"
            )
            
            # Preparar el payload según la documentación de Vertex AI
            payload = {
                "instances": [
                    {
                        "prompt": prompt
                    }
                ],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": aspect_ratio,
                    "personGeneration": "allow_all"
                }
            }
            
            # Headers con autenticación
            headers = {
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            logger.info(f"Enviando request a: {endpoint}")
            
            # Hacer la request
            response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:500]}")
            
            # Manejar respuesta
            if response.status_code == 200:
                response_data = response.json()
                
                # La respuesta contiene el nombre de la operación long-running
                operation_name = response_data.get('name')
                
                result = {
                    'status': 'processing',
                    'video_id': operation_name,  # Este es el ID que usaremos para consultar
                    'title': title,
                    'prompt': prompt,
                    'operation_name': operation_name,
                    'metadata': {
                        'duration': duration,
                        'aspect_ratio': aspect_ratio,
                        'model': 'veo-2.0-generate-001',
                        'response': response_data
                    }
                }
                
                logger.info(f"✅ Video iniciado. Operation: {operation_name}")
                return result
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                logger.error(f"❌ Error en Veo 2: {error_msg}")
                raise Exception(error_msg)
            
        except Exception as e:
            logger.error(f"❌ Error al generar video con Veo 2: {str(e)}")
            raise
    
    def get_video_status(self, operation_name: str) -> dict:
        """
        Obtiene el estado de una operación long-running
        
        Args:
            operation_name: Nombre de la operación retornado por generate_video
        
        Returns:
            dict con el estado y datos del video si está completo
        """
        try:
            logger.info(f"Consultando estado de operación: {operation_name}")
            
            # Endpoint especial de Veo para consultar operaciones
            # Usa fetchPredictOperation en lugar del endpoint estándar de operations
            endpoint = (
                f"{self.base_url}/projects/{self.project_id}/"
                f"locations/{self.location}/publishers/google/"
                f"models/{self.model_name}:fetchPredictOperation"
            )
            
            # El operation_name completo va en el body, no en la URL
            payload = {
                "operationName": operation_name
            }
            
            logger.info(f"Endpoint de consulta: {endpoint}")
            logger.info(f"Operation name: {operation_name}")
            
            headers = {
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                operation_data = response.json()
                
                logger.info(f"Response data: {str(operation_data)[:500]}")
                
                # Verificar si la operación está completa
                done = operation_data.get('done', False)
                
                if done:
                    # Operación completada
                    if 'error' in operation_data:
                        # Error en la generación
                        error = operation_data['error']
                        logger.error(f"❌ Video falló: {error}")
                        return {
                            'status': 'failed',
                            'error': error.get('message', 'Unknown error'),
                            'operation_data': operation_data
                        }
                    else:
                        # Éxito - extraer URL del video según la estructura de Veo
                        response_data = operation_data.get('response', {})
                        videos = response_data.get('videos', [])
                        rai_filtered_count = response_data.get('raiMediaFilteredCount', 0)
                        
                        video_url = None
                        if videos and len(videos) > 0:
                            # Veo devuelve un array de videos con gcsUri o bytesBase64Encoded
                            first_video = videos[0]
                            video_url = first_video.get('gcsUri') or first_video.get('bytesBase64Encoded')
                        
                        logger.info(f"✅ Video completado! URL: {video_url}")
                        logger.info(f"Videos generados: {len(videos)}, Filtrados: {rai_filtered_count}")
                        
                        return {
                            'status': 'completed',
                            'video_url': video_url,
                            'operation_data': operation_data,
                            'videos': videos,
                            'rai_filtered_count': rai_filtered_count
                        }
                else:
                    # Aún procesando
                    metadata = operation_data.get('metadata', {})
                    logger.info(f"⏳ Video aún procesando... Metadata: {metadata}")
                    
                    return {
                        'status': 'processing',
                        'metadata': metadata,
                        'operation_data': operation_data
                    }
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                logger.error(f"❌ Error consultando estado: {error_msg}")
                return {
                    'status': 'error',
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Error al consultar estado: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_video_url(self, operation_name: str) -> Optional[str]:
        """Obtiene la URL del video si está disponible"""
        try:
            status = self.get_video_status(operation_name)
            return status.get('video_url')
        except Exception as e:
            logger.error(f"Error al obtener URL: {str(e)}")
            return None

