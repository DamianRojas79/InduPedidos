from datetime import date
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from .models import LineaPedido, Pedido, PedidoGeneral, Producto


class PeriodosPedidosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('cliente')
        self.admin = get_user_model().objects.create_user('admin', is_staff=True)
        self.client.force_login(self.usuario)
        self.administracion = Client()
        self.administracion.force_login(self.admin)
        self.producto = Producto.objects.create(nombre='Zapatos', precio=100)

    def crear_periodo(self):
        general = PedidoGeneral.objects.create(descripcion='Octubre')
        self.client.post(reverse('agregar_pedido'))
        linea = LineaPedido.objects.get()
        linea.nombre = 'Zapatos de octubre'
        linea.save()
        self.client.post(reverse('agregar_opcion', args=[linea.pk]))
        return general, linea

    def cerrar(self, general):
        self.assertRedirects(self.administracion.post(
            reverse('cerrar_pedido_general', args=[general.pk])), reverse('gestion_pedidos'))

    def test_ciclo_octubre_cierre_diciembre_conserva_historial_y_reinicia_planilla(self):
        octubre, linea = self.crear_periodo()
        pagina = self.client.get(reverse('mis_pedidos'))
        self.assertContains(pagina, 'Pedido: Octubre')
        self.assertContains(pagina, 'Zapatos de octubre')
        self.assertEqual(linea.pedido.pedido_general, octubre)
        self.cerrar(octubre)
        pagina = self.client.get(reverse('mis_pedidos'))
        self.assertNotContains(pagina, 'Zapatos de octubre')
        self.assertContains(pagina, 'No hay un pedido general abierto.')
        self.assertFalse(pagina.context['lineas'].exists())
        self.assertFalse(pagina.context['pedidos'].exists())
        self.assertEqual(LineaPedido.objects.count(), 2)
        self.administracion.post(reverse('crear_pedido_general'), {'descripcion': 'Diciembre'})
        diciembre = PedidoGeneral.objects.first()
        pagina = self.client.get(reverse('mis_pedidos'))
        self.assertContains(pagina, 'Pedido: Diciembre')
        self.assertNotContains(pagina, 'Zapatos de octubre')
        self.assertFalse(pagina.context['lineas'].exists())
        self.client.post(reverse('agregar_pedido'))
        nueva = LineaPedido.objects.latest('pk')
        self.assertEqual(nueva.posicion, 1)
        self.assertEqual(nueva.pedido.pedido_general, diciembre)
        self.client.post(reverse('agregar_opcion', args=[nueva.pk]))
        self.assertEqual(nueva.opciones.count(), 1)
        self.client.post(reverse('eliminar_pedido', args=[nueva.pk]))
        self.assertFalse(nueva.pedido.lineas.exists())
        self.assertEqual(LineaPedido.objects.filter(pedido__pedido_general=octubre).count(), 2)

    def test_sin_abierto_bloquea_carga_manual_catalogo_y_json(self):
        pagina = self.client.get(reverse('mis_pedidos'))
        self.assertContains(pagina, '<tbody>')
        self.assertFalse(pagina.context['lineas'].exists())
        self.assertNotContains(pagina, 'id="agregar-pedido"')
        self.assertEqual(self.client.post(reverse('agregar_pedido')).status_code, 409)
        self.assertEqual(self.client.post(reverse('crear_pedido'), {'id': self.producto.pk}).status_code, 409)
        respuesta = self.client.post(reverse('crear_pedido'), [
            {'id': self.producto.pk, 'quantity': 1}], content_type='application/json')
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn('No hay un pedido general abierto', respuesta.json()['error'])
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(LineaPedido.objects.exists())
        self.assertContains(self.client.get(reverse('detalle_producto', args=[self.producto.pk])),
                            'No hay un pedido general abierto.')

    def test_formularios_viejos_no_editan_eliminan_ni_agregan_opciones_al_historial(self):
        general, linea = self.crear_periodo()
        opcion = linea.opciones.get()
        self.cerrar(general)
        for nuevo_abierto in [False, True]:
            if nuevo_abierto:
                PedidoGeneral.objects.create(descripcion='Diciembre')
            for fila in [linea, opcion]:
                for ruta, datos in [('modificar_pedido', {'campo': 'nombre', 'valor': 'Cambio'}),
                                    ('eliminar_pedido', {}), ('agregar_opcion', {})]:
                    with self.subTest(abierto=nuevo_abierto, fila=fila.pk, ruta=ruta):
                        respuesta = self.client.post(reverse(ruta, args=[fila.pk]), datos)
                        self.assertEqual(respuesta.status_code, 404 if nuevo_abierto else 409)
            linea.refresh_from_db()
            self.assertEqual(linea.nombre, 'Zapatos de octubre')
            self.assertEqual(LineaPedido.objects.count(), 2)

    def test_catalogo_vincula_al_periodo_abierto(self):
        general = PedidoGeneral.objects.create(descripcion='Octubre')
        for es_json in [True, False]:
            datos = {'id': self.producto.pk, 'quantity': 1}
            if es_json:
                respuesta = self.client.post(reverse('crear_pedido'), [datos], content_type='application/json')
                self.assertEqual(respuesta.status_code, 201)
            else:
                self.assertRedirects(self.client.post(reverse('crear_pedido'), datos), reverse('mis_pedidos'))
        self.assertEqual(Pedido.objects.filter(pedido_general=general).count(), 2)

    def test_pedidos_sin_periodo_no_aparecen_ni_se_renumeran(self):
        anterior = Pedido.objects.create(usuario=self.usuario)
        linea = LineaPedido.objects.create(pedido=anterior, nombre='Histórico', precio=1, cantidad=1, posicion=8)
        PedidoGeneral.objects.create(descripcion='Octubre')
        self.client.post(reverse('agregar_pedido'))
        self.assertNotContains(self.client.get(reverse('mis_pedidos')), 'Histórico')
        self.assertEqual(LineaPedido.objects.latest('pk').posicion, 1)
        linea.refresh_from_db()
        self.assertEqual(linea.posicion, 8)

    def test_migracion_asocia_pedidos_existentes_solo_si_hay_abierto(self):
        migracion = import_module('producto.migrations.0015_pedido_pedido_general')
        pedido = Pedido.objects.create(usuario=self.usuario)
        editor = SimpleNamespace(connection=connection)
        migracion.vincular_pedidos_actuales(apps, editor)
        pedido.refresh_from_db()
        self.assertIsNone(pedido.pedido_general)
        abierto = PedidoGeneral.objects.create(descripcion='Octubre')
        migracion.vincular_pedidos_actuales(apps, editor)
        pedido.refresh_from_db()
        self.assertEqual(pedido.pedido_general, abierto)


class EdicionGeneralTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('admin', is_staff=True)
        self.client.force_login(self.admin)
        self.cerrado = PedidoGeneral.objects.create(descripcion='Septiembre', estado='cerrado')
        self.abierto = PedidoGeneral.objects.create(descripcion='Octubre')
        self.url = reverse('modificar_pedido_general', args=[self.abierto.pk])

    def test_solo_primera_fila_editable_y_cierre_fuera_de_columnas(self):
        respuesta = self.client.get(reverse('gestion_pedidos'))
        self.assertEqual(list(respuesta.context['pedidos_generales']), [self.abierto, self.cerrado])
        self.assertContains(respuesta, 'name="descripcion"', count=1)
        self.assertContains(respuesta, 'name="fecha_entrega"', count=1)
        self.assertContains(respuesta, 'Cerrar pedido', count=1)
        self.assertContains(respuesta, '<th scope="col">', count=4)
        self.assertContains(respuesta, 'class="acciones-pedido"')

    def test_edicion_guarda_descripcion_y_fecha_sin_modificar_estado_ni_creacion(self):
        creacion = self.abierto.fecha_creacion
        self.assertEqual(self.client.post(self.url, {'campo': 'descripcion', 'valor': ' Noviembre '}).json(),
                         {'valor': 'Noviembre'})
        self.assertEqual(self.client.post(self.url, {'campo': 'fecha_entrega', 'valor': '2026-11-30'}).status_code, 200)
        self.abierto.refresh_from_db()
        self.assertEqual(self.abierto.descripcion, 'Noviembre')
        self.assertEqual(self.abierto.fecha_entrega, date(2026, 11, 30))
        self.assertEqual(self.abierto.estado, 'abierto')
        self.assertEqual(self.abierto.fecha_creacion, creacion)
        self.client.post(self.url, {'campo': 'fecha_entrega', 'valor': ''})
        self.abierto.refresh_from_db()
        self.assertIsNone(self.abierto.fecha_entrega)

    def test_campos_invalidos_y_filas_cerradas_no_se_modifican(self):
        for campo, valor in [('descripcion', ' '), ('descripcion', 'x' * 201),
                             ('fecha_entrega', '2026-02-30'), ('estado', 'cerrado'),
                             ('fecha_creacion', '2020-01-01')]:
            self.assertEqual(self.client.post(self.url, {'campo': campo, 'valor': valor}).status_code, 400)
        self.assertEqual(self.client.post(reverse('modificar_pedido_general', args=[self.cerrado.pk]),
                         {'campo': 'descripcion', 'valor': 'Cambio'}).status_code, 409)
        self.client.post(reverse('cerrar_pedido_general', args=[self.abierto.pk]))
        self.assertEqual(self.client.post(self.url, {'campo': 'descripcion', 'valor': 'Cambio'}).status_code, 409)
        self.abierto.refresh_from_db()
        self.cerrado.refresh_from_db()
        self.assertEqual(self.abierto.descripcion, 'Octubre')
        self.assertEqual(self.cerrado.descripcion, 'Septiembre')
        pagina = self.client.get(reverse('gestion_pedidos'))
        self.assertNotContains(pagina, 'name="descripcion"')

    def test_edicion_requiere_post_y_csrf(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.admin)
        self.assertEqual(protegido.post(self.url, {'campo': 'descripcion', 'valor': 'Cambio'}).status_code, 403)
