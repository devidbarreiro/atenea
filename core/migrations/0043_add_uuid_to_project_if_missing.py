# Generated manually to fix missing uuid column in core_project
# This migration handles the case where the squashed migration was marked as fake
# and the uuid column was never actually added to the database

import uuid
from django.db import migrations, models
from django.db import connection


def add_uuid_column_if_missing(apps, schema_editor):
    """
    Añade la columna uuid a core_project si no existe.
    Si ya existe, solo genera UUIDs para los registros que no tengan.
    """
    db_alias = schema_editor.connection.alias
    vendor = connection.vendor
    
    # Verificar si la columna ya existe (compatible con SQLite y PostgreSQL)
    column_exists = False
    with connection.cursor() as cursor:
        if vendor == 'sqlite':
            # SQLite: usar PRAGMA table_info
            cursor.execute("PRAGMA table_info(core_project)")
            columns = [row[1] for row in cursor.fetchall()]
            column_exists = 'uuid' in columns
        else:
            # PostgreSQL y otros: usar information_schema
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='core_project' AND column_name='uuid'
            """)
            column_exists = cursor.fetchone() is not None
    
    if not column_exists:
        # Añadir columna nullable primero (compatible con SQLite y PostgreSQL)
        with connection.cursor() as cursor:
            if vendor == 'sqlite':
                # SQLite: usar TEXT para UUID (se almacena como string)
                cursor.execute("""
                    ALTER TABLE core_project 
                    ADD COLUMN uuid TEXT NULL;
                """)
            else:
                # PostgreSQL: usar tipo UUID
                cursor.execute("""
                    ALTER TABLE core_project 
                    ADD COLUMN uuid UUID NULL;
                """)
            
            # Crear índice
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS core_project_uuid_idx ON core_project(uuid);
            """)
    
    # Generar UUIDs para registros existentes que no tengan
    Project = apps.get_model('core', 'Project')
    for project in Project.objects.using(db_alias).all():
        if not project.uuid:
            project.uuid = uuid.uuid4()
            project.save(update_fields=['uuid'])
    
    # Si la columna no existía, hacerla NOT NULL y UNIQUE
    if not column_exists:
        with connection.cursor() as cursor:
            # Verificar si hay NULLs antes de hacer NOT NULL
            cursor.execute("SELECT COUNT(*) FROM core_project WHERE uuid IS NULL")
            null_count = cursor.fetchone()[0]
            
            if null_count == 0:
                # Hacer NOT NULL (compatible con SQLite y PostgreSQL)
                if vendor == 'sqlite':
                    # SQLite requiere recrear la tabla para cambiar NOT NULL
                    # Por ahora, dejamos nullable y Django manejará el constraint a nivel de aplicación
                    pass
                else:
                    # PostgreSQL: hacer NOT NULL
                    cursor.execute("""
                        ALTER TABLE core_project 
                        ALTER COLUMN uuid SET NOT NULL;
                    """)
                
                # Añadir constraint UNIQUE (compatible con ambos)
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS core_project_uuid_unique 
                    ON core_project(uuid);
                """)


def reverse_add_uuid_column(apps, schema_editor):
    """Revertir la adición de la columna uuid"""
    vendor = connection.vendor
    
    with connection.cursor() as cursor:
        # Verificar si la columna existe (compatible con SQLite y PostgreSQL)
        column_exists = False
        if vendor == 'sqlite':
            cursor.execute("PRAGMA table_info(core_project)")
            columns = [row[1] for row in cursor.fetchall()]
            column_exists = 'uuid' in columns
        else:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='core_project' AND column_name='uuid'
            """)
            column_exists = cursor.fetchone() is not None
        
        if column_exists:
            # Eliminar índice único primero
            cursor.execute("""
                DROP INDEX IF EXISTS core_project_uuid_unique;
            """)
            # Eliminar índice normal
            cursor.execute("""
                DROP INDEX IF EXISTS core_project_uuid_idx;
            """)
            # Eliminar columna (SQLite y PostgreSQL soportan DROP COLUMN)
            if vendor == 'sqlite':
                # SQLite 3.35.0+ soporta DROP COLUMN
                try:
                    cursor.execute("""
                        ALTER TABLE core_project 
                        DROP COLUMN uuid;
                    """)
                except Exception:
                    # Si la versión de SQLite no soporta DROP COLUMN, saltar
                    pass
            else:
                cursor.execute("""
                    ALTER TABLE core_project 
                    DROP COLUMN uuid;
                """)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0042_add_uploaded_audio_type'),
    ]

    operations = [
        # Separar operaciones de base de datos y estado del modelo
        migrations.SeparateDatabaseAndState(
            # Operaciones de base de datos: añadir columna si no existe
            database_operations=[
                migrations.RunPython(
                    add_uuid_column_if_missing,
                    reverse_add_uuid_column,
                ),
            ],
            # Operaciones de estado: actualizar el modelo Django
            state_operations=[
                migrations.AddField(
                    model_name='project',
                    name='uuid',
                    field=models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        null=True,  # Temporalmente nullable
                        blank=True,
                    ),
                ),
                migrations.AlterField(
                    model_name='project',
                    name='uuid',
                    field=models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True
                    ),
                ),
            ],
        ),
    ]

