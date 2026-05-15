"""
🔐 Sistema de roles y permisos basado en Django Groups.

Roles:
- Admin    : Todo (crear, editar, eliminar, ver)
- Operador : Crear y cambiar estado (no elimina, no edita clientes)
- Lector   : Solo lectura (consulta dashboard y reportes)
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import HttpResponseForbidden
from django.shortcuts import render


# Constantes de roles
ROL_ADMIN = 'Admin'
ROL_OPERADOR = 'Operador'
ROL_LECTOR = 'Lector'

ROLES = [ROL_ADMIN, ROL_OPERADOR, ROL_LECTOR]


def usuario_es(user, *roles):
    """Verifica si el usuario pertenece a alguno de los roles dados."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True  # Superuser tiene acceso total
    return user.groups.filter(name__in=roles).exists()


def rol_requerido(*roles):
    """
    Decorator para vistas. Uso:
        @rol_requerido('Admin', 'Operador')
        def mi_vista(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if usuario_es(request.user, *roles):
                return view_func(request, *args, **kwargs)
            return render(request, '403.html', {
                'rol_requerido': ', '.join(roles)
            }, status=403)
        return wrapper
    return decorator


def asegurar_grupos_existen():
    """Crea los grupos en BD si no existen (idempotente)."""
    for nombre in ROLES:
        Group.objects.get_or_create(name=nombre)


def get_rol(user):
    """Devuelve el nombre del rol principal del usuario."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROL_ADMIN
    grupo = user.groups.filter(name__in=ROLES).first()
    return grupo.name if grupo else None
