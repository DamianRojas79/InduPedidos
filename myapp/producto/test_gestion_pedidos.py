from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import PedidoGeneralForm
from .models import PedidoGeneral


class GestionPedidosTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('administrador', is_staff=True)
        self.cliente = get_user_model().objects.create_user('cliente')
        self.client.force_login(self.admin)
        self.gestion = reverse('gestion_pedidos')
        self.crear = reverse('crear_pedido_general')

    def test_estado_vacio_y_acceso_desde_menu(self):
        response = self.client.get(self.gestion)
        self.assertContains(response, 'Todavía no hay pedidos creados.')
        self.assertContains(response, f'href="{self.crear}"')
        self.assertNotContains(response, 'Cerrar pedido')
        self.assertContains(self.client.get(reverse('producto')), f'href="{self.gestion}"')
        self.assertContains(self.client.get(self.crear), 'type="date"')
        self.assertFalse(PedidoGeneral.objects.exists())

    def test_crear_sin_fecha_con_valores_generados_en_servidor(self):
        antes = timezone.now()
        response = self.client.post(self.crear, {
            'descripcion': '  Pedido Octubre  ', 'fecha_entrega': '',
            'estado': 'cerrado', 'id': '1234', 'fecha_creacion': '2000-01-01',
        })
        self.assertRedirects(response, self.gestion)
        pedido = PedidoGeneral.objects.get()
        self.assertEqual(pedido.descripcion, 'Pedido Octubre')
        self.assertEqual(pedido.estado, 'abierto')
        self.assertNotEqual(pedido.pk, 1234)
        self.assertGreaterEqual(pedido.fecha_creacion, antes)
        self.assertIsNone(pedido.fecha_entrega)
        pagina = self.client.get(self.gestion)
        self.assertContains(pagina, 'name="fecha_entrega" value=""')
        self.assertContains(pagina, 'Cerrar pedido')
        self.assertContains(pagina, 'disabled aria-describedby="ayuda-nuevo-pedido"')
        self.assertNotContains(pagina, f'href="{self.crear}"')

    def test_crear_con_fecha_de_entrega(self):
        self.assertRedirects(self.client.post(self.crear, {
            'descripcion': 'Pedido Octubre', 'fecha_entrega': '2026-10-31',
        }), self.gestion)
        self.assertEqual(PedidoGeneral.objects.get().fecha_entrega, date(2026, 10, 31))
        self.assertContains(self.client.get(self.gestion), '2026-10-31')

    def test_validaciones_no_guardan_pedido(self):
        casos = [({}, 'descripcion'), ({'descripcion': '   '}, 'descripcion'),
                 ({'descripcion': 'x' * 201}, 'descripcion'),
                 ({'descripcion': 'Octubre', 'fecha_entrega': '2026-02-30'}, 'fecha_entrega')]
        for datos, campo in casos:
            with self.subTest(datos=datos):
                response = self.client.post(self.crear, datos)
                self.assertEqual(response.status_code, 200)
                self.assertIn(campo, response.context['form'].errors)
                self.assertFalse(PedidoGeneral.objects.exists())

    def test_bloquea_creacion_directa_si_hay_pedido_abierto(self):
        PedidoGeneral.objects.create(descripcion='Pedido Octubre')
        self.assertRedirects(self.client.get(self.crear), self.gestion)
        response = self.client.post(self.crear, {'descripcion': 'Pedido Noviembre'}, follow=True)
        self.assertContains(response, 'Cerrá el último pedido antes de crear uno nuevo.')
        self.assertEqual(PedidoGeneral.objects.count(), 1)

    def test_cerrar_habilita_nuevo_y_muestra_historial_descendente(self):
        primero = PedidoGeneral.objects.create(descripcion='Pedido Octubre')
        fecha_creacion = primero.fecha_creacion
        cerrar = reverse('cerrar_pedido_general', args=[primero.pk])
        self.assertRedirects(self.client.post(cerrar), self.gestion)
        primero.refresh_from_db()
        self.assertEqual(primero.estado, 'cerrado')
        self.assertEqual(primero.fecha_creacion, fecha_creacion)
        pagina = self.client.get(self.gestion)
        self.assertContains(pagina, 'Cerrado')
        self.assertNotContains(pagina, 'Cerrar pedido')
        self.assertContains(pagina, f'href="{self.crear}"')
        self.assertRedirects(self.client.post(cerrar), self.gestion)
        self.assertRedirects(self.client.post(self.crear, {'descripcion': 'Pedido Noviembre'}), self.gestion)
        ultimo = PedidoGeneral.objects.first()
        self.assertGreater(ultimo.pk, primero.pk)
        self.assertEqual(ultimo.estado, 'abierto')
        pagina = self.client.get(self.gestion)
        self.assertContains(pagina, 'Pedido Noviembre')
        self.assertContains(pagina, 'Pedido Octubre')
        self.assertLess(pagina.content.index(b'Pedido Noviembre'), pagina.content.index(b'Pedido Octubre'))
        self.assertEqual(PedidoGeneral.objects.count(), 2)
        # Un formulario de cierre viejo no debe cerrar el pedido nuevo.
        self.client.post(cerrar)
        ultimo.refresh_from_db()
        self.assertEqual(ultimo.estado, 'abierto')

    def test_cierre_inexistente_no_modifica_el_pedido(self):
        pedido = PedidoGeneral.objects.create(descripcion='Octubre')
        response = self.client.post(reverse('cerrar_pedido_general', args=[pedido.pk + 1]), follow=True)
        self.assertContains(response, 'Solo se puede cerrar el último pedido creado.')
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'abierto')

    def test_permisos_para_todas_las_rutas(self):
        pedido = PedidoGeneral.objects.create(descripcion='Octubre')
        rutas = [(self.gestion, 'get'), (self.crear, 'get'), (self.crear, 'post'),
                 (reverse('cerrar_pedido_general', args=[pedido.pk]), 'post'),
                 (reverse('modificar_pedido_general', args=[pedido.pk]), 'post')]
        self.client.logout()
        for url, metodo in rutas:
            self.assertRedirects(getattr(self.client, metodo)(url), reverse('login') + '?next=' + url)
        self.client.force_login(self.cliente)
        for url, metodo in rutas:
            self.assertEqual(getattr(self.client, metodo)(url).status_code, 403)
        self.assertNotContains(self.client.get(reverse('producto')), f'href="{self.gestion}"')
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'abierto')
        self.assertEqual(PedidoGeneral.objects.count(), 1)

    def test_metodos_y_csrf(self):
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.admin)
        self.assertEqual(protegido.post(self.crear, {'descripcion': 'Octubre'}).status_code, 403)
        pagina = protegido.get(self.crear)
        token = pagina.cookies['csrftoken'].value
        self.assertRedirects(protegido.post(self.crear, {
            'descripcion': 'Octubre', 'csrfmiddlewaretoken': token,
        }), self.gestion)
        pedido = PedidoGeneral.objects.get()
        cerrar = reverse('cerrar_pedido_general', args=[pedido.pk])
        self.assertEqual(self.client.get(cerrar).status_code, 405)
        self.assertEqual(protegido.post(cerrar).status_code, 403)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'abierto')
        self.assertRedirects(protegido.post(cerrar, {'csrfmiddlewaretoken': token}), self.gestion)
        self.assertEqual(self.client.post(self.gestion).status_code, 405)
        self.assertEqual(self.client.put(self.crear).status_code, 405)

    def test_base_de_datos_impide_dos_abiertos_y_admite_cerrados(self):
        PedidoGeneral.objects.create(descripcion='Octubre')
        with self.assertRaises(IntegrityError), transaction.atomic():
            PedidoGeneral.objects.create(descripcion='Noviembre')
        for descripcion in ['Agosto', 'Septiembre']:
            PedidoGeneral.objects.create(descripcion=descripcion, estado='cerrado')
        self.assertEqual(PedidoGeneral.objects.count(), 3)

    def test_base_de_datos_rechaza_estado_invalido_y_descripcion_vacia(self):
        for datos in [{'descripcion': 'Octubre', 'estado': 'otro'}, {'descripcion': ''}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                PedidoGeneral.objects.create(**datos)

    def test_conflicto_de_alta_simultanea_muestra_error_sin_duplicar(self):
        validar = PedidoGeneralForm.is_valid

        def validar_y_crear_otro(form):
            valido = validar(form)
            PedidoGeneral.objects.create(descripcion='Pedido de otro administrador')
            return valido

        with patch.object(PedidoGeneralForm, 'is_valid', validar_y_crear_otro):
            response = self.client.post(self.crear, {'descripcion': 'Octubre'}, follow=True)
        self.assertContains(response, 'Ya existe un pedido abierto.')
        self.assertEqual(PedidoGeneral.objects.count(), 1)
