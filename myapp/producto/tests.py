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


class PlanillaPedidosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('planilla')
        self.otro = get_user_model().objects.create_user('ajeno')
        self.producto = Producto.objects.create(nombre='Remera', precio=100, color=['Negro'], talle=[38])
        self.nuevo = Producto.objects.create(nombre='Buzo', precio=200, color=['Azul'], talle=['L'])
        self.pedido = Pedido.objects.create(usuario=self.usuario)
        self.filas = [LineaPedido.objects.create(pedido=self.pedido, producto=self.producto,
                      nombre='Remera', precio=100, cantidad=1, color='Negro', talle='38') for _ in range(3)]
        self.client.force_login(self.usuario)

    def editar(self, fila, campo, valor):
        return self.client.post(reverse('modificar_pedido', args=[fila.pk]), {'campo': campo, 'valor': valor})

    def test_agregar_fila_en_blanco_al_final_y_editarla(self):
        response = self.client.post(reverse('agregar_pedido'))
        fila = LineaPedido.objects.latest('pk')
        self.assertRedirects(response, reverse('mis_pedidos') + f'#pedido-{fila.pk}')
        self.assertEqual(fila.pedido.usuario, self.usuario)
        self.assertEqual(fila.posicion, 4)
        self.assertIsNone(fila.producto)
        self.assertEqual((fila.nombre, fila.color, fila.talle), ('', '', ''))
        for campo, valor in [('nombre', 'Pedido manual'), ('color', 'Rojo'), ('talle', 'XL')]:
            self.assertEqual(self.editar(fila, campo, valor).status_code, 200)
        fila.refresh_from_db()
        self.assertEqual((fila.nombre, fila.color, fila.talle), ('Pedido manual', 'Rojo', 'XL'))
        self.client.post(reverse('agregar_pedido'))
        self.assertEqual(LineaPedido.objects.latest('pk').posicion, 5)

    def test_agregar_primer_pedido_solo_para_usuario_actual(self):
        self.client.force_login(self.otro)
        pagina = self.client.get(reverse('mis_pedidos'))
        self.assertContains(pagina, 'Agregar nuevo pedido')
        self.assertLess(pagina.content.index(b'Agregar nuevo pedido'), pagina.content.index(b'Ver productos'))
        self.client.post(reverse('agregar_pedido'), {'usuario': self.usuario.pk})
        fila = LineaPedido.objects.get(pedido__usuario=self.otro)
        self.assertEqual(fila.posicion, 1)
        self.assertEqual(LineaPedido.objects.filter(pedido__usuario=self.usuario).count(), 3)

    def test_agregar_pedido_requiere_post_sesion_y_csrf(self):
        from django.test import Client
        url = reverse('agregar_pedido')
        self.assertEqual(self.client.get(url).status_code, 405)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.usuario)
        self.assertEqual(protegido.post(url).status_code, 403)
        pagina = protegido.get(reverse('mis_pedidos'))
        self.assertEqual(protegido.post(url, {
            'csrfmiddlewaretoken': pagina.cookies['csrftoken'].value,
        }).status_code, 302)
        self.client.logout()
        self.assertRedirects(self.client.post(url), reverse('login') + '?next=' + url)
        self.assertEqual(LineaPedido.objects.count(), 4)

    def test_planilla_editable_sin_desplegables_ni_importes(self):
        response = self.client.get(reverse('mis_pedidos'))
        self.assertContains(response, '<table ', count=1)
        self.assertContains(response, '<th scope="col">', count=4)
        for texto in ['<select', '>Guardar<', 'Precio', 'Subtotal', 'Total:', 'Cantidad']:
            self.assertNotContains(response, texto)
        self.assertContains(response, '>Eliminar</button>', count=3)
        self.assertContains(response, 'value="Remera"', count=3)
        self.assertEqual(list(response.context['lineas']), self.filas)

    def test_editar_texto_libre_y_reordenar(self):
        fila = self.filas[2]
        for campo, valor in [('nombre', 'Buzo personalizado'), ('color', 'Verde'), ('talle', 'XXL')]:
            respuesta = self.editar(fila, campo, valor)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.json()['valor'], valor)
        respuesta = self.editar(fila, 'numero', '1')
        self.assertEqual(respuesta.json()['orden'], [fila.pk, self.filas[0].pk, self.filas[1].pk])
        fila.refresh_from_db()
        self.assertEqual((fila.nombre, fila.color, fila.talle), ('Buzo personalizado', 'Verde', 'XXL'))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Remera')
        self.assertEqual(fila.producto, self.producto)
        self.assertContains(self.client.get(reverse('mis_pedidos')), 'value="Buzo personalizado"')

    def test_eliminar_fila_intermedia_renumera_y_agregar_continua(self):
        self.client.post(reverse('eliminar_pedido', args=[self.filas[1].pk]))
        response = self.client.get(reverse('mis_pedidos'))
        self.assertEqual([(fila.pk, fila.posicion) for fila in response.context['lineas']],
                         [(self.filas[0].pk, 1), (self.filas[2].pk, 2)])
        self.client.post(reverse('crear_pedido'), [{'id': self.producto.pk, 'quantity': 1,
                         'color': 'Negro', 'size': '38'}], content_type='application/json')
        response = self.client.get(reverse('mis_pedidos'))
        self.assertEqual([fila.posicion for fila in response.context['lineas']], [1, 2, 3])

    def test_eliminar_ultima_fila_limpia_pedido_y_muestra_estado_vacio(self):
        for fila in self.filas:
            self.client.post(reverse('eliminar_pedido', args=[fila.pk]))
        self.assertFalse(Pedido.objects.filter(pk=self.pedido.pk).exists())
        self.assertContains(self.client.get(reverse('mis_pedidos')), 'Todavía no realizaste pedidos.')

    def test_cambios_invalidos_no_modifican_pedido(self):
        for campo, valor in [('numero', '0'), ('numero', '4'), ('numero', 'abc'),
                             ('nombre', '   '), ('nombre', 'x' * 101),
                             ('color', 'x' * 101), ('talle', 'x' * 101), ('precio', '1')]:
            self.assertEqual(self.editar(self.filas[0], campo, valor).status_code, 400)
        self.filas[0].refresh_from_db()
        self.assertEqual(self.filas[0].nombre, 'Remera')
        self.assertEqual(self.filas[0].color, 'Negro')

    def test_editar_una_celda_preserva_las_otras_y_admite_color_talle_vacios(self):
        for campo in ['color', 'talle']:
            self.assertEqual(self.editar(self.filas[0], campo, '').status_code, 200)
        self.filas[0].refresh_from_db()
        self.assertEqual((self.filas[0].nombre, self.filas[0].color, self.filas[0].talle), ('Remera', '', ''))

    def test_proteccion_de_propietario_metodo_y_csrf(self):
        from django.test import Client
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.usuario)
        for nombre in ['modificar_pedido', 'eliminar_pedido']:
            url = reverse(nombre, args=[self.filas[0].pk])
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(protegido.post(url).status_code, 403)
            self.client.force_login(self.otro)
            self.assertEqual(self.client.post(url).status_code, 404)
            self.client.logout()
            self.assertEqual(self.client.post(url).status_code, 302)
            self.client.force_login(self.usuario)
        self.assertEqual(LineaPedido.objects.count(), 3)


class OpcionesPedidoTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('opciones')
        self.client.force_login(self.usuario)
        self.pedido = Pedido.objects.create(usuario=self.usuario)
        self.principal = LineaPedido.objects.create(
            pedido=self.pedido, nombre='Zapatilla', precio=100, cantidad=1, posicion=1)
        self.url = reverse('agregar_opcion', args=[self.principal.pk])

    def agregar(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        return self.principal.opciones.latest('pk')

    def test_limite_edicion_y_botones_solo_en_principal(self):
        opciones = [self.agregar() for _ in range(3)]
        self.assertEqual(self.client.post(self.url).status_code, 400)
        self.assertEqual(self.principal.opciones.count(), 3)
        pagina = self.client.get(reverse('mis_pedidos'))
        self.assertContains(pagina, '>Agregar opción</button>', count=1)
        self.assertContains(pagina, '>Eliminar</button>', count=4)
        for numero in range(1, 4):
            self.assertContains(pagina, f'Opción {numero}')
        for campo, valor in [('nombre', 'Ojota'), ('color', 'Blanco'), ('talle', '40')]:
            response = self.client.post(reverse('modificar_pedido', args=[opciones[0].pk]),
                                        {'campo': campo, 'valor': valor})
            self.assertEqual(response.status_code, 200)
        opciones[0].refresh_from_db()
        self.assertEqual((opciones[0].nombre, opciones[0].color, opciones[0].talle), ('Ojota', 'Blanco', '40'))
        self.assertEqual(self.client.post(reverse('modificar_pedido', args=[opciones[0].pk]),
                                         {'campo': 'numero', 'valor': '1'}).status_code, 400)
        self.assertEqual(self.client.post(reverse('agregar_opcion', args=[opciones[0].pk])).status_code, 404)
        opciones[0].precio = 50
        opciones[0].save()
        self.assertEqual(self.pedido.total, 100)

    def test_eliminar_renumera_y_permite_reemplazar(self):
        primera, segunda, tercera = [self.agregar() for _ in range(3)]
        self.client.post(reverse('eliminar_pedido', args=[segunda.pk]))
        self.assertEqual(list(self.principal.opciones.order_by('posicion').values_list('pk', 'posicion')),
                         [(primera.pk, 1), (tercera.pk, 2)])
        self.assertEqual(self.agregar().posicion, 3)
        self.client.post(reverse('eliminar_pedido', args=[self.principal.pk]))
        self.assertFalse(LineaPedido.objects.exists())
        self.assertFalse(Pedido.objects.exists())

    def test_numeracion_principal_independiente_y_orden_visual(self):
        opcion = self.agregar()
        self.client.post(reverse('agregar_pedido'))
        nuevo = LineaPedido.objects.latest('pk')
        self.assertEqual(nuevo.posicion, 2)
        response = self.client.post(reverse('modificar_pedido', args=[nuevo.pk]), {'campo': 'numero', 'valor': '1'})
        self.assertEqual(response.json()['orden'], [nuevo.pk, self.principal.pk])
        pagina = self.client.get(reverse('mis_pedidos')).content.decode()
        self.assertLess(pagina.index(f'id="pedido-{nuevo.pk}"'), pagina.index(f'id="pedido-{self.principal.pk}"'))
        self.assertLess(pagina.index(f'id="pedido-{self.principal.pk}"'), pagina.index(f'id="pedido-{opcion.pk}"'))
        opcion.refresh_from_db()
        self.assertEqual(opcion.posicion, 1)

    def test_protecciones(self):
        from django.test import Client
        opcion = self.agregar()
        urls = [self.url, reverse('modificar_pedido', args=[opcion.pk]), reverse('eliminar_pedido', args=[opcion.pk])]
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.usuario)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(protegido.post(url).status_code, 403)
        otro = get_user_model().objects.create_user('otro')
        self.client.force_login(otro)
        for url in urls:
            self.assertEqual(self.client.post(url).status_code, 404)
        self.client.logout()
        for url in urls:
            self.assertEqual(self.client.post(url).status_code, 302)
