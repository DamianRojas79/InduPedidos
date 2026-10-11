import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import VerPedidosForm
from .gestion_pedidos import administrador_required
from .models import LineaPedido, Pedido, PedidoGeneral, Producto, Proveedor


def filas_usuario(usuario, pedido_general):
    if pedido_general is None:
        return LineaPedido.objects.none()
    return LineaPedido.objects.filter(
        pedido__usuario=usuario, pedido__pedido_general=pedido_general, principal__isnull=True,
    ).order_by('posicion', 'pk')


def pedido_abierto_required(view):
    @wraps(view)
    def protegida(request, *args, **kwargs):
        # El cierre del administrador usa el mismo bloqueo. Una carga iniciada
        # antes del cierre termina primero; después del cierre no se puede editar.
        with transaction.atomic():
            pedido_general = PedidoGeneral.objects.select_for_update().filter(
                estado=PedidoGeneral.Estado.ABIERTO,
            ).first()
            if pedido_general is None:
                error = 'No hay un pedido general abierto. Esperá a que el administrador cree uno nuevo.'
                if view.__name__ == 'modificar_pedido' or request.content_type == 'application/json':
                    return JsonResponse({'error': error}, status=409)
                return planilla(request, error=error, status=409)
            request.pedido_general = pedido_general
            return view(request, *args, **kwargs)
    return protegida



def contexto_lineas(usuario, periodo):
    return {
        'pedido_general': periodo,
        'pedidos': Pedido.objects.filter(usuario=usuario, pedido_general=periodo) if periodo else Pedido.objects.none(),
        'lineas': filas_usuario(usuario, periodo).select_related('producto').prefetch_related(
            Prefetch('opciones', queryset=LineaPedido.objects.select_related('producto').order_by('posicion', 'pk'))
        ),
    }


def planilla_administrador(request, datos=None, error=None, status=200):
    datos = request.GET.copy() if datos is None else datos.copy()
    periodos = PedidoGeneral.objects.order_by('-fecha_creacion', '-pk')
    if not datos.get('periodo'):
        ultimo = periodos.filter(estado=PedidoGeneral.Estado.ABIERTO).first() or periodos.first()
        datos['periodo'] = ultimo.pk if ultimo else ''
    datos.setdefault('filtro', 'cliente')
    form = VerPedidosForm(datos)
    contexto = {'form': form, 'error': error, 'es_gestion': True, 'hay_periodos': periodos.exists()}
    if form.is_valid():
        periodo = form.cleaned_data['periodo']
        cliente = form.cleaned_data['cliente']
        if form.cleaned_data['filtro'] == 'cliente' and cliente and periodo:
            contexto.update(contexto_lineas(cliente, periodo))
            contexto['cliente_elegido'] = cliente
            contexto['proveedores'] = Proveedor.objects.order_by(Lower('nombre'), 'nombre', 'pk')
    return render(request, 'producto/ver_pedidos.html', contexto, status=status)


@administrador_required
@require_GET
def ver_pedidos(request):
    return planilla_administrador(request)


def edicion_planilla_required(view):
    @wraps(view)
    def protegida(request, *args, periodo_id=None, cliente_id=None, **kwargs):
        if periodo_id is None:
            request.cliente_pedido = request.user
            return pedido_abierto_required(view)(request, *args, **kwargs)
        if not request.user.is_staff:
            raise PermissionDenied
        # Las rutas administrativas fijan el cliente y el período en el servidor.
        # El administrador también puede corregir pedidos de períodos cerrados.
        with transaction.atomic():
            request.pedido_general = get_object_or_404(
                PedidoGeneral.objects.select_for_update(), pk=periodo_id,
            )
            request.cliente_pedido = get_object_or_404(
                get_user_model(), pk=cliente_id, is_staff=False,
            )
            request.es_gestion = True
            return view(request, *args, **kwargs)
    return protegida


def destino_planilla(request):
    if getattr(request, 'es_gestion', False):
        return reverse('ver_pedidos') + '?' + urlencode({
            'periodo': request.pedido_general.pk, 'filtro': 'cliente',
            'cliente': request.cliente_pedido.pk,
        })
    return reverse('mis_pedidos')


