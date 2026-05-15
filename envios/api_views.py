import os
import requests
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.throttling import UserRateThrottle


class DNISearchThrottle(UserRateThrottle):
    """
    🔐 Rate limit específico para búsqueda de DNI.
    Protege el token de Decolecta (100 búsquedas/mes).
    Cada usuario puede hacer máximo 10 búsquedas por minuto.
    """
    scope = 'dni_search'


class BusquedaGlobalView(APIView):
    """
    GET /api/v1/buscar/?q=texto

    Busca en clientes, encomiendas y rutas. Devuelve hasta 5 de cada uno.
    Usado por el modal global Cmd+K.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q
        from rutas.models import Ruta

        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return Response({'clientes': [], 'encomiendas': [], 'rutas': []})

        clientes = list(
            Cliente.objects.activos().filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(nro_doc__icontains=q) |
                Q(email__icontains=q)
            ).values('id', 'nombres', 'apellidos', 'nro_doc')[:5]
        )

        encomiendas = list(
            Encomienda.objects.con_relaciones().filter(
                Q(codigo__icontains=q) |
                Q(remitente__nombres__icontains=q) |
                Q(remitente__apellidos__icontains=q) |
                Q(destinatario__nombres__icontains=q) |
                Q(destinatario__apellidos__icontains=q)
            ).values(
                'id', 'codigo', 'estado',
                'remitente__nombres', 'remitente__apellidos',
                'ruta__origen', 'ruta__destino',
            )[:5]
        )

        rutas = list(
            Ruta.objects.activas().filter(
                Q(codigo__icontains=q) | Q(origen__icontains=q) | Q(destino__icontains=q)
            ).values('id', 'codigo', 'origen', 'destino')[:5]
        )

        return Response({
            'clientes': clientes,
            'encomiendas': encomiendas,
            'rutas': rutas,
        })


class DashboardStatsView(APIView):
    """
    GET /api/v1/dashboard/stats/

    Devuelve todas las estadísticas del dashboard en JSON
    para actualizar la UI en tiempo real sin recargar la página.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta
        from sistema.choices import EstadoEnvio

        hoy = timezone.now().date()
        primer_dia_mes = hoy.replace(day=1)

        # Stats principales
        stats = {
            'total_activas':   Encomienda.objects.activas().count(),
            'en_transito':     Encomienda.objects.en_transito().count(),
            'con_retraso':     Encomienda.objects.con_retraso().count(),
            'entregadas_hoy':  Encomienda.objects.filter(
                estado=EstadoEnvio.ENTREGADO, fecha_entrega_real=hoy
            ).count(),
            'ingresos_mes': float(
                Encomienda.objects.filter(
                    fecha_entrega_real__gte=primer_dia_mes,
                    estado=EstadoEnvio.ENTREGADO,
                ).aggregate(total=Sum('costo_envio'))['total'] or 0
            ),
        }

        # Distribución por estado
        estado_meta = {
            'PE': ('Pendiente', '#94a3b8'),
            'TR': ('En tránsito', '#3b82f6'),
            'DE': ('En destino', '#f59e0b'),
            'EN': ('Entregado', '#10b981'),
            'DV': ('Devuelto', '#ef4444'),
        }
        chart_estados = {'labels': [], 'data': [], 'colors': []}
        for est in (
            Encomienda.objects.values('estado')
            .annotate(total=Count('id'))
            .order_by('estado')
        ):
            label, color = estado_meta.get(est['estado'], (est['estado'], '#cbd5e1'))
            chart_estados['labels'].append(label)
            chart_estados['data'].append(est['total'])
            chart_estados['colors'].append(color)

        # Últimos 7 días
        chart_semana = {'labels': [], 'data': []}
        for i in range(6, -1, -1):
            dia = hoy - timedelta(days=i)
            count = Encomienda.objects.filter(fecha_registro__date=dia).count()
            chart_semana['labels'].append(dia.strftime('%d %b'))
            chart_semana['data'].append(count)

        # Top 5 rutas
        top_rutas = list(
            Encomienda.objects.values('ruta__origen', 'ruta__destino')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )
        chart_rutas = {
            'labels': [f"{r['ruta__origen']} → {r['ruta__destino']}" for r in top_rutas],
            'data': [r['total'] for r in top_rutas],
        }

        return Response({
            **stats,
            'chart_estados': chart_estados,
            'chart_semana': chart_semana,
            'chart_rutas': chart_rutas,
            'timestamp': timezone.now().isoformat(),
        })
