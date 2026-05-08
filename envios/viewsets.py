from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Encomienda, Empleado
from .serializers import (
    EncomiendaSerializer,
    EncomiendaDetailSerializer,
    HistorialEstadoSerializer,
)
from api.pagination import EncomiendaPagination, HistorialPagination
from sistema.choices import EstadoEnvio


class EncomiendaViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet genera automáticamente:
      list()          → GET    /encomiendas/
      create()        → POST   /encomiendas/
      retrieve()      → GET    /encomiendas/{pk}/
      update()        → PUT    /encomiendas/{pk}/
      partial_update()→ PATCH  /encomiendas/{pk}/
      destroy()       → DELETE /encomiendas/{pk}/
    """
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = EncomiendaPagination

    # ── Filtros ────────────────────────────────────────────────────
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'ruta', 'remitente', 'destinatario']
    search_fields = ['codigo', 'descripcion', 'remitente__nombres', 'destinatario__nombres']
    ordering_fields = ['fecha_registro', 'fecha_entrega_est', 'costo_envio', 'peso_kg']
    ordering = ['-fecha_registro']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EncomiendaDetailSerializer
        return EncomiendaSerializer

    def perform_create(self, serializer):
        try:
            empleado = Empleado.objects.get(email=self.request.user.email)
        except Empleado.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'Tu usuario no tiene un empleado asociado. Contacta al administrador.'
            )
        serializer.save(empleado_registro=empleado)

    # ── Acción de detalle: POST /encomiendas/{pk}/cambiar_estado/ ──
    @action(detail=True, methods=['post'], url_path='cambiar_estado')
    def cambiar_estado(self, request, pk=None):
        enc = self.get_object()
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')

        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            empleado = Empleado.objects.get(email=request.user.email)
            enc.cambiar_estado(nuevo_estado, empleado, observacion)
            return Response(EncomiendaSerializer(enc).data)
        except Empleado.DoesNotExist:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ── Acción de lista: GET /encomiendas/con_retraso/ ─────────────
    @action(detail=False, methods=['get'], url_path='con_retraso')
    def con_retraso(self, request):
        qs = Encomienda.objects.con_retraso().con_relaciones()
        return Response(self.get_serializer(qs, many=True).data)

    # ── Acción de lista: GET /encomiendas/pendientes/ ───────────────
    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        qs = Encomienda.objects.pendientes().con_relaciones()
        return Response(self.get_serializer(qs, many=True).data)

    # ── Acción de detalle: GET /encomiendas/{pk}/historial/ ─────────
    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None):
        """
        GET /api/v1/encomiendas/{pk}/historial/
        GET /api/v1/encomiendas/{pk}/historial/?limit=5&offset=10
        """
        enc = self.get_object()
        qs = enc.historial.select_related('empleado').order_by('-fecha_cambio')
        paginator = HistorialPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = HistorialEstadoSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = HistorialEstadoSerializer(qs, many=True)
        return Response(serializer.data)

    # ── Acción de lista: GET /encomiendas/estadisticas/ ─────────────
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """GET /api/v1/encomiendas/estadisticas/ — sin paginación."""
        from django.utils import timezone
        hoy = timezone.now().date()
        return Response({
            'total_activas': Encomienda.objects.activas().count(),
            'en_transito': Encomienda.objects.en_transito().count(),
            'con_retraso': Encomienda.objects.con_retraso().count(),
            'entregadas_hoy': Encomienda.objects.filter(
                estado=EstadoEnvio.ENTREGADO,
                fecha_entrega_real=hoy
            ).count(),
        })
