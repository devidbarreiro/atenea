# Generated manually for video configuration fields
# Migration for adding video_type, video_orientation, and generate_previews to Script

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_script_agent_flow_script_final_video_scene'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='video_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('ultra', 'Modo Ultra (Veo3 y Sora2)'),
                    ('avatar', 'Con Avatares (HeyGen)'),
                    ('general', 'Video General')
                ],
                help_text='Tipo de video para el flujo del agente',
                max_length=20,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='script',
            name='video_orientation',
            field=models.CharField(
                choices=[
                    ('16:9', 'Horizontal (16:9)'),
                    ('9:16', 'Vertical (9:16)')
                ],
                default='16:9',
                help_text='Orientación del video (heredada a todas las escenas)',
                max_length=10
            ),
        ),
        migrations.AddField(
            model_name='script',
            name='generate_previews',
            field=models.BooleanField(
                default=True,
                help_text='Si se deben generar previews automáticamente'
            ),
        ),
    ]

