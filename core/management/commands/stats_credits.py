"""
Comando para mostrar estadísticas generales del sistema de créditos
Uso: python manage.py stats_credits [--period PERIOD]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserCredits, CreditTransaction, ServiceUsage
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Command(BaseCommand):
    help = 'Muestra estadísticas generales del sistema de créditos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            choices=['today', 'week', 'month', 'all'],
            default='all',
            help='Período de tiempo para las estadísticas (today, week, month, all)',
        )

    def handle(self, *args, **options):
        period = options['period']

        # Calcular fechas según período
        now = timezone.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = 'Hoy'
        elif period == 'week':
            start_date = now - timedelta(days=7)
            period_name = 'Últimos 7 días'
        elif period == 'month':
            start_date = now - timedelta(days=30)
            period_name = 'Últimos 30 días'
        else:
            start_date = None
            period_name = 'Todo el tiempo'

        self.stdout.write(self.style.SUCCESS(f'\n📊 Estadísticas del Sistema de Créditos ({period_name})'))
        self.stdout.write('=' * 80)

        # 1. Estadísticas de Usuarios
        self.stdout.write(self.style.SUCCESS('\n👥 Usuarios'))
        self.stdout.write('-' * 80)
        
        total_users = User.objects.count()
        users_with_credits = UserCredits.objects.count()
        users_with_balance = UserCredits.objects.filter(credits__gt=0).count()
        users_active_this_period = ServiceUsage.objects.filter(
            created_at__gte=start_date
        ).values('user').distinct().count() if start_date else ServiceUsage.objects.values('user').distinct().count()

        self.stdout.write(f'Total de usuarios: {total_users}')
        self.stdout.write(f'Usuarios con créditos registrados: {users_with_credits}')
        self.stdout.write(f'Usuarios con saldo > 0: {users_with_balance}')
        self.stdout.write(f'Usuarios activos en el período: {users_active_this_period}')

        # 2. Estadísticas de Créditos
        self.stdout.write(self.style.SUCCESS('\n💰 Créditos'))
        self.stdout.write('-' * 80)

        credits_stats = UserCredits.objects.aggregate(
            total_credits=Sum('credits'),
            avg_credits=Avg('credits'),
            total_purchased=Sum('total_purchased'),
            total_spent=Sum('total_spent'),
            total_monthly_limit=Sum('monthly_limit'),
            total_current_usage=Sum('current_month_usage'),
        )

        self.stdout.write(f'Total de créditos en el sistema: {credits_stats["total_credits"] or 0:.2f}')
        self.stdout.write(f'Promedio de créditos por usuario: {credits_stats["avg_credits"] or 0:.2f}')
        self.stdout.write(f'Total comprado históricamente: {credits_stats["total_purchased"] or 0:.2f}')
        self.stdout.write(f'Total gastado históricamente: {credits_stats["total_spent"] or 0:.2f}')
        self.stdout.write(f'Total límite mensual: {credits_stats["total_monthly_limit"] or 0:.0f}')
        self.stdout.write(f'Total usado este mes: {credits_stats["total_current_usage"] or 0:.2f}')

        # 3. Transacciones
        self.stdout.write(self.style.SUCCESS('\n📝 Transacciones'))
        self.stdout.write('-' * 80)

        transaction_filter = Q(created_at__gte=start_date) if start_date else Q()
        
        transactions_stats = CreditTransaction.objects.filter(transaction_filter).aggregate(
            total=Count('id'),
            purchases=Count('id', filter=Q(transaction_type='purchase')),
            deductions=Count('id', filter=Q(transaction_type='deduction')),
            refunds=Count('id', filter=Q(transaction_type='refund')),
            adjustments=Count('id', filter=Q(transaction_type='adjustment')),
            total_amount_purchased=Sum('amount', filter=Q(transaction_type='purchase')),
            total_amount_spent=Sum('amount', filter=Q(transaction_type='deduction')),
        )

        self.stdout.write(f'Total de transacciones: {transactions_stats["total"] or 0}')
        self.stdout.write(f'  - Compras: {transactions_stats["purchases"] or 0}')
        self.stdout.write(f'  - Gastos: {transactions_stats["deductions"] or 0}')
        self.stdout.write(f'  - Reembolsos: {transactions_stats["refunds"] or 0}')
        self.stdout.write(f'  - Ajustes: {transactions_stats["adjustments"] or 0}')
        self.stdout.write(f'Total comprado: {transactions_stats["total_amount_purchased"] or 0:.2f} créditos')
        self.stdout.write(f'Total gastado: {abs(transactions_stats["total_amount_spent"] or 0):.2f} créditos')

        # 4. Uso por Servicio
        self.stdout.write(self.style.SUCCESS('\n🔧 Uso por Servicio'))
        self.stdout.write('-' * 80)

        usage_filter = Q(created_at__gte=start_date) if start_date else Q()
        
        service_usage = ServiceUsage.objects.filter(usage_filter).values('service_name').annotate(
            total_credits=Sum('credits_spent'),
            count=Count('id'),
            avg_cost=Avg('credits_spent'),
        ).order_by('-total_credits')

        if service_usage:
            self.stdout.write(f"{'Servicio':<30} {'Operaciones':<15} {'Total Créditos':<20} {'Promedio':<15}")
            self.stdout.write('-' * 80)
            for item in service_usage:
                self.stdout.write(
                    f"{item['service_name']:<30} {item['count']:<15} "
                    f"{item['total_credits']:<20.2f} {item['avg_cost']:<15.2f}"
                )
        else:
            self.stdout.write('No hay uso de servicios registrado en este período.')

        # 5. Top Usuarios
        self.stdout.write(self.style.SUCCESS('\n🏆 Top 10 Usuarios por Uso'))
        self.stdout.write('-' * 80)

        top_users = UserCredits.objects.order_by('-current_month_usage')[:10]
        if top_users:
            self.stdout.write(f"{'Usuario':<20} {'Créditos':<15} {'Usado/Mes':<15} {'% Uso':<10}")
            self.stdout.write('-' * 80)
            for user_credits in top_users:
                percentage = (user_credits.current_month_usage / user_credits.monthly_limit * 100) if user_credits.monthly_limit > 0 else 0
                self.stdout.write(
                    f"{user_credits.user.username:<20} {user_credits.credits:<15.2f} "
                    f"{user_credits.current_month_usage:<15.2f} {percentage:<10.1f}%"
                )
        else:
            self.stdout.write('No hay usuarios con uso registrado.')

        # 6. Resumen Financiero
        self.stdout.write(self.style.SUCCESS('\n💵 Resumen Financiero'))
        self.stdout.write('-' * 80)

        total_purchased_usd = (credits_stats["total_purchased"] or 0) / 100
        total_spent_usd = abs(credits_stats["total_spent"] or 0) / 100
        current_balance_usd = (credits_stats["total_credits"] or 0) / 100

        self.stdout.write(f'Total comprado: ${total_purchased_usd:.2f} USD')
        self.stdout.write(f'Total gastado: ${total_spent_usd:.2f} USD')
        self.stdout.write(f'Saldo actual en sistema: ${current_balance_usd:.2f} USD')

        # 7. Tendencias (si hay datos del período)
        if start_date:
            self.stdout.write(self.style.SUCCESS('\n📈 Tendencias'))
            self.stdout.write('-' * 80)
            
            # Comparar con período anterior
            if period == 'today':
                previous_start = start_date - timedelta(days=1)
                previous_end = start_date
            elif period == 'week':
                previous_start = start_date - timedelta(days=7)
                previous_end = start_date
            elif period == 'month':
                previous_start = start_date - timedelta(days=30)
                previous_end = start_date
            
            if period != 'all':
                previous_usage = ServiceUsage.objects.filter(
                    created_at__gte=previous_start,
                    created_at__lt=previous_end
                ).aggregate(total=Sum('credits_spent'))['total'] or 0
                
                current_usage = ServiceUsage.objects.filter(
                    created_at__gte=start_date
                ).aggregate(total=Sum('credits_spent'))['total'] or 0
                
                if previous_usage > 0:
                    change = ((current_usage - previous_usage) / previous_usage) * 100
                    self.stdout.write(f'Uso período anterior: {previous_usage:.2f} créditos')
                    self.stdout.write(f'Uso período actual: {current_usage:.2f} créditos')
                    self.stdout.write(f'Cambio: {change:+.1f}%')

        self.stdout.write('\n' + '=' * 80)

