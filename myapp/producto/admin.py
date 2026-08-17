from django.contrib import admin

#Models
from .models import Categoria, Producto


# Register your models here.
#admin.site.register(Producto)

# Personalizacion Administrador de productos
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display=('id','nombre','categoria','talle','color','imagen','precio')
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
