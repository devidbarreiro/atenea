# Sistema de Permisos de Gestión de Usuarios - Resumen de Cambios

Documento de resumen de cambios implementados para el sistema de control de permisos en la gestión de usuarios.

## 📋 Requisitos Implementados

### Roles y Permisos

| Rol       | Descripción                     | Permisos                             | Acceso a Panel            |
|-----------|---------------------------------|--------------------------------------|---------------------------|
| **usar**  | Solo acceso a la app | ninguno  | ❌ NO                                |
| **ver**   | Ver usuarios                    | `auth.view_user`                     | ✅ SÍ (lectura)          |
| **crear** | Crear usuarios                  | `auth.add_user`                      | ✅ SOLO crear (no admin) |
| **editar**| Editar usuarios                 | `auth.view_user`, `auth.change_user` | ✅ SÍ + editar           |
| **borrar**| Borrar usuarios                 | `auth.view_user`, `auth.delete_user` | ✅ SÍ + eliminar         |
| **admin** | Todos los permisos              | Todos                                | ✅ TODO                  |

### Comportamiento de Roles Acumulables

- Los permisos se **acumulan**: un usuario con `crear` + `ver` tendrá ambos permisos.
- El rol **admin** sincroniza automáticamente:
  - Si marcas `admin` → marcan todos los otros checkboxes
  - Si todos los otros están marcados → marca `admin`
  - Si desmarcar `admin` → desmarca todos
  - Si desmarcar cualquier otro → desmarca `admin`

---

## 🔧 Cambios en `c:\Proyectos\atenea\core\views.py`

### 1. Actualización de `UserMenuView.dispatch()`

**Antes:**
```python
class UserMenuView(PermissionRequiredMixin, View):
    permission_required = 'auth.view_user'
    # Solo permitía acceso a usuarios con view_user
```

**Después:**
```python
class UserMenuView(View):
    def dispatch(self, request, *args, **kwargs):
        # Permitir acceso si tiene CUALQUIERA de:
        # - auth.view_user (panel admin)
        # - auth.change_user (editar)
        # - auth.delete_user (borrar)
        # - auth.add_user (crear)
        # - es superuser
        
        has_admin_access = (
            request.user.has_perm('auth.view_user') or
            request.user.has_perm('auth.change_user') or
            request.user.has_perm('auth.delete_user') or
            request.user.is_superuser
        )
        
        has_create_access = request.user.has_perm('auth.add_user') or request.user.is_superuser
        
        # Rechazar si no tiene admin ni create
        if not (has_admin_access or has_create_access):
            messages.error(request, 'No tienes permiso para acceder a esta página.')
            return redirect(self.login_url)
```

### 2. Servidor Valida Permisos para Operaciones

**Creación de usuarios:**
```python
# POST normal - requiere auth.add_user
if not request.user.has_perm('auth.add_user'):
    messages.error(request, 'No tienes permiso para crear usuarios.')
    return redirect('core:user_menu')
```

**Edición masiva (AJAX):**
```python
# Si la petición intenta actualizar usuarios → requiere auth.change_user
if any(k.startswith('usuarios[') for k in request.POST):
    if not request.user.has_perm('auth.change_user'):
        return JsonResponse({'success': False, 'error': 'No tienes permiso para modificar usuarios.'})
```

**Eliminación:**
```python
# Individual o masiva → requiere auth.delete_user
if not request.user.has_perm('auth.delete_user'):
    return JsonResponse({'success': False, 'error': 'No tienes permiso para eliminar usuarios.'})
```

**Cambio de contraseña:**
```python
# Permite si es self (cambiar propia contraseña) O tiene auth.change_user
if not (request.user.has_perm('auth.change_user') or str(request.user.id) == str(user_id)):
    return JsonResponse({'success': False, 'error': 'No tienes permiso para cambiar la contraseña.'})
```

---

## 🎨 Cambios en `c:\Proyectos\atenea\templates\users\menu.html`

### 1. Tarjeta de Crear Siempre Visible

**Antes:**
```html
{% if perms.auth.add_user %}
    <div onclick="selectContentType('user-create')" class="...">
        <!-- Tarjeta visible -->
    </div>
{% endif %}
```

**Después:**
```html
<!-- SIEMPRE renderizada -->
<div id="user-create-card"
    {% if perms.auth.add_user %}
        onclick="selectContentType('user-create')"
        class="bg-white border-blue-600 hover:shadow-xl" <!-- Activa -->
    {% else %}
        class="bg-gray-200 border-gray-400 opacity-70 cursor-not-allowed" <!-- Deshabilitada -->
        data-disabled="true"
    {% endif %}>
    <div class="w-16 h-16 {% if perms.auth.add_user %}bg-gray-100{% else %}bg-gray-300{% endif %}">
    </div>
    <p class="text-sm">
        {% if perms.auth.add_user %}
            Crea un usuario de cero...
        {% else %}
            No tienes permisos para crear usuarios
        {% endif %}
    </p>
</div>
```

### 2. Panel Admin Solo Visible para Usuarios con Permisos Válidos

