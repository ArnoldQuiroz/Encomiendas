from django.db import models
from django.utils import timezone

class EncomiendaQuerySet(models.QuerySet):
    def pendientes(self):
        return self.filter(estado='PE')

    def activas(self):
        return self.filter(estado__in=['PE', 'TR', 'DE'])

    def con_retraso(self):
        return self.activas().filter(fecha_entrega_est__lt=timezone.now().date())

    def con_relaciones(self):
        return self.select_related('remitente', 'destinatario', 'ruta', 'empleado_registro')