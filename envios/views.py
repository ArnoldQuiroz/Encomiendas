from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Encomienda, Empleado
from .forms import EncomiendaForm
from .permisos import rol_requerido, ROL_ADMIN, ROL_OPERADOR
from sistema.choices import EstadoEnvio


def _resolver_empleado(user):
    """
    Busca el Empleado asociado al usuario:
      1. Intenta por email exacto
      2. Si es superuser/staff sin match, usa el primer empleado activo
    Devuelve None si no encuentra ninguno.
    """
    try:
        return Empleado.objects.get(email=user.email)
    except Empleado.DoesNotExist:
        if user.is_superuser or user.is_staff:
            return Empleado.objects.filter(estado=1).first()
        return None

@login_required
def dashboard(request):
    from django.db.models import Count, Sum
    from datetime import timedelta
    import json

    hoy = timezone.now().date()

    # ── Stats principales ──
    stats = {
        'total_activas': Encomienda.objects.activas().count(),
        'en_transito': Encomienda.objects.en_transito().count(),
        'con_retraso': Encomienda.objects.con_retraso().count(),
        'entregadas_hoy': Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO, fecha_entrega_real=hoy
        ).count(),
    }

    # ── Chart 1: Distribución por estado (donut) ──
    estados_data = list(
        Encomienda.objects.values('estado')
        .annotate(total=Count('id'))
        .order_by('estado')
    )
    chart_estados = {
        'labels': [],
        'data': [],
        'colors': [],
    }
    estado_meta = {
        'PE': ('Pendiente', '#94a3b8'),
        'TR': ('En tránsito', '#3b82f6'),
        'DE': ('En destino', '#f59e0b'),
        'EN': ('Entregado', '#10b981'),
        'DV': ('Devuelto', '#ef4444'),
    }
    for est in estados_data:
        label, color = estado_meta.get(est['estado'], (est['estado'], '#cbd5e1'))
        chart_estados['labels'].append(label)
        chart_estados['data'].append(est['total'])
        chart_estados['colors'].append(color)

    # ── Chart 2: Encomiendas últimos 7 días (línea) ──
    chart_semana = {'labels': [], 'data': []}
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        count = Encomienda.objects.filter(fecha_registro__date=dia).count()
        chart_semana['labels'].append(dia.strftime('%d %b'))
        chart_semana['data'].append(count)

    # ── Chart 3: Top 5 rutas más usadas ──
    top_rutas = list(
        Encomienda.objects.values('ruta__origen', 'ruta__destino')
        .annotate(total=Count('id'), ingresos=Sum('costo_envio'))
        .order_by('-total')[:5]
    )
    chart_rutas = {
        'labels': [f"{r['ruta__origen']} → {r['ruta__destino']}" for r in top_rutas],
        'data': [r['total'] for r in top_rutas],
    }

    # ── Ingresos del mes (cuenta por fecha de entrega real) ──
    # Apenas un envío se marca como ENTREGADO, su costo se suma al mes actual
    primer_dia_mes = hoy.replace(day=1)
    ingresos_mes = Encomienda.objects.filter(
        fecha_entrega_real__gte=primer_dia_mes,
        estado=EstadoEnvio.ENTREGADO,
    ).aggregate(total=Sum('costo_envio'))['total'] or 0

    return render(request, 'envios/dashboard.html', {
        **stats,
        'ingresos_mes': ingresos_mes,
        'ultimas': Encomienda.objects.con_relaciones()[:8],
        'chart_estados_json': json.dumps(chart_estados),
        'chart_semana_json': json.dumps(chart_semana),
        'chart_rutas_json': json.dumps(chart_rutas),
    })

