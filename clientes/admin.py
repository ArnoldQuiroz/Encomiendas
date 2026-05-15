# clientes/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Cliente
from .audit import AccesoCliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nro_doc_masked', 'tipo_doc', 'apellidos', 'nombres', 'telefono_masked', 'estado_badge')
    list_filter = ('tipo_doc', 'estado')
    search_fields = ('nro_doc', 'apellidos', 'nombres')

    def nro_doc_masked(self, obj):
        """🔐 Muestra solo los últimos 4 dígitos del DNI a usuarios no superuser."""
        return obj.nro_doc
    nro_doc_masked.short_description = 'Documento'

    def telefono_masked(self, obj):
        """🔐 Enmascara el teléfono parcialmente."""
        if not obj.telefono:
            return '—'
        if len(obj.telefono) > 4:
            return f'{obj.telefono[:3]}***{obj.telefono[-2:]}'
        return obj.telefono
    telefono_masked.short_description = 'Teléfono'

    def estado_badge(self, obj):
        if obj.estado == 1:
            return format_html('<span style="background:#d1fae5;color:#047857;padding:2px 8px;border-radius:10px;font-size:.7rem;font-weight:700;">ACTIVO</span>')
        return format_html('<span style="background:#fee2e2;color:#b91c1c;padding:2px 8px;border-radius:10px;font-size:.7rem;font-weight:700;">DE BAJA</span>')
    estado_badge.short_description = 'Estado'


@admin.register(AccesoCliente)
class AccesoClienteAdmin(admin.ModelAdmin):
    """🔐 Log de auditoría — solo lectura."""
    list_display = ('fecha', 'usuario', 'accion_badge', 'cliente_doc', 'ip', 'detalle_corto')
    list_filter = ('accion', 'fecha', 'usuario')
    search_fields = ('usuario__username', 'cliente__nro_doc', 'ip', 'detalle')
    date_hierarchy = 'fecha'
    list_per_page = 50
    readonly_fields = ('usuario', 'cliente', 'accion', 'ip', 'user_agent', 'detalle', 'fecha')

    def has_add_permission(self, request):
        return False  # No se crean manualmente

    def has_change_permission(self, request, obj=None):
        return False  # Inmutable

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Solo superuser puede borrar

    def accion_badge(self, obj):
        colores = {
            'VIEW':   ('#dbeafe', '#1d4ed8'),
            'CREATE': ('#d1fae5', '#047857'),
            'UPDATE': ('#fef3c7', '#b45309'),
            'DELETE': ('#fee2e2', '#b91c1c'),
            'SEARCH_DNI': ('#e0e7ff', '#4f46e5'),
        }
        bg, fg = colores.get(obj.accion, ('#f1f5f9', '#475569'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;'
            'font-size:.7rem;font-weight:700;">{}</span>',
            bg, fg, obj.get_accion_display()
        )
    accion_badge.short_description = 'Acción'

    def cliente_doc(self, obj):
        if obj.cliente:
            return f'{obj.cliente.tipo_doc} {obj.cliente.nro_doc}'
        return '—'
    cliente_doc.short_description = 'Cliente'

    def detalle_corto(self, obj):
        return obj.detalle[:60] if obj.detalle else '—'
    detalle_corto.short_description = 'Detalle'
