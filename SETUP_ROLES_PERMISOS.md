# Configuración de Roles y Permisos - Guía Práctica

## 🎯 Cómo Configurar los Roles en Django Admin

### 1. Acceder a Django Admin

1. Ir a: `http://localhost:8000/admin/`
2. Ingresar con un usuario superuser (admin)

### 2. Crear los Grupos de Permisos

En Django Admin:
- Ir a: **Authentication and Authorization** → **Groups**
- Click en **Add Group** (botón verde superior derecho)

---

## 📋 Crear Cada Rol

### Rol: **usar**
- **Nombre del Grupo**: `usar`
- **Permisos**: (ninguno - dejar vacío)
- Click en **Save**

### Rol: **ver**
- **Nombre del Grupo**: `ver`
- **Permisos Disponibles**: Buscar en la caja y seleccionar:
  - ✅ `auth | user | Can view user`
- Click en **Save**

### Rol: **crear**
- **Nombre del Grupo**: `crear`
- **Permisos Disponibles**: Seleccionar:
  - ✅ `auth | user | Can add user`
- Click en **Save**

### Rol: **editar**
- **Nombre del Grupo**: `editar`
- **Permisos Disponibles**: Seleccionar:
  - ✅ `auth | user | Can view user`
  - ✅ `auth | user | Can change user`
- Click en **Save**

### Rol: **borrar**
- **Nombre del Grupo**: `borrar`
- **Permisos Disponibles**: Seleccionar:
  - ✅ `auth | user | Can view user`
  - ✅ `auth | user | Can delete user`
- Click en **Save**

### Rol: **admin**
- **Nombre del Grupo**: `admin`
- **Permisos Disponibles**: Seleccionar TODO:
  - ✅ `auth | user | Can add user`
  - ✅ `auth | user | Can view user`
  - ✅ `auth | user | Can change user`
  - ✅ `auth | user | Can delete user`
- Click en **Save**

---

## 👥 Asignar Roles a Usuarios

### Opción 1: Desde Django Admin (Clásico)

1. Ir a: **Authentication and Authorization** → **Users**
2. Seleccionar un usuario
3. Bajar hasta la sección **Groups** (abajo a la derecha)
4. Seleccionar los grupos que quieres asignar (puedes marcar múltiples)
5. Click en **Save**

### Opción 2: Desde el Panel de Gestión de Usuarios (Panel Personalizado)

1. Ir a: `/users/menu/`
2. Click en **Administrar Usuarios**
3. Click en el botón ✏️ (lápiz) para editar
4. Marcar/desmarcar las **Roles** (grupos) en la tabla
5. Click en **Guardar cambios**

**Nota**: Si tienes múltiples roles, todos se acumulan. Ejemplo:
- Usuario con `ver` + `crear` = puede ver el panel admin Y puede crear usuarios
- Usuario con `crear` + `borrar` = puede crear usuarios Y eliminar usuarios

---

## 🔑 Tabla de Referencia Rápida

| Acción | Permiso Requerido |
|--------|------------------|
| Acceder al panel de admin (lista usuarios) | `auth.view_user` |
| Acceder al panel de crear usuarios | `auth.add_user` |
| Crear un usuario nuevo | `auth.add_user` |
| Editar datos de usuario (username, email, staff, active) | `auth.change_user` |
| Cambiar contraseña de otro usuario | `auth.change_user` |
| Cambiar propia contraseña | (sin permiso especial) |
| Eliminar un usuario | `auth.delete_user` |
| Eliminar múltiples usuarios | `auth.delete_user` |

---

## 🧪 Pruebas Rápidas

### Prueba 1: Usuario sin permisos
1. Crear un usuario nuevo (sin asignar grupos)
2. Intentar acceder a `/users/menu/`
3. **Resultado esperado**: Redirige a dashboard con mensaje "No tienes permiso..."

### Prueba 2: Usuario con rol 'crear'
1. Crear usuario y asignar grupo `crear`
2. Acceder a `/users/menu/`
3. **Resultado esperado**: 
   - ✅ Ve la tarjeta "Crear Usuarios" activa
   - ❌ NO ve la tarjeta "Administrar Usuarios"
   - ✅ Puede crear usuarios nuevo
   - ❌ No puede acceder a la lista de admin

### Prueba 3: Usuario con rol 'ver'
1. Crear usuario y asignar grupo `ver`
2. Acceder a `/users/menu/`
3. **Resultado esperado**:
   - ❌ Ve la tarjeta "Crear Usuarios" deshabilitada (gris)
   - ✅ Ve la tarjeta "Administrar Usuarios" activa
   - ❌ No puede crear usuarios
   - ✅ Puede ver la lista de usuarios

