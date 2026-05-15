"""
SESIÓN 06 — Tema 7: Vistas basadas en funciones (@api_view)
y vistas genéricas para Empleados (CBV con mixins).

FBVs implementadas:
  GET  /api/v1/rutas/                → ruta_list
  GET  /api/v1/rutas/<pk>/           → ruta_detail
  GET  /api/v1/empleados/            → empleado_list  (FBV)
  POST /api/v1/empleados/            → empleado_list  (FBV)
  GET  /api/v1/empleados/<pk>/       → empleado_detail (FBV)
  PUT  /api/v1/empleados/<pk>/       → empleado_detail (FBV)
  DELETE /api/v1/empleados/<pk>/     → empleado_detail (FBV)

CBVs genéricas para Empleados (alternativa):
  GET/POST  /api/v1/empleados/cbv/   → EmpleadoListCreateView
  GET/PUT/DELETE /api/v1/empleados/cbv/<pk>/ → EmpleadoDetailView
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

from rutas.models import Ruta
from envios.models import Empleado
from envios.serializers import RutaSerializer, EmpleadoSerializer
from sistema.choices import EstadoGeneral


# ════════════════════════════════════════════════════════════
# FBV — RUTAS
# ════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ruta_list(request):
    """
    GET /api/v1/rutas/fbv/
    Lista todas las rutas activas. Soporta ?origen= y ?destino= como filtros.
    """
    qs = Ruta.objects.activas().order_by('codigo')

    origen  = request.query_params.get('origen')
    destino = request.query_params.get('destino')
    if origen:
        qs = qs.filter(origen__icontains=origen)
    if destino:
        qs = qs.filter(destino__icontains=destino)

    serializer = RutaSerializer(qs, many=True)
    return Response({
        'ok': True,
        'total': qs.count(),
        'rutas': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ruta_detail(request, pk):
    """
    GET /api/v1/rutas/fbv/<pk>/
    Devuelve el detalle de una ruta junto con estadísticas de uso.
    """
    try:
        ruta = Ruta.objects.get(pk=pk)
    except Ruta.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Ruta no encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )

    from envios.models import Encomienda
    total_envios = Encomienda.objects.filter(ruta=ruta).count()
    en_transito  = Encomienda.objects.filter(ruta=ruta, estado='TR').count()

    return Response({
        'ok': True,
        'ruta': RutaSerializer(ruta).data,
        'estadisticas': {
            'total_envios': total_envios,
            'en_transito':  en_transito,
        },
    })


# ════════════════════════════════════════════════════════════
# FBV — EMPLEADOS (lista + crear)
# ════════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def empleado_list(request):
    """
    GET  /api/v1/empleados/fbv/  → lista de empleados activos
    POST /api/v1/empleados/fbv/  → crear nuevo empleado
    """
    if request.method == 'GET':
        qs = Empleado.objects.filter(estado=EstadoGeneral.ACTIVO).order_by('apellidos')
        serializer = EmpleadoSerializer(qs, many=True)
        return Response({
            'ok': True,
            'total': qs.count(),
            'empleados': serializer.data,
        })

    elif request.method == 'POST':
        serializer = EmpleadoSerializer(data=request.data)
        if serializer.is_valid():
            from django.utils import timezone
            import random, string
            codigo = 'EC-' + ''.join(random.choices(string.digits, k=4))
            while Empleado.objects.filter(codigo=codigo).exists():
                codigo = 'EC-' + ''.join(random.choices(string.digits, k=4))
            serializer.save(codigo=codigo)
            return Response(
                {'ok': True, 'empleado': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'ok': False, 'errores': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


# ════════════════════════════════════════════════════════════
# FBV — EMPLEADOS (detalle, editar, eliminar)
# ════════════════════════════════════════════════════════════

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def empleado_detail(request, pk):
    """
    GET    /api/v1/empleados/fbv/<pk>/  → detalle
    PUT    /api/v1/empleados/fbv/<pk>/  → actualización completa
    PATCH  /api/v1/empleados/fbv/<pk>/  → actualización parcial
    DELETE /api/v1/empleados/fbv/<pk>/  → dar de baja (soft delete)
    """
    try:
        empleado = Empleado.objects.get(pk=pk)
    except Empleado.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Empleado no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        return Response({'ok': True, 'empleado': EmpleadoSerializer(empleado).data})

    elif request.method in ('PUT', 'PATCH'):
        partial = request.method == 'PATCH'
        serializer = EmpleadoSerializer(empleado, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({'ok': True, 'empleado': serializer.data})
        return Response(
            {'ok': False, 'errores': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    elif request.method == 'DELETE':
        empleado.estado = EstadoGeneral.DE_BAJA
        empleado.save()
        return Response(
            {'ok': True, 'mensaje': f'Empleado {empleado.codigo} dado de baja.'},
            status=status.HTTP_200_OK
        )


# ════════════════════════════════════════════════════════════
# CBV GENÉRICAS — Empleados (versión alternativa con mixins)
# Demuestra cómo la misma lógica se puede expresar con clases
# ════════════════════════════════════════════════════════════

class EmpleadoListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/empleados/
    POST /api/v1/empleados/
    """
    queryset = Empleado.objects.filter(estado=EstadoGeneral.ACTIVO).order_by('apellidos')
    serializer_class = EmpleadoSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        import random, string
        codigo = 'EC-' + ''.join(random.choices(string.digits, k=4))
        while Empleado.objects.filter(codigo=codigo).exists():
            codigo = 'EC-' + ''.join(random.choices(string.digits, k=4))
        serializer.save(codigo=codigo)


class EmpleadoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/empleados/<pk>/
    PUT    /api/v1/empleados/<pk>/
    PATCH  /api/v1/empleados/<pk>/
    DELETE /api/v1/empleados/<pk>/
    """
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.estado = EstadoGeneral.DE_BAJA
        instance.save()
