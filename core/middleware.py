from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.conf import settings
from django.contrib import messages


class LoginRequiredMiddleware:
    MANAGEMENT_PERMS = {'auth.add_user', 'auth.change_user', 'auth.view_user', 'auth.delete_user'}
    def __init__(self, get_response):
        self.get_response = get_response
        # Cachear dashboard path
        try:
            self._dashboard_path = reverse('core:dashboard')
        except Exception:
            self._dashboard_path = None

    def __call__(self, request):
        # URLs que no requieren login o deben permitirse siempre (login/logout/no_permissions)
        try:
            exempt_urls = set([
                reverse('core:login'),
                reverse('core:logout'),
                reverse('core:no_permissions'),
            ])
        except Exception:
            # If URL reversing fails during some startup phase, default to empty set
            exempt_urls = set()

        # Allow activation links (they look like /users/activate/<uid>/<token>/)
        if request.path.startswith('/users/activate/'):
            return self.get_response(request)

        # Allow static and media during development
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Allow exempt urls for everyone (important so logout isn't blocked for no-perm users)
        if request.path in exempt_urls:
            return self.get_response(request)

        # If user is not authenticated, redirect to login
        if not request.user.is_authenticated:
            return redirect('core:login')

        # Compute user permissions early (used in several checks)
        try:
            user_perms = set(request.user.get_all_permissions() or [])
        except Exception:
            user_perms = set()

        # Enforce app-level 'use' permission or group. Behavior:
        # - If REQUIRED_APP_PERMISSION is set and starts with 'group:', require that group.
        # - Else if REQUIRED_APP_PERMISSION is set, treat it as a permission string.
        # - If not set, default to requiring a group named 'usar' to use the app.
        required = getattr(settings, 'REQUIRED_APP_PERMISSION', None)
        required_group = None
        required_perm = None
        if required:
            if isinstance(required, str) and required.lower().startswith('group:'):
                required_group = required.split(':', 1)[1]
            else:
                required_perm = required
        else:
            # default group name to require for app usage
            required_group = 'usar'

        # Determine the requested view name for special-casing user_menu
        try:
            match = resolve(request.path_info)
            view_name = match.view_name
        except Resolver404:
            view_name = None

        # If the user is superuser, allow everything
        if request.user.is_superuser:
            return self.get_response(request)

        # Check group requirement if any
        if required_group:
            if not request.user.groups.filter(name__iexact=required_group).exists():
                # allow access to user_menu if user has management perms
                if view_name == 'core:user_menu' and (user_perms & self.MANAGEMENT_PERMS):
                    pass
                else:
                    return redirect('core:no_permissions')

        # Check permission requirement if any
        if required_perm:
            try:
                if not request.user.has_perm(required_perm):
                    if view_name == 'core:user_menu' and (user_perms & self.MANAGEMENT_PERMS):
                        pass
                    else:
                        return redirect('core:no_permissions')
            except Exception:
                pass

        # If user is authenticated, ensure they have at least one permission to use the app.
        # Users who have no permissions (or only management perms) will be redirected
        # to the `no_permissions` page. Exception: allow access to the user_menu if they
        # have add_user permission (management-only accounts).
        # user_perms already computed above

        # If user has no permissions at all -> redirect to no_permissions
        if not user_perms:
            return redirect('core:no_permissions')

        # If user's permissions are only management-related, restrict access to
        # the rest of the app. Allow access to the user_menu if they have add_user.
        if user_perms.issubset(self.MANAGEMENT_PERMS):
            # allow user_menu if they have add_user
            try:
                if request.user.has_perm('auth.add_user') and view_name == 'core:user_menu':
                    return self.get_response(request)
            except Exception:
                pass
            
            if view_name == 'core:dashboard' or (self._dashboard_path and request.path.startswith(self._dashboard_path)):
                return redirect('core:no_permissions')

            return redirect('core:no_permissions')

        return self.get_response(request)
