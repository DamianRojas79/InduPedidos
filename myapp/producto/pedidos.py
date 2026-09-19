import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import LineaPedido, Pedido, Producto


def filas_usuario(usuario):
    return LineaPedido.objects.filter(pedido__usuario=usuario).order_by('posicion', 'pk')


def planilla(request, error=None, status=200):
    return render(request, 'producto/mis_pedidos.html', {
        'pedidos': Pedido.objects.filter(usuario=request.user),
        'lineas': filas_usuario(request.user).select_related('producto'),
        'error': error,
    }, status=status)


def renumerar(filas):
    for posicion, fila in enumerate(filas, 1):
        fila.posicion = posicion
    LineaPedido.objects.bulk_update(filas, ['posicion'])


@login_required
def mis_pedidos(request):
    return planilla(request)


@login_required
@require_POST
def modificar_pedido(request, linea_id):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        linea = get_object_or_404(filas_usuario(request.user), pk=linea_id)
        filas = list(filas_usuario(request.user))
        campo = request.POST.get('campo')
        valor = request.POST.get('valor', '').strip()
        if campo not in ('numero', 'nombre', 'color', 'talle'):
            return JsonResponse({'error': 'La columna no es válida.'}, status=400)
        if campo == 'numero':
            try:
                numero = int(valor)
                if not 1 <= numero <= len(filas):
                    raise ValueError
            except ValueError:
                return JsonResponse({'error': 'Ingresá un número entre 1 y la cantidad de pedidos.'}, status=400)
            filas = [fila for fila in filas if fila.pk != linea.pk]
            filas.insert(numero - 1, linea)
            renumerar(filas)
            valor = str(numero)
        else:
            if len(valor) > 100 or (campo == 'nombre' and not valor):
                return JsonResponse({'error': 'El producto es obligatorio y cada celda admite hasta 100 caracteres.'}, status=400)
            setattr(linea, campo, valor)
            linea.save(update_fields=[campo])
    return JsonResponse({'valor': valor, 'orden': [fila.pk for fila in filas]})


@login_required
@require_POST
def eliminar_pedido(request, linea_id):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        linea = get_object_or_404(filas_usuario(request.user), pk=linea_id)
        pedido = linea.pedido
        linea.delete()
        if not pedido.lineas.exists():
            pedido.delete()
        renumerar(list(filas_usuario(request.user)))
    return redirect('mis_pedidos')


@login_required
@require_POST
def crear_pedido(request):
    es_formulario = request.content_type in ('application/x-www-form-urlencoded', 'multipart/form-data')
    producto = None
    try:
        if es_formulario:
            items = [{
                'id': request.POST.get('id', ''),
                'quantity': int(request.POST.get('quantity', '1')),
                'color': request.POST.get('color', ''),
                'size': request.POST.get('size', ''),
            }]
        else:
            items = json.loads(request.body)
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise ValueError
        lineas = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError
            cantidad = item.get('quantity')
            if type(cantidad) is not int or not 1 <= cantidad <= 999:
                raise ValueError
            producto = Producto.objects.get(pk=int(item.get('id', '')))
            color, talle = item.get('color', ''), item.get('size', '')
            for valor, opciones in ((color, producto.color), (talle, producto.talle)):
                if not isinstance(valor, str) or len(valor) > 100:
                    raise ValueError
                if valor not in ([str(opcion) for opcion in opciones] if opciones else ['']):
                    raise ValueError
            precio = Decimal(str(producto.precio)).quantize(Decimal('0.01'))
            if not precio.is_finite() or not 0 <= precio < Decimal('1000000000000'):
                raise ValueError
            lineas.append(LineaPedido(producto=producto, nombre=producto.nombre,
                                      precio=precio, cantidad=cantidad, color=color, talle=talle))
    except (ValueError, TypeError, OverflowError, InvalidOperation, Producto.DoesNotExist):
        error = 'Revisá los productos, las cantidades, los talles y los colores del pedido.'
        if es_formulario and producto is not None:
            return render(request, 'producto/detalle_producto.html',
                          {'producto': producto, 'error_pedido': error}, status=400)
        return JsonResponse({'error': error}, status=400)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existentes = list(filas_usuario(request.user))
        renumerar(existentes)
        for posicion, linea in enumerate(lineas, len(existentes) + 1):
            linea.posicion = posicion
        pedido = Pedido.objects.create(usuario=request.user)
        for linea in lineas:
            linea.pedido = pedido
        LineaPedido.objects.bulk_create(lineas)
    if es_formulario:
        return redirect('mis_pedidos')
    return JsonResponse({'url': reverse('mis_pedidos')}, status=201)
