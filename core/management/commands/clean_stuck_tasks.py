"""
Comando Django para limpiar tareas atascadas en la BD.

Uso: python manage.py clean_stuck_tasks [--dry-run]

Limpia:
- GenerationTasks en estado 'queued' o 'failed'
- Videos/Imágenes/Audios atascados en 'pending' o 'processing'

Opciones:
  --dry-run: Mostrar qué se eliminaría sin eliminar nada
"""

from django.core.management.base import BaseCommand
from core.models import GenerationTask, Video, Image, Audio
from datetime import datetime


class Command(BaseCommand):
    help = 'Limpia tareas atascadas en la BD'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se eliminaría sin eliminar nada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🧹 Limpiador de Tareas Atascadas'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  MODO DRY-RUN: No se eliminará nada\n'))

        total_deleted = 0

        # 1. Limpiar GenerationTasks
        self.stdout.write(self.style.WARNING('\n📋 GenerationTasks'))
        total_deleted += self._clean_generation_tasks(dry_run)

        # 2. Limpiar Videos atascados
        self.stdout.write(self.style.WARNING('\n📹 Videos atascados'))
        total_deleted += self._clean_stuck_videos(dry_run)

        # 3. Limpiar Imágenes atascadas
        self.stdout.write(self.style.WARNING('\n🖼️  Imágenes atascadas'))
        total_deleted += self._clean_stuck_images(dry_run)

        # 4. Limpiar Audios atascados
        self.stdout.write(self.style.WARNING('\n🔊 Audios atascados'))
        total_deleted += self._clean_stuck_audios(dry_run)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        if dry_run:
            self.stdout.write(self.style.WARNING(f'📊 Total que se eliminaría: {total_deleted} items'))
            self.stdout.write(self.style.WARNING('\n💡 Para aplicar estos cambios, ejecuta sin --dry-run'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✨ Total eliminados: {total_deleted} items'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

    def _clean_generation_tasks(self, dry_run):
        """Limpiar GenerationTasks en estado queued o failed"""
        # Tareas queued
        queued = GenerationTask.objects.filter(status='queued')
        failed = GenerationTask.objects.filter(status='failed')

        queued_count = queued.count()
        failed_count = failed.count()

        self.stdout.write(f'  Queued: {queued_count}')
        self.stdout.write(f'  Failed: {failed_count}')

        if not dry_run:
            queued.delete()
            failed.delete()

        total = queued_count + failed_count
        if total > 0 and not dry_run:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Eliminados {total}'))
        elif total > 0:
            self.stdout.write(self.style.WARNING(f'  ℹ️  Estos serían eliminados'))

        return total

    def _clean_stuck_videos(self, dry_run):
        """Limpiar Videos en estado pending o processing"""
        stuck = Video.objects.filter(status__in=['pending', 'processing'])
        count = stuck.count()

        self.stdout.write(f'  Atascados: {count}')

        if count > 0:
            for video in stuck:
                self.stdout.write(f'    - {video.uuid}: {video.title} ({video.status})')

            if not dry_run:
                stuck.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✅ Eliminados {count}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  Estos serían eliminados'))

        return count

    def _clean_stuck_images(self, dry_run):
        """Limpiar Imágenes en estado pending o processing"""
        stuck = Image.objects.filter(status__in=['pending', 'processing'])
        count = stuck.count()

        self.stdout.write(f'  Atascadas: {count}')

        if count > 0:
            for image in stuck:
                self.stdout.write(f'    - {image.uuid}: {image.title} ({image.status})')

            if not dry_run:
                stuck.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✅ Eliminadas {count}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  Estas serían eliminadas'))

        return count

    def _clean_stuck_audios(self, dry_run):
        """Limpiar Audios en estado pending o processing"""
        stuck = Audio.objects.filter(status__in=['pending', 'processing'])
        count = stuck.count()

        self.stdout.write(f'  Atascados: {count}')

        if count > 0:
            for audio in stuck:
                self.stdout.write(f'    - {audio.uuid}: {audio.title} ({audio.status})')

            if not dry_run:
                stuck.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✅ Eliminados {count}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ℹ️  Estos serían eliminados'))

        return count
