from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Encomienda, Empleado
from .forms import EncomiendaForm
from sistema.choices import EstadoEnvio

@login_required
def dashboard(request):
    hoy = timezone.now().date()
    context = {
        'total_activas': Encomienda.objects.activas().count(),
        'en_transito': Encomienda.objects.en_transito().count(),
        'con_retraso': Encomienda.objects.con_retraso().count(),
        'entregadas_hoy': Encomienda.objects.filter(estado=EstadoEnvio.ENTREGADO, fecha_entrega_real=hoy).count(),
        'ultimas': Encomienda.objects.con_relaciones()[:5],
    }
    return render(request, 'envios/dashboard.html', context)

@login_required
def encomienda_lista(request):
    qs = Encomienda.objects.con_relaciones()
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '')
    
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(codigo__icontains=q) |
            Q(remitente__apellidos__icontains=q) |
            Q(destinatario__apellidos__icontains=q)
        )
        
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page', 1)
    encomiendas = paginator.get_page(page_number)
    
    return render(request, 'envios/lista.html', {
        'encomiendas': encomiendas,
        'estados': EstadoEnvio.choices,
        'estado_activo': estado,
        'q': q,
    })

@login_required
def encomienda_detalle(request, pk):
    enc = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    return render(request, 'envios/detalle.html', {'encomienda': enc})

@login_required
def encomienda_crear(request):
    if request.method == 'POST':
        form = EncomiendaForm(request.POST)
        if form.is_valid():
            enc = form.save(commit=False)
            try:
                empleado = Empleado.objects.get(email=request.user.email)
                enc.empleado_registro = empleado
                enc.save()
                messages.success(request, f'Encomienda {enc.codigo} registrada correctamente.')
                return redirect('encomienda_detalle', pk=enc.pk)
            except Empleado.DoesNotExist:
                messages.error(request, 'No puedes registrar: tu usuario no está enlazado a un empleado.')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = EncomiendaForm()
        
    return render(request, 'envios/form.html', {
        'form': form,
        'titulo': 'Nueva Encomienda',
    })

@login_required
@require_POST
def encomienda_cambiar_estado(request, pk):
    enc = get_object_or_404(Encomienda, pk=pk)
    
    try:
        empleado = Empleado.objects.get(email=request.user.email)
    except Empleado.DoesNotExist:
        raise PermissionDenied("El usuario actual no es un empleado activo.")

    nuevo_estado = request.POST.get('estado')
    observacion = request.POST.get('observacion', '')
    
    try:
        enc.cambiar_estado(nuevo_estado, empleado, observacion)
        messages.success(request, f'Estado actualizado a: {enc.get_estado_display()}')
    except Exception as e:
        messages.error(request, str(e))
        
    return redirect('encomienda_detalle', pk=pk)
