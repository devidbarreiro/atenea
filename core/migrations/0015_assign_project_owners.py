# Generated manually

from django.db import migrations


def assign_project_owners(apps, schema_editor):
    """
    Asigna un owner a todos los proyectos existentes que no tengan uno.
    Si hay proyectos sin owner, se asigna al primer usuario activo disponible.
    """
    Project = apps.get_model('core', 'Project')
    User = apps.get_model('auth', 'User')
    
    # Obtener proyectos sin owner
    projects_without_owner = Project.objects.filter(owner__isnull=True)
    
    if projects_without_owner.exists():
        # Obtener el primer usuario activo (o el superuser si existe)
        first_user = User.objects.filter(is_active=True).order_by('id').first()
        
        if first_user:
            # Asignar el primer usuario como owner de todos los proyectos sin owner
            projects_without_owner.update(owner=first_user)
            print(f"Asignados {projects_without_owner.count()} proyectos al usuario {first_user.username}")
        else:
            print("ADVERTENCIA: No hay usuarios activos. Los proyectos quedan sin owner.")


def reverse_assign_project_owners(apps, schema_editor):
    """Reversa la migración (no hace nada, ya que owner puede ser null)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_add_project_sharing'),
    ]

    operations = [
        migrations.RunPython(assign_project_owners, reverse_assign_project_owners),
    ]

