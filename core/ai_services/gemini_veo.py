"""Cliente para Gemini Veo 2 API (Vertex AI)"""
import logging
from typing import Dict, Optional
import requests
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class GeminiVeoClient:
    """Cliente para Gemini Veo 2 (Vertex AI Video Generation)"""
    
    def __init__(self, api_key: str = None, project_id: str = "proeduca-472312", location: str = "us-central1", model_name: str = "veo-2.0-generate-001"):
        """
        Inicializa el cliente de Veo 2
        
        Args:
            api_key: No se usa, mantiene compatibilidad con la interfaz
            project_id: ID del proyecto de Google Cloud
            location: Región del endpoint (us-central1, europe-west4, etc.)
            model_name: Modelo a usar (veo-2.0-generate-001 o veo-2.0-generate-exp)
        """
        self.project_id = project_id
        self.location = location
        self.base_url = f"https://{location}-aiplatform.googleapis.com/v1"
        self.model_name = model_name
        
        # Obtener credenciales con los scopes correctos para Vertex AI
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        self.credentials, _ = default(scopes=scopes)
        
        logger.info(f"Cliente Veo 2 inicializado: {project_id} @ {location}")
        logger.info(f"Modelo: {model_name}")
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
        duration: int = 8,
        aspect_ratio: str = "16:9",
        sample_count: int = 1,
        negative_prompt: str = None,
        enhance_prompt: bool = True,
        person_generation: str = "allow_adult",
        compression_quality: str = "optimized",
        seed: int = None,
        storage_uri: str = None,
        # Funcionalidades avanzadas (Fase 2)
        input_image_gcs_uri: str = None,
        input_image_base64: str = None,
        input_image_mime_type: str = "image/jpeg",
        reference_images: list = None,  # [{gcs_uri/base64, reference_type: asset/style, mime_type}]
        **kwargs
    ) -> dict:
        """
        Genera un video usando Gemini Veo 2
        
        Args:
            prompt: Descripción del video a generar
            title: Título del video (para referencia local)
            duration: Duración en segundos (5-8 para Veo 2, default: 8)
            aspect_ratio: Relación de aspecto ("16:9", "9:16", "1:1")
            sample_count: Número de videos a generar (1-4)
            negative_prompt: Descripción de lo que NO quieres en el video
            enhance_prompt: Usar Gemini para mejorar el prompt (default: True)
            person_generation: "allow_adult" (default), "dont_allow"
            compression_quality: "optimized" (default), "lossless"
            seed: Seed para reproducibilidad (0-4294967295)
            storage_uri: URI de GCS donde guardar (ej: gs://bucket/path/)
            
            # Funcionalidades avanzadas (Fase 2):
            input_image_gcs_uri: URI de GCS de imagen inicial para imagen-a-video
            input_image_base64: String base64 de imagen inicial (alternativa a gcs_uri)
            input_image_mime_type: Tipo MIME de la imagen ("image/jpeg" o "image/png")
            reference_images: Lista de imágenes de referencia para consistencia
                             Formato: [{"gcs_uri": "...", "reference_type": "asset/style", "mime_type": "..."}]
                             Máximo: 3 imágenes "asset" o 1 imagen "style"
                             Solo disponible en veo-2.0-generate-exp
        
        Returns:
            dict con 'video_id' (operation name) y otros metadatos
        """
        try:
            logger.info(f"Generando video con Gemini Veo 2: {title}")
            logger.info(f"Prompt: {prompt[:100]}...")
            logger.info(f"Duración: {duration}s, Aspect Ratio: {aspect_ratio}")
            logger.info(f"Sample Count: {sample_count}, Quality: {compression_quality}")
            
            # Endpoint para predictLongRunning
            endpoint = (
                f"{self.base_url}/projects/{self.project_id}/"
                f"locations/{self.location}/publishers/google/"
                f"models/{self.model_name}:predictLongRunning"
            )
            
            # Preparar el payload según la documentación de Vertex AI
            instance = {
                "prompt": prompt
            }
            
            # Fase 2: Agregar imagen inicial si se proporciona (imagen-a-video)
            if input_image_gcs_uri or input_image_base64:
                image_data = {
                    "mimeType": input_image_mime_type
                }
                
                if input_image_gcs_uri:
                    image_data["gcsUri"] = input_image_gcs_uri
                    logger.info(f"🎨 Imagen-a-Video: {input_image_gcs_uri}")
                elif input_image_base64:
                    image_data["bytesBase64Encoded"] = input_image_base64
                    logger.info(f"🎨 Imagen-a-Video: imagen base64 ({len(input_image_base64)} chars)")
                
                instance["image"] = image_data
            
            # Fase 2: Agregar imágenes de referencia si se proporcionan
            if reference_images and len(reference_images) > 0:
                # IMPORTANTE: referenceImages requiere duración de 8 segundos (validado en formulario)
                if duration != 8:
                    logger.warning(f"⚠️  Imágenes de referencia con duración {duration}s (debería ser 8s)")
                
                ref_images_payload = []
                for idx, ref_img in enumerate(reference_images):
                    ref_image_obj = {
                        "image": {
                            "mimeType": ref_img.get("mime_type", "image/jpeg")
                        },
                        "referenceType": ref_img.get("reference_type", "asset")
                    }
                    
                    if ref_img.get("gcs_uri"):
                        ref_image_obj["image"]["gcsUri"] = ref_img["gcs_uri"]
                    elif ref_img.get("base64"):
                        ref_image_obj["image"]["bytesBase64Encoded"] = ref_img["base64"]
                    
                    ref_images_payload.append(ref_image_obj)
                
                instance["referenceImages"] = ref_images_payload
                logger.info(f"🎭 Imágenes de referencia: {len(ref_images_payload)} imagen(es)")
                for idx, ref in enumerate(reference_images):
                    logger.info(f"   Ref {idx + 1}: tipo={ref.get('reference_type', 'asset')}")
            
            payload = {
                "instances": [instance],
                "parameters": {
                    "durationSeconds": duration,
                    "aspectRatio": aspect_ratio,
                    "sampleCount": sample_count,
                    "personGeneration": person_generation,
                    "compressionQuality": compression_quality,
                    "enhancePrompt": enhance_prompt
                }
            }
            
            # Agregar parámetros opcionales si están presentes
            if negative_prompt:
                payload["parameters"]["negativePrompt"] = negative_prompt
                logger.info(f"Negative prompt: {negative_prompt[:100]}...")
            
            if seed is not None:
                payload["parameters"]["seed"] = seed
                logger.info(f"Seed: {seed}")
            
            if storage_uri:
                payload["parameters"]["storageUri"] = storage_uri
                logger.info(f"Storage URI: {storage_uri}")
            
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
                # Parsear el error de Google
                error_msg = response.text
                error_data = None
                
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_detail = error_data['error']
                        error_code = error_detail.get('code', response.status_code)
                        error_message = error_detail.get('message', error_msg)
                        
                        # Detectar errores específicos de contenido sensible
                        if 'sensitive words' in error_message.lower() or 'responsible ai' in error_message.lower():
                            logger.error(f"🚫 Contenido bloqueado por filtro de IA Responsable")
                            logger.error(f"   Mensaje: {error_message}")
                            raise ValueError(
                                f"❌ Tu prompt fue bloqueado por el filtro de contenido de Google.\n\n"
                                f"Motivo: {error_message}\n\n"
                                f"💡 Sugerencias:\n"
                                f"- Evita nombres de personas famosas o marcas\n"
                                f"- Reformula para ser más descriptivo y menos específico\n"
                                f"- Evita contenido violento, sexual o controversial\n"
                                f"- Usa términos artísticos y técnicos\n\n"
                                f"Si crees que es un error, contacta a Google con el código de soporte en los logs."
                            )
                        
                        error_msg = f"Error {error_code}: {error_message}"
                except:
                    pass
                
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
                        all_video_urls = []
                        
                        if videos and len(videos) > 0:
                            # Veo devuelve un array de videos con gcsUri o bytesBase64Encoded
                            for idx, video in enumerate(videos):
                                url = video.get('gcsUri') or video.get('bytesBase64Encoded')
                                if url:
                                    all_video_urls.append({
                                        'index': idx,
                                        'url': url,
                                        'mime_type': video.get('mimeType', 'video/mp4')
                                    })
                            
                            # El primer video es el principal
                            if all_video_urls:
                                video_url = all_video_urls[0]['url']
                        
                        logger.info(f"✅ Video completado!")
                        logger.info(f"   Videos generados: {len(all_video_urls)}, Filtrados: {rai_filtered_count}")
                        if len(all_video_urls) > 1:
                            logger.info(f"   📹 Multi-generación: {len(all_video_urls)} videos disponibles")
                        
                        return {
                            'status': 'completed',
                            'video_url': video_url,  # Primer video (compatibilidad)
                            'all_video_urls': all_video_urls,  # TODOS los videos
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