### Prueba 4: Usuario con rol 'crear' + 'ver'
1. Crear usuario y asignar grupos `crear` + `ver`
2. Acceder a `/users/menu/`
3. **Resultado esperado**:
   - ✅ Ve ambas tarjetas activas
   - ✅ Puede crear usuarios
   - ✅ Puede ver la lista de usuarios

### Prueba 5: Usuario con rol 'editar'
1. Crear usuario y asignar grupo `editar`
2. Acceder a `/users/menu/`
3. **Resultado esperado**:
   - ❌ Ve la tarjeta "Crear Usuarios" deshabilitada
   - ✅ Ve la tarjeta "Administrar Usuarios" activa
   - ✅ Puede ver y editar usuarios
   - ✅ Puede cambiar contraseña de otros
   - ❌ No puede eliminar usuarios

### Prueba 6: Usuario con rol 'borrar'
1. Crear usuario y asignar grupo `borrar`
2. Acceder a `/users/menu/`
3. **Resultado esperado**:
   - ❌ Ve la tarjeta "Crear Usuarios" deshabilitada
   - ✅ Ve la tarjeta "Administrar Usuarios" activa
   - ✅ Puede ver usuarios
   - ✅ Puede eliminar usuarios
   - ❌ No puede editar otros campos

---

## 🔒 Validaciones de Seguridad

### Validaciones Cliente (UI)
- Tarjeta deshabilitada: color gris oscuro + `opacity-70`
- Inputs deshabilitados: no se pueden interactuar
- Botones deshabilitados: no responden a clicks
- Mensaje de alerta si intentas clickear tarjeta deshabilitada

### Validaciones Servidor (Críticas)
- **POST** de creación: valida `auth.add_user` antes de crear
- **AJAX** de edición: valida `auth.change_user` antes de modificar
- **AJAX** de eliminación: valida `auth.delete_user` antes de borrar
- **AJAX** de cambio de contraseña: valida `auth.change_user` o that you are self

---

## 📞 Troubleshooting

### Problema: El usuario no ve la tarjeta de crear
**Solución**: Asegurate que el usuario tiene el grupo `crear` (con permiso `auth.add_user`)

### Problema: El usuario ve la tarjeta de crear pero NO puede crear
**Solución**: El servidor rechaza porque:
1. El usuario no tiene el permiso `auth.add_user` en la BD
2. Asigna el grupo `crear` nuevamente
3. Logout y login para refrescar los permisos en caché

### Problema: El usuario puede crear pero no ve el panel admin
**Solución**: Usuario tiene `crear` pero no `ver`. Asigna el grupo `ver` también:
- Un usuario puede tener múltiples grupos simultáneamente
- `crear` + `ver` = acceso a ambos paneles

### Problema: No puedo cambiar la contraseña de otro usuario
**Solución**: Necesitas el grupo `editar` (que incluye `auth.change_user`)
- O eres un superuser
- O cambias tu propia contraseña (sin permiso especial)

---

## 📌 Comandos Django Shell (Avanzado)

```python
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

# Crear grupo
grupo_ver = Group.objects.create(name='ver')

# Obtener permisos
auth_content_type = ContentType.objects.get_for_model(User)
view_perm = Permission.objects.get(codename='view_user', content_type=auth_content_type)

# Asignar permisos a grupo
grupo_ver.permissions.add(view_perm)

# Obtener usuario
user = User.objects.get(username='john')

# Asignar grupo a usuario
user.groups.add(grupo_ver)

# Verificar permisos del usuario
print(user.has_perm('auth.view_user'))  # True
```

---

## 🎓 Conceptos Clave

### Diferencia entre is_staff e Grupos

- **is_staff**: Permite acceder a Django Admin (/admin/)
- **Grupos**: Controlan qué puede hacer en la app (nuestro panel de usuarios)

Ejemplo:
```
Usuario A:
- is_staff: True
- grupos: ninguno
→ Puede acceder a /admin/ pero NO a /users/menu/

Usuario B:
- is_staff: False
- grupos: ['ver', 'crear']
→ NO puede acceder a /admin/ pero SÍ a /users/menu/
```

### Jerarquía de Permisos

```
Superuser (is_superuser=True)
  ↓ (tiene todos los permisos automáticamente)
Grupos (Groups)
  ↓ (contienen Permisos específicos)
Permisos (Permissions)
  ↓ (ej: auth.view_user, auth.add_user, etc)
Acciones (en la app)
```

---

Este documento describe todo lo necesario para configurar y usar el sistema de permisos personalizado.
