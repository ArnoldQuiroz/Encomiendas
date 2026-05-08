from django.db import models

class EncomiendaQuerySet(models.QuerySet):
    def pendientes(self):
        return self.filter(estado='PE')
    def en_transito(self):
        return self.filter(estado='TR')
    def entregadas(self):
        return self.filter(estado='EN')
    def devueltas(self):
        return self.filter(estado='DV')
    def activas(self):
        return self.filter(estado__in=['PE', 'TR', 'DE'])
    def por_ruta(self, ruta):
        return self.filter(ruta=ruta)
    def por_remitente(self, cliente):
        return self.filter(remitente=cliente)
    def por_destinatario(self, cliente):
        return self.filter(destinatario=cliente)
    def en_transito_por_ruta(self, ruta):
        return self.en_transito().por_ruta(ruta)
    def con_retraso(self):
        from django.utils import timezone
        return self.activas().filter(fecha_entrega_est__lt=timezone.now().date())
    def con_relaciones(self):
        return self.select_related('remitente', 'destinatario', 'ruta', 'empleado_registro')

class ClienteQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(estado=1)
    def de_baja(self):
        return self.filter(estado=9)
    def con_dni(self):
        return self.filter(tipo_doc='DNI')
    def buscar(self, termino):
        return self.filter(
            models.Q(nombres__icontains=termino) |
            models.Q(apellidos__icontains=termino) |
            models.Q(nro_doc__icontains=termino)
        )

class RutaQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(estado=1)
    def por_origen(self, ciudad):
        return self.filter(origen__icontains=ciudad)
    def por_destino(self, ciudad):
        return self.filter(destino__icontains=ciudad)
