"""
Comando para generar INSERTs SQL de permisos de usuario.

Uso: 
    python manage.py generate_permission_inserts <source_username> <target_username> [--output archivo.txt]
    
Ejemplo:
    python manage.py generate_permission_inserts juan david
    python manage.py generate_permission_inserts juan david --output permisos.txt
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
import os


class Command(BaseCommand):
    help = 'Genera INSERTs SQL para copiar permisos de un usuario a otro'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_username',
            type=str,
            help='Username del usuario que tiene los permisos (tu compañero)'
        )
        parser.add_argument(
            'target_username',
            type=str,
            help='Username del usuario que recibirá los permisos (tú)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Ruta del archivo .txt donde guardar los INSERTs (opcional, se genera automático si no se especifica)'
        )

    def handle(self, *args, **options):
        source_username = options['source_username']
        target_username = options['target_username']
        output_file = options['output']
        
        try:
            source_user = User.objects.get(username=source_username)
            target_user = User.objects.get(username=target_username)
        except User.DoesNotExist as e:
            raise CommandError(f'Usuario no encontrado: {e}')
        
        # Obtener todos los permisos del usuario fuente
        source_permissions = source_user.user_permissions.all()
        
        if not source_permissions.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'El usuario "{source_username}" no tiene permisos asignados.'
                )
            )
            return
        
        # Obtener permisos que ya tiene el usuario destino (para evitar duplicados)
        target_permission_ids = set(target_user.user_permissions.values_list('id', flat=True))
        
        # Generar INSERTs SQL
        inserts = []
        new_permissions = []
        
        for perm in source_permissions:
            if perm.id not in target_permission_ids:
                insert_sql = f"INSERT INTO auth_user_user_permissions (user_id, permission_id) VALUES ({target_user.id}, {perm.id});"
                inserts.append(insert_sql)
                new_permissions.append(f"  - {perm.content_type.app_label}.{perm.codename}")
        
        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('RESUMEN DE PERMISOS'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'Usuario fuente: {source_username} (ID: {source_user.id})')
        self.stdout.write(f'Usuario destino: {target_username} (ID: {target_user.id})')
        self.stdout.write(f'\nPermisos totales del usuario fuente: {source_permissions.count()}')
        self.stdout.write(f'Permisos nuevos a agregar: {len(inserts)}')
        
        if not inserts:
            self.stdout.write(
                self.style.WARNING(
                    f'\nEl usuario "{target_username}" ya tiene todos los permisos de "{source_username}".'
                )
            )
            return
        
        if new_permissions:
            self.stdout.write('\nPermisos que se agregarán:')
            for perm in new_permissions:
                self.stdout.write(perm)
        
        # Generar contenido del archivo
        file_content = []
        file_content.append("=" * 70)
        file_content.append("INSERTS SQL PARA PERMISOS DE USUARIO")
        file_content.append("=" * 70)
        file_content.append("")
        file_content.append(f"Usuario fuente: {source_username} (ID: {source_user.id})")
        file_content.append(f"Usuario destino: {target_username} (ID: {target_user.id})")
        file_content.append(f"Fecha de generación: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_content.append("")
        file_content.append("=" * 70)
        file_content.append("INSTRUCCIONES:")
        file_content.append("=" * 70)
        file_content.append("1. Ejecuta estos INSERTs en tu base de datos SQL")
        file_content.append("2. Opción A - Desde Django shell:")
        file_content.append("   python manage.py shell")
        file_content.append("   >>> from django.db import connection")
        file_content.append("   >>> cursor = connection.cursor()")
        file_content.append("   >>> cursor.execute('INSERT ...')")
        file_content.append("   >>> connection.commit()")
        file_content.append("")
        file_content.append("3. Opción B - Desde dbshell:")
        file_content.append("   python manage.py dbshell")
        file_content.append("   # Luego pega los INSERTs de abajo")
        file_content.append("")
        file_content.append("=" * 70)
        file_content.append("INSERTS SQL:")
        file_content.append("=" * 70)
        file_content.append("")
        
        for insert in inserts:
            file_content.append(insert)
        
        file_content.append("")
        file_content.append("=" * 70)
        file_content.append("FIN")
        file_content.append("=" * 70)
        
        # Determinar nombre del archivo
        if output_file:
            filename = output_file
        else:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f'permisos_{source_username}_para_{target_username}_{timestamp}.txt'
        
        # Guardar archivo
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(file_content))
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Archivo guardado en: {os.path.abspath(filename)}'))
        except Exception as e:
            raise CommandError(f'Error al guardar archivo: {e}')
        
        # Mostrar los INSERTs en consola también
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('INSERTS SQL GENERADOS'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        for insert in inserts:
            self.stdout.write(insert)
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70 + '\n'))