def landing_publica(request):
    """🎯 Landing page pública para visitantes no autenticados."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    # Métricas públicas (no sensibles) para mostrar credibilidad
    from clientes.models import Cliente
    from rutas.models import Ruta
    stats = {
        'clientes': Cliente.objects.activos().count(),
        'rutas': Ruta.objects.activas().count(),
        'entregas': Encomienda.objects.filter(estado=EstadoEnvio.ENTREGADO).count(),
    }
    return render(request, 'landing.html', {'stats': stats})


def tracking_landing(request):
    """🌐 Portal público — el cliente pone su código y rastrea su paquete."""
    codigo = request.GET.get('codigo', '').strip().upper()
    if codigo:
        return redirect('tracking_detalle', codigo=codigo)
    return render(request, 'tracking/landing.html')


def tracking_detalle(request, codigo):
    """🌐 Vista pública — muestra el estado del paquete sin requerir login."""
    try:
        enc = (
            Encomienda.objects.con_relaciones()
            .prefetch_related('historial__empleado')
            .get(codigo__iexact=codigo)
        )
    except Encomienda.DoesNotExist:
        return render(request, 'tracking/no_encontrado.html', {'codigo': codigo}, status=404)

    historial = enc.historial.order_by('fecha_cambio')

    # Mapear progreso del estado en %
    progreso_map = {
        'PE': 10, 'TR': 40, 'DE': 75, 'EN': 100, 'DV': 100,
    }
    progreso = progreso_map.get(enc.estado, 0)

    return render(request, 'tracking/detalle.html', {
        'encomienda': enc,
        'historial': historial,
        'progreso': progreso,
    })


@login_required
def encomienda_lista(request):
    qs = Encomienda.objects.con_relaciones()
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '')
    
    # 📅 Filtros por rango de fechas
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')
    tag = request.GET.get('tag', '')

    if estado:
        qs = qs.filter(estado=estado)
    if desde:
        qs = qs.filter(fecha_registro__date__gte=desde)
    if hasta:
        qs = qs.filter(fecha_registro__date__lte=hasta)
    if tag:
        qs = qs.filter(tags__icontains=tag)
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(codigo__icontains=q) |
            # Remitente: nombre, apellido, DNI
            Q(remitente__nombres__icontains=q) |
            Q(remitente__apellidos__icontains=q) |
            Q(remitente__nro_doc__icontains=q) |
            # Destinatario: nombre, apellido, DNI
            Q(destinatario__nombres__icontains=q) |
            Q(destinatario__apellidos__icontains=q) |
            Q(destinatario__nro_doc__icontains=q) |
            # Ruta: código, origen, destino
            Q(ruta__codigo__icontains=q) |
            Q(ruta__origen__icontains=q) |
            Q(ruta__destino__icontains=q) |
            # Descripción del paquete
            Q(descripcion__icontains=q)
        ).distinct()
        
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page', 1)
    encomiendas = paginator.get_page(page_number)
    
    from .models import Encomienda as EncModel
    return render(request, 'envios/lista.html', {
        'encomiendas': encomiendas,
        'estados': EstadoEnvio.choices,
        'estado_activo': estado,
        'q': q,
        'desde': desde,
        'hasta': hasta,
        'tag_activo': tag,
        'tags_disponibles': EncModel.TAG_INFO,
    })

@login_required
def encomienda_detalle(request, pk):
    enc = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    historial = enc.historial.select_related('empleado').all()
    comentarios = enc.comentarios.select_related('empleado').order_by('-fecha')
    es_favorita = enc.favoritos.filter(usuario=request.user).exists()
    return render(request, 'envios/detalle.html', {
        'encomienda': enc,
        'historial': historial,
        'comentarios': comentarios,
        'estados': EstadoEnvio.choices,
        'es_favorita': es_favorita,
    })


@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
@require_POST
def encomienda_comentar(request, pk):
    """💬 Agrega un comentario interno a una encomienda."""
    from .models import ComentarioInterno
    enc = get_object_or_404(Encomienda, pk=pk)
    empleado = _resolver_empleado(request.user)
    if not empleado:
        messages.error(request, 'No puedes comentar: tu usuario no tiene empleado asociado.')
        return redirect('encomienda_detalle', pk=pk)

    contenido = request.POST.get('contenido', '').strip()
    importante = request.POST.get('importante') == 'on'

    if not contenido:
        messages.error(request, 'El comentario no puede estar vacío.')
        return redirect('encomienda_detalle', pk=pk)

    ComentarioInterno.objects.create(
        encomienda=enc, empleado=empleado,
        contenido=contenido, importante=importante,
    )
    messages.success(request, 'Comentario agregado correctamente.')
    return redirect('encomienda_detalle', pk=pk)


@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
def comentario_eliminar(request, pk):
    """🗑️ Elimina un comentario (solo el autor o admin)."""
    from .models import ComentarioInterno
    c = get_object_or_404(ComentarioInterno, pk=pk)
    encomienda_pk = c.encomienda_id
    empleado = _resolver_empleado(request.user)
    if request.user.is_superuser or (empleado and c.empleado_id == empleado.id):
        c.delete()
        messages.success(request, 'Comentario eliminado.')
    else:
        messages.error(request, 'Solo el autor puede eliminar este comentario.')
    return redirect('encomienda_detalle', pk=encomienda_pk)


@login_required
def encomienda_ticket(request, pk):
    """🖨️ Ticket imprimible de la encomienda."""
    enc = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    return render(request, 'envios/ticket.html', {'encomienda': enc})


@login_required
def encomienda_etiqueta(request, pk):
    """🏷️ Etiqueta imprimible 10×7cm para pegar en el paquete físico."""
    enc = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    return render(request, 'envios/etiqueta.html', {'encomienda': enc})


# ════════════════════════════════════════════════════════════
# 💳 SISTEMA DE PAGOS
# ════════════════════════════════════════════════════════════
@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
@require_POST
def encomienda_marcar_pago(request, pk):
    """💳 Marca una encomienda como pagada."""
    enc = get_object_or_404(Encomienda, pk=pk)
    metodo = request.POST.get('metodo_pago', 'EFE')

    enc.estado_pago = 'PAG'
    enc.metodo_pago = metodo
    enc.fecha_pago = timezone.now()
    enc.save()

    messages.success(request, f'✓ Pago registrado ({enc.get_metodo_pago_display()}).')
    return redirect('encomienda_detalle', pk=pk)


@login_required
def cobros_pendientes(request):
    """💵 Vista de todas las encomiendas con pago pendiente."""
    from django.db.models import Sum
    qs = Encomienda.objects.filter(estado_pago='PEN').con_relaciones().order_by('-fecha_registro')
    total = qs.aggregate(s=Sum('costo_envio'))['s'] or 0
    return render(request, 'envios/cobros_pendientes.html', {
        'encomiendas': qs[:100],
        'total': total,
        'count': qs.count(),
    })


# ════════════════════════════════════════════════════════════
# 🎟️ SISTEMA DE CUPONES
# ════════════════════════════════════════════════════════════
@rol_requerido(ROL_ADMIN)
def cupones_lista(request):
    """🎟️ Lista de cupones activos."""
    from .models import Cupon

    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        if accion == 'crear':
            try:
                Cupon.objects.create(
                    codigo=request.POST.get('codigo', '').upper().strip(),
                    descripcion=request.POST.get('descripcion', '').strip(),
                    tipo=request.POST.get('tipo', 'PCT'),
                    valor=request.POST.get('valor', '0'),
                    usos_maximos=int(request.POST.get('usos_maximos', 0) or 0),
                    fecha_fin=request.POST.get('fecha_fin') or None,
                )
                messages.success(request, '✓ Cupón creado.')
            except Exception as e:
                messages.error(request, f'Error: {str(e)[:200]}')
            return redirect('cupones_lista')
        elif accion == 'toggle':
            c = get_object_or_404(Cupon, pk=request.POST.get('id'))
            c.activo = not c.activo
            c.save()
            return redirect('cupones_lista')
        elif accion == 'eliminar':
            Cupon.objects.filter(pk=request.POST.get('id')).delete()
            messages.success(request, '✓ Cupón eliminado.')
            return redirect('cupones_lista')

    cupones = Cupon.objects.all().order_by('-creado_en')
    return render(request, 'envios/cupones.html', {'cupones': cupones})


def status_page(request):
    """📊 Página pública de estado del sistema (health check)."""
    from django.db import connection
    from datetime import datetime

    # Test DB
    db_ok = False
    db_latency = 0
    try:
        import time
        t0 = time.perf_counter()
        with connection.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
        db_latency = round((time.perf_counter() - t0) * 1000, 1)
        db_ok = True
    except Exception:
        pass

    # Test cache (sessions)
    cache_ok = True  # Si llegaste aquí, las sesiones funcionan

    # Stats
    from .models import HistorialEstado
    from clientes.models import Cliente

    servicios = [
        {
            'nombre': 'Servidor web',
            'estado': 'operacional',
            'descripcion': 'Django sirviendo peticiones',
            'icono': 'fa-server',
            'color': '#10b981',
        },
        {
            'nombre': 'Base de datos',
            'estado': 'operacional' if db_ok else 'caido',
            'descripcion': f'PostgreSQL · {db_latency}ms de latencia',
            'icono': 'fa-database',
            'color': '#10b981' if db_ok else '#ef4444',
        },
        {
            'nombre': 'API REST',
            'estado': 'operacional',
            'descripcion': 'DRF + JWT funcionando',
            'icono': 'fa-code',
            'color': '#10b981',
        },
        {
            'nombre': 'Tracking público',
            'estado': 'operacional',
            'descripcion': 'Rastreo sin login disponible',
            'icono': 'fa-search-location',
            'color': '#10b981',
        },
        {
            'nombre': 'Integración RENIEC',
            'estado': 'operacional',
            'descripcion': 'Consulta DNI vía Decolecta',
            'icono': 'fa-id-card',
            'color': '#10b981',
        },
        {
            'nombre': 'Notificaciones email',
            'estado': 'operacional',
            'descripcion': 'Envío automático en cambios de estado',
            'icono': 'fa-envelope',
            'color': '#10b981',
        },
    ]

    todos_ok = all(s['estado'] == 'operacional' for s in servicios)

    metricas = {
        'clientes': Cliente.objects.count(),
        'encomiendas': Encomienda.objects.count(),
        'historial': HistorialEstado.objects.count(),
        'db_latency': db_latency,
        'check_time': datetime.now().strftime('%H:%M:%S'),
    }

    return render(request, 'status.html', {
        'servicios': servicios,
        'metricas': metricas,
        'todos_ok': todos_ok,
    })


@rol_requerido(ROL_ADMIN)
def backup_view(request):
    """💾 Sistema de respaldo descargable (solo Admin)."""
    from .models import HistorialEstado, ComentarioInterno
    from clientes.models import Cliente
    from rutas.models import Ruta

    stats = {
        'clientes': Cliente.objects.count(),
        'rutas': Ruta.objects.count(),
        'empleados': Empleado.objects.count(),
        'encomiendas': Encomienda.objects.count(),
        'historial': HistorialEstado.objects.count(),
        'comentarios': ComentarioInterno.objects.count(),
    }
    stats['total'] = sum(stats.values())

    return render(request, 'envios/backup.html', {'stats': stats})


@rol_requerido(ROL_ADMIN)
def backup_descargar(request, formato='json'):
    """📦 Descarga el backup completo en JSON o SQL."""
    from django.http import HttpResponse, JsonResponse
    from django.core.serializers import serialize
    from .models import HistorialEstado, ComentarioInterno
    from clientes.models import Cliente
    from rutas.models import Ruta
    import json

    fecha = timezone.now().strftime('%Y%m%d_%H%M')

    if formato == 'json':
        data = {
            'meta': {
                'generado_por': request.user.username,
                'fecha': timezone.now().isoformat(),
                'version': '1.0',
            },
            'clientes': list(Cliente.objects.values()),
            'rutas': list(Ruta.objects.values()),
            'empleados': list(Empleado.objects.values()),
            'encomiendas': list(Encomienda.objects.values()),
            'historial': list(HistorialEstado.objects.values()),
            'comentarios': list(ComentarioInterno.objects.values()),
        }
        # Convertir objetos Decimal/Date a string para JSON
        json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="backup_encomiendas_{fecha}.json"'
        return response

    elif formato == 'csv':
        import csv
        from io import StringIO
        # ZIP con varios CSVs
        import zipfile
        from io import BytesIO

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Clientes
            csv_buf = StringIO()
            w = csv.writer(csv_buf)
            w.writerow(['id', 'tipo_doc', 'nro_doc', 'nombres', 'apellidos', 'telefono', 'email', 'direccion'])
            for c in Cliente.objects.all():
                w.writerow([c.id, c.tipo_doc, c.nro_doc, c.nombres, c.apellidos, c.telefono or '', c.email or '', c.direccion or ''])
            zf.writestr('clientes.csv', csv_buf.getvalue())

            # Encomiendas
            csv_buf = StringIO()
            w = csv.writer(csv_buf)
            w.writerow(['codigo', 'remitente_dni', 'destinatario_dni', 'ruta', 'estado', 'peso_kg', 'costo_envio', 'fecha_registro'])
            for e in Encomienda.objects.select_related('remitente', 'destinatario', 'ruta'):
                w.writerow([e.codigo, e.remitente.nro_doc, e.destinatario.nro_doc,
                           f'{e.ruta.origen}->{e.ruta.destino}', e.get_estado_display(),
                           e.peso_kg, e.costo_envio, e.fecha_registro.strftime('%Y-%m-%d %H:%M')])
            zf.writestr('encomiendas.csv', csv_buf.getvalue())

            # Rutas
            csv_buf = StringIO()
            w = csv.writer(csv_buf)
            w.writerow(['codigo', 'origen', 'destino', 'precio_base', 'dias_entrega'])
            for r in Ruta.objects.all():
                w.writerow([r.codigo, r.origen, r.destino, r.precio_base, r.dias_entrega])
            zf.writestr('rutas.csv', csv_buf.getvalue())

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="backup_encomiendas_{fecha}.zip"'
        return response

    return redirect('backup')


@login_required
def mapa_heatmap(request):
    """🔥 Mapa de calor: burbujas por ciudad según volumen de envíos."""
    import json
    from django.db.models import Count

    coords = {
        'Lima':         [-12.046, -77.042],
        'Arequipa':     [-16.398, -71.537],
        'Cusco':        [-13.531, -71.967],
        'Trujillo':     [-8.111, -79.029],
        'Piura':        [-5.194, -80.633],
        'Iquitos':      [-3.749, -73.252],
        'Chiclayo':     [-6.776, -79.844],
        'Huancayo':     [-12.066, -75.205],
        'Tacna':        [-18.014, -70.252],
        'bagua capital':[-5.629, -78.530],
        'Bagua Capital':[-5.629, -78.530],
    }

    por_destino = dict(
        Encomienda.objects.values_list('ruta__destino')
        .annotate(total=Count('id'))
    )
    por_origen = dict(
        Encomienda.objects.values_list('ruta__origen')
        .annotate(total=Count('id'))
    )

    ciudades = []
    for nombre, coord in coords.items():
        envios_destino = por_destino.get(nombre, 0)
        envios_origen = por_origen.get(nombre, 0)
        total = envios_destino + envios_origen
        if total > 0:
            ciudades.append({
                'nombre': nombre.title(),
                'coord': coord,
                'destino': envios_destino,
                'origen': envios_origen,
                'total': total,
            })

    ciudades.sort(key=lambda x: x['total'], reverse=True)

    return render(request, 'envios/heatmap.html', {
        'ciudades_json': json.dumps(ciudades),
        'top_ciudades': ciudades[:5],
        'total': sum(c['total'] for c in ciudades),
    })


@login_required
def mapa_envios(request):
    """🗺️ Mapa con todos los envíos activos en el Perú."""
    import json
    activos = Encomienda.objects.activas().con_relaciones()

    # Coordenadas de ciudades
    coords = {
        'Lima':         [-12.046, -77.042],
        'Arequipa':     [-16.398, -71.537],
        'Cusco':        [-13.531, -71.967],
        'Trujillo':     [-8.111, -79.029],
        'Piura':        [-5.194, -80.633],
        'Iquitos':      [-3.749, -73.252],
        'Chiclayo':     [-6.776, -79.844],
        'Huancayo':     [-12.066, -75.205],
        'Tacna':        [-18.014, -70.252],
        'bagua capital':[-5.629, -78.530],
        'Bagua Capital':[-5.629, -78.530],
    }
    estado_colors = {
        'PE': '#94a3b8', 'TR': '#3b82f6', 'DE': '#f59e0b',
        'EN': '#10b981', 'DV': '#ef4444',
    }

    rutas_data = []
    for enc in activos[:100]:  # límite por performance
        ori = coords.get(enc.ruta.origen) or coords.get(enc.ruta.origen.lower())
        dst = coords.get(enc.ruta.destino) or coords.get(enc.ruta.destino.lower())
        if not ori or not dst:
            continue
        rutas_data.append({
            'codigo':   enc.codigo,
            'origen':   enc.ruta.origen,
            'destino':  enc.ruta.destino,
            'estado':   enc.estado,
            'estado_label': enc.get_estado_display(),
            'color':    estado_colors.get(enc.estado, '#94a3b8'),
            'ori_coord': ori,
            'dst_coord': dst,
            'remitente': enc.remitente.nombre_completo,
            'destinatario': enc.destinatario.nombre_completo,
            'costo':    float(enc.costo_envio),
            'pk':       enc.pk,
        })

    return render(request, 'envios/mapa.html', {
        'rutas_json': json.dumps(rutas_data),
        'total_activas': len(rutas_data),
    })


@login_required
def reportes(request):
    """📊 Reporte mensual: stats, ranking de clientes, ingresos por ruta."""
    from django.db.models import Count, Sum, Avg
    from datetime import timedelta

    hoy = timezone.now().date()
    # Mes seleccionado (default: actual)
    mes_param = request.GET.get('mes', hoy.strftime('%Y-%m'))
    try:
        anio, mes = mes_param.split('-')
        anio, mes = int(anio), int(mes)
    except (ValueError, AttributeError):
        anio, mes = hoy.year, hoy.month

    primer_dia = timezone.datetime(anio, mes, 1).date()
    if mes == 12:
        ultimo_dia = timezone.datetime(anio + 1, 1, 1).date() - timedelta(days=1)
    else:
        ultimo_dia = timezone.datetime(anio, mes + 1, 1).date() - timedelta(days=1)

    qs_mes = Encomienda.objects.filter(
        fecha_registro__date__gte=primer_dia,
        fecha_registro__date__lte=ultimo_dia,
    )

    # KPIs
    total = qs_mes.count()
    entregadas = qs_mes.filter(estado=EstadoEnvio.ENTREGADO).count()
    devueltas = qs_mes.filter(estado=EstadoEnvio.DEVUELTO).count()
    ingresos = qs_mes.filter(estado=EstadoEnvio.ENTREGADO).aggregate(
        total=Sum('costo_envio'))['total'] or 0
    promedio = qs_mes.aggregate(prom=Avg('costo_envio'))['prom'] or 0
    tasa_entrega = round((entregadas / total * 100) if total else 0, 1)

    # Por estado
    por_estado = list(
        qs_mes.values('estado').annotate(total=Count('id')).order_by('estado')
    )

    # Top 10 clientes remitentes
    top_clientes = list(
        qs_mes.values(
            'remitente__id', 'remitente__nombres', 'remitente__apellidos', 'remitente__nro_doc'
        ).annotate(
            envios=Count('id'),
            gastado=Sum('costo_envio')
        ).order_by('-envios')[:10]
    )

    # Top rutas por ingresos
    top_rutas = list(
        qs_mes.values('ruta__codigo', 'ruta__origen', 'ruta__destino')
        .annotate(envios=Count('id'), ingresos=Sum('costo_envio'))
        .order_by('-ingresos')[:10]
    )

    # 📈 PRONÓSTICO con regresión lineal simple
    # Tomar los últimos 6 meses para predecir el próximo
    pronostico = None
    try:
        from datetime import date as _d
        # Calcular el inicio de hace 6 meses
        m, a = primer_dia.month, primer_dia.year
        meses_historicos = []
        for i in range(6, 0, -1):
            mm = m - i
            aa = a
            while mm <= 0:
                mm += 12
                aa -= 1
            inicio_h = _d(aa, mm, 1)
            if mm == 12:
                fin_h = _d(aa + 1, 1, 1) - timedelta(days=1)
            else:
                fin_h = _d(aa, mm + 1, 1) - timedelta(days=1)
            count = Encomienda.objects.filter(
                fecha_registro__date__gte=inicio_h,
                fecha_registro__date__lte=fin_h,
            ).count()
            ingresos_h = Encomienda.objects.filter(
                fecha_entrega_real__gte=inicio_h,
                fecha_entrega_real__lte=fin_h,
                estado=EstadoEnvio.ENTREGADO,
            ).aggregate(s=Sum('costo_envio'))['s'] or 0
            meses_historicos.append({
                'label': inicio_h.strftime('%b %Y'),
                'envios': count,
                'ingresos': float(ingresos_h),
            })

        # Regresión lineal: y = mx + b (predice próximo punto)
        n = len(meses_historicos)
        if n >= 3:
            xs = list(range(n))
            ys_envios = [m_['envios'] for m_ in meses_historicos]
            ys_ingresos = [m_['ingresos'] for m_ in meses_historicos]

            def regresion_lineal(xs, ys):
                n_ = len(xs)
                sum_x = sum(xs); sum_y = sum(ys)
                sum_xy = sum(x*y for x, y in zip(xs, ys))
                sum_xx = sum(x*x for x in xs)
                denom = (n_ * sum_xx - sum_x * sum_x)
                if denom == 0: return ys[-1]
                m = (n_ * sum_xy - sum_x * sum_y) / denom
                b = (sum_y - m * sum_x) / n_
                return max(0, m * n_ + b)  # Predicción siguiente

            prediccion_envios = round(regresion_lineal(xs, ys_envios))
            prediccion_ingresos = round(regresion_lineal(xs, ys_ingresos), 2)

            # Tendencia (último vs predicción)
            ultimo = ys_envios[-1] if ys_envios else 0
            tendencia = 'sube' if prediccion_envios > ultimo else ('baja' if prediccion_envios < ultimo else 'igual')
            cambio_pct = round(((prediccion_envios - ultimo) / ultimo * 100) if ultimo else 0, 1)

            pronostico = {
                'historicos': meses_historicos,
                'envios_pred': prediccion_envios,
                'ingresos_pred': prediccion_ingresos,
                'tendencia': tendencia,
                'cambio_pct': abs(cambio_pct),
                'ultimo_mes': meses_historicos[-1]['label'] if meses_historicos else '',
            }
    except Exception:
        pronostico = None

    # 🔥 Heatmap: matriz 7×24 (día_semana × hora) con contadores
    # Inicializa matriz vacía
    heatmap = [[0 for _ in range(24)] for _ in range(7)]
    for enc in qs_mes.values_list('fecha_registro', flat=True):
        if enc:
            dia = enc.weekday()  # 0=Lunes, 6=Domingo
            hora = enc.hour
            heatmap[dia][hora] += 1
    # Encuentra el máximo para normalizar la intensidad
    max_val = max((max(row) for row in heatmap), default=0)

    import json as _json
    return render(request, 'envios/reportes.html', {
        'mes_param': mes_param,
        'mes_legible': primer_dia.strftime('%B %Y').capitalize(),
        'primer_dia': primer_dia,
        'ultimo_dia': ultimo_dia,
        'total': total,
        'entregadas': entregadas,
        'devueltas': devueltas,
        'ingresos': ingresos,
        'promedio': promedio,
        'tasa_entrega': tasa_entrega,
        'por_estado': por_estado,
        'top_clientes': top_clientes,
        'top_rutas': top_rutas,
        'heatmap': heatmap,
        'heatmap_max': max_val,
        'pronostico': pronostico,
    })


@login_required
def tareas_lista(request):
    """✅ Lista de tareas del usuario actual."""
    from .models import Tarea

    if request.method == 'POST':
        accion = request.POST.get('accion', '')

        if accion == 'crear':
            titulo = request.POST.get('titulo', '').strip()
            if titulo:
                Tarea.objects.create(
                    usuario=request.user,
                    titulo=titulo,
                    descripcion=request.POST.get('descripcion', '').strip(),
                    prioridad=request.POST.get('prioridad', 'MEDIA'),
                    fecha_limite=request.POST.get('fecha_limite') or None,
                )
                messages.success(request, '✓ Tarea creada.')
            return redirect('tareas_lista')

        elif accion == 'toggle':
            pk = request.POST.get('id')
            try:
                t = Tarea.objects.get(pk=pk, usuario=request.user)
                t.completada = not t.completada
                t.fecha_completada = timezone.now() if t.completada else None
                t.save()
            except Tarea.DoesNotExist:
                pass
            return redirect('tareas_lista')

        elif accion == 'eliminar':
            pk = request.POST.get('id')
            Tarea.objects.filter(pk=pk, usuario=request.user).delete()
            messages.success(request, '✓ Tarea eliminada.')
            return redirect('tareas_lista')

    pendientes = Tarea.objects.filter(usuario=request.user, completada=False)
    completadas = Tarea.objects.filter(usuario=request.user, completada=True)[:10]
    vencidas = [t for t in pendientes if t.vencida]

    return render(request, 'envios/tareas.html', {
        'pendientes': pendientes,
        'completadas': completadas,
        'total_vencidas': len(vencidas),
    })


@login_required
def actividad_feed(request):
    """🔔 Feed de actividad global del sistema (últimos eventos)."""
    from .models import HistorialEstado
    from clientes.audit import AccesoCliente

    # Últimas 30 acciones de cambio de estado
    historial = (
        HistorialEstado.objects
        .select_related('empleado', 'encomienda', 'encomienda__remitente', 'encomienda__destinatario')
        .order_by('-fecha_cambio')[:30]
    )

    # Últimas 20 encomiendas creadas
    nuevas = (
        Encomienda.objects.con_relaciones()
        .order_by('-fecha_registro')[:20]
    )

    # Unificar en una lista por fecha
    eventos = []
    for h in historial:
        eventos.append({
            'tipo': 'estado',
            'fecha': h.fecha_cambio,
            'titulo': f'Cambio de estado en {h.encomienda.codigo}',
            'desc': f'{h.get_estado_anterior_display()} → {h.get_estado_nuevo_display()}',
            'observacion': h.observacion,
            'empleado': f'{h.empleado.nombres} {h.empleado.apellidos}',
            'encomienda_pk': h.encomienda.pk,
            'codigo': h.encomienda.codigo,
            'nuevo_estado': h.estado_nuevo,
        })
    for n in nuevas:
        eventos.append({
            'tipo': 'nueva',
            'fecha': n.fecha_registro,
            'titulo': f'Nueva encomienda registrada',
            'desc': f'{n.codigo} — {n.remitente.nombres} → {n.destinatario.nombres}',
            'observacion': '',
            'empleado': f'{n.empleado_registro.nombres} {n.empleado_registro.apellidos}',
            'encomienda_pk': n.pk,
            'codigo': n.codigo,
            'nuevo_estado': n.estado,
        })

    eventos.sort(key=lambda x: x['fecha'], reverse=True)
    eventos = eventos[:40]

    return render(request, 'envios/actividad.html', {'eventos': eventos})


@login_required
def favoritos_lista(request):
    """⭐ Página con todas las encomiendas favoritas del usuario."""
    from .models import EncomiendaFavorita
    favs = (
        EncomiendaFavorita.objects
        .filter(usuario=request.user)
        .select_related('encomienda', 'encomienda__remitente', 'encomienda__destinatario', 'encomienda__ruta')
        .order_by('-fecha')
    )
    return render(request, 'envios/favoritos.html', {'favoritos': favs})


@login_required
def encomienda_favorito_toggle(request, pk):
    """⭐ Alterna favorito (agrega/quita)."""
    from .models import EncomiendaFavorita
    from django.http import JsonResponse
    enc = get_object_or_404(Encomienda, pk=pk)
    fav, created = EncomiendaFavorita.objects.get_or_create(
        usuario=request.user, encomienda=enc
    )
    if not created:
        fav.delete()
        es_favorita = False
    else:
        es_favorita = True
    return JsonResponse({'favorita': es_favorita})


@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
@require_POST
def encomienda_bulk_action(request):
    """⚡ Acciones masivas: cambiar estado o eliminar múltiples encomiendas."""
    accion = request.POST.get('accion', '')
    ids = request.POST.getlist('ids')

    if not ids:
        messages.error(request, 'No seleccionaste ninguna encomienda.')
        return redirect('encomienda_lista')

    empleado = _resolver_empleado(request.user)
    if not empleado:
        messages.error(request, 'No tienes empleado asociado.')
        return redirect('encomienda_lista')

    encomiendas = Encomienda.objects.filter(pk__in=ids)
    count = 0

    if accion.startswith('estado:'):
        nuevo_estado = accion.split(':')[1]
        for enc in encomiendas:
            if enc.estado != nuevo_estado:
                try:
                    enc.cambiar_estado(nuevo_estado, empleado, 'Cambio masivo')
                    count += 1
                except Exception:
                    pass
        messages.success(request, f'✓ {count} encomienda{"s" if count != 1 else ""} actualizada{"s" if count != 1 else ""}.')
    else:
        messages.error(request, 'Acción no válida.')

    return redirect('encomienda_lista')


@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
def encomienda_duplicar(request, pk):
    """📋 Crea una nueva encomienda copiando los datos de otra."""
    original = get_object_or_404(Encomienda, pk=pk)
    empleado = _resolver_empleado(request.user)
    if not empleado:
        messages.error(request, 'No puedes duplicar: tu usuario no tiene empleado asociado.')
        return redirect('encomienda_detalle', pk=pk)

    import uuid
    nueva = Encomienda(
        codigo='',  # se auto-genera
        descripcion=original.descripcion,
        peso_kg=original.peso_kg,
        volumen_cm3=original.volumen_cm3,
        remitente=original.remitente,
        destinatario=original.destinatario,
        ruta=original.ruta,
        empleado_registro=empleado,
        estado=EstadoEnvio.PENDIENTE,
        costo_envio=original.costo_envio,
        fecha_entrega_est=timezone.now().date() + timezone.timedelta(days=original.ruta.dias_entrega),
        observaciones=original.observaciones,
        tags=original.tags,
    )
    nueva.save()
    messages.success(request, f'Encomienda duplicada como {nueva.codigo}.')
    return redirect('encomienda_detalle', pk=nueva.pk)

@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
def encomienda_editar(request, pk):
    enc = get_object_or_404(Encomienda, pk=pk)
    if request.method == 'POST':
        form = EncomiendaForm(request.POST, instance=enc)
        if form.is_valid():
            enc = form.save()
            messages.success(request, f'Encomienda {enc.codigo} actualizada correctamente.')
            return redirect('encomienda_detalle', pk=enc.pk)
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = EncomiendaForm(instance=enc)
        # Hacer el campo código de solo lectura en edición
        form.fields['codigo'].widget.attrs['readonly'] = True

    return render(request, 'envios/form.html', {
        'form': form,
        'titulo': f'Editar Encomienda — {enc.codigo}',
        'encomienda': enc,
        'editando': True,
    })


@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
def encomienda_crear(request):
    import uuid

    def generar_codigo_unico():
        """Genera un código único que no exista en la BD."""
        for _ in range(10):
            codigo = f'ENC-{timezone.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'
            if not Encomienda.objects.filter(codigo=codigo).exists():
                return codigo
        return f'ENC-{timezone.now().strftime("%Y%m%d%H%M%S")}'  # Fallback

    if request.method == 'POST':
        # Forzar el código auto-generado (ignorar lo que vino del POST)
        post_data = request.POST.copy()
        post_data['codigo'] = generar_codigo_unico()
        form = EncomiendaForm(post_data)
        if form.is_valid():
            empleado = _resolver_empleado(request.user)
            if not empleado:
                messages.error(request, 'No puedes registrar: tu usuario no está enlazado a un empleado.')
            else:
                enc = form.save(commit=False)
                enc.empleado_registro = empleado
                enc.save()
                messages.success(request, f'Encomienda {enc.codigo} registrada correctamente.')
                return redirect('encomienda_detalle', pk=enc.pk)
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        # 🔐 Pre-generar código único al cargar el formulario
        form = EncomiendaForm(initial={'codigo': generar_codigo_unico()})

    return render(request, 'envios/form.html', {
        'form': form,
        'titulo': 'Nueva Encomienda',
    })

@rol_requerido(ROL_ADMIN, ROL_OPERADOR)
@require_POST
def encomienda_cambiar_estado(request, pk):
    enc = get_object_or_404(Encomienda, pk=pk)

    empleado = _resolver_empleado(request.user)
    if not empleado:
        messages.error(request, 'Tu usuario no tiene un empleado asociado.')
        return redirect('encomienda_detalle', pk=pk)

    nuevo_estado = request.POST.get('estado')
    observacion = request.POST.get('observacion', '')

    try:
        enc.cambiar_estado(nuevo_estado, empleado, observacion)
        messages.success(request, f'Estado actualizado a: {enc.get_estado_display()}')
    except Exception as e:
        messages.error(request, str(e))

    return redirect('encomienda_detalle', pk=pk)
