from django.contrib import admin
from django.db import models
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from .models import Categoria, Producto, Proveedor
from .views import detalle


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

    def test_configuracion_del_modelo_proveedor(self):
        self.assertEqual(Proveedor._meta.db_table, 'proveedor')
        self.assertEqual(Proveedor._meta.get_field('nombre').max_length, 100)
        self.assertEqual(Proveedor._meta.get_field('calle_nombre').max_length, 100)
        self.assertEqual(Proveedor._meta.get_field('localidad').max_length, 100)
        self.assertFalse(Proveedor._meta.get_field('calle_nombre').blank)
        self.assertFalse(Proveedor._meta.get_field('calle_numero').blank)
        self.assertFalse(Proveedor._meta.get_field('localidad').blank)
        self.assertTrue(Proveedor._meta.get_field('telefono').blank)

    def test_producto_se_relaciona_con_proveedor(self):
        campo = Producto._meta.get_field('id_proveedor')

        self.assertEqual(campo.related_model, Proveedor)
        self.assertEqual(campo.db_column, 'id_proveedor')
        self.assertEqual(campo.remote_field.on_delete, models.PROTECT)

    def test_proveedor_esta_registrado_en_admin(self):
        self.assertIn(Proveedor, admin.site._registry)

    def test_url_de_detalle_del_producto(self):
        url = reverse('detalle_producto', args=[42])

        self.assertEqual(url, '/productos/42/')
        self.assertIs(resolve(url).func, detalle)

# Create your tests here.


from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Pedido, LineaPedido


class UsuariosYPedidosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('cliente', password='ClaveSegura-984!')
        self.otro = get_user_model().objects.create_user('otro', password='ClaveSegura-984!')
        self.producto = Producto.objects.create(nombre='Remera', desc='Algodón', precio=1250.50,
                                                color=['Negro'], talle=[38])

    def test_registro_crea_usuario_comun_y_abre_catalogo(self):
        response = self.client.post(reverse('registro'), {
            'username': 'nuevo', 'password1': 'ClaveSegura-984!',
            'password2': 'ClaveSegura-984!', 'is_staff': 'true', 'is_superuser': 'true',
        })
        self.assertRedirects(response, reverse('producto'))
        usuario = get_user_model().objects.get(username='nuevo')
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(usuario.check_password('ClaveSegura-984!'))

    def test_registro_rechaza_contrasenas_distintas_y_nombre_duplicado(self):
        for username, password2 in [('nuevo', 'OtraClave-984!'), ('cliente', 'ClaveSegura-984!')]:
            response = self.client.post(reverse('registro'), {
                'username': username, 'password1': 'ClaveSegura-984!', 'password2': password2,
            })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_paginas_requieren_login(self):
        for url in [reverse('producto'), reverse('detalle_producto', args=[self.producto.pk]),
                    reverse('mis_pedidos'), reverse('crear_pedido')]:
            self.assertRedirects(self.client.get(url), reverse('login') + '?next=' + url)

    def test_login_logout_y_restriccion_admin(self):
        response = self.client.post(reverse('login'), {'username': 'cliente', 'password': 'incorrecta'})
        self.assertTrue(response.context['form'].errors)
        response = self.client.post(reverse('login'), {'username': 'cliente', 'password': 'ClaveSegura-984!'})
        self.assertRedirects(response, reverse('producto'))
        self.assertEqual(self.client.get(reverse('detalle_producto', args=[self.producto.pk])).status_code, 200)
        self.assertRedirects(self.client.get(reverse('admin:index')), '/admin/login/?next=/admin/')
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cada_usuario_solo_ve_sus_pedidos(self):
        propio = Pedido.objects.create(usuario=self.usuario)
        ajeno = Pedido.objects.create(usuario=self.otro)
        LineaPedido.objects.create(pedido=ajeno, producto=self.producto, nombre='Producto privado', precio=10, cantidad=1)
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('mis_pedidos'), {'usuario': self.otro.pk})
        self.assertEqual(list(response.context['pedidos']), [propio])
        self.assertNotContains(response, 'Producto privado')

    def test_confirma_con_usuario_y_precio_del_servidor(self):
        self.client.force_login(self.usuario)
        response = self.client.post(reverse('crear_pedido'), [{
            'id': self.producto.pk, 'quantity': 2, 'color': 'Negro', 'size': '38',
            'price': 1, 'usuario': self.otro.pk,
        }], content_type='application/json')
        self.assertEqual(response.status_code, 201)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.usuario, self.usuario)
        self.assertEqual(pedido.total, 2501)
        self.producto.precio = 9999
        self.producto.save()
        self.assertEqual(Pedido.objects.get().total, 2501)
        self.assertContains(self.client.get(reverse('mis_pedidos')), 'Remera')

    def test_pedido_invalido_no_guarda_lineas_parciales(self):
        self.client.force_login(self.usuario)
        valido = {'id': self.producto.pk, 'quantity': 1, 'color': 'Negro', 'size': '38'}
        for cambio in [{'quantity': 0}, {'quantity': True}, {'quantity': 1000},
                       {'color': 'Azul'}, {'size': ''}, {'id': 99999}]:
            response = self.client.post(reverse('crear_pedido'), [valido, {**valido, **cambio}], content_type='application/json')
            self.assertEqual(response.status_code, 400)
        for body in ['[]', '{}', 'null', 'invalid']:
            self.assertEqual(self.client.post(reverse('crear_pedido'), body, content_type='application/json').status_code, 400)
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(LineaPedido.objects.exists())

    def test_confirmacion_requiere_post_y_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(client.get(reverse('crear_pedido')).status_code, 405)
        self.assertEqual(client.post(reverse('crear_pedido'), '[]', content_type='application/json').status_code, 403)

    def test_anadir_producto_desde_detalle_lo_guarda_en_mis_pedidos(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        detalle = client.get(reverse('detalle_producto', args=[self.producto.pk]))
        self.assertContains(detalle, 'id="agregar-pedido"')
        self.assertNotContains(detalle, 'Mi pedido')
        self.assertNotContains(client.get(reverse('producto')), 'Mi pedido')
        response = client.post(reverse('crear_pedido'), [{
            'id': str(self.producto.pk), 'quantity': 1, 'color': 'Negro', 'size': '38',
        }], content_type='application/json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['url'], reverse('mis_pedidos'))
        linea = LineaPedido.objects.get()
        self.assertEqual(linea.pedido.usuario, self.usuario)
        self.assertEqual((linea.color, linea.talle, linea.cantidad), ('Negro', '38', 1))
        self.assertContains(client.get(response.json()['url']), 'Remera')

    def test_formulario_sin_javascript_crea_pedido_con_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        detalle = client.get(reverse('detalle_producto', args=[self.producto.pk]))
        self.assertContains(detalle, 'name="color"')
        self.assertContains(detalle, 'name="size"')
        response = client.post(reverse('crear_pedido'), {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
            'id': self.producto.pk, 'quantity': '1', 'color': 'Negro', 'size': '38',
        })
        self.assertRedirects(response, reverse('mis_pedidos'))
        linea = LineaPedido.objects.get()
        self.assertEqual(linea.pedido.usuario, self.usuario)
        self.assertEqual((linea.color, linea.talle, linea.cantidad), ('Negro', '38', 1))

    def test_formulario_rechaza_opciones_invalidas_sin_crear_pedido(self):
        self.client.force_login(self.usuario)
        response = self.client.post(reverse('crear_pedido'), {
            'id': self.producto.pk, 'quantity': '1', 'color': 'Azul', 'size': '38',
        })
        self.assertContains(response, 'Revisá los productos', status_code=400)
        self.assertTemplateUsed(response, 'producto/detalle_producto.html')
        self.assertFalse(Pedido.objects.exists())

    def test_formulario_producto_sin_opciones(self):
        self.producto.color = []
        self.producto.talle = []
        self.producto.save()
        self.client.force_login(self.usuario)
        response = self.client.post(reverse('crear_pedido'), f'id={self.producto.pk}&quantity=1',
                                    content_type='application/x-www-form-urlencoded')
        self.assertRedirects(response, reverse('mis_pedidos'))
        self.assertEqual(LineaPedido.objects.get().cantidad, 1)
