"""
SESIÓN 06 — Tema 8: Versionamiento de APIs
La API está bajo /api/v1/. Las rutas FBV y CBV de empleados
demuestran los dos estilos de vista para el mismo recurso.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from envios.viewsets import EncomiendaViewSet
from envios import api_views
from api.views_fbv import (
    ruta_list, ruta_detail,
    empleado_list, empleado_detail,
    EmpleadoListCreateView, EmpleadoDetailView,
)

router = DefaultRouter()
router.register('encomiendas', EncomiendaViewSet, basename='encomienda')

urlpatterns = [

    # ── Autenticación JWT ───────────────────────────────────
    path('auth/token/',         TokenObtainPairView.as_view(),  name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),

    # ── Documentación OpenAPI ───────────────────────────────
    path('schema/', SpectacularAPIView.as_view(),                          name='schema'),
    path('docs/',   SpectacularSwaggerView.as_view(url_name='schema'),     name='swagger'),

    # ── Clientes (CBV genérica — ListAPIView) ───────────────
    path('clientes/', api_views.ClienteListView.as_view(), name='cliente-list'),

    # ── Rutas — CBV (sesión 05) ─────────────────────────────
    path('rutas/', api_views.RutaListView.as_view(), name='ruta-list'),

    # ── Rutas — FBV con @api_view (sesión 06) ──────────────
    path('rutas/fbv/',      ruta_list,   name='ruta-list-fbv'),
    path('rutas/fbv/<int:pk>/', ruta_detail, name='ruta-detail-fbv'),

    # ── Empleados — FBV con @api_view (sesión 06) ──────────
    path('empleados/fbv/',          empleado_list,   name='empleado-list-fbv'),
    path('empleados/fbv/<int:pk>/', empleado_detail, name='empleado-detail-fbv'),

    # ── Empleados — CBV genérica con mixins (sesión 06) ────
    path('empleados/',          EmpleadoListCreateView.as_view(), name='empleado-list'),
    path('empleados/<int:pk>/', EmpleadoDetailView.as_view(),     name='empleado-detail'),

    # ── Consulta DNI — RENIEC ───────────────────────────────
    path('reniec/dni/<str:dni>/', api_views.ConsultarDNIView.as_view(), name='consultar-dni'),

    # ── Dashboard en tiempo real ────────────────────────────
    path('dashboard/stats/', api_views.DashboardStatsView.as_view(), name='dashboard-stats'),

    # ── Búsqueda global (Cmd+K) ─────────────────────────────
    path('buscar/', api_views.BusquedaGlobalView.as_view(), name='buscar-global'),

    # ── ViewSets (encomiendas + acciones custom) ────────────
    path('', include(router.urls)),
]
