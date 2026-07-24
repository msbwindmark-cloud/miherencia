import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from .models import (
    Edificio, Sensor, Lectura, Alerta, Mantenimiento, Equipo,
    Informe, PerfilUsuario, Notificacion, AuditLog, AnalisisIA,
    PrediccionML, Donacion, ReporteCiudadano, Seguro,
    EficienciaEnergetica, CumplimientoLegal, CertificadoBlockchain,
    TourVirtual, Evento, TiendaPatrimonio, ComentarioEdificio,
    GaleriaFoto, ChatMensajeIA, DocumentoEdificio, Herramienta,
    FormularioInspeccion, TimelineHistorico, RecomendacionIA,
    AnomaliaDetectada, Voluntario
)

MOCK_PRAYER = {
    'fajr': '06:30', 'sunrise': '08:00', 'dhuhr': '14:00',
    'asr': '17:30', 'maghrib': '20:30', 'isha': '22:00',
    'imsak': '06:00', 'midnight': '01:00', 'hijri': {}, 'method': '',
    'next_prayer': 'Dhuhr', 'next_prayer_name': 'Dhuhr', 'next_prayer_time': '14:00'
}


def mock_context(view_func):
    """Decorator to mock external API calls in context processor."""
    return patch('monitor.context_processors.get_prayer_times', return_value=MOCK_PRAYER)(
        patch('monitor.context_processors.get_weather', return_value=None)(view_func)
    )


class BaseModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', email='test@test.com'
        )
        self.edificio = Edificio.objects.create(
            nombre='Test Cathedral',
            direccion='Calle Test 1',
            ciudad='Sevilla',
            provincia='Sevilla',
            codigo_postal='41001',
            categoria='iglesia',
            descripcion='Test building',
            anno_construccion=1500,
            proteccion_oficial=True,
            propietario=self.user,
            estado_general='bueno',
            latitud=37.3891,
            longitud=-5.9845,
        )
        self.sensor = Sensor.objects.create(
            edificio=self.edificio,
            nombre='Sensor Temp 1',
            tipo='temperatura',
            ubicacionDescripcion='Nave principal',
            umbral_min=10.0,
            umbral_max=35.0,
            unidad_medida='°C',
            latitud=37.3891,
            longitud=-5.9845,
        )
        self.lectura = Lectura.objects.create(
            sensor=self.sensor,
            valor=22.5,
            fecha_hora=timezone.now(),
        )


class EdificioModelTest(BaseModelTestCase):
    def test_creacion_edificio(self):
        self.assertEqual(self.edificio.nombre, 'Test Cathedral')
        self.assertEqual(self.edificio.ciudad, 'Sevilla')
        self.assertTrue(self.edificio.activo)

    def test_str_edificio(self):
        self.assertIn('Test Cathedral', str(self.edificio))

    def test_get_absolute_url(self):
        url = self.edificio.get_absolute_url()
        self.assertIn(str(self.edificio.id), url)

    def test_num_sensores(self):
        self.assertEqual(self.edificio.num_sensores, 1)

    def test_salud_score(self):
        score = self.edificio.salud_score
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_alertas_activas(self):
        self.assertEqual(self.edificio.alertas_activas, 0)

    def test_ultima_lectura(self):
        self.assertIsNotNone(self.edificio.ultima_lectura)


class SensorModelTest(BaseModelTestCase):
    def test_creacion_sensor(self):
        self.assertEqual(self.sensor.nombre, 'Sensor Temp 1')
        self.assertEqual(self.sensor.tipo, 'temperatura')

    def test_str_sensor(self):
        s = str(self.sensor)
        self.assertIn('Sensor Temp 1', s)

    def test_lecturas_hoy(self):
        self.assertEqual(self.sensor.lecturas_hoy, 1)

    def test_ultima_lectura_sensor(self):
        self.assertIsNotNone(self.sensor.ultima_lectura)

    def test_qr_code(self):
        qr = self.sensor.qr_code_b64
        self.assertIsInstance(qr, str)
        self.assertTrue(len(qr) > 0)


