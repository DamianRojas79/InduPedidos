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


class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, verbose_name='Nombre Producto')
    desc = RichTextField(verbose_name='Descripción')
    precio = models.FloatField()
    precio_costo = models.FloatField(null=True, blank=True)
    id_proveedor = models.IntegerField(null=True, blank=True)
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
