"""
SESIÓN 06 — Tema 6: Manejo de errores personalizado
Centraliza y da formato consistente a todos los errores de la API.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        view = context.get('view', None)
        view_name = view.__class__.__name__ if view else 'unknown'

        error_data = {
            'ok': False,
            'status_code': response.status_code,
            'error': _get_error_type(response.status_code),
            'mensaje': _flatten_errors(response.data),
            'vista': view_name,
        }
        return Response(error_data, status=response.status_code)

    return response


def _get_error_type(status_code):
    return {
        400: 'Solicitud inválida',
        401: 'No autenticado',
        403: 'Acceso denegado',
        404: 'No encontrado',
        405: 'Método no permitido',
        429: 'Demasiadas solicitudes',
        500: 'Error interno del servidor',
    }.get(status_code, 'Error desconocido')


def _flatten_errors(data):
    if isinstance(data, list):
        return ' '.join(str(e) for e in data)
    if isinstance(data, dict):
        msgs = []
        for key, val in data.items():
            if isinstance(val, list):
                msgs.append(f"{key}: {' '.join(str(v) for v in val)}")
            else:
                msgs.append(f"{key}: {val}")
        return ' | '.join(msgs)
    return str(data)
