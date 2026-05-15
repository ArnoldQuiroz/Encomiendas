from django.utils import timezone
from envios.models import Encomienda
from envios.permisos import get_rol


def estadisticas_globales(request):
    if not request.user.is_authenticated:
        return {}

    # 🔔 Notificaciones para el navbar
    encomiendas_retraso = (
        Encomienda.objects.con_retraso()
        .con_relaciones()
        .order_by('fecha_entrega_est')[:5]
    )
    hoy = timezone.now().date()
    nuevas_hoy = Encomienda.objects.filter(fecha_registro__date=hoy).count()

    # ✅ Contar tareas pendientes del usuario
    from envios.models import Tarea
    tareas_pend = Tarea.objects.filter(usuario=request.user, completada=False).count()

    return {
        'nav_activas': Encomienda.objects.activas().count(),
        'nav_retraso': Encomienda.objects.con_retraso().count(),
        'notif_retraso_list': encomiendas_retraso,
        'notif_nuevas_hoy': nuevas_hoy,
        'notif_total': Encomienda.objects.con_retraso().count() + (1 if nuevas_hoy > 0 else 0),
        'user_rol': get_rol(request.user),
        'nav_tareas_pend': tareas_pend,
    }
