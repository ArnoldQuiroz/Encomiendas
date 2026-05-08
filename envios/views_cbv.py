cat > envios/views_cbv.py << 'EOF'
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from .models import Encomienda, Empleado
from .forms import EncomiendaForm
from sistema.choices import EstadoEnvio


class EncomiendaListView(LoginRequiredMixin, ListView):
    model               = Encomienda
    template_name       = 'envios/lista.html'
    context_object_name = 'encomiendas'
    paginate_by         = 15
    ordering            = ['-fecha_registro']

    def get_queryset(self):
        qs     = Encomienda.objects.con_relaciones()
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados']       = EstadoEnvio.choices
        ctx['estado_activo'] = self.request.GET.get('estado', '')
        ctx['q']             = self.request.GET.get('q', '')
        return ctx


class EncomiendaDetailView(LoginRequiredMixin, DetailView):
    model               = Encomienda
    template_name       = 'envios/detalle.html'
    context_object_name = 'encomienda'

    def get_queryset(self):
        return Encomienda.objects.con_relaciones()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['historial'] = self.object.historial.select_related('empleado')
        ctx['estados']   = EstadoEnvio.choices
        return ctx


class EncomiendaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model           = Encomienda
    form_class      = EncomiendaForm
    template_name   = 'envios/form.html'
    success_message = 'Encomienda %(codigo)s creada correctamente.'

    def get_success_url(self):
        return reverse_lazy('encomienda_detalle', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        try:
            form.instance.empleado_registro = Empleado.objects.get(email=self.request.user.email)
        except Empleado.DoesNotExist:
            form.instance.empleado_registro = Empleado.objects.first()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nueva Encomienda'
        return ctx


class EncomiendaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model           = Encomienda
    form_class      = EncomiendaForm
    template_name   = 'envios/form.html'
    success_message = 'Encomienda actualizada correctamente.'

    def get_success_url(self):
        return reverse_lazy('encomienda_detalle', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Editar Encomienda'
        return ctx
EOF