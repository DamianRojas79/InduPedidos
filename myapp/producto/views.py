from django.shortcuts import get_object_or_404, render
from django.db.models import Count

from .models import Categoria, Producto

# Create your views here.
def index(request):
    productos = Producto.objects.select_related('categoria').order_by('nombre')
    categorias = (
        Categoria.objects.annotate(product_count=Count('productos'))
        .filter(product_count__gt=0)
        .order_by('descripcion')
    )
    return render(
        request,
        'producto/productos.html',
        {
            'productos': productos,
            'categorias': categorias,
        },
    )


def detalle(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria'),
        pk=producto_id,
    )
    return render(
        request,
        'producto/detalle_producto.html',
        {'producto': producto},
    )
