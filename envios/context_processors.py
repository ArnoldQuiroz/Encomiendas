from envios.models import Encomienda

def estadisticas_globales(request):
    if request.user.is_authenticated:
        return {
            'nav_activas': Encomienda.objects.activas().count(),
            'nav_retraso': Encomienda.objects.con_retraso().count(),
        }
    return {}
