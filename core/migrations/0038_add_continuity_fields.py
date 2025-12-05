# Generated migration for adding continuity fields to Script and Scene

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_add_model_preferences_to_script'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='character_reference_images',
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text='Imágenes de referencia de personajes. Ejemplo: {"char_1": "gcs_path/to/image.jpg"}'
            ),
        ),
        migrations.AddField(
            model_name='script',
            name='visual_style_guide',
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text='Guía de estilo visual compartida. Ejemplo: {"color_palette": ["#hex1", "#hex2"], "time_period": "Segunda Guerra Mundial", "visual_style": "Realista cinematográfico"}'
            ),
        ),
        migrations.AddField(
            model_name='scene',
            name='continuity_context',
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text='Contexto de continuidad con otras escenas. Ejemplo: {"references_previous_scenes": ["Escena 1"], "time_progression": "+2 horas", "maintained_elements": ["uniforme", "locación"]}'
            ),
        ),
    ]