def planilla(request, error=None, status=200):
    if getattr(request, 'es_gestion', False):
        return planilla_administrador(request, {
            'periodo': request.pedido_general.pk, 'filtro': 'cliente',
            'cliente': request.cliente_pedido.pk,
        }, error=error, status=status)
    pedido_general = PedidoGeneral.objects.filter(estado=PedidoGeneral.Estado.ABIERTO).first()
    return render(request, 'producto/mis_pedidos.html', {
        **contexto_lineas(request.user, pedido_general), 'error': error,
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
@edicion_planilla_required
def agregar_pedido(request):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.cliente_pedido.pk)
        filas = list(filas_usuario(request.cliente_pedido, request.pedido_general))
        renumerar(filas)
        pedido = Pedido.objects.create(usuario=request.cliente_pedido, pedido_general=request.pedido_general)
        linea = LineaPedido.objects.create(
            pedido=pedido, posicion=len(filas) + 1,
            nombre='', color='', talle='', precio=0, cantidad=1,
        )
    return redirect(destino_planilla(request) + f'#pedido-{linea.pk}')


@login_required
@require_POST
@edicion_planilla_required
def agregar_opcion(request, linea_id):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.cliente_pedido.pk)
        principal = get_object_or_404(filas_usuario(request.cliente_pedido, request.pedido_general), pk=linea_id)
        cantidad = principal.opciones.count()
        if cantidad >= 3:
            return planilla(request, error='Cada pedido admite hasta 3 opciones de compra.', status=400)
        opcion = LineaPedido.objects.create(
            pedido=principal.pedido, principal=principal, posicion=cantidad + 1,
            nombre='', color='', talle='', precio=0, cantidad=1,
        )
    return redirect(destino_planilla(request) + f'#pedido-{opcion.pk}')


@login_required
@require_POST
@edicion_planilla_required
def modificar_pedido(request, linea_id):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.cliente_pedido.pk)
        linea = get_object_or_404(
            LineaPedido.objects.filter(pedido__usuario=request.cliente_pedido, pedido__pedido_general=request.pedido_general),
            pk=linea_id,
        )
        filas = list(filas_usuario(request.cliente_pedido, request.pedido_general))
        campo = request.POST.get('campo')
        valor = request.POST.get('valor', '').strip()
        campos = ('numero', 'nombre', 'color', 'talle')
        if getattr(request, 'es_gestion', False):
            campos += ('proveedor',)
        if campo not in campos:
            return JsonResponse({'error': 'La columna no es válida.'}, status=400)
        if campo == 'proveedor':
            proveedor = None
            if valor:
                try:
                    proveedor_id = int(valor)
                    if not 0 < proveedor_id <= 2147483647:
                        raise ValueError
                    proveedor = Proveedor.objects.get(pk=proveedor_id)
                except (ValueError, Proveedor.DoesNotExist):
                    return JsonResponse({'error': 'Seleccioná un proveedor existente.'}, status=400)
            linea.proveedor = proveedor
            linea.save(update_fields=['proveedor'])
            valor = str(linea.proveedor_actual_id or '')
        elif campo == 'numero':
            if linea.principal_id:
                return JsonResponse({'error': 'Las opciones se numeran automáticamente.'}, status=400)
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
@edicion_planilla_required
def eliminar_pedido(request, linea_id):
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.cliente_pedido.pk)
        linea = get_object_or_404(
            LineaPedido.objects.filter(pedido__usuario=request.cliente_pedido, pedido__pedido_general=request.pedido_general),
            pk=linea_id,
        )
        pedido = linea.pedido
        principal = linea.principal
        linea.delete()
        if principal:
            renumerar(list(principal.opciones.order_by('posicion', 'pk')))
        if not pedido.lineas.exists():
            pedido.delete()
        renumerar(list(filas_usuario(request.cliente_pedido, request.pedido_general)))
    return redirect(destino_planilla(request))


@login_required
@require_POST
@pedido_abierto_required
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
                          {'producto': producto, 'error_pedido': error, 'pedido_abierto': True}, status=400)
        return JsonResponse({'error': error}, status=400)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existentes = list(filas_usuario(request.user, request.pedido_general))
        renumerar(existentes)
        for posicion, linea in enumerate(lineas, len(existentes) + 1):
            linea.posicion = posicion
        pedido = Pedido.objects.create(usuario=request.user, pedido_general=request.pedido_general)
        for linea in lineas:
            linea.pedido = pedido
        LineaPedido.objects.bulk_create(lineas)
    if es_formulario:
        return redirect('mis_pedidos')
    return JsonResponse({'url': reverse('mis_pedidos')}, status=201)
