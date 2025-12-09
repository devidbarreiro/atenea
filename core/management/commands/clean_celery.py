"""
Comando Django para limpiar completamente Celery.

Uso: python manage.py clean_celery [--hard]

Limpia:
- Todas las keys de Celery/Kombu en Redis
- Todas las tareas en django_celery_results
- Todas las tareas periódicas en django_celery_beat

Opciones:
  --hard: También vacía todo Redis (no solo Celery)
"""

from django.core.management.base import BaseCommand
import redis
from django_celery_results.models import TaskResult
from django_celery_beat.models import PeriodicTask
from django.conf import settings


class Command(BaseCommand):
    help = 'Limpia completamente Celery (Redis y BD)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hard',
            action='store_true',
            help='Vacía TODO Redis (no solo Celery)',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Solo verificar limpieza sin borrar nada',
        )

    def handle(self, *args, **options):
        hard = options['hard']
        verify_only = options['verify']

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🧹 Limpiador de Celery'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        try:
            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=0
            )
            r.ping()
        except redis.ConnectionError:
            self.stdout.write(
                self.style.ERROR('❌ Error: No se puede conectar a Redis')
            )
            return

        if verify_only:
            self._verify_clean(r)
            return

        self.stdout.write(self.style.WARNING('\n🔴 Limpiando Redis...'))
        self._clean_redis(r, hard)

        self.stdout.write(self.style.WARNING('\n💾 Limpiando BD de Django...'))
        self._clean_django_db()

        self.stdout.write(self.style.SUCCESS('\n✓ Verificando limpieza...'))
        self._verify_clean(r)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('✨ ¡Listo! Celery ha sido completamente limpiado'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self.stdout.write(self.style.WARNING('\n💡 Próximos pasos:'))
        self.stdout.write('   1. Reinicia tu worker de Celery:')
        self.stdout.write('      celery -A atenea worker --loglevel=info')
        self.stdout.write('   2. Reinicia tu servidor Django:')
        self.stdout.write('      python manage.py runserver')

    def _clean_redis(self, r, hard=False):
        """Limpiar Redis"""
        if hard:
            # Vaciar todo Redis
            count_before = len(r.keys('*'))
            r.flushdb()
            self.stdout.write(f'  ✅ Vaciado todo Redis ({count_before} keys eliminadas)')
        else:
            # Solo Celery/Kombu
            count = 0
            for key in r.scan_iter('*'):
                if b'celery' in key or b'kombu' in key:
                    r.delete(key)
                    count += 1
            self.stdout.write(f'  ✅ Eliminadas {count} keys de Celery/Kombu')

    def _clean_django_db(self):
        """Limpiar BD de Django"""
        count_tasks = TaskResult.objects.all().count()
        TaskResult.objects.all().delete()
        self.stdout.write(f'  ✅ Eliminadas {count_tasks} tareas de django_celery_results')

        count_periodic = PeriodicTask.objects.all().count()
        PeriodicTask.objects.all().delete()
        self.stdout.write(f'  ✅ Eliminadas {count_periodic} tareas periódicas de django_celery_beat')

    def _verify_clean(self, r):
        """Verificar que todo está limpio"""
        remaining = len(list(r.scan_iter('celery*')))
        task_count = TaskResult.objects.count()
        periodic_count = PeriodicTask.objects.count()

        self.stdout.write(f'  Keys de celery en Redis: {remaining}')
        self.stdout.write(f'  Tareas en django_celery_results: {task_count}')
        self.stdout.write(f'  Tareas periódicas en django_celery_beat: {periodic_count}')

        if remaining == 0 and task_count == 0 and periodic_count == 0:
            self.stdout.write(self.style.SUCCESS('  ✅ Celery está completamente limpio'))
            return True
        else:
            self.stdout.write(self.style.WARNING('  ⚠️  Todavía hay datos residuales'))
            return False
