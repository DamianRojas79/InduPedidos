from django import forms

from .models import PedidoGeneral


class PedidoGeneralForm(forms.ModelForm):
    class Meta:
        model = PedidoGeneral
        fields = ['descripcion', 'fecha_entrega']
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Ej.: Pedido Octubre',
            }),
            'fecha_entrega': forms.DateInput(
                format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'},
            ),
        }
