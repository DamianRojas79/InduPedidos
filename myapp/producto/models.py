from django.conf import settings
from django.db import models

#Ckeditor
from ckeditor.fields import RichTextField


# Modelo
class Categoria(models.Model):
    id = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100)

    def __str__(self):
        return self.descripcion

    class Meta:
        db_table = 'categoria'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'


class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    calle_nombre = models.CharField(max_length=100)
    calle_numero = models.IntegerField()
    localidad = models.CharField(max_length=100)
    telefono = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'


class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, verbose_name='Nombre Producto')
    desc = RichTextField(verbose_name='Descripción')
    precio = models.FloatField()
    precio_costo = models.FloatField(null=True, blank=True)
    id_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='productos',
        db_column='id_proveedor',
        null=True,
        blank=True,
        verbose_name='Proveedor',
    )
    talle = models.JSONField(default=list, blank=True)
    color = models.JSONField(default=list, blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos',
        null=True,
        blank=True,
    )

    imagen = models.ImageField(
        upload_to='producto/',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'producto'
        verbose_name='Productos'


class Pedido(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pedidos')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado', '-pk']

    @property
    def total(self):
        return sum(linea.subtotal for linea in self.lineas.filter(principal__isnull=True))

    def __str__(self):
        return f'Pedido #{self.pk}'


class LineaPedido(models.Model):
    principal = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name='opciones', null=True, blank=True,
    )
    posicion = models.PositiveIntegerField(default=0)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=14, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    color = models.CharField(max_length=100, blank=True)
    talle = models.CharField(max_length=100, blank=True)

    @property
    def subtotal(self):
        return self.precio * self.cantidad
