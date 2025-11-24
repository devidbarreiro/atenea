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
        duration = video.duration or video.metadata.get('duration', 0)
        if duration == 0:
            logger.warning(f"Video {video.id} no tiene duración, usando estimación")
            duration = 8  # Estimación por defecto
        
        if video.type == 'heygen_avatar_v2':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_v2']['video']))
        elif video.type == 'heygen_avatar_iv':
            return Decimal(str(duration * CreditService.PRICING['heygen_avatar_iv']['video']))
        elif video.type == 'gemini_veo':
            has_audio = video.metadata.get('generate_audio', False)
            price_key = 'video_audio' if has_audio else 'video'
            return Decimal(str(duration * CreditService.PRICING['gemini_veo'][price_key]))
        elif video.type == 'sora':
            model = video.config.get('sora_model', 'sora-2')
            return Decimal(str(duration * CreditService.PRICING['sora'][model]))
        
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
        
        return Decimal('0')
    
    # Métodos específicos de deducción
    @staticmethod
    def deduct_credits_for_video(user, video):
        """Deduce créditos para un video"""
        if video.metadata.get('credits_charged'):
            logger.warning(f"Video {video.id} ya fue cobrado")
            return
        
        cost = CreditService.calculate_video_cost(video)
        if cost == 0:
            logger.warning(f"No se pudo calcular costo para video {video.id}")
            return
        
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
    
    @staticmethod
    def deduct_credits_for_image(user, image):
        """Deduce créditos para una imagen"""
        if image.metadata.get('credits_charged'):
            return
        
        cost = CreditService.calculate_image_cost(image)
        
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
    
    @staticmethod
    def deduct_credits_for_audio(user, audio):
        """Deduce créditos para un audio"""
        if audio.metadata.get('credits_charged'):
            return
        
        cost = CreditService.calculate_audio_cost(audio)
        
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
        if scene.metadata.get('credits_charged'):
            return
        
        cost = CreditService.calculate_scene_video_cost(scene)
        if cost == 0:
            logger.warning(f"No se pudo calcular costo para escena {scene.id}")
            return
        
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
    
    @staticmethod
    def estimate_video_cost(video_type, duration, config=None):
        """Estima costo antes de generar (para mostrar al usuario)"""
        duration = duration or 8
        
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
            return Decimal(str(duration * CreditService.PRICING['sora'][model]))
        
        return Decimal('0')
    
    @staticmethod
    def estimate_image_cost():
        """Estima costo de una imagen"""
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



