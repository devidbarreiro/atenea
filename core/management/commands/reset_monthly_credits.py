"""
Comando para resetear el uso mensual de créditos de todos los usuarios
Uso: python manage.py reset_monthly_credits
"""
from django.core.management.base import BaseCommand
from core.models import UserCredits
from django.utils import timezone


class Command(BaseCommand):
    help = 'Resetea el uso mensual de créditos de todos los usuarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué usuarios serían reseteados sin hacer cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        # Obtener todos los usuarios con créditos
        all_credits = UserCredits.objects.all()
        
        # Filtrar solo los que necesitan reset
        to_reset = []
        for credits in all_credits:
            if credits.last_reset_date is None:
                to_reset.append(credits)
            elif credits.last_reset_date.month != today.month or credits.last_reset_date.year != today.year:
                to_reset.append(credits)

        if not to_reset:
            self.stdout.write(self.style.SUCCESS('No hay usuarios que necesiten reset mensual'))
            return

        self.stdout.write(f'Encontrados {len(to_reset)} usuarios para resetear:')
        for credits in to_reset:
            self.stdout.write(
                f'  - {credits.user.username}: {credits.current_month_usage} créditos usados '
                f'(último reset: {credits.last_reset_date or "nunca"})'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No se hicieron cambios'))
            return

        # Resetear
        reset_count = 0
        for credits in to_reset:
            try:
                credits.reset_monthly_usage()
                reset_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Resetado: {credits.user.username}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error al resetear {credits.user.username}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ {reset_count} usuarios reseteados exitosamente')
        )



