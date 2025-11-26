"""Cliente para Gemini Veo API (Vertex AI) - Todos los modelos"""
import logging
from typing import Dict, Optional, List
import requests
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Modelos disponibles de Veo
VEO_MODELS = {
    # Veo 2.0
    'veo-2.0-generate-001': {
        'version': '2.0',
        'duration_range': (5, 8),
        'supports_audio': False,
        'supports_resolution': False,
        'supports_reference_images': False,
        'supports_last_frame': True,
        'supports_video_extension': True,
        'supports_mask': False,
        'description': 'Veo 2.0 - Modelo base estable'
    },
    'veo-2.0-generate-exp': {
        'version': '2.0',
        'duration_range': (5, 8),
        'supports_audio': False,
        'supports_resolution': False,
        'supports_reference_images': True,  # Asset y Style
        'supports_last_frame': False,
        'supports_video_extension': False,
        'supports_mask': False,
        'description': 'Veo 2.0 Experimental - Soporta imágenes de referencia'
    },
    'veo-2.0-generate-preview': {
        'version': '2.0',
        'duration_range': (5, 8),
        'supports_audio': False,
        'supports_resolution': False,
        'supports_reference_images': False,
        'supports_last_frame': False,
        'supports_video_extension': False,
        'supports_mask': True,
        'description': 'Veo 2.0 Preview - Soporta máscaras para edición'
    },
    
    # Veo 3.0
    'veo-3.0-generate-001': {
        'version': '3.0',
        'duration_range': (4, 8),
        'duration_options': [4, 6, 8],
        'supports_audio': True,
        'supports_resolution': True,  # 720p, 1080p
        'supports_reference_images': False,
        'supports_last_frame': False,
        'supports_video_extension': False,
        'supports_mask': False,
        'supports_resize_mode': True,
        'description': 'Veo 3.0 - Generación con audio y alta resolución'
    },
    'veo-3.0-fast-generate-001': {
        'version': '3.0',
        'duration_range': (4, 8),
        'duration_options': [4, 6, 8],
        'supports_audio': True,
        'supports_resolution': True,
        'supports_reference_images': False,
        'supports_last_frame': False,
        'supports_video_extension': False,
        'supports_mask': False,
        'supports_resize_mode': True,
        'description': 'Veo 3.0 Fast - Generación rápida con audio'
    },
    'veo-3.0-generate-preview': {
        'version': '3.0',
        'duration_range': (4, 8),
        'duration_options': [4, 6, 8],
        'supports_audio': True,
        'supports_resolution': True,
        'supports_reference_images': False,
        'supports_last_frame': True,
        'supports_video_extension': True,
        'supports_mask': False,
        'supports_resize_mode': True,
        'description': 'Veo 3.0 Preview - Con extensión de video'
    },
    'veo-3.0-fast-generate-preview': {
        'version': '3.0',
        'duration_range': (4, 8),
        'duration_options': [4, 6, 8],
        'supports_audio': True,
        'supports_resolution': True,
        'supports_reference_images': False,
        'supports_last_frame': False,
        'supports_video_extension': False,
        'supports_mask': False,
        'supports_resize_mode': True,
        'description': 'Veo 3.0 Fast Preview - Rápido con audio'
    },
    
    # Veo 3.1
    'veo-3.1-generate-preview': {
        'version': '3.1',
        'duration_range': (4, 8),
        'duration_options': [4, 6, 8],
        'supports_audio': True,
        'supports_resolution': True,
        'supports_reference_images': True,  # Solo Asset (no Style)
        'supports_last_frame': True,
        'supports_video_extension': False,
        'supports_mask': False,
        'supports_resize_mode': True,
        'description': 'Veo 3.1 Preview - Última versión con imágenes de referencia'
    },
    'veo-3.1-fast-generate-preview': {
        'version': '3.1',
        'duration_range': (4, 8),
        'duration_options': [4, 6, 8],
        'supports_audio': True,
        'supports_resolution': True,
        'supports_reference_images': True,  # Solo Asset (no Style)
        'supports_last_frame': True,
        'supports_video_extension': False,
        'supports_mask': False,
        'supports_resize_mode': True,
        'description': 'Veo 3.1 Fast Preview - Rápido con todas las características'
    }
}