from .models import Encomienda, Empleado
from clientes.models import Cliente
from rutas.models import Ruta
from .serializers import (
    EncomiendaSerializer,
    EncomiendaDetailSerializer,
    ClienteSerializer,
    RutaSerializer,
)
from api.pagination import ClientePagination


class EncomiendaListCreateView(generics.ListCreateAPIView):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        try:
            empleado = Empleado.objects.get(email=self.request.user.email)
        except Empleado.DoesNotExist:
            raise ValidationError(
                'Tu usuario no tiene un empleado asociado. Contacta al administrador.'
            )
        serializer.save(empleado_registro=empleado)


class EncomiendaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EncomiendaDetailSerializer
        return EncomiendaSerializer


class ClienteListView(generics.ListAPIView):
    serializer_class = ClienteSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = ClientePagination

    def get_queryset(self):
        from django.db.models import Q
        qs = Cliente.objects.activos()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(nro_doc__icontains=q)
            )
        return qs.order_by('apellidos', 'nombres')


class RutaListView(generics.ListAPIView):
    serializer_class = RutaSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Ruta.objects.activas().order_by('codigo')


# ════════════════════════════════════════════════════════════
# CONSULTA DNI - RENIEC (apis.net.pe + fallback Faker)
# ════════════════════════════════════════════════════════════
class ConsultarDNIView(APIView):
    """
    GET /api/v1/reniec/dni/<dni>/

    Consulta los datos de un DNI peruano usando apis.net.pe (RENIEC).
    Si no hay token configurado en APIS_NET_PE_TOKEN, devuelve datos
    simulados con Faker (modo demo) — útil para desarrollo.

    Respuesta:
    {
        "dni": "72927772",
        "nombres": "Arnold Braian",
        "apellido_paterno": "Mejia",
        "apellido_materno": "Quiroz",
        "apellidos": "Mejia Quiroz",
        "fuente": "reniec" | "demo"
    }
    """
    # Acepta tanto JWT (Postman) como Session (navegador del sistema)
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DNISearchThrottle]  # 🔐 10 búsquedas/min/usuario

    @staticmethod
    def _generar_datos_sugeridos(dni, nombres, paterno):
        """
        Genera teléfono, email y dirección coherentes y consistentes
        para el DNI dado. Mismo DNI = mismos datos siempre.
        Estos son SUGERENCIAS — el usuario puede editarlos antes de guardar.
        """
        import random, unicodedata

        def slugify(s):
            """Quita tildes y caracteres especiales."""
            normalized = unicodedata.normalize('NFKD', s)
            return ''.join(c for c in normalized if not unicodedata.combining(c)).lower().split()[0]

        # Seed determinístico: mismo DNI siempre devuelve mismos datos sugeridos
        rng = random.Random(int(dni))

        # Email: nombre.apellido + número aleatorio + @gmail.com
        n = slugify(nombres) if nombres else 'usuario'
        a = slugify(paterno) if paterno else 'pe'
        proveedores = ['gmail.com', 'hotmail.com', 'outlook.com']
        email = f'{n}.{a}{rng.randint(10, 999)}@{rng.choice(proveedores)}'

        # Teléfono: 9 dígitos comenzando con 9 (móvil peruano)
        telefono = f'9{rng.randint(10000000, 99999999)}'

        # Dirección: avenida + número + distrito de Lima
        tipos_via = ['Av.', 'Jr.', 'Calle']
        nombres_via = [
            'Las Flores', 'Los Pinos', 'San Martín', 'Bolívar', 'Grau',
            'Arequipa', 'Brasil', 'Petit Thouars', 'Salaverry', 'La Marina',
            'Javier Prado', 'Benavides', 'Larco', 'Pardo', 'Angamos',
        ]
        distritos = [
            'Miraflores', 'San Isidro', 'Surco', 'La Molina', 'Surquillo',
            'Lince', 'Magdalena', 'San Borja', 'Jesús María', 'Pueblo Libre',
            'Barranco', 'Chorrillos', 'San Juan de Lurigancho', 'Los Olivos', 'Comas',
        ]
        direccion = (
            f'{rng.choice(tipos_via)} {rng.choice(nombres_via)} '
            f'{rng.randint(100, 9999)}, {rng.choice(distritos)}, Lima'
        )

        return {
            'email': email,
            'telefono': telefono,
            'direccion': direccion,
        }

    def get(self, request, dni):
        # 1. Validar formato
        if not dni.isdigit() or len(dni) != 8:
            return Response(
                {'error': 'El DNI debe tener exactamente 8 dígitos numéricos.'},
                status=400
            )

        # 2. Verificar si el cliente ya existe en nuestra BD
        try:
            cliente = Cliente.objects.get(nro_doc=dni)
            return Response({
                'dni': cliente.nro_doc,
                'nombres': cliente.nombres,
                'apellido_paterno': cliente.apellidos.split(' ')[0] if cliente.apellidos else '',
                'apellido_materno': ' '.join(cliente.apellidos.split(' ')[1:]) if cliente.apellidos else '',
                'apellidos': cliente.apellidos,
                'telefono': cliente.telefono or '',
                'email': cliente.email or '',
                'direccion': cliente.direccion or '',
                'fuente': 'local',
                'cliente_id': cliente.id,
                'mensaje': 'Cliente ya registrado en el sistema.',
            })
        except Cliente.DoesNotExist:
            pass

        # 3. Intentar consulta real
        # Primero Decolecta (decolecta.com), si no, apis.net.pe
        decolecta_token = os.environ.get('DECOLECTA_TOKEN', '').strip()
        apis_net_pe_token = os.environ.get('APIS_NET_PE_TOKEN', '').strip()

        # ── Decolecta ──
        if decolecta_token:
            try:
                r = requests.get(
                    f'https://api.decolecta.com/v1/reniec/dni?numero={dni}',
                    headers={'Authorization': f'Bearer {decolecta_token}'},
                    timeout=8,
                )
                if r.status_code == 200:
                    data = r.json()
                    nombres = (data.get('first_name') or data.get('nombres') or '').strip().title()
                    paterno = (data.get('first_last_name') or data.get('apellidoPaterno') or '').strip().title()
                    materno = (data.get('second_last_name') or data.get('apellidoMaterno') or '').strip().title()

                    return Response({
                        'dni': data.get('document_number', dni),
                        'nombres': nombres,
                        'apellido_paterno': paterno,
                        'apellido_materno': materno,
                        'apellidos': f'{paterno} {materno}'.strip(),
                        'fuente': 'reniec',
                    })
                if r.status_code in (401, 403):
                    return Response(
                        {'error': 'Token de Decolecta inválido o expirado.'},
                        status=401
                    )
                if r.status_code == 404:
                    return Response(
                        {'error': 'DNI no encontrado en RENIEC.'},
                        status=404
                    )
            except requests.RequestException:
                pass  # cae al siguiente

        # ── apis.net.pe ──
        if apis_net_pe_token:
            try:
                r = requests.get(
                    f'https://api.apis.net.pe/v2/reniec/dni?numero={dni}',
                    headers={'Authorization': f'Bearer {apis_net_pe_token}'},
                    timeout=8,
                )
                if r.status_code == 200:
                    data = r.json()
                    paterno = (data.get('apellidoPaterno') or '').strip().title()
                    materno = (data.get('apellidoMaterno') or '').strip().title()
                    return Response({
                        'dni': data.get('numeroDocumento', dni),
                        'nombres': (data.get('nombres') or '').strip().title(),
                        'apellido_paterno': paterno,
                        'apellido_materno': materno,
                        'apellidos': f'{paterno} {materno}'.strip(),
                        'fuente': 'reniec',
                    })
                if r.status_code == 404:
                    return Response(
                        {'error': 'DNI no encontrado en RENIEC.'},
                        status=404
                    )
            except requests.RequestException:
                pass  # cae al fallback demo

        # 4. Fallback: generar datos coherentes con Faker
        # Mismo DNI siempre devuelve mismos datos (seed)
        from faker import Faker
        fake = Faker('es_ES')
        Faker.seed(int(dni))

        nombres = fake.first_name()
        paterno = fake.last_name()
        materno = fake.last_name()

        return Response({
            'dni': dni,
            'nombres': nombres,
            'apellido_paterno': paterno,
            'apellido_materno': materno,
            'apellidos': f'{paterno} {materno}',
            'fuente': 'demo',
            'mensaje': 'Datos simulados (modo desarrollo). Configura APIS_NET_PE_TOKEN en .env para datos reales.',
        })
