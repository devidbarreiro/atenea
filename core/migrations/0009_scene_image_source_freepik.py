# Generated manually for Freepik integration
# Migration for adding image_source and freepik_resource_id to Scene

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_script_video_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='scene',
            name='image_source',
            field=models.CharField(
                choices=[
                    ('ai_generated', 'Generada con IA'),
                    ('freepik_stock', 'Freepik Stock'),
                    ('user_upload', 'Subida por Usuario')
                ],
                default='ai_generated',
                help_text='Origen de la imagen preview/referencia',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='scene',
            name='freepik_resource_id',
            field=models.CharField(
                blank=True,
                help_text='ID del recurso de Freepik si se usó stock',
                max_length=255,
                null=True
            ),
        ),
    ]