class GeminiVeoClient:
    """Cliente para Gemini Veo (Vertex AI Video Generation) - Todos los modelos"""
    
    def __init__(self, api_key: str = None, project_id: str = "proeduca-472312", location: str = "us-central1", model_name: str = "veo-3.1-generate-preview"):
        """
        Inicializa el cliente de Veo
        
        Args:
            api_key: No se usa, mantiene compatibilidad con la interfaz
            project_id: ID del proyecto de Google Cloud
            location: Región del endpoint (us-central1, europe-west4, etc.)
            model_name: Modelo a usar (ver VEO_MODELS)
        """
        if model_name not in VEO_MODELS:
            raise ValueError(f"Modelo no soportado: {model_name}. Modelos disponibles: {list(VEO_MODELS.keys())}")
        
        self.project_id = project_id
        self.location = location
        self.base_url = f"https://{location}-aiplatform.googleapis.com/v1"
        self.model_name = model_name
        self.model_config = VEO_MODELS[model_name]
        
        # Obtener credenciales con los scopes correctos para Vertex AI
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        self.credentials, _ = default(scopes=scopes)
        
        logger.info(f"Cliente Veo inicializado: {project_id} @ {location}")
        logger.info(f"Modelo: {model_name} - {self.model_config['description']}")
        logger.info(f"Scopes configurados: {scopes}")
    
    def _get_access_token(self) -> str:
        """Obtiene un access token válido de Google Cloud"""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token
    
    def _validate_parameters(
        self, 
        duration: int, 
        reference_images: List[Dict], 
        generate_audio: bool,
        last_frame_gcs_uri: str,
        last_frame_base64: str,
        video_gcs_uri: str,
        video_base64: str,
        mask_gcs_uri: str,
        mask_base64: str
    ):
        """Valida parámetros según el modelo seleccionado"""
        
        # Validar que duration no sea None
        if duration is None:
            raise ValueError("La duración es requerida y no puede ser None")
        
        # Asegurar que duration sea int
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            raise ValueError(f"Duración inválida: {duration}")
        
        # Validar duración
        min_dur, max_dur = self.model_config['duration_range']
        if duration < min_dur or duration > max_dur:
            raise ValueError(
                f"Duración {duration}s no válida para {self.model_name}. "
                f"Rango permitido: {min_dur}-{max_dur}s"
            )
        
        # Para modelos Veo 3, validar opciones específicas
        if self.model_config['version'] in ['3.0', '3.1']:
            duration_options = self.model_config.get('duration_options', [])
            if duration_options and duration not in duration_options:
                raise ValueError(
                    f"Duración {duration}s no válida para {self.model_name}. "
                    f"Opciones: {duration_options}"
                )
        
        # Validar reference images
        if reference_images and len(reference_images) > 0:
            if not self.model_config['supports_reference_images']:
                raise ValueError(
                    f"El modelo {self.model_name} no soporta imágenes de referencia. "
                    f"Usa veo-2.0-generate-exp o veo-3.1-*"
                )
            
            # Validar tipo de referencia según modelo
            if self.model_config['version'] == '3.1':
                for ref_img in reference_images:
                    if ref_img.get('reference_type') == 'style':
                        raise ValueError(
                            f"Veo 3.1 no soporta imágenes de estilo (style). "
                            f"Solo soporta 'asset'. Usa veo-2.0-generate-exp para imágenes de estilo."
                        )
            
            # La duración debe ser 8 segundos con reference images
            if duration != 8:
                raise ValueError(
                    f"Cuando usas imágenes de referencia, la duración debe ser 8 segundos. "
                    f"Duración actual: {duration}s"
                )
        
        # Validar lastFrame
        if (last_frame_gcs_uri or last_frame_base64):
            if not self.model_config['supports_last_frame']:
                raise ValueError(
                    f"El modelo {self.model_name} no soporta lastFrame. "
                    f"Modelos compatibles: veo-2.0-generate-001, veo-3.0-generate-preview, veo-3.1-*"
                )
        
        # Validar video extension
        if (video_gcs_uri or video_base64):
            if not self.model_config['supports_video_extension']:
                raise ValueError(
                    f"El modelo {self.model_name} no soporta extensión de video. "
                    f"Modelos compatibles: veo-2.0-generate-001, veo-3.0-generate-preview"
                )
        
        # Validar mask
        if (mask_gcs_uri or mask_base64):
            if not self.model_config['supports_mask']:
                raise ValueError(
                    f"El modelo {self.model_name} no soporta máscaras. "
                    f"Usa veo-2.0-generate-preview"
                )
    
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
        # Image-to-Video
        input_image_gcs_uri: str = None,
        input_image_base64: str = None,
        input_image_mime_type: str = "image/jpeg",
        # Reference Images (Veo 2.0-exp, Veo 3.1)
        reference_images: List[Dict] = None,  # [{gcs_uri/base64, reference_type: asset/style, mime_type}]
        # Veo 3 Features
        generate_audio: bool = None,  # Required for Veo 3
        resolution: str = "720p",  # "720p" or "1080p" (Veo 3 only)
        resize_mode: str = "pad",  # "pad" or "crop" (Veo 3 image-to-video only)
        # Advanced Features
        last_frame_gcs_uri: str = None,  # Fill-in-the-blank (algunos modelos)
        last_frame_base64: str = None,
        last_frame_mime_type: str = "image/jpeg",
        video_gcs_uri: str = None,  # Video extension (algunos modelos)
        video_base64: str = None,
        video_mime_type: str = "video/mp4",
        mask_gcs_uri: str = None,  # Video editing with mask (veo-2.0-generate-preview)
        mask_base64: str = None,
        mask_mime_type: str = "image/png",
        mask_mode: str = "background",  # "background" or "foreground"
        **kwargs
    ) -> dict:
        """
        Genera un video usando Gemini Veo (todos los modelos)
        
        Args:
            prompt: Descripción del video a generar (requerido para text-to-video)
            title: Título del video (para referencia local)
            duration: Duración en segundos
                     - Veo 2: 5-8 segundos
                     - Veo 3/3.1: 4, 6 u 8 segundos
            aspect_ratio: Relación de aspecto ("16:9", "9:16")
            sample_count: Número de videos a generar (1-4)
            negative_prompt: Descripción de lo que NO quieres en el video
            enhance_prompt: Usar Gemini para mejorar el prompt (default: True)
            person_generation: "allow_adult" (default), "dont_allow"
            compression_quality: "optimized" (default), "lossless"
            seed: Seed para reproducibilidad (0-4294967295)
            storage_uri: URI de GCS donde guardar (ej: gs://bucket/path/)
            
            # Image-to-Video:
            input_image_gcs_uri: URI de GCS de imagen inicial
            input_image_base64: String base64 de imagen inicial
            input_image_mime_type: Tipo MIME ("image/jpeg", "image/png", "image/webp")
            
            # Reference Images (Veo 2.0-exp, Veo 3.1):
            reference_images: Lista de hasta 3 imágenes de referencia
                             Formato: [{"gcs_uri"/"base64": "...", "reference_type": "asset"/"style", "mime_type": "..."}]
                             - Veo 2.0-exp: soporta "asset" y "style" (max 1 style)
                             - Veo 3.1: solo "asset" (no "style")
                             - Duración debe ser 8 segundos
            
            # Veo 3/3.1 Features:
            generate_audio: Generar audio para el video (requerido para Veo 3)
            resolution: "720p" o "1080p" (solo Veo 3)
            resize_mode: "pad" o "crop" (solo Veo 3 image-to-video)
            
            # Advanced Features:
            last_frame_gcs_uri/base64: Imagen del último frame (fill-in-the-blank)
                                      Soportado: veo-2.0-generate-001, veo-3.0-generate-preview, veo-3.1-*
            video_gcs_uri/base64: Video para extensión
                                 Soportado: veo-2.0-generate-001, veo-3.0-generate-preview
            mask_gcs_uri/base64: Máscara para edición de video
                                Soportado: veo-2.0-generate-preview
            mask_mode: "background" o "foreground"
        
        Returns:
            dict con 'video_id' (operation name) y otros metadatos
        """
        try:
            # Validaciones según el modelo
            self._validate_parameters(
                duration, reference_images, generate_audio, last_frame_gcs_uri, 
                last_frame_base64, video_gcs_uri, video_base64, mask_gcs_uri, mask_base64
            )
            
            logger.info(f"🎬 Generando video con {self.model_name}: {title}")
            logger.info(f"   Modelo: {self.model_config['description']}")
            logger.info(f"   Prompt: {prompt[:100]}...")
            logger.info(f"   Duración: {duration}s, Aspect Ratio: {aspect_ratio}")
            logger.info(f"   Sample Count: {sample_count}, Quality: {compression_quality}")
            
            # Endpoint para predictLongRunning
            endpoint = (
                f"{self.base_url}/projects/{self.project_id}/"
                f"locations/{self.location}/publishers/google/"
                f"models/{self.model_name}:predictLongRunning"
            )
            
            # Preparar instancia
            instance = {
                "prompt": prompt
            }
            
            # Image-to-Video
            if input_image_gcs_uri or input_image_base64:
                image_data = {
                    "mimeType": input_image_mime_type
                }
                
                if input_image_gcs_uri:
                    image_data["gcsUri"] = input_image_gcs_uri
                    logger.info(f"   🎨 Imagen-a-Video: {input_image_gcs_uri}")
                elif input_image_base64:
                    image_data["bytesBase64Encoded"] = input_image_base64
                    logger.info(f"   🎨 Imagen-a-Video: imagen base64 ({len(input_image_base64)} chars)")
                
                instance["image"] = image_data
            
            # Reference Images
            if reference_images and len(reference_images) > 0:
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
                logger.info(f"   🎭 Imágenes de referencia: {len(ref_images_payload)} imagen(es)")
                for idx, ref in enumerate(reference_images):
                    logger.info(f"      Ref {idx + 1}: tipo={ref.get('reference_type', 'asset')}")
            
            # Last Frame (fill-in-the-blank)
            if last_frame_gcs_uri or last_frame_base64:
                last_frame_data = {
                    "mimeType": last_frame_mime_type
                }
                
                if last_frame_gcs_uri:
                    last_frame_data["gcsUri"] = last_frame_gcs_uri
                    logger.info(f"   🖼️  Last Frame: {last_frame_gcs_uri}")
                elif last_frame_base64:
                    last_frame_data["bytesBase64Encoded"] = last_frame_base64
                    logger.info(f"   🖼️  Last Frame: base64 ({len(last_frame_base64)} chars)")
                
                instance["lastFrame"] = last_frame_data
            
            # Video Extension
            if video_gcs_uri or video_base64:
                video_data = {
                    "mimeType": video_mime_type
                }
                
                if video_gcs_uri:
                    video_data["gcsUri"] = video_gcs_uri
                    logger.info(f"   📹 Video Extension: {video_gcs_uri}")
                elif video_base64:
                    video_data["bytesBase64Encoded"] = video_base64
                    logger.info(f"   📹 Video Extension: base64 ({len(video_base64)} chars)")
                
                instance["video"] = video_data
            
            # Mask (video editing)
            if mask_gcs_uri or mask_base64:
                mask_data = {
                    "mimeType": mask_mime_type,
                    "maskMode": mask_mode
                }
                
                if mask_gcs_uri:
                    mask_data["gcsUri"] = mask_gcs_uri
                    logger.info(f"   🎭 Mask: {mask_gcs_uri} (mode: {mask_mode})")
                elif mask_base64:
                    mask_data["bytesBase64Encoded"] = mask_base64
                    logger.info(f"   🎭 Mask: base64 (mode: {mask_mode})")
                
                instance["mask"] = mask_data
            
            # Preparar parámetros
            parameters = {
                "durationSeconds": duration,
                "aspectRatio": aspect_ratio,
                "sampleCount": sample_count,
                "personGeneration": person_generation,
                "compressionQuality": compression_quality,
                "enhancePrompt": enhance_prompt
            }
            
            # Veo 3 specific parameters
            if self.model_config['version'] in ['3.0', '3.1']:
                if generate_audio is None:
                    generate_audio = True  # Default para Veo 3
                parameters["generateAudio"] = generate_audio
                logger.info(f"   🔊 Generate Audio: {generate_audio}")
                
                if self.model_config['supports_resolution']:
                    parameters["resolution"] = resolution
                    logger.info(f"   📺 Resolution: {resolution}")
                
                if self.model_config['supports_resize_mode'] and (input_image_gcs_uri or input_image_base64):
                    parameters["resizeMode"] = resize_mode
                    logger.info(f"   ↔️  Resize Mode: {resize_mode}")
            
            # Agregar parámetros opcionales
            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt
                logger.info(f"   ❌ Negative prompt: {negative_prompt[:100]}...")
            
            if seed is not None:
                parameters["seed"] = seed
                logger.info(f"   🎲 Seed: {seed}")
            
            if storage_uri:
                parameters["storageUri"] = storage_uri
                logger.info(f"   💾 Storage URI: {storage_uri}")
            
            payload = {
                "instances": [instance],
                "parameters": parameters
            }
            
            # Headers con autenticación
            headers = {
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            logger.info(f"📤 Enviando request a: {endpoint}")
            
            # Hacer la request
            response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
            
            logger.info(f"📥 Response status: {response.status_code}")
            logger.info(f"   Response body: {response.text[:500]}")
            
            # Manejar respuesta
            if response.status_code == 200:
                response_data = response.json()
                
                # La respuesta contiene el nombre de la operación long-running
                operation_name = response_data.get('name')
                
                result = {
                    'status': 'processing',
                    'video_id': operation_name,
                    'title': title,
                    'prompt': prompt,
                    'operation_name': operation_name,
                    'metadata': {
                        'duration': duration,
                        'aspect_ratio': aspect_ratio,
                        'model': self.model_name,
                        'model_version': self.model_config['version'],
                        'generate_audio': generate_audio if self.model_config['version'] in ['3.0', '3.1'] else False,
                        'resolution': resolution if self.model_config['supports_resolution'] else None,
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

