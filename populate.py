import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema.settings')
django.setup()

from django.utils import timezone
from clientes.models import Cliente
from rutas.models import Ruta
from envios.models import Empleado, Encomienda
from sistema.choices import EstadoEnvio, EstadoGeneral
import random

def populate():
    print("Creando datos de prueba...")
    
    # Crear Clientes
    c1, _ = Cliente.objects.get_or_create(
        nro_doc='12345678', 
        defaults={'nombres': 'Juan', 'apellidos': 'Perez', 'email': 'juan@test.com'}
    )
    c2, _ = Cliente.objects.get_or_create(
        nro_doc='87654321', 
        defaults={'nombres': 'Maria', 'apellidos': 'Gomez', 'email': 'maria@test.com'}
    )
    
    # Crear Ruta
    r1, _ = Ruta.objects.get_or_create(
        codigo='R001',
        defaults={'origen': 'Lima', 'destino': 'Arequipa', 'precio_base': 15.00, 'dias_entrega': 2}
    )
    r2, _ = Ruta.objects.get_or_create(
        codigo='R002',
        defaults={'origen': 'Lima', 'destino': 'Cusco', 'precio_base': 20.00, 'dias_entrega': 3}
    )
    
    # Crear Empleado
    e1, _ = Empleado.objects.get_or_create(
        codigo='E001', 
        defaults={
            'nombres': 'Carlos', 'apellidos': 'Empleado', 
            'email': 'admin@admin.com', # asumiendo que este es el user
            'fecha_ingreso': timezone.now().date(),
            'estado': EstadoGeneral.ACTIVO
        }
    )
    
    # Crear Encomiendas
    # 1 Activa / Pendiente
    Encomienda.crear_con_costo_calculado(
        remitente=c1, destinatario=c2, ruta=r1, empleado=e1, 
        descripcion='Caja de libros', peso_kg=10.0
    )
    
    # 1 En tránsito
    enc2 = Encomienda.crear_con_costo_calculado(
        remitente=c2, destinatario=c1, ruta=r2, empleado=e1, 
        descripcion='Ropa variada', peso_kg=5.0
    )
    enc2.cambiar_estado(EstadoEnvio.EN_TRANSITO, e1, 'Saliendo de la base')
    
    # 1 Con retraso (fecha est en el pasado)
    enc3 = Encomienda.crear_con_costo_calculado(
        remitente=c1, destinatario=c2, ruta=r1, empleado=e1, 
        descripcion='Documentos importantes', peso_kg=1.0
    )
    Encomienda.objects.filter(pk=enc3.pk).update(fecha_entrega_est=timezone.now().date() - timedelta(days=2))
    
    # 1 Entregada hoy
    enc4 = Encomienda.crear_con_costo_calculado(
        remitente=c2, destinatario=c1, ruta=r2, empleado=e1, 
        descripcion='Regalo', peso_kg=2.0
    )
    enc4.fecha_entrega_est = timezone.now().date()
    enc4.save()
    enc4.cambiar_estado(EstadoEnvio.ENTREGADO, e1, 'Entregado a titular')
    enc4.fecha_entrega_real = timezone.now().date()
    enc4.save()
    
    print("Datos creados exitosamente.")

if __name__ == '__main__':
    populate()
