from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LineaPedido, Pedido, PedidoGeneral, Producto, Proveedor


class VerPedidosTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('admin', is_staff=True)
        self.cliente = get_user_model().objects.create_user('ana')
        self.otro = get_user_model().objects.create_user('beatriz', is_active=False)
        self.anterior = PedidoGeneral.objects.create(descripcion='Octubre 1', estado='cerrado')
        self.actual = PedidoGeneral.objects.create(descripcion='Octubre 2')
        self.historica = self.crear_linea(self.cliente, self.anterior, 'Campera histórica')
        self.linea = self.crear_linea(self.cliente, self.actual, 'Remera actual')
        self.ajena = self.crear_linea(self.otro, self.actual, 'Pedido ajeno')
        self.client.force_login(self.admin)

    def crear_linea(self, cliente, periodo, nombre):
        pedido = Pedido.objects.create(usuario=cliente, pedido_general=periodo)
        return LineaPedido.objects.create(pedido=pedido, nombre=nombre, precio=0, cantidad=1, posicion=1)

    def url(self, accion, linea=None, periodo=None, cliente=None):
        args = [(periodo or self.actual).pk, (cliente or self.cliente).pk]
        if linea is not None:
            args.append(linea.pk)
        return reverse('admin_' + accion, args=args)

    def destino(self, periodo=None):
        return reverse('ver_pedidos') + '?' + urlencode({
            'periodo': (periodo or self.actual).pk, 'filtro': 'cliente', 'cliente': self.cliente.pk,
        })

    def test_menu_periodo_predeterminado_y_clientes_sin_pedidos(self):
        self.assertContains(self.client.get(reverse('producto')), f'href="{reverse("ver_pedidos")}"')
        respuesta = self.client.get(reverse('ver_pedidos'))
        form = respuesta.context['form']
        self.assertEqual(form.cleaned_data['periodo'], self.actual)
        self.assertEqual(list(form.fields['periodo'].queryset), [self.actual, self.anterior])
        self.assertEqual(list(form.fields['cliente'].queryset), [self.cliente, self.otro])
        self.assertContains(respuesta, 'Proveedor')
        self.assertNotContains(respuesta, 'planilla-pedidos')
        nuevo = get_user_model().objects.create_user('sin_pedidos')
        respuesta = self.client.get(reverse('ver_pedidos'), {'cliente': nuevo.pk})
        self.assertContains(respuesta, 'todavía no tiene pedidos en el período seleccionado')
        self.assertContains(respuesta, self.url('agregar_pedido', cliente=nuevo))

    def test_orden_por_fecha_de_creacion_y_seleccion_sin_abierto(self):
        PedidoGeneral.objects.filter(pk=self.actual.pk).update(estado='cerrado')
        PedidoGeneral.objects.filter(pk=self.anterior.pk).update(fecha_creacion=timezone.now() + timedelta(days=1))
        respuesta = self.client.get(reverse('ver_pedidos'))
        form = respuesta.context['form']
        self.assertEqual(list(form.fields['periodo'].queryset), [self.anterior, self.actual])
        self.assertEqual(form.cleaned_data['periodo'], self.anterior)

    def test_filtros_aislan_cliente_y_periodo_y_comparten_planilla(self):
        respuesta = self.client.get(self.destino())
        self.assertTemplateUsed(respuesta, 'producto/planilla_pedidos.html')
        self.assertContains(respuesta, 'Remera actual')
        self.assertNotContains(respuesta, 'Campera histórica')
        self.assertNotContains(respuesta, 'Pedido ajeno')
        self.assertContains(respuesta, self.url('modificar_pedido', self.linea))
        respuesta = self.client.get(self.destino(self.anterior))
        self.assertContains(respuesta, 'Campera histórica')
        self.assertNotContains(respuesta, 'Remera actual')

    def test_cliente_e_invalido(self):
        respuesta = self.client.get(reverse('ver_pedidos'), {'cliente': self.cliente.pk})
        self.assertEqual(respuesta.context['cliente_elegido'], self.cliente)
        self.assertContains(respuesta, 'Remera actual')
        for datos in [{'cliente': 99999}, {'cliente': self.admin.pk},
                      {'cliente': 'incorrecto'}, {'periodo': 'incorrecto'}, {'periodo': 99999},
                      {'filtro': 'desconocido'}, {'filtro': ['cliente', 'proveedor']}]:
            with self.subTest(datos=datos):
                respuesta = self.client.get(reverse('ver_pedidos'), datos)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context['form'].errors)
                self.assertNotContains(respuesta, 'id="agregar-pedido"')

    def test_proveedor_muestra_combo_completo_y_solicita_seleccion(self):
        zeta = self.crear_proveedor('Zeta')
        alfa = self.crear_proveedor('alfa')
        respuesta = self.client.get(reverse('ver_pedidos'), {'filtro': 'proveedor', 'cliente': self.cliente.pk})
        self.assertEqual(list(respuesta.context['form'].fields['proveedor'].queryset), [alfa, zeta])
        self.assertContains(respuesta, 'id="filtro-proveedor" class="mb-3">')
        self.assertContains(respuesta, 'Seleccioná un proveedor o ingresá su nombre')
        self.assertNotContains(respuesta, 'Remera actual')
        self.assertNotContains(respuesta, 'id="agregar-pedido"')

    def test_planilla_proveedor_incluye_todos_los_clientes_y_es_solo_lectura(self):
        proveedor = self.crear_proveedor('Proveedor compartido')
        for linea in [self.linea, self.ajena, self.historica]:
            linea.proveedor = proveedor
            linea.color = 'Azul'
            linea.talle = 'XL'
            linea.save()
        respuesta = self.client.get(reverse('ver_pedidos'), {
            'filtro': 'proveedor', 'proveedor': proveedor.pk, 'cliente': self.cliente.pk,
        })
        self.assertTemplateUsed(respuesta, 'producto/planilla_proveedor.html')
        self.assertEqual(set(respuesta.context['lineas']), {self.linea, self.ajena})
        for valor in ['Remera actual', 'Pedido ajeno', 'Azul', 'XL', 'ana', 'beatriz']:
            self.assertContains(respuesta, f'<span class="valor-pedido">{valor}</span>', html=True)
        self.assertContains(respuesta, '<th scope="col">Producto</th><th scope="col">Color</th>'
                            '<th scope="col">Talle</th><th scope="col">Cliente</th>', html=True)
        self.assertNotContains(respuesta, 'Campera histórica')
        tabla = respuesta.content.decode().split('<table', 1)[1].split('</table>', 1)[0]
        for control in ['<input', '<select', '<button', '<form', 'contenteditable', 'data-url']:
            self.assertNotIn(control, tabla)
        self.assertNotContains(respuesta, 'js/mis_pedidos.js')
        self.assertNotContains(respuesta, 'id="agregar-pedido"')
        respuesta = self.client.get(reverse('ver_pedidos'), {
            'filtro': 'proveedor', 'proveedor': proveedor.pk, 'periodo': self.anterior.pk,
        })
        self.assertEqual(list(respuesta.context['lineas']), [self.historica])

    def test_filtro_proveedor_respeta_asignacion_manual_catalogo_y_opciones(self):
        original = self.crear_proveedor('Original')
        elegido = self.crear_proveedor('Elegido')
        producto = Producto.objects.create(nombre='Remera', precio=100, id_proveedor=original)
        self.linea.producto = producto
        self.linea.save()
        self.ajena.producto = producto
        self.ajena.proveedor = elegido
        self.ajena.save()
        opcion = LineaPedido.objects.create(
            pedido=self.ajena.pedido, principal=self.ajena, proveedor=original,
            nombre='Alternativa', precio=0, cantidad=1, posicion=1,
        )
        for proveedor, esperadas in [(original, {self.linea, opcion}), (elegido, {self.ajena})]:
            with self.subTest(proveedor=proveedor):
                respuesta = self.client.get(reverse('ver_pedidos'), {
                    'filtro': 'proveedor', 'proveedor': proveedor.pk,
                })
                self.assertEqual(set(respuesta.context['lineas']), esperadas)

    def test_proveedor_sin_pedidos_e_invalido(self):
        proveedor = self.crear_proveedor('Sin pedidos')
        respuesta = self.client.get(reverse('ver_pedidos'), {
            'filtro': 'proveedor', 'proveedor': proveedor.pk,
        })
        self.assertContains(respuesta, 'Este proveedor todavía no tiene pedidos en el período seleccionado.')
        for valor in ['incorrecto', 99999, '-1', '9' * 100]:
            with self.subTest(valor=valor):
                respuesta = self.client.get(reverse('ver_pedidos'), {'filtro': 'proveedor', 'proveedor': valor})
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn('proveedor', respuesta.context['form'].errors)
                self.assertTemplateNotUsed(respuesta, 'producto/planilla_proveedor.html')

    def crear_proveedor(self, nombre):
        return Proveedor.objects.create(nombre=nombre, calle_nombre='Mitre', calle_numero=123, localidad='Rosario')

    def test_columna_proveedor_precarga_producto_y_ordena_combo_por_nombre(self):
        zeta = self.crear_proveedor('Zeta')
        alfa = self.crear_proveedor('alfa')
        producto = Producto.objects.create(nombre='Remera', precio=100, id_proveedor=zeta)
        self.linea.producto = producto
        self.linea.save()
        respuesta = self.client.get(self.destino())
        self.assertContains(respuesta, '<th scope="col">Talle</th><th scope="col">Proveedor</th>', html=False)
        self.assertEqual(list(respuesta.context['proveedores']), [alfa, zeta])
        self.assertContains(respuesta, f'<option value="{zeta.pk}" selected>Zeta</option>', html=True)
        self.assertLess(respuesta.content.index(b'>alfa</option>'), respuesta.content.index(b'>Zeta</option>'))

    def test_proveedor_se_guarda_en_lineas_manuales_y_opciones(self):
        proveedor = self.crear_proveedor('Proveedor elegido')
        self.client.post(self.url('agregar_opcion', self.linea))
        opcion = self.linea.opciones.get()
        for linea in [self.linea, opcion]:
            respuesta = self.client.post(self.url('modificar_pedido', linea), {
                'campo': 'proveedor', 'valor': str(proveedor.pk),
            })
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.json()['valor'], str(proveedor.pk))
            linea.refresh_from_db()
            self.assertEqual(linea.proveedor, proveedor)
        self.assertContains(self.client.get(self.destino()),
                            f'<option value="{proveedor.pk}" selected>Proveedor elegido</option>', count=2, html=True)
        self.client.post(self.url('modificar_pedido', self.linea), {'campo': 'proveedor', 'valor': ''})
        self.linea.refresh_from_db()
        self.assertIsNone(self.linea.proveedor_actual_id)

    def test_proveedor_del_pedido_no_modifica_catalogo_y_puede_restaurarse(self):
        original = self.crear_proveedor('Original')
        elegido = self.crear_proveedor('Elegido')
        producto = Producto.objects.create(nombre='Remera', precio=100, id_proveedor=original)
        self.linea.producto = producto
        self.linea.save()
        url = self.url('modificar_pedido', self.linea)
        self.client.post(url, {'campo': 'proveedor', 'valor': elegido.pk})
        self.linea.refresh_from_db()
        producto.refresh_from_db()
        self.assertEqual(self.linea.proveedor_actual_id, elegido.pk)
        self.assertEqual(producto.id_proveedor, original)
        self.assertContains(self.client.get(self.destino()),
                            f'<option value="{elegido.pk}" selected>Elegido</option>', html=True)
        respuesta = self.client.post(url, {'campo': 'proveedor', 'valor': ''})
        self.assertEqual(respuesta.json()['valor'], str(original.pk))
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.proveedor_actual_id, original.pk)

    def test_proveedor_invalido_y_cliente_no_puede_asignarlo(self):
        proveedor = self.crear_proveedor('Existente')
        self.linea.proveedor = proveedor
        self.linea.save()
        for valor in ['inexistente', '99999', '-1', '9' * 100]:
            respuesta = self.client.post(self.url('modificar_pedido', self.linea), {
                'campo': 'proveedor', 'valor': valor,
            })
            self.assertEqual(respuesta.status_code, 400)
        self.client.force_login(self.cliente)
        self.assertNotContains(self.client.get(reverse('mis_pedidos')), 'name="proveedor"')
        respuesta = self.client.post(reverse('modificar_pedido', args=[self.linea.pk]), {
            'campo': 'proveedor', 'valor': '',
        })
        self.assertEqual(respuesta.status_code, 400)
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.proveedor, proveedor)

    def test_sin_periodos(self):
        Pedido.objects.all().delete()
        PedidoGeneral.objects.all().delete()
        respuesta = self.client.get(reverse('ver_pedidos'))
        self.assertContains(respuesta, 'Todavía no hay períodos creados.')
        self.assertNotContains(respuesta, 'id="agregar-pedido"')

    def test_admin_agrega_edita_opciones_y_elimina_en_periodo_cerrado(self):
        url = self.url('agregar_pedido', periodo=self.anterior)
        respuesta = self.client.post(url, {'usuario': self.admin.pk, 'periodo': self.actual.pk})
        nueva = LineaPedido.objects.latest('pk')
        self.assertEqual(nueva.pedido.usuario, self.cliente)
        self.assertEqual(nueva.pedido.pedido_general, self.anterior)
        self.assertEqual(nueva.posicion, 2)
        self.assertRedirects(respuesta, self.destino(self.anterior) + f'#pedido-{nueva.pk}')
        respuesta = self.client.post(self.url('modificar_pedido', nueva, self.anterior), {
            'campo': 'nombre', 'valor': ' Buzo corregido ',
        })
        self.assertEqual(respuesta.json()['valor'], 'Buzo corregido')
        self.client.post(self.url('agregar_opcion', nueva, self.anterior))
        opcion = nueva.opciones.get()
        self.assertRedirects(self.client.post(self.url('eliminar_pedido', opcion, self.anterior)), self.destino(self.anterior))
        self.client.post(self.url('agregar_opcion', nueva, self.anterior))
        self.assertRedirects(self.client.post(self.url('eliminar_pedido', nueva, self.anterior)), self.destino(self.anterior))
        self.assertFalse(Pedido.objects.filter(pk=nueva.pedido_id).exists())
        self.assertTrue(LineaPedido.objects.filter(pk=self.historica.pk).exists())
        self.actual.refresh_from_db()
        self.anterior.refresh_from_db()
        self.assertEqual((self.actual.estado, self.anterior.estado), ('abierto', 'cerrado'))

    def test_opciones_limite_y_reordenamiento_no_afectan_otros_clientes(self):
        for _ in range(3):
            self.client.post(self.url('agregar_opcion', self.linea))
        respuesta = self.client.post(self.url('agregar_opcion', self.linea))
        self.assertContains(respuesta, 'Cada pedido admite hasta 3 opciones', status_code=400)
        self.assertTemplateUsed(respuesta, 'producto/ver_pedidos.html')
        self.assertEqual(respuesta.context['cliente_elegido'], self.cliente)
        opcion = self.linea.opciones.order_by('posicion').first()
        self.assertEqual(self.client.post(self.url('modificar_pedido', opcion), {
            'campo': 'color', 'valor': 'Azul',
        }).json()['valor'], 'Azul')
        self.client.post(self.url('eliminar_pedido', opcion))
        self.assertEqual(list(self.linea.opciones.order_by('posicion').values_list('posicion', flat=True)), [1, 2])
        self.client.post(self.url('agregar_pedido'))
        nueva = LineaPedido.objects.latest('pk')
        respuesta = self.client.post(self.url('modificar_pedido', nueva), {'campo': 'numero', 'valor': '1'})
        self.assertEqual(respuesta.json()['orden'], [nueva.pk, self.linea.pk])
        self.ajena.refresh_from_db()
        self.historica.refresh_from_db()
        self.assertEqual((self.ajena.posicion, self.historica.posicion), (1, 1))

    def test_rutas_rechazan_lineas_de_otro_cliente_o_periodo(self):
        for linea in [self.ajena, self.historica]:
            for accion in ['modificar_pedido', 'eliminar_pedido', 'agregar_opcion']:
                with self.subTest(linea=linea.pk, accion=accion):
                    respuesta = self.client.post(self.url(accion, linea), {'campo': 'nombre', 'valor': 'Cambio'})
                    self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(LineaPedido.objects.count(), 3)

    def test_acceso_metodos_y_csrf(self):
        rutas = [self.url('agregar_pedido')] + [
            self.url(accion, self.linea) for accion in ['modificar_pedido', 'eliminar_pedido', 'agregar_opcion']
        ]
        self.client.logout()
        for url in [reverse('ver_pedidos'), *rutas]:
            self.assertRedirects(self.client.get(url), reverse('login') + '?next=' + url)
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse('ver_pedidos')).status_code, 403)
        self.assertNotContains(self.client.get(reverse('producto')), f'href="{reverse("ver_pedidos")}"')
        for url in rutas:
            self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.admin)
        for url in rutas:
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(protegido.post(url).status_code, 403)
        self.assertEqual(self.client.post(reverse('ver_pedidos')).status_code, 405)
        protegido.get(self.destino())
        self.assertEqual(protegido.post(self.url('modificar_pedido', self.linea), {
            'campo': 'nombre', 'valor': 'Con CSRF',
            'csrfmiddlewaretoken': protegido.cookies['csrftoken'].value,
        }).status_code, 200)