class LecturaModelTest(BaseModelTestCase):
    def test_creacion_lectura(self):
        self.assertEqual(self.lectura.valor, 22.5)
        self.assertFalse(self.lectura.es_alerta)

    def test_str_lectura(self):
        s = str(self.lectura)
        self.assertIn('22.5', s)

    def test_lectura_genera_alerta(self):
        lectura_alerta = Lectura.objects.create(
            sensor=self.sensor,
            valor=40.0,
            fecha_hora=timezone.now(),
        )
        self.assertTrue(lectura_alerta.es_alerta)

    def test_lectura_inferior_genera_alerta(self):
        lectura_baja = Lectura.objects.create(
            sensor=self.sensor,
            valor=5.0,
            fecha_hora=timezone.now(),
        )
        self.assertTrue(lectura_baja.es_alerta)

    def test_ordenamiento_lecturas(self):
        Lectura.objects.create(sensor=self.sensor, valor=20.0, fecha_hora=timezone.now() - timedelta(hours=1))
        Lectura.objects.create(sensor=self.sensor, valor=21.0, fecha_hora=timezone.now())
        lecturas = list(self.sensor.lecturas.all())
        self.assertEqual(lecturas[0].valor, 21.0)


class AlertaModelTest(BaseModelTestCase):
    def test_creacion_alerta(self):
        alerta = Alerta.objects.create(
            sensor=self.sensor,
            lectura=self.lectura,
            tipo_alerta='alto',
            severidad='warning',
            mensaje='Temperatura alta',
            valor_detectado=40.0,
        )
        self.assertFalse(alerta.resuelta)

    def test_alerta_resuelta(self):
        alerta = Alerta.objects.create(
            sensor=self.sensor,
            lectura=self.lectura,
            tipo_alerta='alto',
            severidad='info',
            mensaje='Test',
            valor_detectado=22.0,
        )
        alerta.resolver(self.user, notas='Resuelto manualmente')
        alerta.refresh_from_db()
        self.assertTrue(alerta.resuelta)


class MantenimientoModelTest(BaseModelTestCase):
    def test_creacion_mantenimiento(self):
        m = Mantenimiento.objects.create(
            edificio=self.edificio,
            titulo='Reparar techo',
            descripcion='El techo tiene filtraciones',
            estado='pendiente',
            prioridad='alta',
            fecha_limite=timezone.now().date() + timedelta(days=7),
        )
        self.assertEqual(m.estado, 'pendiente')


class EquipoModelTest(BaseModelTestCase):
    def test_creacion_equipo(self):
        e = Equipo.objects.create(
            nombre='Equipo de restoration',
            descripcion='Equipo especializado',
        )
        self.assertEqual(e.nombre, 'Equipo de restoration')


class AuditLogTest(BaseModelTestCase):
    def test_registrar_log(self):
        AuditLog.registrar(
            self.user, 'crear', 'Edificio', str(self.edificio.id),
            'Creo edificio de prueba'
        )
        logs = AuditLog.objects.filter(usuario=self.user)
        self.assertEqual(logs.count(), 1)


class NotificacionTest(BaseModelTestCase):
    def test_creacion_notificacion(self):
        n = Notificacion.objects.create(
            usuario=self.user,
            titulo='Nueva alerta',
            mensaje='Se detecto una anomalia',
            tipo='alerta',
        )
        self.assertFalse(n.leida)


