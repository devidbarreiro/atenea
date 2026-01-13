# Generated manually to fix missing generation_task table
# This migration handles the case where the squashed migration was marked as fake
# and the generation_task table was never actually created in the database

from django.conf import settings
from django.db import migrations, models
from django.db import connection
import django.db.models.deletion
import uuid


def create_generation_task_table_if_missing(apps, schema_editor):
    """
    Crea la tabla generation_task si no existe.
    Esta función maneja el caso donde la migración squashed estaba marcada como fake
    y la tabla nunca se creó realmente.
    """
    db_alias = schema_editor.connection.alias
    vendor = connection.vendor
    
    # Verificar si la tabla ya existe (compatible con SQLite y PostgreSQL)
    table_exists = False
    with connection.cursor() as cursor:
        if vendor == 'sqlite':
            # SQLite: usar sqlite_master
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='generation_task'
            """)
            table_exists = cursor.fetchone() is not None
        else:
            # PostgreSQL y otros: usar information_schema
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'generation_task'
                );
            """)
            table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        # Crear la tabla con SQL directo (compatible con SQLite y PostgreSQL)
        with connection.cursor() as cursor:
            if vendor == 'sqlite':
                # SQLite: usar TEXT para UUID y JSON, TIMESTAMP sin TIME ZONE
                cursor.execute("""
                    CREATE TABLE generation_task (
                        uuid TEXT NOT NULL PRIMARY KEY,
                        task_id VARCHAR(255) NULL,
                        task_type VARCHAR(20) NOT NULL,
                        item_uuid TEXT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'queued',
                        queue_name VARCHAR(50) NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 5,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        started_at DATETIME NULL,
                        completed_at DATETIME NULL,
                        error_message TEXT NULL,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        max_retries INTEGER NOT NULL DEFAULT 3,
                        metadata TEXT NOT NULL DEFAULT '{}',
                        user_id INTEGER NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
                    );
                """)
            else:
                # PostgreSQL: usar tipos UUID y JSONB nativos
                cursor.execute("""
                    CREATE TABLE generation_task (
                        uuid UUID NOT NULL PRIMARY KEY,
                        task_id VARCHAR(255) NULL,
                        task_type VARCHAR(20) NOT NULL,
                        item_uuid UUID NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'queued',
                        queue_name VARCHAR(50) NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 5,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        started_at TIMESTAMP WITH TIME ZONE NULL,
                        completed_at TIMESTAMP WITH TIME ZONE NULL,
                        error_message TEXT NULL,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        max_retries INTEGER NOT NULL DEFAULT 3,
                        metadata JSONB NOT NULL DEFAULT '{}',
                        user_id INTEGER NOT NULL,
                        CONSTRAINT generation_task_user_id_fkey 
                            FOREIGN KEY (user_id) 
                            REFERENCES auth_user(id) 
                            ON DELETE CASCADE
                    );
                """)
            
            # Crear índices (usando los nombres renombrados de la migración 0024)
            # Usar IF NOT EXISTS para evitar errores si los índices ya existen
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation__user_id_7f7fbf_idx 
                ON generation_task(user_id, status);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation__task_ty_5520e3_idx 
                ON generation_task(task_type, item_uuid);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation__status_9aa419_idx 
                ON generation_task(status, created_at);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation__queue_n_5acd90_idx 
                ON generation_task(queue_name, priority, created_at);
            """)
            
            # Índices adicionales para campos individuales
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation_task_task_id_idx 
                ON generation_task(task_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation_task_item_uuid_idx 
                ON generation_task(item_uuid);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS generation_task_created_at_idx 
                ON generation_task(created_at);
            """)
            
            # Nota: task_id NO es único (la migración 0030 eliminó el unique constraint)
            # Solo tiene un índice normal para búsquedas rápidas
            
            # Añadir comentarios para documentación (solo PostgreSQL)
            if vendor != 'sqlite':
                cursor.execute("""
                    COMMENT ON TABLE generation_task IS 'Tareas de generación en cola';
                    COMMENT ON COLUMN generation_task.uuid IS 'UUID único de la tarea';
                    COMMENT ON COLUMN generation_task.task_id IS 'Celery task ID (puede ser null antes de que Celery procese la tarea)';
                    COMMENT ON COLUMN generation_task.task_type IS 'Tipo de generación (video, image, audio, scene)';
                    COMMENT ON COLUMN generation_task.item_uuid IS 'UUID del item generado (no ID numérico)';
                    COMMENT ON COLUMN generation_task.status IS 'Estado de la tarea (queued, processing, completed, failed, cancelled)';
                """)


def reverse_create_generation_task_table(apps, schema_editor):
    """Revertir la creación de la tabla generation_task"""
    vendor = connection.vendor
    
    with connection.cursor() as cursor:
        # Verificar si la tabla existe (compatible con SQLite y PostgreSQL)
        table_exists = False
        if vendor == 'sqlite':
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='generation_task'
            """)
            table_exists = cursor.fetchone() is not None
        else:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'generation_task'
                );
            """)
            table_exists = cursor.fetchone()[0]
        
        if table_exists:
            if vendor == 'sqlite':
                cursor.execute("DROP TABLE IF EXISTS generation_task;")
            else:
                cursor.execute("DROP TABLE IF EXISTS generation_task CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0043_add_uuid_to_project_if_missing'),
    ]

    operations = [
        # Separar operaciones de base de datos y estado del modelo
        migrations.SeparateDatabaseAndState(
            # Operaciones de base de datos: crear tabla si no existe
            database_operations=[
                migrations.RunPython(
                    create_generation_task_table_if_missing,
                    reverse_create_generation_task_table,
                ),
            ],
            # Operaciones de estado: registrar el modelo en Django
            state_operations=[
                migrations.CreateModel(
                    name='GenerationTask',
                    fields=[
                        ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID único de la tarea', primary_key=True, serialize=False)),
                        ('task_id', models.CharField(blank=True, db_index=True, help_text='Celery task ID (puede ser null antes de que Celery procese la tarea)', max_length=255, null=True)),
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
                # Añadir índices (usando los nombres renombrados de la migración 0024)
                migrations.AddIndex(
                    model_name='generationtask',
                    index=models.Index(fields=['user', 'status'], name='generation__user_id_7f7fbf_idx'),
                ),
                migrations.AddIndex(
                    model_name='generationtask',
                    index=models.Index(fields=['task_type', 'item_uuid'], name='generation__task_ty_5520e3_idx'),
                ),
                migrations.AddIndex(
                    model_name='generationtask',
                    index=models.Index(fields=['status', 'created_at'], name='generation__status_9aa419_idx'),
                ),
                migrations.AddIndex(
                    model_name='generationtask',
                    index=models.Index(fields=['queue_name', 'priority', 'created_at'], name='generation__queue_n_5acd90_idx'),
                ),
            ],
        ),
    ]

