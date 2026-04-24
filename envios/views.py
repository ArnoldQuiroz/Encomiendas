from django.shortcuts import render
from .models import Encomienda

def dashboard_encomiendas(request):
    # Usamos el QuerySet optimizado que creamos en la sesión anterior
    encomiendas = Encomienda.objects.con_relaciones().all()
    return render(request, 'dashboard.html', {'encomiendas': encomiendas})