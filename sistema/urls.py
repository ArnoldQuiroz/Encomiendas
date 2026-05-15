from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Título del admin personalizado (Checklist Punto 9)
admin.site.site_header = 'Sistema de Gestión de Encomiendas USS'
admin.site.site_title = 'Encomiendas Admin'
admin.site.index_title = 'Panel de Administración'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('envios.urls')),
    path('', include('clientes.urls')),
    path('api/v1/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 🎨 Handlers de errores personalizados
handler404 = 'envios.views_errors.error_404'
handler500 = 'envios.views_errors.error_500'
handler403 = 'envios.views_errors.error_403'