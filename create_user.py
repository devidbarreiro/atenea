#!/usr/bin/env python
"""Script temporal para crear usuario de prueba"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atenea.settings')
django.setup()

from django.contrib.auth.models import User

# Crear o actualizar usuario
user, created = User.objects.get_or_create(
    username='admin',
    email='admin@example.com',
    defaults={
        'is_staff': True,
        'is_superuser': True
    }
)

user.set_password('password')
user.save()

print(f'Usuario {"creado" if created else "actualizado"}: {user.username} ({user.email})')
print(f'Es staff: {user.is_staff}')
print(f'Es superusuario: {user.is_superuser}')

