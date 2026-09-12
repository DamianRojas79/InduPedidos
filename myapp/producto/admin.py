from django.contrib import admin

#Models
from .models import Categoria, Producto, Proveedor


# Register your models here.
#admin.site.register(Producto)

# Personalizacion Administrador de productos
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display=('id','nombre','categoria','id_proveedor','talle','color','imagen','precio')
    list_display_links=('nombre',)
    list_filter=('categoria','nombre',)
    search_fields=('nombre',)

    #Para solo lectura
    #readonly_fields=('precio',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'descripcion')
    list_display_links = ('descripcion',)
    search_fields = ('descripcion',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'calle_nombre',
        'calle_numero',
        'localidad',
        'telefono',
    )
    list_display_links = ('nombre',)
    search_fields = ('nombre', 'calle_nombre', 'localidad')
