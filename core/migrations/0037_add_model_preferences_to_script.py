# Generated migration for adding model_preferences to Script

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_increase_prompt_text_length_to_2000'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='model_preferences',
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text='Preferencias de modelos por servicio. Ejemplo: {"gemini_veo": "veo-3.1-generate-preview", "sora": "sora-2", "heygen": "heygen_v2", "default_voice_id": "voice_id"}'
            ),
        ),
    ]


