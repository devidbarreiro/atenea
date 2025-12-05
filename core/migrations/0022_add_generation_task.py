# Generated manually for GenerationTask model
#
# NOTA: Esta migración tiene un bug de diseño - task_id se define como NOT NULL y unique,
# pero el código en queue.py crea GenerationTask con task_id=None antes de encolar.
# La migración 0025_fix_generation_task_task_id_nullable corrige esto.
# Para nuevas instalaciones, usar la migración squashed que tiene task_id nullable desde el inicio.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0021_alter_scene_ai_service'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenerationTask',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID único de la tarea', primary_key=True, serialize=False)),
                ('task_id', models.CharField(db_index=True, help_text='Celery task ID', max_length=255, unique=True)),
                ('task_type', models.CharField(choices=[('video', 'Video'), ('image', 'Imagen'), ('audio', 'Audio'), ('scene', 'Escena')], help_text='Tipo de generación', max_length=20)),
                ('item_uuid', models.UUIDField(db_index=True, help_text='UUID del item generado (no ID numérico)')),
                ('status', models.CharField(choices=[('queued', 'En Cola'), ('processing', 'Procesando'), ('completed', 'Completado'), ('failed', 'Fallido'), ('cancelled', 'Cancelado')], db_index=True, default='queued', help_text='Estado de la tarea', max_length=20)),
                ('queue_name', models.CharField(help_text='Nombre de la cola de Celery', max_length=50)),
                ('priority', models.IntegerField(default=5, help_text='Prioridad (1-10, mayor = más prioridad, por tipo de generación)')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, help_text='Mensaje de error o razón de cancelación', null=True)),
                ('retry_count', models.IntegerField(default=0, help_text='Número de reintentos realizados')),
                ('max_retries', models.IntegerField(default=3, help_text='Máximo número de reintentos permitidos')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Metadata adicional (prompt, parámetros, etc.)')),
                ('user', models.ForeignKey(help_text='Usuario que creó la tarea', on_delete=django.db.models.deletion.CASCADE, related_name='generation_tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tarea de Generación',
                'verbose_name_plural': 'Tareas de Generación',
                'db_table': 'generation_task',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='generationtask',
            index=models.Index(fields=['user', 'status'], name='core_genera_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='generationtask',
            index=models.Index(fields=['task_type', 'item_uuid'], name='core_genera_task_ty_idx'),
        ),
        migrations.AddIndex(
            model_name='generationtask',
            index=models.Index(fields=['status', 'created_at'], name='core_genera_status_idx'),
        ),
        migrations.AddIndex(
            model_name='generationtask',
            index=models.Index(fields=['queue_name', 'priority', 'created_at'], name='core_genera_queue_n_idx'),
        ),
    ]




