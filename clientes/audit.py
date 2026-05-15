"""
🔐 Sistema de auditoría de accesos a datos sensibles.

Registra cada vez que un usuario consulta datos personales de un cliente,
para poder detectar accesos no autorizados o filtraciones.
"""
from django.db import models
from django.conf import settings


class AccesoCliente(models.Model):
    """Log inmutable de accesos a perfiles de clientes."""

    ACCION_CHOICES = [
        ('VIEW',   'Consulta de perfil'),
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('SEARCH_DNI', 'Búsqueda por DNI (RENIEC)'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accesos_clientes',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accesos_log',
    )
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    detalle = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'acceso_cliente_log'
        verbose_name = 'Acceso a cliente'
        verbose_name_plural = 'Accesos a clientes (auditoría)'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['usuario', '-fecha']),
            models.Index(fields=['cliente', '-fecha']),
        ]

    def __str__(self):
        u = self.usuario.username if self.usuario else 'anónimo'
        c = self.cliente.nro_doc if self.cliente else '?'
        return f'{u} → {self.get_accion_display()} cliente {c} @ {self.fecha:%Y-%m-%d %H:%M}'


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar_acceso(request, cliente=None, accion='VIEW', detalle=''):
    """
    Helper para registrar un acceso desde una vista.
    Uso: registrar_acceso(request, cliente=c, accion='VIEW')
    """
    try:
        AccesoCliente.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            cliente=cliente,
            accion=accion,
            ip=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            detalle=detalle[:255],
        )
    except Exception:
        # Nunca fallar la request por un error de auditoría
        pass