**Cambio:**
```html
<!-- Antes: {% if perms.auth.view_user %} -->
<!-- Después: permite acceso si tiene CUALQUIERA de estos permisos: -->
{% if perms.auth.view_user or perms.auth.change_user or perms.auth.delete_user %}
    <div id="user-admin-card" onclick="selectContentType('user-admin')">
        Administrar Usuarios
    </div>
{% endif %}
```

### 3. Sincronización de Checkboxes Admin/Roles

Añadidas funciones JS para:

**En formulario de creación:**
```javascript
function syncAdminCheckbox(checkbox) {
    // Si marcas admin → marcan todos los demás
    // Si desmarcar admin → desmarcan todos
}

function updateAdminCheckbox(changedCheckbox) {
    // Si todos están marcados → marcar admin
    // Si uno se desmarca → desmarcar admin
}
```

**En tabla de administración:**
```javascript
function syncAdminCheckboxInRow(checkbox) {
    // Sincroniza admin en la fila actual
}

function updateAdminCheckboxInRow(changedCheckbox) {
    // Actualiza admin si todos los demás están marcados
}
```

### 4. Checkboxes de Grupos con ID de Grupo

```html
{% for g in groups %}
<label class="inline-flex items-center mr-4">
    <input type="checkbox" 
           name="groups" 
           value="{{ g.id }}" 
           class="group-checkbox scale-125 accent-blue-600 mr-2" 
           data-group-name="{{ g.name }}"
           {% if not perms.auth.add_user %}disabled{% endif %}>
    <span>{{ g.name }}</span>
</label>
{% endfor %}
```

### 5. Prevención de Clics en Tarjetas Deshabilitadas

```javascript
function selectContentType(type) {
    // Prevenir acción si la tarjeta de crear está deshabilitada
    if (type === 'user-create' && document.getElementById('user-create-card').dataset.disabled === 'true') {
        alert('No tienes permisos para crear usuarios');
        return;
    }
    // ...resto del código
}
```

## 🚀 Cómo Funciona

### Flujo 1: Usuario con rol 'crear'
1. Intenta acceder a `/users/menu/`
2. `dispatch()` verifica: ¿tiene `add_user`? → ✅ SÍ → permitir acceso
3. En template: se muestra la tarjeta de crear **activa** (blanca, clickeable)
4. Se oculta la tarjeta de admin (no tiene `view_user`, `change_user`, o `delete_user`)
5. El usuario puede crear usuarios pero NO acceder al panel de administración

### Flujo 2: Usuario con rol 'ver'
1. Intenta acceder a `/users/menu/`
2. `dispatch()` verifica: ¿tiene `view_user`? → ✅ SÍ → permitir acceso
3. En template: se muestra la tarjeta de crear **deshabilitada** (gris oscuro, no clickeable)
4. Se muestra la tarjeta de admin (tiene `view_user`)
5. El usuario puede acceder al panel admin (lectura) pero NO puede crear usuarios

### Flujo 3: Usuario con rol 'crear' + 'ver'
1. Intenta acceder a `/users/menu/`
2. `dispatch()` verifica: ¿tiene `add_user` O `view_user`? → ✅ SÍ → permitir acceso
3. En template: ambas tarjetas son **activas**
4. El usuario puede hacer ambas acciones

---

## 📝 Notas Importantes

- **Servidor es Autoritario**: Aunque la UI oculte elementos, el servidor valida TODOS los permisos en POST/AJAX
- **Sincronización Admin**: Se implementó tanto en formulario como en tabla de administración
- **Permisos Acumulables**: Los roles se pueden combinar (usuario puede tener múltiples grupos)
- **Superusers**: Los superusers siempre tienen acceso total (no necesitan verificar permisos)

---

## 🔐 Seguridad

✅ **Validaciones Cliente:**
- UI oculta/deshabilita elementos sin permiso
- Tarjeta deshabilitada muestra mensaje al intentar clickear

✅ **Validaciones Servidor (Críticas):**
- POST de creación requiere `auth.add_user`
- AJAX de edición requiere `auth.change_user`
- AJAX de eliminación requiere `auth.delete_user`
- AJAX de cambio de contraseña requiere `auth.change_user` o ser uno mismo

✅ **Protecciones Adicionales:**
- No se puede eliminar el usuario actual
- Validación de duplicado de username/email
- Manejo de excepciones y rollback

---

## 🎯 Próximos Pasos Recomendados

1. **Tests**: Ejecutar suite de tests (requiere resolver dependencias de `google-genai` e `imghdr`)
2. **Frontend**: Probar sincronización de checkboxes admin con usuarios reales
3. **Auditoría**: Revisar otros endpoints que puedan mutar usuarios (APIs, webhooks)
4. **Documentación**: Agregar al manual de usuario cómo crear/gestionar roles
<<<<<<< HEAD
5. **UX**: Considerar mensajes más descriptivos cuando se intenta acceder sin permiso
=======
5. **UX**: Considerar mensajes más descriptivos cuando se intenta acceder sin permiso
>>>>>>> f5abafd (Role-based permissions system, automatic password creation with link sent to set password and activate account, views for users without permissions, bug fixes, visual improvements)