class AnalisisIATest(BaseModelTestCase):
    def test_creacion_analisis(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = SimpleUploadedFile('test.jpg', b'\xff\xd8\xff\xe0' + b'\x00' * 100, content_type='image/jpeg')
        a = AnalisisIA.objects.create(
            edificio=self.edificio,
            imagen=img,
            titulo='Analisis estructural',
            confianza=0.95,
        )
        self.assertEqual(a.confianza, 0.95)


class DonacionTest(BaseModelTestCase):
    def test_creacion_donacion(self):
        d = Donacion.objects.create(
            edificio=self.edificio,
            donador_nombre='Maria Lopez',
            donador_email='maria@test.com',
            monto=150.00,
            moneda='EUR',
            donador_mensaje='Para la restauracion',
        )
        self.assertEqual(d.monto, 150.00)


class SeguroTest(BaseModelTestCase):
    def test_creacion_seguro(self):
        s = Seguro.objects.create(
            edificio=self.edificio,
            compania='Seguros SA',
            poliza_numero='POL-001',
            tipo='todo_riesgo',
            cobertura_monto=100000.00,
            prima_anual=5000.00,
            fecha_inicio=timezone.now().date(),
            fecha_fin=timezone.now().date() + timedelta(days=365),
        )
        self.assertEqual(s.poliza_numero, 'POL-001')


class VoluntarioTest(BaseModelTestCase):
    def test_creacion_voluntario(self):
        v = Voluntario.objects.create(
            usuario=self.user,
            habilidades='Pintura, carpinteria',
            estado='activo',
        )
        self.assertEqual(v.estado, 'activo')


class AuthViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    @mock_context
    def test_login_view(self, *args):
        response = self.client.get(reverse('monitor:login'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_login_post(self, *args):
        response = self.client.post(reverse('monitor:login'), {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.assertIn(response.status_code, [200, 302])

    @mock_context
    def test_register_view(self, *args):
        response = self.client.get(reverse('monitor:register'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_auth(self):
        response = self.client.get(reverse('monitor:dashboard'))
        self.assertIn(response.status_code, [302, 403])

    def test_logout(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('monitor:logout'))
        self.assertIn(response.status_code, [200, 302])


class EdificioViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_edificio_list(self, *args):
        response = self.client.get(reverse('monitor:edificio_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_edificio_detail(self, *args):
        response = self.client.get(reverse('monitor:edificio_detail', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_edificio_create(self, *args):
        response = self.client.get(reverse('monitor:edificio_create'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_edificio_update(self, *args):
        response = self.client.get(reverse('monitor:edificio_update', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_mapa_global(self, *args):
        response = self.client.get(reverse('monitor:mapa_global'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_comparativa(self, *args):
        response = self.client.get(reverse('monitor:comparativa'))
        self.assertEqual(response.status_code, 200)


class SensorViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_sensor_detail(self, *args):
        response = self.client.get(reverse('monitor:sensor_detail', kwargs={'pk': self.sensor.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_lectura_create(self, *args):
        response = self.client.get(reverse('monitor:lectura_create', kwargs={'sensor_pk': self.sensor.pk}))
        self.assertEqual(response.status_code, 200)


class AlertaViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        self.alerta = Alerta.objects.create(
            sensor=self.sensor,
            lectura=self.lectura,
            tipo_alerta='alto',
            severidad='warning',
            mensaje='Test alerta',
            valor_detectado=40.0,
        )

    @mock_context
    def test_alerta_list(self, *args):
        response = self.client.get(reverse('monitor:alerta_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_alerta_resolver(self, *args):
        response = self.client.get(reverse('monitor:alerta_resolver', kwargs={'pk': self.alerta.pk}))
        self.assertEqual(response.status_code, 200)


class IAViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_analisis_ia_list(self, *args):
        response = self.client.get(reverse('monitor:analisis_ia_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_predicciones_list(self, *args):
        response = self.client.get(reverse('monitor:predicciones_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_chatbot_ia(self, *args):
        response = self.client.get(reverse('monitor:chatbot_ia'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_recomendaciones_ia(self, *args):
        response = self.client.get(reverse('monitor:recomendaciones_ia', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_anomalias_list(self, *args):
        response = self.client.get(reverse('monitor:anomalias_list'))
        self.assertEqual(response.status_code, 200)


class DashboardViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_dashboard(self, *args):
        response = self.client.get(reverse('monitor:dashboard'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_tiempo_real(self, *args):
        response = self.client.get(reverse('monitor:dashboard_tiempo_real'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_dashboard_energia(self, *args):
        response = self.client.get(reverse('monitor:dashboard_energia'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_dashboard_seguros(self, *args):
        response = self.client.get(reverse('monitor:dashboard_seguros'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_dashboard_legal(self, *args):
        response = self.client.get(reverse('monitor:dashboard_legal'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_dashboard_inversores(self, *args):
        response = self.client.get(reverse('monitor:dashboard_inversores'))
        self.assertEqual(response.status_code, 200)


class FinancieroViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_panel_financiero(self, *args):
        response = self.client.get(reverse('monitor:panel_financiero'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_ingresos_list(self, *args):
        response = self.client.get(reverse('monitor:ingreso_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_gastos_list(self, *args):
        response = self.client.get(reverse('monitor:gasto_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_facturas_list(self, *args):
        response = self.client.get(reverse('monitor:factura_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_nominas_list(self, *args):
        response = self.client.get(reverse('monitor:nomina_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_presupuestos_list(self, *args):
        response = self.client.get(reverse('monitor:presupuesto_list'))
        self.assertEqual(response.status_code, 200)


class KanbanViewsTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_kanban(self, *args):
        response = self.client.get(reverse('monitor:kanban'))
        self.assertEqual(response.status_code, 200)


class AdvancedFeaturesTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @mock_context
    def test_visor_3d(self, *args):
        response = self.client.get(reverse('monitor:visor_3d', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_mapa_calor(self, *args):
        response = self.client.get(reverse('monitor:mapa_calor', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_huella_co2(self, *args):
        response = self.client.get(reverse('monitor:huella_co2', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_portal_educativo(self, *args):
        response = self.client.get(reverse('monitor:portal_educativo'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_voluntarios_list(self, *args):
        response = self.client.get(reverse('monitor:voluntarios_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_ranking_global(self, *args):
        response = self.client.get(reverse('monitor:ranking_global'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_gamificacion(self, *args):
        response = self.client.get(reverse('monitor:gamificacion'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_calendario(self, *args):
        response = self.client.get(reverse('monitor:calendario'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_tareas_pendientes(self, *args):
        response = self.client.get(reverse('monitor:tareas_pendientes'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_buscador_global(self, *args):
        response = self.client.get(reverse('monitor:buscador_global'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_audit_log(self, *args):
        response = self.client.get(reverse('monitor:audit_log'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_herramientas_list(self, *args):
        response = self.client.get(reverse('monitor:herramienta_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_galeria_list(self, *args):
        response = self.client.get(reverse('monitor:galeria_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_donacion_list(self, *args):
        response = self.client.get(reverse('monitor:donacion_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_seguro_list(self, *args):
        response = self.client.get(reverse('monitor:seguro_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_energia_list(self, *args):
        response = self.client.get(reverse('monitor:eficiencia_energetica_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_legal_list(self, *args):
        response = self.client.get(reverse('monitor:cumplimiento_legal_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_blockchain_list(self, *args):
        response = self.client.get(reverse('monitor:certificado_blockchain_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_tour_virtual_list(self, *args):
        response = self.client.get(reverse('monitor:tour_virtual_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_evento_list(self, *args):
        response = self.client.get(reverse('monitor:evento_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_tienda_list(self, *args):
        response = self.client.get(reverse('monitor:tienda_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_reporte_ciudadano_list(self, *args):
        response = self.client.get(reverse('monitor:reporte_ciudadano_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_mantenimiento_list(self, *args):
        response = self.client.get(reverse('monitor:mantenimiento_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_equipo_list(self, *args):
        response = self.client.get(reverse('monitor:equipo_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_mantenimiento_predictivo(self, *args):
        response = self.client.get(reverse('monitor:mantenimiento_predictivo'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_resumen_diario(self, *args):
        response = self.client.get(reverse('monitor:resumen_diario'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_notificaciones(self, *args):
        response = self.client.get(reverse('monitor:notificaciones'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_configurar_email(self, *args):
        response = self.client.get(reverse('monitor:configurar_email'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_reportes_automaticos(self, *args):
        response = self.client.get(reverse('monitor:reportes_automaticos'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_backup(self, *args):
        response = self.client.get(reverse('monitor:backup'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_sms_config(self, *args):
        response = self.client.get(reverse('monitor:sms_config'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_whatsapp_config(self, *args):
        response = self.client.get(reverse('monitor:whatsapp_config'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_notificaciones_push(self, *args):
        response = self.client.get(reverse('monitor:notificaciones_push'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_rbac(self, *args):
        response = self.client.get(reverse('monitor:rbac'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_webhooks(self, *args):
        response = self.client.get(reverse('monitor:webhooks'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_idiomas(self, *args):
        response = self.client.get(reverse('monitor:idiomas'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_mapa_reportes(self, *args):
        response = self.client.get(reverse('monitor:mapa_reportes'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_comparativa_periodos(self, *args):
        response = self.client.get(reverse('monitor:comparativa_periodos'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_comparativa_ciudades(self, *args):
        response = self.client.get(reverse('monitor:comparativa_ciudades'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_digital_twin(self, *args):
        response = self.client.get(reverse('monitor:digital_twin', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_generar_qr(self, *args):
        response = self.client.get(reverse('monitor:generar_qr', kwargs={'pk': self.edificio.pk}))
        self.assertIn(response.status_code, [200, 302])

    @mock_context
    def test_generar_pdf(self, *args):
        response = self.client.get(reverse('monitor:generar_pdf', kwargs={'pk': self.edificio.pk}))
        self.assertIn(response.status_code, [200, 302])

    @mock_context
    def test_calculadora_roi(self, *args):
        response = self.client.get(reverse('monitor:calculadora_roi', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_calculadora_restauracion(self, *args):
        response = self.client.get(reverse('monitor:calculadora_restauracion', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_modo_emergencia(self, *args):
        response = self.client.get(reverse('monitor:modo_emergencia', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_timeline_historico(self, *args):
        response = self.client.get(reverse('monitor:timeline_historico_list', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_inspeccion_list(self, *args):
        response = self.client.get(reverse('monitor:inspeccion_list', kwargs={'edificio_pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_documento_list(self, *args):
        response = self.client.get(reverse('monitor:documento_list', kwargs={'edificio_pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_comentarios(self, *args):
        response = self.client.get(reverse('monitor:comentarios', kwargs={'edificio_pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_recordatorios(self, *args):
        response = self.client.get(reverse('monitor:recordatorios'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_exportar_multiples(self, *args):
        response = self.client.get(reverse('monitor:exportar_multiples'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_fotos_inspeccion(self, *args):
        response = self.client.get(reverse('monitor:foto_inspeccion_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_citas(self, *args):
        response = self.client.get(reverse('monitor:cita_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_contratos(self, *args):
        response = self.client.get(reverse('monitor:contrato_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_inventario(self, *args):
        response = self.client.get(reverse('monitor:inventario_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_bitacora(self, *args):
        response = self.client.get(reverse('monitor:bitacora_list'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_analisis_predictivo_avanzado(self, *args):
        response = self.client.get(reverse('monitor:analisis_predictivo_avanzado', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_crear_prediccion(self, *args):
        response = self.client.get(reverse('monitor:crear_prediccion', kwargs={'pk': self.edificio.pk}))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_cambiar_idioma(self, *args):
        response = self.client.post(reverse('monitor:cambiar_idioma'), {'idioma': 'en'})
        self.assertIn(response.status_code, [200, 302])

    @mock_context
    def test_dashboard_personalizado(self, *args):
        response = self.client.get(reverse('monitor:dashboard_personalizado'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_busqueda_avanzada(self, *args):
        response = self.client.get(reverse('monitor:busqueda_avanzada'))
        self.assertEqual(response.status_code, 200)

    @mock_context
    def test_notificaciones_push(self, *args):
        response = self.client.get(reverse('monitor:notificaciones_push'))
        self.assertEqual(response.status_code, 200)


class APITest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_api_dashboard(self):
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_api_estadisticas(self):
        response = self.client.get('/api/v1/estadisticas/')
        self.assertEqual(response.status_code, 200)

    def test_api_edificios(self):
        response = self.client.get('/api/v1/edificios/')
        self.assertEqual(response.status_code, 200)

    def test_api_sensores(self):
        response = self.client.get('/api/v1/sensores/')
        self.assertEqual(response.status_code, 200)

    def test_api_lecturas(self):
        response = self.client.get('/api/v1/lecturas/')
        self.assertEqual(response.status_code, 200)

    def test_api_alertas(self):
        response = self.client.get('/api/v1/alertas/')
        self.assertEqual(response.status_code, 200)

    def test_api_lecturas_recientes(self):
        response = self.client.get('/api/v1/lecturas/recientes/')
        self.assertEqual(response.status_code, 200)

    def test_api_ultimas_lecturas_sensor(self):
        response = self.client.get(f'/api/sensor/{self.sensor.pk}/lecturas/')
        self.assertEqual(response.status_code, 200)

    def test_api_resumen_edificio(self):
        response = self.client.get(f'/api/edificio/{self.edificio.pk}/resumen/')
        self.assertEqual(response.status_code, 200)


class SwaggerTest(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_swagger_ui(self):
        response = self.client.get('/swagger/')
        self.assertEqual(response.status_code, 200)

    def test_redoc(self):
        response = self.client.get('/redoc/')
        self.assertEqual(response.status_code, 200)

    def test_schema_json(self):
        response = self.client.get('/swagger.json')
        self.assertEqual(response.status_code, 200)


class CeleryTasksTest(BaseModelTestCase):
    def test_verificar_alertas_task(self):
        from .tasks import verificar_alertas_task
        result = verificar_alertas_task.delay()
        self.assertIsNotNone(result.id)

    def test_generar_reporte_semanal_task(self):
        from .tasks import generar_reporte_semanal_task
        result = generar_reporte_semanal_task.delay()
        self.assertIsNotNone(result.id)

    def test_backup_database_task(self):
        from .tasks import backup_database_task
        result = backup_database_task.delay()
        self.assertIsNotNone(result.id)

    def test_mantenimiento_predictivo_task(self):
        from .tasks import mantenimiento_predictivo_task
        result = mantenimiento_predictivo_task.delay()
        self.assertIsNotNone(result.id)

    def test_limpiar_datos_antiguos_task(self):
        from .tasks import limpiar_datos_antiguos_task
        result = limpiar_datos_antiguos_task.delay(dias=30)
        self.assertIsNotNone(result.id)
