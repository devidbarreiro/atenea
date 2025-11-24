"""
Comando para listar todos los usuarios con sus créditos
Uso: python manage.py list_users_credits [--min-credits MIN] [--sort-by SORT]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.services.credits import CreditService
from core.models import UserCredits
from django.db.models import Q


class Command(BaseCommand):
    help = 'Lista todos los usuarios con sus créditos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-credits',
            type=float,
            default=0,
            help='Mostrar solo usuarios con al menos esta cantidad de créditos',
        )
        parser.add_argument(
            '--sort-by',
            type=str,
            choices=['username', 'credits', 'usage', 'percentage'],
            default='username',
            help='Campo por el que ordenar (username, credits, usage, percentage)',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Mostrar solo usuarios activos (con créditos > 0 o uso > 0)',
        )

    def handle(self, *args, **options):
        min_credits = options['min_credits']
        sort_by = options['sort_by']
        active_only = options['active_only']

        # Obtener todos los usuarios con créditos
        users_with_credits = UserCredits.objects.select_related('user').all()

        # Filtrar por créditos mínimos
        if min_credits > 0:
            users_with_credits = users_with_credits.filter(credits__gte=min_credits)

        # Filtrar solo activos
        if active_only:
            users_with_credits = users_with_credits.filter(
                Q(credits__gt=0) | Q(current_month_usage__gt=0)
            )

        # Ordenar
        if sort_by == 'username':
            users_with_credits = users_with_credits.order_by('user__username')
        elif sort_by == 'credits':
            users_with_credits = users_with_credits.order_by('-credits')
        elif sort_by == 'usage':
            users_with_credits = users_with_credits.order_by('-current_month_usage')
        elif sort_by == 'percentage':
            # Ordenar por porcentaje de uso (necesitamos calcularlo)
            users_with_credits = sorted(
                users_with_credits,
                key=lambda uc: (uc.current_month_usage / uc.monthly_limit * 100) if uc.monthly_limit > 0 else 0,
                reverse=True
            )

        # Mostrar resultados
        self.stdout.write(self.style.SUCCESS('\n📊 Usuarios con Créditos'))
        self.stdout.write('=' * 100)
        
        if not users_with_credits:
            self.stdout.write(self.style.WARNING('No se encontraron usuarios con créditos.'))
            return

        # Encabezado
        self.stdout.write(
            f"{'Usuario':<20} {'Créditos':<15} {'Usado/Mes':<15} {'Límite':<15} {'Restante':<15} {'% Uso':<10}"
        )
        self.stdout.write('-' * 100)

        total_credits = 0
        total_usage = 0
        total_limit = 0

        for user_credits in users_with_credits:
            username = user_credits.user.username
            credits = user_credits.credits
            usage = user_credits.current_month_usage
            limit = user_credits.monthly_limit
            remaining = limit - usage if limit > 0 else 0
            percentage = (usage / limit * 100) if limit > 0 else 0

            total_credits += credits
            total_usage += usage
            total_limit += limit

            # Color según porcentaje de uso
            if percentage >= 90:
                style = self.style.ERROR
            elif percentage >= 75:
                style = self.style.WARNING
            else:
                style = self.style.SUCCESS

            self.stdout.write(
                style(
                    f"{username:<20} {credits:<15.2f} {usage:<15.2f} {limit:<15.0f} "
                    f"{remaining:<15.2f} {percentage:<10.1f}%"
                )
            )

        # Totales
        self.stdout.write('-' * 100)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'TOTALES':<20} {total_credits:<15.2f} {total_usage:<15.2f} {total_limit:<15.0f} "
                f"{total_limit - total_usage:<15.2f} {(total_usage / total_limit * 100) if total_limit > 0 else 0:<10.1f}%"
            )
        )
        self.stdout.write('=' * 100)
        self.stdout.write(f'\nTotal de usuarios: {len(users_with_credits)}')

