"""Cliente para Google Lyria Music Generation API (Vertex AI)"""
import logging
from typing import Dict, Optional, List
import requests
import base64
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

# Importar deep-translator para traducción obligatoria
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    logger.error("❌ deep-translator NO está instalado. Instala con: pip install deep-translator")
    raise ImportError(
        "deep-translator es requerido para Google Lyria. "
        "Instala con: pip install deep-translator"
    )

# Modelos disponibles de Lyria
LYRIA_MODELS = {
    'lyria-002': {
        'version': '2.0',
        'description': 'Lyria 2 - Generación de música instrumental de alta calidad',
        'duration_seconds': 30,  # Fijo: siempre genera clips de 30 segundos
        'sample_rate': 48000,  # 48 kHz
        'format': 'wav',
        'instrumental_only': True,
        'language': 'en-us',  # Solo inglés de EE.UU. para prompts
    },
}


class GoogleLyriaClient:
    """Cliente para Google Lyria Music Generation (Vertex AI)"""
    
    def __init__(self, project_id: str = None, location: str = "us-central1", model_name: str = "lyria-002"):
        """
        Inicializa el cliente de Lyria
        
        Args:
            project_id: ID del proyecto de Google Cloud (si None, se obtiene de settings)
            location: Región del endpoint (us-central1, europe-west4, etc.)
            model_name: Modelo a usar (actualmente solo 'lyria-002')
        """
        from django.conf import settings
        
        if model_name not in LYRIA_MODELS:
            raise ValueError(f"Modelo no soportado: {model_name}. Modelos disponibles: {list(LYRIA_MODELS.keys())}")
        
        # Verificar que deep-translator esté disponible
        if not TRANSLATOR_AVAILABLE:
            raise ImportError(
                "deep-translator es requerido para Google Lyria. "
                "Instala con: pip install deep-translator"
            )
        
        self.project_id = project_id or getattr(settings, 'GCS_PROJECT_ID', None)
        if not self.project_id:
            raise ValueError("project_id es requerido. Configura GCS_PROJECT_ID en settings.")
        
        self.location = location
        self.base_url = f"https://{location}-aiplatform.googleapis.com/v1"
        self.model_name = model_name
        self.model_config = LYRIA_MODELS[model_name]
        
        # No inicializar traductor aquí, se crea por cada traducción
        pass
        
        # Obtener credenciales con los scopes correctos para Vertex AI
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        self.credentials, _ = default(scopes=scopes)
        
        logger.info(f"Cliente Lyria inicializado: {self.project_id} @ {location}")
        logger.info(f"Modelo: {model_name} - {self.model_config['description']}")
    
    def _get_access_token(self) -> str:
        """Obtiene un access token válido de Google Cloud"""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token
    
    def _translate_to_english(self, text: str) -> str:
        """
        Traduce el texto al inglés de forma obligatoria.
        Lyria solo acepta prompts en inglés (en-us).
        
        Args:
            text: Texto a traducir
            
        Returns:
            Texto traducido al inglés
            
        Raises:
            ValueError: Si no se puede traducir el texto
        """
        if not text or not text.strip():
            raise ValueError("El texto a traducir no puede estar vacío")
        
        try:
            # Crear instancia del traductor (deep-translator usa Google Translate API gratuita)
            translator = GoogleTranslator(source='auto', target='en')
            
            logger.info(f"🌐 Traduciendo prompt a inglés: {text[:50]}...")
            
            # Traducir al inglés de forma obligatoria
            translated_text = translator.translate(text)
            
            if not translated_text or not translated_text.strip():
                raise ValueError(f"No se pudo traducir el texto: '{text}' (resultado vacío)")
            
            # Si el texto traducido es igual al original (o muy similar), probablemente ya estaba en inglés
            if translated_text.strip().lower() == text.strip().lower():
                logger.info(f"✓ Prompt ya estaba en inglés: {text[:50]}...")
                return text
            
            logger.info(f"✓ Prompt traducido exitosamente: {translated_text[:100]}...")
            return translated_text
            
        except Exception as e:
            logger.error(f"❌ Error al traducir prompt: {e}", exc_info=True)
            raise ValueError(
                f"No se pudo traducir el prompt al inglés. "
                f"Error: {str(e)}. "
                f"Asegúrate de que deep-translator esté instalado correctamente: pip install deep-translator"
            ) from e
    
    def generate_music(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        sample_count: Optional[int] = None,
    ) -> Dict:
        """
        Genera música usando Google Lyria
        
        Args:
            prompt: Descripción de texto del audio a generar (se traducirá automáticamente al inglés).
                   Ejemplo: "Una canción acústica folk tranquila con una melodía suave de guitarra y cuerdas suaves."
            negative_prompt: Opcional. Descripción de lo que se debe excluir del audio generado.
                           Ejemplo: "voces, tempo lento"
            seed: Opcional. Semilla para generación determinista (0-4294967295).
                  No se puede usar con sample_count en la misma solicitud.
            sample_count: Opcional. Número de muestras de audio a generar (default: 1).
                         No se puede usar con seed en la misma solicitud.
        
        Returns:
            dict con:
                - 'audio_samples': Lista de dicts con 'audio_data' (bytes) y 'mime_type'
                - 'model': Nombre del modelo usado
                - 'model_display_name': Nombre visible del modelo
                - 'deployed_model_id': ID del modelo desplegado (si aplica)
        
        Raises:
            ValueError: Si los parámetros son inválidos
            Exception: Si la generación falla
        """
        try:
            # Validar parámetros mutuamente excluyentes
            if seed is not None and sample_count is not None:
                raise ValueError("No se puede usar 'seed' y 'sample_count' en la misma solicitud. Usa uno u otro.")
            
            # Validar prompt
            if not prompt or not prompt.strip():
                raise ValueError("El prompt es obligatorio y no puede estar vacío")
            
            # Validar seed si se proporciona
            if seed is not None:
                if not isinstance(seed, int) or seed < 0:
                    raise ValueError("seed debe ser un entero no negativo")
            
            # Validar sample_count si se proporciona
            if sample_count is not None:
                if not isinstance(sample_count, int) or sample_count < 1:
                    raise ValueError("sample_count debe ser un entero mayor a 0")
            
            # TRADUCIR PROMPT AL INGLÉS DE FORMA OBLIGATORIA
            original_prompt = prompt
            prompt = self._translate_to_english(prompt)
            
            # Traducir negative_prompt si existe
            original_negative_prompt = negative_prompt
            if negative_prompt:
                negative_prompt = self._translate_to_english(negative_prompt)
            
            logger.info(f"🎵 Generando música con {self.model_name}")
            if prompt != original_prompt:
                logger.info(f"   Prompt original: {original_prompt[:100]}{'...' if len(original_prompt) > 100 else ''}")
            logger.info(f"   Prompt (en): {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            if negative_prompt:
                if negative_prompt != original_negative_prompt:
                    logger.info(f"   Negative prompt original: {original_negative_prompt[:100]}{'...' if len(original_negative_prompt) > 100 else ''}")
                logger.info(f"   Negative prompt (en): {negative_prompt[:100]}{'...' if len(negative_prompt) > 100 else ''}")
            if seed is not None:
                logger.info(f"   Seed: {seed}")
            if sample_count is not None:
                logger.info(f"   Sample count: {sample_count}")
            
            # Endpoint para predict (síncrono)
            endpoint = (
                f"{self.base_url}/projects/{self.project_id}/"
                f"locations/{self.location}/publishers/google/"
                f"models/{self.model_name}:predict"
            )
            
            # Preparar instancia
            instance = {
                "prompt": prompt
            }
            
            # Agregar parámetros opcionales a la instancia
            if negative_prompt:
                instance["negative_prompt"] = negative_prompt
            
            if seed is not None:
                instance["seed"] = seed
            
            # Preparar parámetros
            parameters = {}
            
            # sample_count va en parameters, no en instances
            if sample_count is not None:
                parameters["sample_count"] = sample_count
            
            payload = {
                "instances": [instance],
                "parameters": parameters
            }
            
            # Log del payload (sin mostrar datos sensibles completos)
            logger.debug(f"📤 Payload: instances={len(payload['instances'])}, parameters={payload['parameters']}")
            logger.debug(f"📤 Instance keys: {list(instance.keys())}")
            
            # Headers con autenticación
            headers = {
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            logger.info(f"📤 Enviando request a: {endpoint}")
            
            # Hacer la request (síncrona)
            response = requests.post(endpoint, json=payload, headers=headers, timeout=120)
            
            logger.info(f"📥 Response status: {response.status_code}")
            logger.debug(f"📥 Response headers: {dict(response.headers)}")
            logger.debug(f"📥 Response text (first 500 chars): {response.text[:500]}")
            
            # Manejar respuesta
            if response.status_code == 200:
                response_data = response.json()
                
                # Log detallado de la respuesta para debugging
                logger.info(f"📥 Response data keys: {list(response_data.keys())}")
                logger.debug(f"📥 Full response: {str(response_data)[:1000]}")  # Primeros 1000 chars
                
                # Verificar si hay errores en la respuesta
                if 'error' in response_data:
                    error_detail = response_data['error']
                    error_code = error_detail.get('code', 'UNKNOWN')
                    error_message = error_detail.get('message', 'Unknown error')
                    raise ValueError(f"Error en respuesta de API: {error_code} - {error_message}")
                
                # Extraer predicciones
                predictions = response_data.get('predictions', [])
                
                if not predictions:
                    logger.error(f"❌ No hay predictions en la respuesta. Response keys: {list(response_data.keys())}")
                    logger.error(f"❌ Response data: {str(response_data)[:500]}")
                    raise ValueError("La API no devolvió predicciones de audio")
                
                logger.info(f"📊 Número de predicciones recibidas: {len(predictions)}")
                
                # Decodificar audio de cada predicción
                audio_samples = []
                for idx, prediction in enumerate(predictions):
                    logger.debug(f"📊 Predicción {idx + 1} keys: {list(prediction.keys()) if isinstance(prediction, dict) else 'Not a dict'}")
                    
                    # Intentar diferentes nombres de campo posibles
                    audio_content_b64 = (
                        prediction.get('audioContent') or 
                        prediction.get('audio_content') or
                        prediction.get('bytesBase64Encoded') or
                        prediction.get('bytes_base64_encoded')
                    )
                    mime_type = prediction.get('mimeType') or prediction.get('mime_type', 'audio/wav')
                    
                    if not audio_content_b64:
                        logger.warning(f"⚠️ Predicción {idx + 1} no contiene audioContent")
                        logger.warning(f"   Predicción keys: {list(prediction.keys()) if isinstance(prediction, dict) else type(prediction)}")
                        logger.warning(f"   Predicción sample: {str(prediction)[:200]}")
                        continue
                    
                    # Decodificar base64 a bytes
                    try:
                        audio_data = base64.b64decode(audio_content_b64)
                        audio_samples.append({
                            'audio_data': audio_data,
                            'mime_type': mime_type,
                            'index': idx
                        })
                        logger.info(f"   ✓ Audio sample {idx + 1} decodificado ({len(audio_data)} bytes)")
                    except Exception as e:
                        logger.error(f"Error decodificando audio sample {idx + 1}: {e}")
                        raise ValueError(f"Error decodificando audio: {str(e)}")
                
                if not audio_samples:
                    logger.error(f"❌ No se pudieron decodificar los audios generados")
                    logger.error(f"   Número de predicciones recibidas: {len(predictions)}")
                    logger.error(f"   Estructura de la primera predicción: {str(predictions[0])[:500] if predictions else 'No hay predicciones'}")
                    logger.error(f"   Response data completo: {str(response_data)[:1000]}")
                    raise ValueError(
                        f"No se pudieron decodificar los audios generados. "
                        f"Se recibieron {len(predictions)} predicción(es) pero ninguna contenía audioContent válido. "
                        f"Verifica los logs para más detalles."
                    )
                
                result = {
                    'audio_samples': audio_samples,
                    'model': response_data.get('model', f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}"),
                    'model_display_name': response_data.get('modelDisplayName', 'Lyria 2'),
                    'deployed_model_id': response_data.get('deployedModelId'),
                    'duration_seconds': self.model_config['duration_seconds'],
                    'sample_rate': self.model_config['sample_rate'],
                    'format': self.model_config['format'],
                }
                
                logger.info(f"✅ Música generada exitosamente: {len(audio_samples)} muestra(s) de {self.model_config['duration_seconds']}s")
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
                                f"- Usa prompts detallados: género, estado de ánimo, instrumentación, tempo\n"
                                f"- Evita contenido violento, sexual o controversial\n"
                                f"- Usa términos musicales y técnicos\n"
                                f"- El prompt será traducido automáticamente al inglés\n\n"
                                f"Si crees que es un error, contacta a Google con el código de soporte en los logs."
                            )
                        
                        # Detectar errores de idioma (no debería pasar si la traducción funciona)
                        if 'unsupported language' in error_message.lower() or 'supported languages' in error_message.lower():
                            logger.error(f"❌ Error de idioma detectado a pesar de la traducción")
                            logger.error(f"   Prompt original: {original_prompt}")
                            logger.error(f"   Prompt traducido: {prompt}")
                            logger.error(f"   Mensaje de error: {error_message}")
                            raise ValueError(
                                f"❌ Error de idioma detectado por la API de Lyria.\n\n"
                                f"Prompt original: {original_prompt}\n"
                                f"Prompt traducido: {prompt}\n\n"
                                f"Esto no debería pasar. Por favor, reporta este error.\n"
                                f"Error de API: {error_message}"
                            )
                        
                        error_msg = f"Error {error_code}: {error_message}"
                except (KeyError, TypeError, AttributeError):
                    pass  # Usar mensaje de error genérico si no se puede parsear
                
                logger.error(f"❌ Error en Lyria: {error_msg}")
                raise Exception(error_msg)
            
        except Exception as e:
            logger.error(f"❌ Error al generar música con Lyria: {str(e)}")
            raise

