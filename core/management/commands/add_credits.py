"""
Comando para asignar créditos a usuarios
Uso: python manage.py add_credits <username> <amount> [--description "Descripción"]
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.services.credits import CreditService


class Command(BaseCommand):
    help = 'Asigna créditos a un usuario'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nombre de usuario')
        parser.add_argument('amount', type=float, help='Cantidad de créditos a asignar')
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Descripción de la asignación'
        )

    def handle(self, *args, **options):
        username = options['username']
        amount = options['amount']
        description = options['description'] or f"Créditos asignados manualmente: {amount}"

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no encontrado')

        if amount <= 0:
            raise CommandError('La cantidad debe ser mayor a 0')

        try:
            # Obtener créditos antes de agregar para mostrar saldo anterior
            from core.services.credits import CreditService
            credits_before = CreditService.get_or_create_user_credits(user)
            balance_before = credits_before.credits
            
            credits = CreditService.add_credits(
                user=user,
                amount=amount,
                description=description,
                transaction_type='adjustment'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {amount} créditos asignados a {username}\n'
                    f'  Saldo anterior: {balance_before} créditos\n'
                    f'  Saldo actual: {credits.credits} créditos'
                )
            )
        except Exception as e:
            raise CommandError(f'Error al asignar créditos: {str(e)}')



