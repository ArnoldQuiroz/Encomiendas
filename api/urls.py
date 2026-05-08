from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from envios.viewsets import EncomiendaViewSet
from envios import api_views

router = DefaultRouter()
router.register('encomiendas', EncomiendaViewSet, basename='encomienda')

urlpatterns = [
    # Autenticación JWT
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Documentación interactiva
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),

    # Clientes y rutas (vistas genéricas)
    path('clientes/', api_views.ClienteListView.as_view(), name='cliente-list'),
    path('rutas/', api_views.RutaListView.as_view(), name='ruta-list'),

    # ViewSets (encomiendas + acciones personalizadas)
    path('', include(router.urls)),
]
