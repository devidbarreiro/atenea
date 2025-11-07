from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def send_user_credentials(sender, instance, created, **kwargs):
    if created:
        try:
            subject = "Tus credenciales de acceso"
            message = f"""Hola {instance.username},

Se ha creado tu cuenta en nuestro sistema.

Tus credenciales son:
Usuario: {instance.username}
Contraseña: {instance.password}

Puedes iniciar sesión en: {settings.DEFAULT_DOMAIN if hasattr(settings, 'DEFAULT_DOMAIN') else 'http://localhost:8000'}/login

Saludos,
El equipo de Atenea"""
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@atenea.local')
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[instance.email],
                fail_silently=False,
            )
            logger.info(f"Email de credenciales enviado a {instance.email}")
        except Exception as exc:
            logger.error(f"Error al enviar email de credenciales a {instance.email}: {exc}")