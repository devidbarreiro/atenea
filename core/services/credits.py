"""
Servicio para manejar créditos de usuarios
"""
from decimal import Decimal
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
import logging

from core.models import UserCredits, CreditTransaction, ServiceUsage

logger = logging.getLogger(__name__)


class InsufficientCreditsException(Exception):
    """Excepción cuando no hay suficientes créditos"""
    pass


class RateLimitExceededException(Exception):
    """Excepción cuando se excede el límite mensual"""
    pass


class CreditService:
    """Servicio para manejar créditos de usuarios"""
    
    # Precios por servicio (en créditos)
    # 100 créditos Atenea = 1 USD
    PRICING = {
        'gemini_veo': {
            'video': 50,  # por segundo
            'video_audio': 75,  # por segundo (con audio)
        },
        'sora': {
            'sora-2': 10,  # por segundo
            'sora-2-pro': 50,  # por segundo
        },
        'heygen_avatar_v2': {
            'video': 5,  # por segundo
        },
        'heygen_avatar_iv': {
            'video': 15,  # por segundo
        },
        'vuela_ai': {
            'basic': 3,  # por segundo
            'premium': 5,  # por segundo
        },
        'gemini_image': {
            'image': 2,  # por imagen
        },
        'elevenlabs': {
            'per_character': Decimal('0.017'),  # por carácter
        },
        # Higgsfield (precios según documentación oficial)
        'higgsfield_dop_standard': {
            'video': 44,  # 7 créditos Higgsfield → ~$0.44 → 44 créditos Atenea
        },
        'higgsfield_dop_preview': {
            'video': 19,  # 3 créditos Higgsfield → ~$0.19 → 19 créditos Atenea
        },
        'higgsfield_seedance_v1_pro': {
            'video': 74,  # 400 créditos Higgsfield → ~$0.74 → 74 créditos Atenea
        },
        'higgsfield_kling_v2_1_pro': {
            'video': 45,  # 35 créditos Higgsfield → ~$0.45 → 45 créditos Atenea
        },
        # Higgsfield Text-to-Image (precios según documentación)
        'higgsfield_soul_standard': {
            'image': 2,  # 0.25 créditos Higgsfield → ~$0.023 → ~2 créditos Atenea
        },
        'reve_text_to_image': {
            'image': 1,  # 1 crédito Reve → ~$0.01 → ~1 crédito Atenea
        },
        # Kling (precios según tabla proporcionada)
        'kling_v1': {
            'std_5s': 14,   # $0.14
            'std_10s': 28,  # $0.28
            'pro_5s': 49,   # $0.49
            'pro_10s': 98,  # $0.98
        },
        'kling_v1_5': {
            'std_5s': 28,   # $0.28
            'std_10s': 56,  # $0.56
            'pro_5s': 49,   # $0.49
            'pro_10s': 98,  # $0.98
        },
        'kling_v1_6': {
            'std_5s': 28,   # $0.28
            'std_10s': 56,  # $0.56
            'pro_5s': 49,   # $0.49
            'pro_10s': 98,  # $0.98
        },
        'kling_v2_master': {
            '5s': 140,   # $1.40
            '10s': 280,  # $2.80
        },
        'kling_v2_1': {
            'std_5s': 28,   # $0.28
            'std_10s': 56,  # $0.56
            'pro_5s': 49,   # $0.49
            'pro_10s': 98,  # $0.98
        },
        'kling_v2_5_turbo': {
            'std_5s': 21,   # $0.21
            'std_10s': 42,  # $0.42
            'pro_5s': 35,   # $0.35
            'pro_10s': 70,  # $0.70
        },
    }
    
    @staticmethod
    def get_or_create_user_credits(user):
        """Obtiene o crea el registro de créditos del usuario"""
        credits, created = UserCredits.objects.get_or_create(
            user=user,
            defaults={
                'credits': Decimal('0'),
                'monthly_limit': 1000,
            }
        )
        
        # Resetear uso mensual si es un nuevo mes
        CreditService._check_monthly_reset(credits)
        
        return credits
    
    @staticmethod
    def _check_monthly_reset(credits):
        """Verifica y resetea el uso mensual si es necesario"""
        today = timezone.now().date()
        
        if credits.last_reset_date is None:
            # Primera vez, establecer fecha actual
            credits.last_reset_date = today
            credits.save(update_fields=['last_reset_date'])
        elif credits.last_reset_date.month != today.month or credits.last_reset_date.year != today.year:
            # Nuevo mes, resetear
            logger.info(f"Reseteando uso mensual para usuario {credits.user.username}")
            credits.reset_monthly_usage()
    
    @staticmethod
    def has_enough_credits(user, amount):
        """Verifica si el usuario tiene suficientes créditos"""
        credits = CreditService.get_or_create_user_credits(user)
        return credits.credits >= Decimal(str(amount))
    
    @staticmethod
    def check_rate_limit(user, amount):
        """Verifica si el usuario puede gastar sin exceder límite mensual"""
        credits = CreditService.get_or_create_user_credits(user)
        amount_decimal = Decimal(str(amount))
        
        # Si el límite es 0, no hay límite (ilimitado)
        if credits.monthly_limit == 0:
            return
        
        if credits.current_month_usage + amount_decimal > credits.monthly_limit:
            raise RateLimitExceededException(
                f"Límite mensual excedido. Usado: {credits.current_month_usage}/{credits.monthly_limit} créditos. "
                f"Necesitas {amount_decimal} créditos más."
            )
    
    @staticmethod
    @transaction.atomic
    def deduct_credits(user, amount, service_name, operation_type, resource=None, metadata=None):
        """Deduce créditos del usuario"""
        credits = CreditService.get_or_create_user_credits(user)
        amount_decimal = Decimal(str(amount))
        
        # Verificar créditos disponibles
        if credits.credits < amount_decimal:
            raise InsufficientCreditsException(
                f"Créditos insuficientes. Disponibles: {credits.credits}, Necesarios: {amount_decimal}"
            )
        
        # Verificar límite mensual
        CreditService.check_rate_limit(user, amount_decimal)
        
        # Guardar balances antes
        balance_before = credits.credits
        balance_after = balance_before - amount_decimal
        
        # Actualizar créditos
        credits.credits = balance_after
        credits.total_spent += amount_decimal
        credits.current_month_usage += amount_decimal
        credits.save(update_fields=['credits', 'total_spent', 'current_month_usage', 'updated_at'])
        
        # Crear transacción
        transaction_obj = CreditTransaction.objects.create(
            user=user,
            transaction_type='spend',
            amount=-amount_decimal,  # Negativo para gastos
            balance_before=balance_before,
            balance_after=balance_after,
            description=f"Gasto en {service_name} - {operation_type}",
            service_name=service_name,
            metadata=metadata or {},
            content_type=ContentType.objects.get_for_model(resource) if resource else None,
            object_id=resource.id if resource else None,
        )
        
        # Crear registro de uso
        ServiceUsage.objects.create(
            user=user,
            service_name=service_name,
            operation_type=operation_type,
            credits_spent=amount_decimal,
            metadata=metadata or {},
            content_type=ContentType.objects.get_for_model(resource) if resource else None,
            object_id=resource.id if resource else None,
        )
        
        logger.info(
            f"Créditos deducidos: {user.username} - {amount_decimal} créditos "
            f"({service_name}/{operation_type}). Balance: {balance_after}"
        )
        
        return transaction_obj
    
    # Métodos de cálculo por tipo de servicio
    @staticmethod
    def calculate_video_cost(video):
        """Calcula costo de un video"""
        # Intentar obtener duración de múltiples fuentes
        duration = None
        
        # 1. Campo duration del modelo
        if video.duration:
            duration = video.duration
        # 2. Metadata duration
        elif video.metadata and video.metadata.get('duration'):
            duration = video.metadata.get('duration')
        # 3. Config duration (para Veo y Sora)
        elif video.config and video.config.get('duration'):
            duration = video.config.get('duration')
        
        # Convertir a int si es necesario
        if duration:
            try:
                duration = int(float(duration))
            except (ValueError, TypeError):
                duration = None
        
        if not duration or duration == 0:
            logger.warning(f"Video {video.id} no tiene duración, usando estimación. duration={video.duration}, metadata.duration={video.metadata.get('duration') if video.metadata else None}, config.duration={video.config.get('duration') if video.config else None}")
            duration = 8  # Estimación por defecto
        
        if video.type == 'heygen_avatar_v2':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_v2']['video']))
        elif video.type == 'heygen_avatar_iv':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_iv']['video']))
        elif video.type == 'gemini_veo':
            # Priorizar config sobre metadata (config es la fuente de verdad al crear el video)
            has_audio = False
            if video.config:
                has_audio = video.config.get('generate_audio', False)
            elif video.metadata:
                has_audio = video.metadata.get('generate_audio', False)
            
            price_key = 'video_audio' if has_audio else 'video'
            # Validar que la clave existe en PRICING
            if price_key not in CreditService.PRICING['gemini_veo']:
                logger.error(f"Clave de precio '{price_key}' no encontrada en PRICING para gemini_veo. Usando 'video' por defecto.")
                price_key = 'video'
            price_per_second = CreditService.PRICING['gemini_veo'][price_key]
            cost = Decimal(str(duration * price_per_second))
            logger.info(f"Cálculo costo Veo: duración={duration}s, audio={has_audio}, precio/seg={price_per_second}, costo={cost}")
            return cost
        elif video.type == 'sora':
            model = video.config.get('sora_model', 'sora-2')
            # Validar que el modelo existe en PRICING
            if model not in CreditService.PRICING['sora']:
                logger.error(f"Modelo Sora '{model}' no encontrado en PRICING. Modelos disponibles: {list(CreditService.PRICING['sora'].keys())}. Usando 'sora-2' por defecto.")
                model = 'sora-2'
            price_per_second = CreditService.PRICING['sora'][model]
            cost = Decimal(str(duration * price_per_second))
            logger.info(f"Cálculo costo Sora: duración={duration}s, modelo={model}, precio/seg={price_per_second}, costo={cost}")
            return cost
        elif video.type in ['higgsfield_dop_standard', 'higgsfield_dop_preview', 'higgsfield_seedance_v1_pro', 'higgsfield_kling_v2_1_pro']:
            # Higgsfield: precio fijo por video
            service_key = video.type
            if service_key not in CreditService.PRICING:
                logger.error(f"Servicio '{service_key}' no encontrado en PRICING")
                return Decimal('0')
            cost = Decimal(str(CreditService.PRICING[service_key]['video']))
            logger.info(f"Cálculo costo Higgsfield: servicio={service_key}, costo={cost}")
            return cost
        elif video.type.startswith('kling_'):
            # Kling: precio según modelo, modo y duración
            model_name = video.type  # ej: 'kling_v1', 'kling_v2_master'
            if model_name not in CreditService.PRICING:
                logger.error(f"Modelo Kling '{model_name}' no encontrado en PRICING")
                return Decimal('0')
            
            model_pricing = CreditService.PRICING[model_name]
            mode = video.config.get('mode', 'std')  # 'std' o 'pro'
            
            # Para v2-master no hay modo, solo duración
            if model_name == 'kling_v2_master':
                duration_key = f"{duration}s"
                if duration_key not in model_pricing:
                    logger.error(f"Duración {duration}s no válida para {model_name}. Opciones: {list(model_pricing.keys())}")
                    return Decimal('0')
                cost = Decimal(str(model_pricing[duration_key]))
            else:
                # Para otros modelos: modo + duración
                duration_key = f"{mode}_{duration}s"
                if duration_key not in model_pricing:
                    logger.error(f"Combinación '{duration_key}' no válida para {model_name}. Opciones: {list(model_pricing.keys())}")
                    return Decimal('0')
                cost = Decimal(str(model_pricing[duration_key]))
            
            logger.info(f"Cálculo costo Kling: modelo={model_name}, modo={mode}, duración={duration}s, costo={cost}")
            return cost
        
        return Decimal('0')
    
    @staticmethod
    def calculate_image_cost(image):
        """Calcula costo de una imagen"""
        return Decimal(str(CreditService.PRICING['gemini_image']['image']))
    
    @staticmethod
    def calculate_audio_cost(audio):
        """Calcula costo de un audio"""
        character_count = len(audio.text)
        return Decimal(str(character_count * CreditService.PRICING['elevenlabs']['per_character']))
    
    @staticmethod
    def calculate_scene_video_cost(scene):
        """Calcula costo de un video de escena"""
        duration = scene.duration_sec or 8
        
        if scene.ai_service == 'heygen_v2':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_v2']['video']))
        elif scene.ai_service == 'heygen_avatar_iv':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_iv']['video']))
        elif scene.ai_service == 'gemini_veo':
            has_audio = scene.ai_config.get('generate_audio', False)
            price_key = 'video_audio' if has_audio else 'video'
            return Decimal(str(duration * CreditService.PRICING['gemini_veo'][price_key]))
        elif scene.ai_service == 'sora':
            model = scene.ai_config.get('sora_model', 'sora-2')
            return Decimal(str(duration * CreditService.PRICING['sora'][model]))
        elif scene.ai_service == 'vuela_ai':
            quality = scene.ai_config.get('quality_tier', 'premium')
            quality_key = 'premium' if quality == 'premium' else 'basic'
            return Decimal(str(duration * CreditService.PRICING['vuela_ai'][quality_key]))
        elif scene.ai_service in ['higgsfield_dop_standard', 'higgsfield_dop_preview', 'higgsfield_seedance_v1_pro', 'higgsfield_kling_v2_1_pro']:
            # Higgsfield: precio fijo por video
            service_key = scene.ai_service
            if service_key not in CreditService.PRICING:
                logger.error(f"Servicio '{service_key}' no encontrado en PRICING")
                return Decimal('0')
            return Decimal(str(CreditService.PRICING[service_key]['video']))
        elif scene.ai_service.startswith('kling_'):
            # Kling: precio según modelo, modo y duración
            model_name = scene.ai_service
            if model_name not in CreditService.PRICING:
                logger.error(f"Modelo Kling '{model_name}' no encontrado en PRICING")
                return Decimal('0')
            
            model_pricing = CreditService.PRICING[model_name]
            mode = scene.ai_config.get('mode', 'std')
            
            # Para v2-master no hay modo, solo duración
            if model_name == 'kling_v2_master':
                duration_key = f"{duration}s"
                if duration_key not in model_pricing:
                    logger.error(f"Duración {duration}s no válida para {model_name}. Opciones: {list(model_pricing.keys())}")
                    return Decimal('0')
                return Decimal(str(model_pricing[duration_key]))
            else:
                # Para otros modelos: modo + duración
                duration_key = f"{mode}_{duration}s"
                if duration_key not in model_pricing:
                    logger.error(f"Combinación '{duration_key}' no válida para {model_name}. Opciones: {list(model_pricing.keys())}")
                    return Decimal('0')
                return Decimal(str(model_pricing[duration_key]))
        
        return Decimal('0')
    
    # Métodos específicos de deducción
    @staticmethod
    def deduct_credits_for_video(user, video):
        """Deduce créditos para un video"""
        # Inicializar metadata si no existe
        if not video.metadata:
            video.metadata = {}
        
        if video.metadata.get('credits_charged'):
            logger.info(f"Créditos ya cobrados para video {video.id} (tipo: {video.type})")
            return
        
        cost = CreditService.calculate_video_cost(video)
        if cost == 0:
            logger.warning(f"No se pudo calcular costo para video {video.id} (tipo: {video.type}, duración: {video.duration or video.metadata.get('duration') or video.config.get('duration', 'N/A')})")
            return
        
        # Obtener duración para logging
        duration_for_log = video.duration or video.metadata.get('duration') or video.config.get('duration', 'N/A')
        logger.info(f"Cobrando {cost} créditos por video {video.id} (tipo: {video.type}, duración: {duration_for_log}s)")
        
        metadata = {
            'duration': video.duration or video.metadata.get('duration'),
            'video_type': video.type,
            'model': video.config.get('sora_model') or video.config.get('veo_model'),
        }
        
        # Mapear tipo de video a nombre de servicio
        service_name_map = {
            'heygen_avatar_v2': 'heygen_avatar_v2',
            'heygen_avatar_iv': 'heygen_avatar_iv',
            'gemini_veo': 'gemini_veo',
            'sora': 'sora',
            'higgsfield_dop_standard': 'higgsfield_dop_standard',
            'higgsfield_dop_preview': 'higgsfield_dop_preview',
            'higgsfield_seedance_v1_pro': 'higgsfield_seedance_v1_pro',
            'higgsfield_kling_v2_1_pro': 'higgsfield_kling_v2_1_pro',
            'kling_v1': 'kling_v1',
            'kling_v1_5': 'kling_v1_5',
            'kling_v1_6': 'kling_v1_6',
            'kling_v2_master': 'kling_v2_master',
            'kling_v2_1': 'kling_v2_1',
            'kling_v2_5_turbo': 'kling_v2_5_turbo',
        }
        service_name = service_name_map.get(video.type, video.type)
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name=service_name,
            operation_type='video_generation',
            resource=video,
            metadata=metadata
        )
        
        video.metadata['credits_charged'] = True
        video.save(update_fields=['metadata'])
        logger.info(f"✓ Créditos cobrados y marcados en metadata para video {video.id}")
    
    @staticmethod
    def deduct_credits_for_image(user, image):
        """Deduce créditos para una imagen"""
        # Inicializar metadata si no existe
        if not image.metadata:
            image.metadata = {}
        
        if image.metadata.get('credits_charged'):
            logger.info(f"Créditos ya cobrados para imagen {image.id} (tipo: {image.type})")
            return
        
        cost = CreditService.calculate_image_cost(image)
        
        logger.info(f"Cobrando {cost} créditos por imagen {image.id} (tipo: {image.type})")
        
        metadata = {
            'image_type': image.type,
            'aspect_ratio': image.aspect_ratio,
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name='gemini_image',
            operation_type='image_generation',
            resource=image,
            metadata=metadata
        )
        
        image.metadata['credits_charged'] = True
        image.save(update_fields=['metadata'])
        logger.info(f"✓ Créditos cobrados y marcados en metadata para imagen {image.id}")
    
    @staticmethod
    def deduct_credits_for_audio(user, audio):
        """Deduce créditos para un audio"""
        # Inicializar metadata si no existe
        if not audio.metadata:
            audio.metadata = {}
        
        if audio.metadata.get('credits_charged'):
            logger.info(f"Créditos ya cobrados para audio {audio.id} (caracteres: {len(audio.text)})")
            return
        
        cost = CreditService.calculate_audio_cost(audio)
        
        logger.info(f"Cobrando {cost} créditos por audio {audio.id} (caracteres: {len(audio.text)}, duración: {audio.duration or 'N/A'}s)")
        
        metadata = {
            'character_count': len(audio.text),
            'duration': audio.duration,
            'voice_id': audio.voice_id,
            'model_id': audio.model_id,
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name='elevenlabs',
            operation_type='audio_generation',
            resource=audio,
            metadata=metadata
        )
        
        audio.metadata['credits_charged'] = True
        audio.save(update_fields=['metadata'])
        logger.info(f"✓ Créditos cobrados y marcados en metadata para audio {audio.id}")
    
    @staticmethod
    def deduct_credits_for_scene_preview(user, scene):
        """Deduce créditos para preview de escena"""
        cost = Decimal(str(CreditService.PRICING['gemini_image']['image']))
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name='gemini_image',
            operation_type='preview_generation',
            resource=scene,
            metadata={'scene_id': scene.scene_id}
        )
    
    @staticmethod
    def deduct_credits_for_scene_video(user, scene):
        """Deduce créditos para video de escena"""
        # Inicializar metadata si no existe
        if not scene.metadata:
            scene.metadata = {}
        
        if scene.metadata.get('credits_charged'):
            logger.info(f"Créditos ya cobrados para video de escena {scene.scene_id} (ID: {scene.id})")
            return
        
        cost = CreditService.calculate_scene_video_cost(scene)
        if cost == 0:
            logger.warning(f"No se pudo calcular costo para escena {scene.scene_id} (ID: {scene.id}, ai_service: {scene.ai_service}, duration: {scene.duration_sec})")
            return
        
        logger.info(f"Cobrando {cost} créditos por video de escena {scene.scene_id} (ID: {scene.id}, servicio: {scene.ai_service}, duración: {scene.duration_sec}s)")
        
        metadata = {
            'duration': scene.duration_sec,
            'ai_service': scene.ai_service,
            'ai_config': scene.ai_config,
        }
        
        CreditService.deduct_credits(
            user=user,
            amount=cost,
            service_name=scene.ai_service,
            operation_type='video_generation',
            resource=scene,
            metadata=metadata
        )
        
        scene.metadata['credits_charged'] = True
        scene.save(update_fields=['metadata'])
        logger.info(f"✓ Créditos cobrados y marcados en metadata para escena {scene.scene_id} (ID: {scene.id})")
    
    @staticmethod
    def estimate_video_cost(video_type=None, duration=None, config=None, model_id=None):
        """
        Estima costo antes de generar (para mostrar al usuario)
        
        Args:
            video_type: Tipo de video (ej: 'gemini_veo', 'sora') - DEPRECATED, usar model_id
            duration: Duración en segundos
            config: Configuración del video
            model_id: ID del modelo (ej: 'veo-3.1-generate-preview', 'sora-2')
        """
        from core.ai_services.model_config import VIDEO_TYPE_TO_MODEL_ID, get_model_capabilities
        
        duration = duration or 8
        
        # Si se proporciona model_id, intentar mapear a video_type
        if model_id and not video_type:
            # Buscar video_type que corresponda a este model_id
            for vtype, mid in VIDEO_TYPE_TO_MODEL_ID.items():
                if mid == model_id:
                    video_type = vtype
                    break
            
            # Si no se encuentra en el mapeo, intentar inferir del model_id
            if not video_type:
                if 'veo' in model_id:
                    video_type = 'gemini_veo'
                elif 'sora' in model_id:
                    video_type = 'sora'
                elif 'heygen-avatar-v2' in model_id:
                    video_type = 'heygen_avatar_v2'
                elif 'heygen-avatar-iv' in model_id:
                    video_type = 'heygen_avatar_iv'
                elif 'kling-v' in model_id:
                    # Mapear kling-v1 -> kling_v1, etc.
                    video_type = model_id.replace('-', '_')
                elif 'higgsfield-ai/dop/standard' in model_id:
                    video_type = 'higgsfield_dop_standard'
                elif 'higgsfield-ai/dop/preview' in model_id:
                    video_type = 'higgsfield_dop_preview'
                elif 'seedance' in model_id:
                    video_type = 'higgsfield_seedance_v1_pro'
                elif 'kling-video/v2.1/pro' in model_id:
                    video_type = 'higgsfield_kling_v2_1_pro'
                elif 'vuela-ai' in model_id or 'vuela_ai' in model_id:
                    video_type = 'vuela_ai'
        
        if not video_type:
            return Decimal('0')
        
        if video_type == 'heygen_avatar_v2':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_v2']['video']))
        elif video_type == 'heygen_avatar_iv':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_iv']['video']))
        elif video_type == 'gemini_veo':
            has_audio = config and config.get('generate_audio', False)
            price_key = 'video_audio' if has_audio else 'video'
            return Decimal(str(duration * CreditService.PRICING['gemini_veo'][price_key]))
        elif video_type == 'sora':
            model = (config and config.get('sora_model')) or 'sora-2'
            if model not in CreditService.PRICING.get('sora', {}):
                model = 'sora-2'  # Fallback
            return Decimal(str(duration * CreditService.PRICING['sora'][model]))
        elif video_type in ['higgsfield_dop_standard', 'higgsfield_dop_preview', 'higgsfield_seedance_v1_pro', 'higgsfield_kling_v2_1_pro']:
            # Higgsfield: precio fijo por video
            if video_type not in CreditService.PRICING:
                return Decimal('0')
            return Decimal(str(CreditService.PRICING[video_type]['video']))
        elif video_type.startswith('kling_'):
            # Kling: precio según modelo, modo y duración
            if video_type not in CreditService.PRICING:
                return Decimal('0')
            
            model_pricing = CreditService.PRICING[video_type]
            mode = (config and config.get('mode')) or 'std'
            
            # Para v2-master no hay modo, solo duración
            if video_type == 'kling_v2_master':
                duration_key = f"{duration}s"
                if duration_key not in model_pricing:
                    return Decimal('0')
                return Decimal(str(model_pricing[duration_key]))
            else:
                # Para otros modelos: modo + duración
                duration_key = f"{mode}_{duration}s"
                if duration_key not in model_pricing:
                    return Decimal('0')
                return Decimal(str(model_pricing[duration_key]))
        
        return Decimal('0')
    
    @staticmethod
    def estimate_image_cost(model_id=None):
        """Estima costo de una imagen según el modelo"""
        if model_id:
            # Mapear model_id a clave de pricing
            model_pricing_map = {
                'higgsfield-ai/soul/standard': 'higgsfield_soul_standard',
                'reve/text-to-image': 'reve_text_to_image',
            }
            
            pricing_key = model_pricing_map.get(model_id)
            if pricing_key and pricing_key in CreditService.PRICING:
                return Decimal(str(CreditService.PRICING[pricing_key]['image']))
        
        # Por defecto, usar Gemini
        return Decimal(str(CreditService.PRICING['gemini_image']['image']))
    
    @staticmethod
    def estimate_audio_cost(text):
        """Estima costo de un audio basado en texto"""
        character_count = len(text)
        return Decimal(str(character_count * CreditService.PRICING['elevenlabs']['per_character']))
    
    @staticmethod
    def add_credits(user, amount, description='', transaction_type='purchase'):
        """Agrega créditos al usuario (para asignación manual)"""
        credits = CreditService.get_or_create_user_credits(user)
        amount_decimal = Decimal(str(amount))
        
        balance_before = credits.credits
        balance_after = balance_before + amount_decimal
        
        credits.credits = balance_after
        credits.total_purchased += amount_decimal
        credits.save(update_fields=['credits', 'total_purchased', 'updated_at'])
        
        CreditTransaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount_decimal,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description or f"Créditos agregados: {amount_decimal}",
        )
        
        logger.info(f"Créditos agregados: {user.username} - {amount_decimal} créditos. Balance: {balance_after}")
        
        return credits



