"""
Comando para mostrar créditos de un usuario
Uso: python manage.py show_user_credits <username>
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.services.credits import CreditService
from core.models import ServiceUsage
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Muestra información de créditos de un usuario'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nombre de usuario')
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Muestra uso detallado por servicio',
        )

    def handle(self, *args, **options):
        username = options['username']
        detailed = options['detailed']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no encontrado')

        credits = CreditService.get_or_create_user_credits(user)

        self.stdout.write(self.style.SUCCESS(f'\n📊 Créditos de {username}'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'Saldo actual: {credits.credits} créditos')
        self.stdout.write(f'Límite mensual: {credits.monthly_limit} créditos')
        self.stdout.write(f'Usado este mes: {credits.current_month_usage} créditos')
        self.stdout.write(f'Disponible este mes: {credits.credits_remaining} créditos')
        self.stdout.write(f'Porcentaje usado: {credits.usage_percentage:.1f}%')
        self.stdout.write(f'Total comprado: {credits.total_purchased} créditos')
        self.stdout.write(f'Total gastado: {credits.total_spent} créditos')
        self.stdout.write(f'Último reset: {credits.last_reset_date or "Nunca"}')

        if detailed:
            # Uso por servicio (últimos 30 días)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            usage_by_service = ServiceUsage.objects.filter(
                user=user,
                created_at__gte=thirty_days_ago
            ).values('service_name').annotate(
                total_credits=Sum('credits_spent'),
                count=Count('id')
            ).order_by('-total_credits')

            if usage_by_service:
                self.stdout.write('\n📈 Uso por servicio (últimos 30 días):')
                self.stdout.write('-' * 50)
                for item in usage_by_service:
                    self.stdout.write(
                        f"  {item['service_name']}: {item['total_credits']} créditos "
                        f"({item['count']} operaciones)"
                    )

