from django.contrib import admin
from django.urls import path
from envios.views import dashboard_encomiendas # Importamos tu nueva vista

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard_encomiendas, name='home'), # La raíz del sitio cargará el dashboard
]
