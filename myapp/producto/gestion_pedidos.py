from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import PedidoGeneralForm
from .models import PedidoGeneral


def administrador_required(view):
    @login_required
    @wraps(view)
    def protegida(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return protegida


def puede_crear(ultimo):
    return ultimo is None or ultimo.estado == PedidoGeneral.Estado.CERRADO


@administrador_required
@require_GET
def gestion_pedidos(request):
    ultimo = PedidoGeneral.objects.first()
    return render(request, 'producto/gestion_pedidos.html', {
        'ultimo_pedido': ultimo,
        'puede_crear': puede_crear(ultimo),
    })


@administrador_required
@require_http_methods(['GET', 'POST'])
def crear_pedido_general(request):
    if not puede_crear(PedidoGeneral.objects.first()):
        messages.error(request, 'Cerrá el último pedido antes de crear uno nuevo.')
        return redirect('gestion_pedidos')

    form = PedidoGeneralForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            # La restricción también protege dos altas simultáneas, incluso
            # cuando todavía no existe ningún pedido para bloquear.
            with transaction.atomic():
                form.save()
        except IntegrityError:
            if not PedidoGeneral.objects.filter(estado=PedidoGeneral.Estado.ABIERTO).exists():
                raise
            messages.error(request, 'Ya existe un pedido abierto. Cerralo antes de crear otro.')
            return redirect('gestion_pedidos')
        messages.success(request, 'Pedido creado correctamente.')
        return redirect('gestion_pedidos')
    return render(request, 'producto/crear_pedido_general.html', {'form': form})


@administrador_required
@require_POST
def cerrar_pedido_general(request, pedido_id):
    with transaction.atomic():
        ultimo = PedidoGeneral.objects.select_for_update().first()
        if ultimo is None or ultimo.pk != pedido_id:
            messages.error(request, 'Solo se puede cerrar el último pedido creado.')
        elif ultimo.estado == PedidoGeneral.Estado.CERRADO:
            messages.info(request, 'El pedido ya está cerrado.')
        else:
            ultimo.estado = PedidoGeneral.Estado.CERRADO
            ultimo.save(update_fields=['estado'])
            messages.success(request, 'Pedido cerrado correctamente.')
    return redirect('gestion_pedidos')
