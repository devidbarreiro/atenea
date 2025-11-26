# Generated manually for adding permission groups

from django.db import migrations


def create_groups_and_permissions(apps, schema_editor):
    """Crea los grupos de permisos y asigna los permisos correspondientes con IDs específicos"""
    
    db = schema_editor.connection
    is_postgres = 'postgresql' in db.vendor
    
    # Crear grupos con IDs específicos
    groups_data = [
        (3, 'usar'),
        (4, 'ver'),
        (5, 'crear'),
        (6, 'editar'),
        (7, 'borrar'),
        (8, 'admin'),
    ]
    
    # Mapeo de permisos por grupo con IDs específicos de auth_group_permissions
    # Formato: (auth_group_permissions_id, group_id, permission_id)
    group_permissions_data = [
        # Grupo 4 (ver): IDs 41-60
        (41, 4, 4), (42, 4, 8), (43, 4, 12), (44, 4, 16), (45, 4, 20),
        (46, 4, 24), (47, 4, 28), (48, 4, 32), (49, 4, 36), (50, 4, 40),
        (51, 4, 44), (52, 4, 48), (53, 4, 52), (54, 4, 56), (55, 4, 60),
        (56, 4, 64), (57, 4, 68), (58, 4, 72), (59, 4, 76), (60, 4, 80),
        # Grupo 3 (usar): IDs 61-80
        (61, 3, 61), (62, 3, 62), (63, 3, 63), (64, 3, 64), (65, 3, 65),
        (66, 3, 66), (67, 3, 67), (68, 3, 68), (69, 3, 69), (70, 3, 70),
        (71, 3, 71), (72, 3, 72), (73, 3, 73), (74, 3, 74), (75, 3, 75),
        (76, 3, 76), (77, 3, 77), (78, 3, 78), (79, 3, 79), (80, 3, 80),
        # Grupo 6 (editar): IDs 81-100
        (81, 6, 2), (82, 6, 6), (83, 6, 10), (84, 6, 14), (85, 6, 18),
        (86, 6, 22), (87, 6, 26), (88, 6, 30), (89, 6, 34), (90, 6, 38),
        (91, 6, 42), (92, 6, 46), (93, 6, 50), (94, 6, 54), (95, 6, 58),
        (96, 6, 62), (97, 6, 66), (98, 6, 70), (99, 6, 74), (100, 6, 78),
        # Grupo 5 (crear): IDs 101-120
        (101, 5, 1), (102, 5, 5), (103, 5, 9), (104, 5, 13), (105, 5, 17),
        (106, 5, 21), (107, 5, 25), (108, 5, 29), (109, 5, 33), (110, 5, 37),
        (111, 5, 41), (112, 5, 45), (113, 5, 49), (114, 5, 53), (115, 5, 57),
        (116, 5, 61), (117, 5, 65), (118, 5, 69), (119, 5, 73), (120, 5, 77),
        # Grupo 7 (borrar): IDs 121-140
        (121, 7, 3), (122, 7, 7), (123, 7, 11), (124, 7, 15), (125, 7, 19),
        (126, 7, 23), (127, 7, 27), (128, 7, 31), (129, 7, 35), (130, 7, 39),
        (131, 7, 43), (132, 7, 47), (133, 7, 51), (134, 7, 55), (135, 7, 59),
        (136, 7, 63), (137, 7, 67), (138, 7, 71), (139, 7, 75), (140, 7, 79),
        # Grupo 8 (admin): IDs 141-220 (permisos 1-80)
        (141, 8, 1), (142, 8, 2), (143, 8, 3), (144, 8, 4), (145, 8, 5),
        (146, 8, 6), (147, 8, 7), (148, 8, 8), (149, 8, 9), (150, 8, 10),
        (151, 8, 11), (152, 8, 12), (153, 8, 13), (154, 8, 14), (155, 8, 15),
        (156, 8, 16), (157, 8, 17), (158, 8, 18), (159, 8, 19), (160, 8, 20),
        (161, 8, 21), (162, 8, 22), (163, 8, 23), (164, 8, 24), (165, 8, 25),
        (166, 8, 26), (167, 8, 27), (168, 8, 28), (169, 8, 29), (170, 8, 30),
        (171, 8, 31), (172, 8, 32), (173, 8, 33), (174, 8, 34), (175, 8, 35),
        (176, 8, 36), (177, 8, 37), (178, 8, 38), (179, 8, 39), (180, 8, 40),
        (181, 8, 41), (182, 8, 42), (183, 8, 43), (184, 8, 44), (185, 8, 45),
        (186, 8, 46), (187, 8, 47), (188, 8, 48), (189, 8, 49), (190, 8, 50),
        (191, 8, 51), (192, 8, 52), (193, 8, 53), (194, 8, 54), (195, 8, 55),
        (196, 8, 56), (197, 8, 57), (198, 8, 58), (199, 8, 59), (200, 8, 60),
        (201, 8, 61), (202, 8, 62), (203, 8, 63), (204, 8, 64), (205, 8, 65),
        (206, 8, 66), (207, 8, 67), (208, 8, 68), (209, 8, 69), (210, 8, 70),
        (211, 8, 71), (212, 8, 72), (213, 8, 73), (214, 8, 74), (215, 8, 75),
        (216, 8, 76), (217, 8, 77), (218, 8, 78), (219, 8, 79), (220, 8, 80),
    ]
    
    # Usar raw_connection para evitar problemas con debug SQL de Django
    raw_conn = schema_editor.connection.connection
    cursor = raw_conn.cursor()
    
    try:
        # Crear grupos
        for group_id, group_name in groups_data:
            if is_postgres:
                cursor.execute(
                    "INSERT INTO auth_group (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                    (group_id, group_name)
                )
            else:
                # SQLite: usar INSERT OR REPLACE
                cursor.execute(
                    "INSERT OR REPLACE INTO auth_group (id, name) VALUES (?, ?)",
                    (group_id, group_name)
                )
        
        # Crear relaciones grupo-permiso con IDs específicos
        for agp_id, group_id, permission_id in group_permissions_data:
            # Verificar que el grupo y permiso existen antes de insertar
            if is_postgres:
                cursor.execute("SELECT COUNT(*) FROM auth_group WHERE id = %s", (group_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM auth_group WHERE id = ?", (group_id,))
            group_exists = cursor.fetchone()[0] > 0
            
            if is_postgres:
                cursor.execute("SELECT COUNT(*) FROM auth_permission WHERE id = %s", (permission_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM auth_permission WHERE id = ?", (permission_id,))
            perm_exists = cursor.fetchone()[0] > 0
            
            if group_exists and perm_exists:
                if is_postgres:
                    cursor.execute(
                        "INSERT INTO auth_group_permissions (id, group_id, permission_id) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                        (agp_id, group_id, permission_id)
                    )
                else:
                    # SQLite: usar INSERT OR IGNORE
                    cursor.execute(
                        "INSERT OR IGNORE INTO auth_group_permissions (id, group_id, permission_id) VALUES (?, ?, ?)",
                        (agp_id, group_id, permission_id)
                    )
        
        raw_conn.commit()
    finally:
        cursor.close()


def reverse_migration(apps, schema_editor):
    """Elimina los grupos y permisos creados (opcional, para rollback)"""
    raw_conn = schema_editor.connection.connection
    cursor = raw_conn.cursor()
    
    try:
        # Eliminar relaciones grupo-permiso (IDs 41-220)
        cursor.execute("DELETE FROM auth_group_permissions WHERE id BETWEEN 41 AND 220")
        # Eliminar grupos (IDs 3-8)
        cursor.execute("DELETE FROM auth_group WHERE id BETWEEN 3 AND 8")
        raw_conn.commit()
    finally:
        cursor.close()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_usercredits_credittransaction_serviceusage'),
        ('auth', '0012_alter_user_first_name_max_length'),  # Asegurar que auth está migrado
    ]

    operations = [
        migrations.RunPython(create_groups_and_permissions, reverse_migration),
    ]

