import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from sistema.choices import TipoDocumento, EstadoGeneral
from .models import Cliente
from .forms import ClienteForm
from .audit import registrar_acceso


@login_required
def cliente_lista(request):
    qs = Cliente.objects.activos()
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(nro_doc__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page = request.GET.get('page', 1)
    clientes = paginator.get_page(page)

    return render(request, 'clientes/lista.html', {
        'clientes': clientes,
        'q': q,
        'total': qs.count(),
    })


@login_required
def cliente_crear(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            registrar_acceso(request, cliente=cliente, accion='CREATE',
                             detalle=f'Cliente creado: {cliente.nombre_completo}')
            messages.success(
                request,
                f'Cliente {cliente.nombre_completo} registrado correctamente.'
            )
            return redirect('cliente_lista')
        else:
            messages.error(request, 'Por favor revisa los errores del formulario.')
    else:
        form = ClienteForm()

    return render(request, 'clientes/form.html', {
        'form': form,
        'titulo': 'Nuevo Cliente',
    })


@login_required
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save()
            registrar_acceso(request, cliente=cliente, accion='UPDATE',
                             detalle=f'Cliente editado: {cliente.nombre_completo}')
            messages.success(request, f'Cliente {cliente.nombre_completo} actualizado correctamente.')
            return redirect('cliente_detalle', pk=cliente.pk)
        else:
            messages.error(request, 'Por favor revisa los errores del formulario.')
    else:
        form = ClienteForm(instance=cliente)
        registrar_acceso(request, cliente=cliente, accion='VIEW',
                         detalle='Acceso a formulario de edición')

    return render(request, 'clientes/form.html', {
        'form': form,
        'titulo': f'Editar Cliente — {cliente.nombre_completo}',
        'cliente': cliente,
        'editando': True,
    })


@login_required
def cliente_importar_csv(request):
    """📥 Importa clientes en bulk desde un archivo CSV."""
    resultados = None
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        try:
            decoded = archivo.read().decode('utf-8-sig')  # maneja BOM de Excel
            reader = csv.DictReader(io.StringIO(decoded))

            creados, actualizados, omitidos, errores = 0, 0, 0, []

            for i, fila in enumerate(reader, start=2):  # fila 1 es header
                try:
                    nro_doc = (fila.get('nro_doc') or fila.get('DNI') or fila.get('Nro Doc') or '').strip()
                    nombres = (fila.get('nombres') or fila.get('Nombres') or '').strip()
                    apellidos = (fila.get('apellidos') or fila.get('Apellidos') or '').strip()
                    if not nro_doc or not nombres or not apellidos:
                        errores.append(f'Fila {i}: faltan campos obligatorios (nro_doc, nombres, apellidos)')
                        omitidos += 1
                        continue

                    tipo_doc = (fila.get('tipo_doc') or fila.get('Tipo Doc') or 'DNI').strip().upper()
                    telefono = (fila.get('telefono') or fila.get('Teléfono') or '').strip()
                    email = (fila.get('email') or fila.get('Email') or '').strip()
                    direccion = (fila.get('direccion') or fila.get('Dirección') or '').strip()

                    cliente, was_created = Cliente.objects.update_or_create(
                        nro_doc=nro_doc,
                        defaults={
                            'tipo_doc': tipo_doc if tipo_doc in ['DNI', 'RUC', 'PAS'] else 'DNI',
                            'nombres': nombres,
                            'apellidos': apellidos,
                            'telefono': telefono or None,
                            'email': email or None,
                            'direccion': direccion or None,
                            'estado': EstadoGeneral.ACTIVO,
                        }
                    )
                    if was_created:
                        creados += 1
                        registrar_acceso(request, cliente=cliente, accion='CREATE',
                                         detalle=f'Importado desde CSV')
                    else:
                        actualizados += 1
                except Exception as e:
                    errores.append(f'Fila {i}: {str(e)[:100]}')
                    omitidos += 1

            resultados = {
                'creados': creados,
                'actualizados': actualizados,
                'omitidos': omitidos,
                'errores': errores[:10],  # primeros 10
                'total_errores': len(errores),
            }
            if creados or actualizados:
                messages.success(
                    request,
                    f'Importación completa: {creados} nuevos, {actualizados} actualizados.'
                )
            if omitidos:
                messages.warning(request, f'{omitidos} filas omitidas con errores.')

        except UnicodeDecodeError:
            messages.error(request, 'El archivo debe estar en UTF-8. Guarda tu Excel como CSV UTF-8.')
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)[:200]}')

    return render(request, 'clientes/importar.html', {
        'resultados': resultados,
    })


@login_required
def cliente_exportar_csv(request):
    """Exporta los clientes activos a CSV."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fecha = timezone.now().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename="clientes_{fecha}.csv"'
    response.write('﻿')  # BOM para Excel
    writer = csv.writer(response)
    writer.writerow([
        'Tipo Doc', 'Nro Doc', 'Nombres', 'Apellidos',
        'Teléfono', 'Email', 'Dirección', 'Estado', 'Fecha registro'
    ])
    for c in Cliente.objects.activos().order_by('apellidos', 'nombres'):
        writer.writerow([
            c.tipo_doc, c.nro_doc, c.nombres, c.apellidos,
            c.telefono or '', c.email or '', c.direccion or '',
            'Activo' if c.estado == 1 else 'De baja',
            c.fecha_registro.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@login_required
def cliente_detalle(request, pk):
    from django.db.models import Sum, Count
    cliente = get_object_or_404(Cliente, pk=pk)

    # 🔐 Auditoría: registrar quién consultó este perfil
    registrar_acceso(request, cliente=cliente, accion='VIEW')

    envios_remitente_qs = cliente.envios_como_remitente.select_related('ruta', 'destinatario')
    envios_destinatario_qs = cliente.envios_como_destinatario.select_related('ruta', 'remitente')

    # Métricas
    total_enviadas = envios_remitente_qs.count()
    total_recibidas = envios_destinatario_qs.count()
    total_invertido = envios_remitente_qs.aggregate(total=Sum('costo_envio'))['total'] or 0
    total_movimientos = total_enviadas + total_recibidas

    # Última actividad
    ultima_actividad = None
    ultimo_remitente = envios_remitente_qs.first()
    ultimo_destinatario = envios_destinatario_qs.first()
    if ultimo_remitente and ultimo_destinatario:
        ultima_actividad = max(ultimo_remitente.fecha_registro, ultimo_destinatario.fecha_registro)
    elif ultimo_remitente:
        ultima_actividad = ultimo_remitente.fecha_registro
    elif ultimo_destinatario:
        ultima_actividad = ultimo_destinatario.fecha_registro

    return render(request, 'clientes/detalle.html', {
        'cliente': cliente,
        'envios_remitente': envios_remitente_qs[:10],
        'envios_destinatario': envios_destinatario_qs[:10],
        'total_enviadas': total_enviadas,
        'total_recibidas': total_recibidas,
        'total_invertido': total_invertido,
        'total_movimientos': total_movimientos,
        'ultima_actividad': ultima_actividad,
    })
