"""
Comando Django para diagnosticar el estado de Celery.

Uso: python manage.py celery_status

Muestra:
- Estado de conexión a Redis
- Tareas pendientes en Redis
- Tareas en BD
- Estado de los workers
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import redis
from django_celery_results.models import TaskResult
from django_celery_beat.models import PeriodicTask
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Diagnostica el estado de Celery'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🔍 Estado de Celery'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # 1. Conexión a Redis
        self.stdout.write(self.style.WARNING('\n🔴 Redis'))
        self._check_redis()

        # 2. Tareas en Redis
        self.stdout.write(self.style.WARNING('\n📋 Tareas en Redis'))
        self._check_redis_queues()

        # 3. Tareas en BD
        self.stdout.write(self.style.WARNING('\n💾 Tareas en BD'))
        self._check_db_tasks()

        # 4. Tareas periódicas
        self.stdout.write(self.style.WARNING('\n⏰ Tareas Periódicas'))
        self._check_periodic_tasks()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))

    def _check_redis(self):
        """Verificar conexión a Redis"""
        try:
            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=0
            )
            r.ping()
            info = r.info()
            self.stdout.write(f'  ✅ Conectado a Redis')
            self.stdout.write(f'     Host: {getattr(settings, "REDIS_HOST", "localhost")}:{getattr(settings, "REDIS_PORT", 6379)}')
            self.stdout.write(f'     Version: {info.get("redis_version", "desconocida")}')
            self.stdout.write(f'     Memory: {info.get("used_memory_human", "?")}')
            self.stdout.write(f'     Clientes: {info.get("connected_clients", "?")}')
        except redis.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Error de conexión: {e}'))

    def _check_redis_queues(self):
        """Verificar colas en Redis"""
        try:
            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=0
            )

            queues = [
                'video_generation',
                'image_generation',
                'audio_generation',
                'scene_processing',
                'polling_tasks',
                'default',
            ]

            total_tasks = 0
            for q in queues:
                # Kombu almacena colas en celery.{queue_name}
                queue_key = f'celery.{q}'
                size = r.llen(queue_key)
                total_tasks += size
                if size > 0:
                    status = self.style.WARNING(f'⚠️  {size}')
                else:
                    status = f'✅ {size}'
                self.stdout.write(f'  {q}: {status}')

            # Tareas en proceso
            active_tasks = r.keys('celery-task-meta-*')
            self.stdout.write(f'\n  Tareas en proceso: {len(active_tasks)}')

            if total_tasks == 0 and len(active_tasks) == 0:
                self.stdout.write(self.style.SUCCESS('  ✅ Redis sin tareas pendientes'))

        except redis.ConnectionError:
            self.stdout.write(self.style.ERROR('  ❌ No se puede conectar a Redis'))

    def _check_db_tasks(self):
        """Verificar tareas en BD"""
        try:
            total = TaskResult.objects.count()
            self.stdout.write(f'  Total de tareas: {total}')

            # Tareas por estado
            statuses = TaskResult.objects.values('status').distinct()
            for item in statuses:
                status = item['status']
                count = TaskResult.objects.filter(status=status).count()
                self.stdout.write(f'    - {status}: {count}')

            # Tareas recientes
            recent = TaskResult.objects.order_by('-date_done')[:5]
            if recent:
                self.stdout.write(f'\n  Últimas 5 tareas:')
                for task in recent:
                    date_str = task.date_done.strftime('%Y-%m-%d %H:%M:%S') if task.date_done else 'N/A'
                    self.stdout.write(f'    - {task.task_id[:8]}...: {task.status} ({date_str})')

            if total == 0:
                self.stdout.write(self.style.SUCCESS('  ✅ BD sin tareas residuales'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))

    def _check_periodic_tasks(self):
        """Verificar tareas periódicas"""
        try:
            total = PeriodicTask.objects.count()
            self.stdout.write(f'  Total de tareas periódicas: {total}')

            enabled = PeriodicTask.objects.filter(enabled=True).count()
            disabled = PeriodicTask.objects.filter(enabled=False).count()

            if enabled > 0:
                self.stdout.write(f'  Habilitadas: {enabled}')
                for task in PeriodicTask.objects.filter(enabled=True):
                    self.stdout.write(f'    - {task.name}')

            if disabled > 0:
                self.stdout.write(f'  Deshabilitadas: {disabled}')

            if total == 0:
                self.stdout.write(self.style.SUCCESS('  ✅ Sin tareas periódicas'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))
