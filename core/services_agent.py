"""
ScriptAgentService - Reemplaza N8nService
Procesa guiones usando LangChain en lugar de n8n
"""

import logging
import time
from typing import Dict, Optional
from django.conf import settings

from .models import Script
from .agents.script_agent import ScriptAgent
from .agents.cache import AgentCache
from .monitoring.metrics import AgentMetrics
from .monitoring.langsmith_config import setup_langsmith

logger = logging.getLogger(__name__)


# Configurar LangSmith al importar
setup_langsmith()


class ScriptAgentService:
    """
    Servicio para procesar guiones usando LangChain.
    Reemplaza completamente N8nService.
    """
    
    def __init__(
        self,
        llm_provider: str = None,
        use_cache: bool = True
    ):
        """
        Inicializa el servicio
        
        Args:
            llm_provider: 'openai' o 'gemini' (default: desde settings)
            use_cache: Si usar caché de respuestas
        """
        # Determinar proveedor
        if llm_provider is None:
            llm_provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'openai')
        
        self.llm_provider = llm_provider
        self.use_cache = use_cache
        
        # Crear agente
        llm_model = getattr(settings, 'DEFAULT_LLM_MODEL', None)
        self.agent = ScriptAgent(
            llm_provider=llm_provider,
            llm_model=llm_model,
            temperature=getattr(settings, 'LLM_TEMPERATURE', 0.7),
            max_retries=getattr(settings, 'LLM_MAX_RETRIES', 2)
        )
        
        logger.info(f"ScriptAgentService inicializado (provider: {llm_provider}, cache: {use_cache})")
    
    def process_script(self, script: Script) -> Script:
        """
        Procesa un guión usando LangChain y crea las escenas.
        Este método reemplaza send_script_for_processing + process_webhook_response de N8nService.
        
        Args:
            script: Objeto Script a procesar
            
        Returns:
            Script procesado con escenas creadas
            
        Raises:
            ValidationException: Si hay errores de validación
            ServiceException: Si hay errores en el procesamiento
        """
        from .services import ValidationException, ServiceException, SceneService
        
        start_time = time.time()
        
        try:
            # Marcar como procesando
            script.mark_as_processing()
            logger.info(f"Procesando guión {script.id} con LangChain")
            
            # Verificar caché
            cached_response = None
            if self.use_cache:
                cached_response = AgentCache.get(
                    script_text=script.original_script,
                    duration_min=script.desired_duration_min
                )
            
            if cached_response:
                logger.info(f"Usando respuesta cacheada para guión {script.id}")
                result_data = cached_response
            else:
                # Procesar con el agente
                logger.info(f"Procesando guión {script.id} con LLM ({self.llm_provider})")
                
                result_data = self.agent.process_script(
                    script_text=script.original_script,
                    duration_min=script.desired_duration_min,
                    script_id=script.id
                )
                
                # Guardar en caché
                if self.use_cache:
                    AgentCache.set(
                        script_text=script.original_script,
                        duration_min=script.desired_duration_min,
                        response=result_data
                    )
            
            # Calcular latencia
            latency_ms = (time.time() - start_time) * 1000
            
            # Trackear métricas
            metrics = result_data.get('_metrics', {})
            AgentMetrics.track_request(
                script_id=script.id,
                provider=metrics.get('provider', self.llm_provider),
                model=metrics.get('model', 'unknown'),
                input_tokens=metrics.get('input_tokens', 0),
                output_tokens=metrics.get('output_tokens', 0),
                latency_ms=latency_ms,
                success=True
            )
            
            # Preparar datos procesados (formato compatible con n8n)
            output_data = {
                'project': result_data.get('project', {}),
                'scenes': result_data.get('scenes', []),
                'characters': result_data.get('characters', [])
            }
            
            # Marcar como completado
            script.mark_as_completed(output_data)
            
            # Si es flujo del agente, crear objetos Scene en la BD
            if script.agent_flow:
                logger.info(f"Script {script.id} es del flujo del agente, creando escenas en BD...")
                scenes_data = output_data.get('scenes', [])
                
                if scenes_data:
                    # Crear escenas usando SceneService
                    created_scenes = SceneService.create_scenes_from_n8n_data(script, scenes_data)
                    
                    # Iniciar generación de preview images solo si está habilitado
                    if script.generate_previews:
                        scene_service = SceneService()
                        for scene in created_scenes:
                            try:
                                # TODO: Idealmente esto debería ser async o con Celery
                                scene_service.generate_preview_image(scene)
                            except Exception as e:
                                # No bloqueamos si falla una preview image
                                logger.error(f"Error al generar preview para escena {scene.scene_id}: {e}")
                    else:
                        logger.info(f"✓ Generación de previews deshabilitada (script.generate_previews=False)")
                    
                    logger.info(f"✓ {len(created_scenes)} escenas creadas para script {script.id}")
            
            logger.info(f"✓ Guión {script.id} procesado exitosamente (latencia: {latency_ms:.0f}ms)")
            return script
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Trackear error
            AgentMetrics.track_request(
                script_id=script.id,
                provider=self.llm_provider,
                model='unknown',
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                success=False,
                errors=[str(e)]
            )
            
            # Marcar como error
            script.mark_as_error(str(e))
            logger.error(f"Error al procesar guión {script.id}: {e}")
            
            from .services import ServiceException
            raise ServiceException(f"Error al procesar guión: {str(e)}")
    
    def process_webhook_response(self, data):
        """
        Método de compatibilidad con N8nService.
        En el nuevo sistema, este método no se usa (todo es síncrono).
        Se mantiene para compatibilidad durante la migración.
        """
        logger.warning("process_webhook_response llamado pero no es necesario con LangChain")
        logger.info("Usando process_script() en su lugar")
        
        script_id = data.get('script_id')
        if not script_id:
            from .services import ValidationException
            raise ValidationException("No se encontró script_id")
        
        try:
            script = Script.objects.get(id=script_id)
        except Script.DoesNotExist:
            from .services import ValidationException
            raise ValidationException(f"Guión con ID {script_id} no encontrado")
        
        # Procesar directamente
        return self.process_script(script)

