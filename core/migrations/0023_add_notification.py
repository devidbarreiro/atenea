# Generated manually for Notification model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0022_add_generation_task'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID único de la notificación', primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('generation_completed', 'Generación Completada'), ('generation_failed', 'Generación Fallida'), ('generation_progress', 'Progreso de Generación'), ('credits_low', 'Créditos Bajos'), ('credits_insufficient', 'Créditos Insuficientes'), ('project_invitation', 'Invitación de Proyecto'), ('system_maintenance', 'Mantenimiento del Sistema'), ('info', 'Información')], help_text='Tipo de notificación', max_length=50)),
                ('title', models.CharField(help_text='Título de la notificación', max_length=255)),
                ('message', models.TextField(help_text='Mensaje de la notificación')),
                ('read', models.BooleanField(db_index=True, default=False, help_text='Si la notificación ha sido leída')),
                ('action_url', models.CharField(blank=True, help_text='URL de acción (opcional)', max_length=500, null=True)),
                ('action_label', models.CharField(blank=True, help_text='Etiqueta del botón de acción', max_length=100, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Metadata adicional (progreso, item_uuid, etc.)')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(help_text='Usuario destinatario', on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notificación',
                'verbose_name_plural': 'Notificaciones',
                'db_table': 'notification',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'read', 'created_at'], name='core_notifi_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'type', 'created_at'], name='core_notifi_user_ty_idx'),
        ),
    ]




