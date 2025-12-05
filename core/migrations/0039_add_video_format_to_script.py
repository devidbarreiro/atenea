# Generated migration for adding video_format to Script

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_add_continuity_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='script',
            name='video_format',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('social', 'Redes Sociales (Reels/TikTok)'),
                    ('educational', 'Video Educativo (Píldora)'),
                    ('longform', 'Video Largo (YouTube/Masterclass)'),
                ],
                default='educational',
                blank=True,
                null=True,
                help_text='Formato de video según uso (estructura y duraciones de escenas)'
            ),
        ),
    ]


