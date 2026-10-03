from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import JsonResponse
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
        'pedidos_generales': PedidoGeneral.objects.all(),
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
def modificar_pedido_general(request, pedido_id):
    with transaction.atomic():
        ultimo = PedidoGeneral.objects.select_for_update().first()
        if ultimo is None or ultimo.pk != pedido_id or ultimo.estado != PedidoGeneral.Estado.ABIERTO:
            return JsonResponse({'error': 'Solo se puede editar el último pedido abierto.'}, status=409)
        campo = request.POST.get('campo')
        if campo not in ('descripcion', 'fecha_entrega'):
            return JsonResponse({'error': 'La columna no es editable.'}, status=400)
        datos = {
            'descripcion': ultimo.descripcion,
            'fecha_entrega': ultimo.fecha_entrega or '',
        }
        datos[campo] = request.POST.get('valor', '').strip()
        form = PedidoGeneralForm(datos, instance=ultimo)
        if not form.is_valid():
            return JsonResponse({'error': ' '.join(error for errores in form.errors.values() for error in errores)}, status=400)
        ultimo = form.save()
        valor = getattr(ultimo, campo)
        if campo == 'fecha_entrega':
            valor = valor.isoformat() if valor else ''
    return JsonResponse({'valor': valor})


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
