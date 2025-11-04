# Generated manually 2025-11-03

from django.db import migrations


def migrate_heygen_to_v2(apps, schema_editor):
    """Migra los servicios 'heygen' existentes a 'heygen_v2'"""
    Scene = apps.get_model('core', 'Scene')
    Scene.objects.filter(ai_service='heygen').update(ai_service='heygen_v2')


def reverse_heygen_migration(apps, schema_editor):
    """Revierte la migración de heygen_v2 a heygen"""
    Scene = apps.get_model('core', 'Scene')
    Scene.objects.filter(ai_service='heygen_v2').update(ai_service='heygen')
    Scene.objects.filter(ai_service='heygen_avatar_iv').update(ai_service='heygen')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_scene_image_source_freepik'),
    ]

    operations = [
        migrations.RunPython(migrate_heygen_to_v2, reverse_heygen_migration),
    ]

