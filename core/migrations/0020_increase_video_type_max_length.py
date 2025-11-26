# Generated manually to fix max_length for Video.type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_add_permission_groups'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='type',
            field=models.CharField(choices=[('heygen_avatar_v2', 'HeyGen Avatar V2'), ('heygen_avatar_iv', 'HeyGen Avatar IV'), ('gemini_veo', 'Gemini Veo'), ('sora', 'OpenAI Sora'), ('higgsfield_dop_standard', 'Higgsfield DoP Standard'), ('higgsfield_dop_preview', 'Higgsfield DoP Preview'), ('higgsfield_seedance_v1_pro', 'Higgsfield Seedance V1 Pro'), ('higgsfield_kling_v2_1_pro', 'Higgsfield Kling V2.1 Pro'), ('kling_v1', 'Kling V1'), ('kling_v1_5', 'Kling V1.5'), ('kling_v1_6', 'Kling V1.6'), ('kling_v2_master', 'Kling V2 Master'), ('kling_v2_1', 'Kling V2.1'), ('kling_v2_5_turbo', 'Kling V2.5 Turbo')], max_length=30),
        ),
    ]

