# Generated manually
import uuid
from django.db import migrations, models


def gen_uuid(apps, schema_editor):
    """Generar UUIDs únicos para registros existentes"""
    Video = apps.get_model('core', 'Video')
    Image = apps.get_model('core', 'Image')
    Audio = apps.get_model('core', 'Audio')
    
    for model in [Video, Image, Audio]:
        for obj in model.objects.all():
            obj.uuid = uuid.uuid4()
            obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_fix_generation_task_task_id_nullable'),
    ]

    operations = [
        # Paso 1: Agregar campo uuid como nullable
        migrations.AddField(
            model_name='video',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='UUID público para URLs y storage', null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='UUID público para URLs y storage', null=True),
        ),
        migrations.AddField(
            model_name='audio',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='UUID público para URLs y storage', null=True),
        ),
        
        # Paso 2: Generar UUIDs para registros existentes
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
        
        # Paso 3: Hacer el campo non-nullable y unique
        migrations.AlterField(
            model_name='video',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='UUID público para URLs y storage', unique=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='UUID público para URLs y storage', unique=True),
        ),
        migrations.AlterField(
            model_name='audio',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='UUID público para URLs y storage', unique=True),
        ),
    ]




