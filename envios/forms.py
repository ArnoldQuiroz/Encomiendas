from django import forms
from .models import Encomienda
from clientes.models import Cliente
from rutas.models import Ruta

class EncomiendaForm(forms.ModelForm):
    # 🏷️ Tags como checkboxes múltiples
    tags = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[
            ('FRAGIL',       'Frágil'),
            ('PRIORITARIO',  'Prioritario'),
            ('REFRIGERADO',  'Refrigerado'),
            ('PAGO_DESTINO', 'Pago en destino'),
            ('DOCUMENTO',    'Documento'),
        ],
        label='Etiquetas',
    )

    class Meta:
        model  = Encomienda
        fields = ['codigo','descripcion','peso_kg','volumen_cm3','remitente','destinatario','ruta','costo_envio','fecha_entrega_est','observaciones','tags']
        widgets = {
            'codigo':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ENC-2026-001'}),
            'descripcion':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'peso_kg':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'volumen_cm3':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remitente':         forms.Select(attrs={'class': 'form-select'}),
            'destinatario':      forms.Select(attrs={'class': 'form-select'}),
            'ruta':              forms.Select(attrs={'class': 'form-select'}),
            'costo_envio':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha_entrega_est': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones':     forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'codigo':            'Código de encomienda',
            'peso_kg':           'Peso (kg)',
            'volumen_cm3':       'Volumen (cm³)',
            'costo_envio':       'Costo de envío (S/)',
            'fecha_entrega_est': 'Fecha estimada de entrega',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['remitente'].queryset    = Cliente.objects.activos()
        self.fields['destinatario'].queryset = Cliente.objects.activos()
        self.fields['ruta'].queryset         = Ruta.objects.activas()
        # Pre-cargar tags si la instancia ya los tiene (edición)
        if self.instance and self.instance.pk and self.instance.tags:
            self.initial['tags'] = self.instance.tags_list

    def clean_tags(self):
        """Convierte la lista de checkboxes a string separado por coma."""
        tags = self.cleaned_data.get('tags', [])
        return ','.join(tags)

    def clean(self):
        cleaned      = super().clean()
        remitente    = cleaned.get('remitente')
        destinatario = cleaned.get('destinatario')
        if remitente and destinatario and remitente == destinatario:
            raise forms.ValidationError('El remitente y el destinatario no pueden ser la misma persona.')
        return cleaned
