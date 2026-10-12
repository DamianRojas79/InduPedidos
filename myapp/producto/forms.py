from django import forms
from django.contrib.auth import get_user_model
from django.db.models.functions import Lower

from .models import PedidoGeneral, Proveedor


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


class VerPedidosForm(forms.Form):
    periodo = forms.ModelChoiceField(
        label='Períodos', queryset=PedidoGeneral.objects.none(), required=False,
        empty_label=None, widget=forms.Select(attrs={'class': 'form-select'}),
    )
    filtro = forms.ChoiceField(
        label='Filtrar por', choices=[('cliente', 'Cliente'), ('proveedor', 'Proveedor')],
    )
    cliente = forms.ModelChoiceField(
        label='Cliente', queryset=get_user_model().objects.none(), required=False,
        empty_label='Seleccioná un cliente', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    proveedor = forms.ModelChoiceField(
        label='Proveedor', queryset=Proveedor.objects.none(), required=False,
        empty_label='Seleccioná un proveedor', widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['periodo'].queryset = PedidoGeneral.objects.order_by('-fecha_creacion', '-pk')
        self.fields['cliente'].queryset = get_user_model().objects.filter(is_staff=False).order_by(Lower('username'), 'username', 'pk')
        self.fields['proveedor'].queryset = Proveedor.objects.order_by(Lower('nombre'), 'nombre', 'pk')

    def clean_filtro(self):
        if hasattr(self.data, 'getlist') and len(self.data.getlist('filtro')) > 1:
            raise forms.ValidationError('Elegí una sola opción: Cliente o Proveedor.')
        return self.cleaned_data['filtro']
