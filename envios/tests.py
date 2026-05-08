from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from clientes.models import Cliente
from rutas.models import Ruta
from envios.models import Encomienda, Empleado
from sistema.choices import EstadoGeneral

class EncomiendaModelTests(TestCase):
    def setUp(self):
        # Crear datos básicos para las pruebas
        self.cliente_rem = Cliente.objects.create(
            nro_doc='11111111', nombres='Remitente', apellidos='Prueba', email='rem@test.com'
        )
        self.cliente_dest = Cliente.objects.create(
            nro_doc='22222222', nombres='Destinatario', apellidos='Prueba', email='dest@test.com'
        )
        self.ruta = Ruta.objects.create(
            codigo='RTEST', origen='A', destino='B', 
            precio_base=10.00, dias_entrega=2
        )
        self.empleado = Empleado.objects.create(
            codigo='E999', nombres='Emp', apellidos='Prueba', 
            email='emp@test.com', fecha_ingreso=timezone.now().date(),
            estado=EstadoGeneral.ACTIVO
        )

    def test_calculo_costo_encomienda(self):
        """El costo debe ser base + (peso_extra * 2.50) si peso > 5kg"""
        # Peso <= 5kg, costo debe ser el base (10.00)
        enc_base = Encomienda.crear_con_costo_calculado(
            remitente=self.cliente_rem, destinatario=self.cliente_dest,
            ruta=self.ruta, empleado=self.empleado,
            descripcion='Paquete pequeño', peso_kg=4.0
        )
        self.assertEqual(enc_base.costo_envio, 10.00)

        # Peso = 6kg, extra = 1kg. Costo = 10 + (1 * 2.50) = 12.50
        enc_extra = Encomienda.crear_con_costo_calculado(
            remitente=self.cliente_rem, destinatario=self.cliente_dest,
            ruta=self.ruta, empleado=self.empleado,
            descripcion='Paquete mediano', peso_kg=6.0
        )
        self.assertEqual(enc_extra.costo_envio, 12.50)

    def test_fecha_estimada_no_pasado(self):
        """Validar que al intentar guardar una encomienda con fecha estimada en el pasado arroja ValidationError"""
        enc = Encomienda(
            codigo='TEST-ERR-1',
            descripcion='Test',
            peso_kg=1.0,
            remitente=self.cliente_rem,
            destinatario=self.cliente_dest,
            ruta=self.ruta,
            empleado_registro=self.empleado,
            costo_envio=10.0,
            fecha_entrega_est=timezone.now().date() - timedelta(days=5)
        )
        
        with self.assertRaises(ValidationError) as context:
            enc.full_clean()
            
        self.assertIn('fecha_entrega_est', context.exception.message_dict)

    def test_mismo_remitente_destinatario(self):
        """Validar que remitente y destinatario no pueden ser la misma persona"""
        enc = Encomienda(
            codigo='TEST-ERR-2',
            descripcion='Test Mismo Cliente',
            peso_kg=1.0,
            remitente=self.cliente_rem,
            destinatario=self.cliente_rem, # Mismo cliente
            ruta=self.ruta,
            empleado_registro=self.empleado,
            costo_envio=10.0,
            fecha_entrega_est=timezone.now().date() + timedelta(days=2)
        )
        
        with self.assertRaises(ValidationError) as context:
            enc.full_clean()
            
        self.assertIn('destinatario', context.exception.message_dict)
