"""
Comando para cambiar el límite mensual de créditos de un usuario
Uso: python manage.py set_monthly_limit <username> <limit> [--description "Descripción"]
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.services.credits import CreditService


class Command(BaseCommand):
    help = 'Cambia el límite mensual de créditos de un usuario'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nombre de usuario')
        parser.add_argument('limit', type=int, help='Nuevo límite mensual de créditos')
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Descripción del cambio (opcional)'
        )

    def handle(self, *args, **options):
        username = options['username']
        limit = options['limit']
        description = options['description']

        if limit < 0:
            raise CommandError('El límite debe ser mayor o igual a 0 (0 = ilimitado)')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no encontrado')

        try:
            # Obtener créditos del usuario
            credits = CreditService.get_or_create_user_credits(user)
            old_limit = credits.monthly_limit
            
            # Actualizar límite mensual
            credits.monthly_limit = limit
            credits.save(update_fields=['monthly_limit', 'updated_at'])
            
            # Mostrar información
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Límite mensual actualizado para {username}\n'
                    f'  Límite anterior: {old_limit} créditos\n'
                    f'  Límite nuevo: {limit} créditos\n'
                    f'  Usado este mes: {credits.current_month_usage} créditos\n'
                    f'  Disponible este mes: {credits.credits_remaining} créditos'
                )
            )
            
            if description:
                self.stdout.write(f'  Descripción: {description}')
                
        except Exception as e:
            raise CommandError(f'Error al actualizar límite mensual: {str(e)}')

