"""
Script de poblado de datos realistas para el sistema de Encomiendas.

Uso:
    docker-compose exec web python populate.py
    docker-compose exec web python populate.py --clean   (borra encomiendas previas)
"""
import os, django, random, sys
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from faker import Faker

from clientes.models import Cliente
from rutas.models import Ruta
from envios.models import Empleado, Encomienda, HistorialEstado
from sistema.choices import EstadoEnvio, EstadoGeneral, TipoDocumento

fake = Faker('es_ES')

NOMBRES_HOMBRES = [
    'Juan Carlos', 'José Luis', 'Carlos Alberto', 'Miguel Ángel', 'Luis Enrique',
    'Pedro Pablo', 'Jorge', 'Diego', 'Manuel', 'Roberto', 'Daniel', 'Christian',
    'Alejandro', 'Fernando', 'Eduardo', 'Ricardo', 'Andrés', 'Sebastián',
    'Marco Antonio', 'Víctor Hugo', 'Raúl', 'Javier', 'Pablo', 'Gabriel',
    'Cristian', 'Hernán', 'Walter', 'Óscar',
]
NOMBRES_MUJERES = [
    'María Elena', 'Rosa María', 'Ana Lucía', 'Carmen Rosa', 'Patricia',
    'Lucía', 'Sofía', 'Valeria', 'Camila', 'Gabriela', 'Andrea', 'Daniela',
    'Mariana', 'Alejandra', 'Verónica', 'Mónica', 'Claudia', 'Silvia',
    'Marleny', 'Genesis', 'Diana', 'Karen', 'Jessica', 'Pamela',
    'Liliana', 'Sandra', 'Yolanda', 'Milagros',
]
APELLIDOS = [
    'García', 'Quispe', 'Mamani', 'Huamán', 'Flores', 'Chávez', 'Rojas',
    'Pérez', 'Sánchez', 'Vargas', 'Ramírez', 'Torres', 'Castillo', 'Gutiérrez',
    'Ramos', 'Mejia', 'Quiroz', 'Salinas', 'Cárdenas', 'Rivera', 'Paredes',
    'Espinoza', 'Sandoval', 'Romero', 'Velasco', 'Ortiz', 'Carrasco',
    'Aguilar', 'Salazar', 'Pacheco', 'Gonzales', 'Medina', 'Castro',
    'Vega', 'Cordero', 'Cabrera', 'Tello', 'Soto', 'Núñez',
]

RUTAS_PERU = [
    ('LIM-AQP', 'Lima',     'Arequipa', 25.00, 2, 'Ruta principal sur'),
    ('LIM-CUS', 'Lima',     'Cusco',    32.00, 3, 'Sierra sur'),
    ('LIM-TRU', 'Lima',     'Trujillo', 18.00, 1, 'Costa norte rápida'),
    ('LIM-PIU', 'Lima',     'Piura',    28.00, 2, 'Norte costero'),
    ('LIM-IQU', 'Lima',     'Iquitos',  45.00, 4, 'Selva — vía aérea'),
    ('LIM-CHI', 'Lima',     'Chiclayo', 22.00, 2, 'Costa norte'),
    ('LIM-HUA', 'Lima',     'Huancayo', 15.00, 1, 'Sierra central'),
    ('LIM-TAC', 'Lima',     'Tacna',    38.00, 3, 'Sur extremo, frontera'),
]

CARGOS = ['Operador', 'Supervisor', 'Coordinador de ruta', 'Encargado de almacén']
DESCRIPCIONES = [
    'Documentos importantes', 'Caja de productos electrónicos',
    'Ropa y accesorios', 'Productos de panadería', 'Repuestos automotrices',
    'Material de oficina', 'Equipo médico', 'Libros y revistas',
    'Productos artesanales', 'Muestras comerciales', 'Regalos personales',
    'Productos farmacéuticos', 'Herramientas', 'Encomienda familiar',
    'Cargador y cables', 'Juguetes', 'Productos cosméticos',
]
DISTRITOS = ['Miraflores', 'San Isidro', 'Surco', 'La Molina', 'Surquillo',
             'Lince', 'Magdalena', 'San Borja', 'Jesús María', 'Pueblo Libre']


