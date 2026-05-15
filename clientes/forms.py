from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['tipo_doc', 'nro_doc', 'nombres', 'apellidos',
                  'telefono', 'email', 'direccion']
        widgets = {
            'tipo_doc': forms.Select(attrs={'class': 'form-select'}),
            'nro_doc': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '15', 'autocomplete': 'off',
            }),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 999 888 777',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Ej: Av. Larco 1234, Miraflores, Lima',
            }),
        }
        labels = {
            'tipo_doc': 'Tipo de documento',
            'nro_doc': 'Número de documento',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'telefono': 'Teléfono',
            'email': 'Correo electrónico',
            'direccion': 'Dirección',
        }
