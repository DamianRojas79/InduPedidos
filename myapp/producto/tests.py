from django.contrib import admin
from django.db import models
from django.test import SimpleTestCase

from .models import Categoria, Producto


class CategoriaModelTests(SimpleTestCase):
    def test_configuracion_del_modelo(self):
        self.assertEqual(Categoria._meta.db_table, 'categoria')
        self.assertEqual(
            Categoria._meta.get_field('descripcion').max_length,
            100,
        )

    def test_representacion(self):
        categoria = Categoria(descripcion='Indumentaria')
        self.assertEqual(str(categoria), 'Indumentaria')

    def test_producto_se_relaciona_con_categoria(self):
        campo = Producto._meta.get_field('categoria')
        self.assertEqual(campo.related_model, Categoria)
        self.assertTrue(campo.null)

    def test_producto_admite_talle_y_una_lista_de_colores(self):
        producto_talles_numericos = Producto(
            nombre='Remera',
            talle=[38, 39, 40],
            color=['Blanco', 'Negro', 'Azul'],
        )
        producto_talles_alfabeticos = Producto(
            nombre='Buzo',
            talle=['L', 'XL', 'XXL'],
        )

        self.assertEqual(producto_talles_numericos.talle, [38, 39, 40])
        self.assertEqual(
            producto_talles_numericos.color,
            ['Blanco', 'Negro', 'Azul'],
        )
        self.assertEqual(
            producto_talles_alfabeticos.talle,
            ['L', 'XL', 'XXL'],
        )
        self.assertIsInstance(Producto._meta.get_field('talle'), models.JSONField)
        self.assertIsInstance(Producto._meta.get_field('color'), models.JSONField)

    def test_categoria_esta_registrada_en_admin(self):
        self.assertIn(Categoria, admin.site._registry)

# Create your tests here.