def limpiar():
    print('🗑️  Limpiando encomiendas e historial previos...')
    HistorialEstado.objects.all().delete()
    Encomienda.objects.all().delete()


def crear_rutas():
    print('🛣️  Creando rutas...')
    creadas = 0
    for cod, ori, des, precio, dias, desc in RUTAS_PERU:
        _, created = Ruta.objects.get_or_create(
            codigo=cod,
            defaults={
                'origen': ori, 'destino': des,
                'precio_base': Decimal(str(precio)),
                'dias_entrega': dias,
                'descripcion': desc,
                'estado': EstadoGeneral.ACTIVO,
            }
        )
        if created:
            creadas += 1
    print(f'   ✓ {creadas} rutas nuevas (total: {Ruta.objects.count()})')


def crear_empleados():
    print('👔 Creando empleados...')
    creados = 0
    for i in range(5):
        codigo = f'EC-{i + 200:04d}'
        nombres = random.choice(NOMBRES_HOMBRES + NOMBRES_MUJERES)
        apellidos = f'{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}'
        _, created = Empleado.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombres': nombres,
                'apellidos': apellidos,
                'cargo': random.choice(CARGOS),
                'email': f'empleado{i+1}@encomiendas.pe',
                'telefono': f'9{random.randint(10000000, 99999999)}',
                'estado': EstadoGeneral.ACTIVO,
                'fecha_ingreso': timezone.now().date() - timedelta(days=random.randint(30, 1500)),
            }
        )
        if created:
            creados += 1
    print(f'   ✓ {creados} empleados nuevos (total: {Empleado.objects.count()})')


def crear_clientes():
    print('👥 Creando clientes...')
    creados = 0
    dnis = set(Cliente.objects.values_list('nro_doc', flat=True))

    intentos = 0
    while creados < 50 and intentos < 200:
        intentos += 1
        nombre = random.choice(NOMBRES_MUJERES if random.random() < 0.5 else NOMBRES_HOMBRES)
        apellidos = f'{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}'
        dni = str(random.randint(70000000, 79999999))
        if dni in dnis:
            continue
        dnis.add(dni)
        Cliente.objects.create(
            tipo_doc=TipoDocumento.DNI,
            nro_doc=dni,
            nombres=nombre,
            apellidos=apellidos,
            telefono=f'9{random.randint(10000000, 99999999)}',
            email=f'{nombre.split()[0].lower()}.{apellidos.split()[0].lower()}@gmail.com',
            direccion=f'{random.choice(["Av.", "Jr.", "Calle"])} {fake.street_name()} {random.randint(100, 9999)}, '
                      f'{random.choice(DISTRITOS)}, Lima',
            estado=EstadoGeneral.ACTIVO,
        )
        creados += 1
    print(f'   ✓ {creados} clientes nuevos (total: {Cliente.objects.count()})')


def crear_encomiendas():
    print('📦 Creando encomiendas...')
    clientes = list(Cliente.objects.activos())
    rutas = list(Ruta.objects.activas())
    empleados = list(Empleado.objects.filter(estado=EstadoGeneral.ACTIVO))

    if len(clientes) < 5 or not rutas or not empleados:
        print('   ⚠️ Faltan datos base')
        return

    estados_dist = (
        [EstadoEnvio.PENDIENTE] * 15 +
        [EstadoEnvio.EN_TRANSITO] * 25 +
        [EstadoEnvio.EN_DESTINO] * 10 +
        [EstadoEnvio.ENTREGADO] * 25 +
        [EstadoEnvio.DEVUELTO] * 5
    )

    creadas = 0
    for i in range(80):
        remitente = random.choice(clientes)
        destinatario = random.choice([c for c in clientes if c.id != remitente.id])
        ruta = random.choice(rutas)
        empleado = random.choice(empleados)
        estado = random.choice(estados_dist)
        peso = Decimal(str(round(random.uniform(0.5, 30.0), 2)))

        costo = float(ruta.precio_base)
        if float(peso) > 5:
            costo += (float(peso) - 5) * 2.50
        costo = round(costo, 2)

        dias_atras = random.randint(0, 60)
        fecha_registro = timezone.now() - timedelta(days=dias_atras)
        fecha_estimada = fecha_registro.date() + timedelta(days=ruta.dias_entrega)
        fecha_real = None
        if estado == EstadoEnvio.ENTREGADO:
            fecha_real = fecha_estimada + timedelta(days=random.randint(-1, 3))

        codigo = f'ENC-{fecha_registro.strftime("%Y%m%d")}-{i+1000:04d}'

        try:
            enc = Encomienda(
                codigo=codigo,
                descripcion=random.choice(DESCRIPCIONES),
                peso_kg=peso,
                volumen_cm3=Decimal(str(random.randint(100, 50000))),
                remitente=remitente,
                destinatario=destinatario,
                ruta=ruta,
                empleado_registro=empleado,
                estado=estado,
                costo_envio=Decimal(str(costo)),
                fecha_entrega_est=fecha_estimada,
                fecha_entrega_real=fecha_real,
                observaciones=fake.sentence() if random.random() < 0.3 else '',
            )
            enc.save_base(force_insert=True)

            if estado != EstadoEnvio.PENDIENTE:
                HistorialEstado.objects.create(
                    encomienda=enc, empleado=empleado,
                    estado_anterior=EstadoEnvio.PENDIENTE,
                    estado_nuevo=EstadoEnvio.EN_TRANSITO,
                    observacion='Salida del almacén central',
                )
            if estado in (EstadoEnvio.EN_DESTINO, EstadoEnvio.ENTREGADO):
                HistorialEstado.objects.create(
                    encomienda=enc, empleado=empleado,
                    estado_anterior=EstadoEnvio.EN_TRANSITO,
                    estado_nuevo=EstadoEnvio.EN_DESTINO,
                    observacion='Llegó a destino',
                )
            if estado == EstadoEnvio.ENTREGADO:
                HistorialEstado.objects.create(
                    encomienda=enc, empleado=empleado,
                    estado_anterior=EstadoEnvio.EN_DESTINO,
                    estado_nuevo=EstadoEnvio.ENTREGADO,
                    observacion='Entregado al destinatario',
                )
            if estado == EstadoEnvio.DEVUELTO:
                HistorialEstado.objects.create(
                    encomienda=enc, empleado=empleado,
                    estado_anterior=EstadoEnvio.EN_DESTINO,
                    estado_nuevo=EstadoEnvio.DEVUELTO,
                    observacion='Destinatario no encontrado',
                )

            Encomienda.objects.filter(pk=enc.pk).update(fecha_registro=fecha_registro)
            creadas += 1
        except Exception:
            pass

    print(f'   ✓ {creadas} encomiendas creadas')


if __name__ == '__main__':
    print('\n' + '═' * 60)
    print(' 📦 POBLANDO BASE DE DATOS DEL SISTEMA DE ENCOMIENDAS')
    print('═' * 60 + '\n')

    if '--clean' in sys.argv:
        limpiar()
        print()

    crear_rutas()
    crear_empleados()
    crear_clientes()
    crear_encomiendas()

    print('\n' + '═' * 60)
    print(' ✅ COMPLETADO')
    print('═' * 60)
    print(f' Clientes:    {Cliente.objects.count()}')
    print(f' Empleados:   {Empleado.objects.count()}')
    print(f' Rutas:       {Ruta.objects.count()}')
    print(f' Encomiendas: {Encomienda.objects.count()}')
    print(f' Historial:   {HistorialEstado.objects.count()} registros')
    print('═' * 60 + '\n')
