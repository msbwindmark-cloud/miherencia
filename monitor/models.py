import uuid
import qrcode
import io
import base64
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings


class Edificio(models.Model):
    CATEGORIA_CHOICES = [
        ('iglesia', 'Iglesia / Catedral'),
        ('museo', 'Museo'),
        ('monumento', 'Monumento'),
        ('casa_historica', 'Casa Histórica'),
        ('archivo', 'Archivo / Biblioteca'),
        ('otro', 'Otro Patrimonio'),
    ]

    ESTADO_CHOICES = [
        ('excelente', 'Excelente'),
        ('bueno', 'Bueno'),
        ('regular', 'Regular'),
        ('malo', 'Malo'),
        ('critico', 'Crítico'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Edificio')
    direccion = models.CharField(max_length=300, verbose_name='Dirección')
    ciudad = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='monumento')
    descripcion = models.TextField(blank=True, verbose_name='Descripción histórica')
    anno_construccion = models.PositiveIntegerField(null=True, blank=True, verbose_name='Año de construcción')
    proteccion_oficial = models.BooleanField(default=False, verbose_name='Protección oficial (Bien de Interés Cultural)')
    imagen_principal = models.ImageField(upload_to='edificios/', null=True, blank=True)
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='edificios')
    estado_general = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='regular')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Edificio Patrimonial'
        verbose_name_plural = 'Edificios Patrimoniales'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.ciudad})'

    def get_absolute_url(self):
        return reverse('monitor:edificio_detail', kwargs={'pk': self.pk})

    @property
    def num_sensores(self):
        return self.sensores.filter(activo=True).count()

    @property
    def ultima_lectura(self):
        lectura = Lectura.objects.filter(sensor__edificio=self).order_by('-fecha_hora').first()
        return lectura

    @property
    def alertas_activas(self):
        return Alerta.objects.filter(sensor__edificio=self, resuelta=False).count()

    @property
    def salud_score(self):
        lecturas = Lectura.objects.filter(sensor__edificio=self).select_related('sensor').order_by('-fecha_hora')[:100]
        if not lecturas:
            return 0
        puntuaciones = []
        for l in lecturas:
            s = 100
            if l.sensor.tipo == 'temperatura':
                if l.valor < 10 or l.valor > 30:
                    s -= 30
                elif l.valor < 15 or l.valor > 25:
                    s -= 10
            elif l.sensor.tipo == 'humedad':
                if l.valor < 30 or l.valor > 80:
                    s -= 30
                elif l.valor < 40 or l.valor > 70:
                    s -= 10
            elif l.sensor.tipo == 'vibracion':
                if l.valor > 5:
                    s -= 40
                elif l.valor > 2:
                    s -= 20
            puntuaciones.append(s)
        return round(sum(puntuaciones) / len(puntuaciones))


class Sensor(models.Model):
    TIPO_CHOICES = [
        ('temperatura', 'Temperatura'),
        ('humedad', 'Humedad'),
        ('vibracion', 'Vibración'),
        ('luz', 'Luz / Radiación UV'),
        ('co2', 'CO₂'),
        ('ruido', 'Ruido'),
        ('grieta', 'Monitor de Grietas'),
        ('presion', 'Presión Atmosférica'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='sensores')
    nombre = models.CharField(max_length=150, verbose_name='Nombre del Sensor')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    ubicacionDescripcion = models.CharField(max_length=300, verbose_name='Ubicación en el edificio', help_text='Ej: "Nave lateral derecha, techos a 3m"')
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    umbral_min = models.FloatField(null=True, blank=True, verbose_name='Umbral Mínimo')
    umbral_max = models.FloatField(null=True, blank=True, verbose_name='Umbral Máximo')
    unidad_medida = models.CharField(max_length=20, default='unidades')
    activo = models.BooleanField(default=True)
    fecha_instalacion = models.DateField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sensor'
        verbose_name_plural = 'Sensores'
        ordering = ['edificio', 'tipo']

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()}) - {self.edificio.nombre}'

    def get_absolute_url(self):
        return reverse('monitor:sensor_detail', kwargs={'pk': self.pk})

    @property
    def ultima_lectura(self):
        return self.lecturas.order_by('-fecha_hora').first()

    @property
    def lecturas_hoy(self):
        hoy = timezone.now().date()
        return self.lecturas.filter(fecha_hora__date=hoy).count()

    @property
    def qr_code_b64(self):
        url = f'{settings.MEDIA_URL}sensores/qr_{self.id}.png'
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f'https://smartheritage.com/sensor/{self.id}/')
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()


class SensorFoto(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='fotos')
    imagen = models.ImageField(upload_to='sensores/fotos/')
    descripcion = models.CharField(max_length=300, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto del Sensor'
        verbose_name_plural = 'Fotos de Sensores'

    def __str__(self):
        return f'Foto de {self.sensor.nombre} - {self.fecha_subida}'


class Lectura(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='lecturas')
    valor = models.FloatField(verbose_name='Valor medido')
    fecha_hora = models.DateTimeField(default=timezone.now, verbose_name='Fecha y Hora')
    es_alerta = models.BooleanField(default=False, verbose_name='Generó alerta')

    class Meta:
        verbose_name = 'Lectura'
        verbose_name_plural = 'Lecturas'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f'{self.sensor.nombre}: {self.valor} {self.sensor.unidad_medida} ({self.fecha_hora})'

    def save(self, *args, **kwargs):
        sensor = self.sensor
        if sensor.umbral_min is not None and self.valor < sensor.umbral_min:
            self.es_alerta = True
        if sensor.umbral_max is not None and self.valor > sensor.umbral_max:
            self.es_alerta = True
        super().save(*args, **kwargs)
        if self.es_alerta:
            Alerta.objects.get_or_create(
                sensor=sensor,
                lectura=self,
                resuelta=False,
                defaults={
                    'tipo_alerta': self._determinar_tipo_alerta(),
                    'mensaje': self._generar_mensaje(),
                    'valor_detectado': self.valor,
                }
            )

    def _determinar_tipo_alerta(self):
        if self.sensor.umbral_min and self.valor < self.sensor.umbral_min:
            return 'bajo'
        return 'alto'

    def _generar_mensaje(self):
        t = self.sensor.get_tipo_display()
        if self._determinar_tipo_alerta() == 'bajo':
            return f'{t}: valor {self.valor} {self.sensor.unidad_medida} por debajo del mínimo ({self.sensor.umbral_min})'
        return f'{t}: valor {self.valor} {self.sensor.unidad_medida} por encima del máximo ({self.sensor.umbral_max})'


class Alerta(models.Model):
    SEVERIDAD_CHOICES = [
        ('info', 'Informativa'),
        ('warning', 'Advertencia'),
        ('critical', 'Crítica'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='alertas')
    lectura = models.ForeignKey(Lectura, on_delete=models.SET_NULL, null=True, related_name='alertas')
    tipo_alerta = models.CharField(max_length=10, choices=[('bajo', 'Bajo umbral'), ('alto', 'Sobre umbral')])
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default='warning')
    mensaje = models.TextField()
    valor_detectado = models.FloatField()
    resuelta = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notas_resolucion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'[{self.get_severidad_display()}] {self.sensor.nombre} - {self.mensaje[:60]}'

    def resolver(self, usuario, notas=''):
        self.resuelta = True
        self.fecha_resolucion = timezone.now()
        self.resuelta_por = usuario
        self.notas_resolucion = notas
        self.save()

    def save(self, *args, **kwargs):
        if self.valor_detectado and self.sensor:
            diff_alto = abs(self.valor_detectado - (self.sensor.umbral_max or 0)) if self.sensor.umbral_max else 0
            diff_bajo = abs(self.valor_detectado - (self.sensor.umbral_min or 0)) if self.sensor.umbral_min else 0
            max_diff = max(diff_alto, diff_bajo)
            if max_diff > 20:
                self.severidad = 'critical'
            elif max_diff > 10:
                self.severidad = 'warning'
            else:
                self.severidad = 'info'
        super().save(*args, **kwargs)


class Informe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='informes')
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    periodo_desde = models.DateField()
    periodo_hasta = models.DateField()
    archivo_pdf = models.FileField(upload_to='informes/pdf/', null=True, blank=True)
    archivo_excel = models.FileField(upload_to='informes/excel/', null=True, blank=True)

    class Meta:
        verbose_name = 'Informe'
        verbose_name_plural = 'Informes'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre}'

    def get_absolute_url(self):
        return reverse('monitor:informe_detail', kwargs={'pk': self.pk})


class PerfilUsuario(models.Model):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('conservador', 'Conservador'),
        ('tecnico', 'Técnico'),
        ('visualizador', 'Visualizador'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='visualizador')
    telefono = models.CharField(max_length=20, blank=True)
    organizacion = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    notificaciones_email = models.BooleanField(default=True)
    edificios_asignados = models.ManyToManyField(Edificio, blank=True, related_name='usuarios_asignados')

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'

    def __str__(self):
        return f'{self.user.username} ({self.get_rol_display()})'


class AuditLog(models.Model):
    ACCION_CHOICES = [
        ('crear', 'Crear'),
        ('editar', 'Editar'),
        ('eliminar', 'Eliminar'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('resolver_alerta', 'Resolver Alerta'),
        ('exportar', 'Exportar'),
        ('importar', 'Importar'),
        ('generar_informe', 'Generar Informe'),
        ('asignar_usuario', 'Asignar Usuario'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    modelo = models.CharField(max_length=100, verbose_name='Modelo/Entidad')
    objeto_id = models.CharField(max_length=100, verbose_name='ID del Objeto', blank=True)
    descripcion = models.TextField(verbose_name='Descripción de la acción')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    datos_previos = models.JSONField(null=True, blank=True, verbose_name='Datos Anteriores')
    datos_nuevos = models.JSONField(null=True, blank=True, verbose_name='Datos Nuevos')

    class Meta:
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'
        ordering = ['-fecha']

    def __str__(self):
        return f'[{self.get_accion_display()}] {self.usuario} - {self.modelo} - {self.fecha}'

    @classmethod
    def registrar(cls, usuario, accion, modelo, objeto_id='', descripcion='', ip=None, previos=None, nuevos=None):
        return cls.objects.create(
            usuario=usuario, accion=accion, modelo=modelo,
            objeto_id=str(objeto_id), descripcion=descripcion,
            ip_address=ip, datos_previos=previos, datos_nuevos=nuevos
        )


class Equipo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Equipo')
    descripcion = models.TextField(blank=True)
    edificios = models.ManyToManyField(Edificio, blank=True, related_name='equipos')
    miembros = models.ManyToManyField(User, blank=True, related_name='equipos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'

    def __str__(self):
        return self.nombre

    @property
    def num_miembros(self):
        return self.miembros.count()

    @property
    def num_edificios(self):
        return self.edificios.count()


class Mantenimiento(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='mantenimientos')
    sensor = models.ForeignKey(Sensor, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos_asignados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre}'

    @property
    def dias_restantes(self):
        if self.fecha_limite:
            delta = self.fecha_limite - timezone.now().date()
            return delta.days
        return None


class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('alerta', 'Alerta'),
        ('mantenimiento', 'Mantenimiento'),
        ('sistema', 'Sistema'),
        ('equipo', 'Equipo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sistema')
    leida = models.BooleanField(default=False)
    url_destino = models.CharField(max_length=300, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} - {self.usuario.username}'


class ChatMensaje(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='chat_mensajes')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_mensajes')
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    editado = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Mensaje de Chat'
        verbose_name_plural = 'Mensajes de Chat'
        ordering = ['fecha']

    def __str__(self):
        return f'{self.autor.username}: {self.texto[:50]}'


class PuntoGamificacion(models.Model):
    ACCION_CHOICES = [
        ('resolver_alerta', 'Resolver Alerta'),
        ('crear_edificio', 'Crear Edificio'),
        ('crear_sensor', 'Crear Sensor'),
        ('registrar_lectura', 'Registrar Lectura'),
        ('generar_informe', 'Generar Informe'),
        ('login_diario', 'Login Diario'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puntos')
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    puntos = models.PositiveIntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'Punto de Gamificación'
        verbose_name_plural = 'Puntos de Gamificación'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario.username}: +{self.puntos} por {self.get_accion_display()}'


class Logro(models.Model):
    ICONO_CHOICES = [
        ('trophy', 'Trofeo'), ('star', 'Estrella'), ('fire', 'Fuego'),
        ('gem', 'Gema'), ('crown', 'Corona'), ('bolt', 'Rayo'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    icono = models.CharField(max_length=20, choices=ICONO_CHOICES, default='trophy')
    puntos_necesarios = models.PositiveIntegerField()
    color = models.CharField(max_length=7, default='#d4a853')
    usuarios = models.ManyToManyField(User, blank=True, related_name='logros')

    class Meta:
        verbose_name = 'Logro'
        verbose_name_plural = 'Logros'
        ordering = ['puntos_necesarios']

    def __str__(self):
        return f'{self.nombre} ({self.puntos_necesarios} pts)'


class TimelineFoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='timeline_fotos')
    imagen = models.ImageField(upload_to='timeline/')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_toma = models.DateField(default=timezone.now)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = 'Foto Timeline'
        verbose_name_plural = 'Fotos Timeline'
        ordering = ['-fecha_toma']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre} ({self.fecha_toma})'


class ConfiguracionSMS(models.Model):
    account_sid = models.CharField(max_length=100, blank=True, verbose_name='Twilio Account SID')
    auth_token = models.CharField(max_length=100, blank=True, verbose_name='Twilio Auth Token')
    numero_origen = models.CharField(max_length=20, blank=True, verbose_name='Número Twilio')
    numeros_destino = models.TextField(blank=True, verbose_name='Números destino (uno por línea)')
    activo = models.BooleanField(default=False)
    alertas_criticas = models.BooleanField(default=True, verbose_name='Enviar alertas críticas por SMS')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Configuración SMS/WhatsApp'
        verbose_name_plural = 'Configuraciones SMS/WhatsApp'

    def __str__(self):
        return f'SMS Config (Activo: {self.activo})'

    def get_numeros_lista(self):
        return [n.strip() for n in self.numeros_destino.split('\n') if n.strip()]


# =============================================
# NUEVAS FUNCIONALIDADES - TODO LO NUEVO
# =============================================

class AnalisisIA(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]
    SEVERIDAD_CHOICES = [
        ('sin_dano', 'Sin Dano'),
        ('leve', 'Dano Leve'),
        ('moderado', 'Dano Moderado'),
        ('severo', 'Dano Severo'),
        ('critico', 'Dano Critico'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='analisis_ia')
    imagen = models.ImageField(upload_to='analisis_ia/')
    titulo = models.CharField(max_length=200, default='Analisis IA')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    severidad_detectada = models.CharField(max_length=20, choices=SEVERIDAD_CHOICES, default='sin_dano')
    confianza = models.FloatField(default=0, verbose_name='Confianza del modelo (%)')
    grietas_detectadas = models.PositiveIntegerField(default=0)
    areas_afectadas = models.JSONField(default=list, blank=True, verbose_name='Areas con dano')
    recomendaciones = models.TextField(blank=True, verbose_name='Recomendaciones de IA')
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Costo estimado reparacion')
    prioridad_ia = models.CharField(max_length=10, choices=[('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('urgente', 'Urgente')], default='baja')
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notas_analista = models.TextField(blank=True)
    fecha_analisis = models.DateTimeField(auto_now_add=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Analisis IA'
        verbose_name_plural = 'Analisis IA'
        ordering = ['-fecha_analisis']

    def __str__(self):
        return f'IA: {self.titulo} - {self.edificio.nombre} ({self.get_severidad_detectada_display()})'


class PrediccionML(models.Model):
    TIPO_CHOICES = [
        ('mantenimiento', 'Mantenimiento Preventivo'),
        ('deterioro', 'Prediccion de Deterioro'),
        ('fallo', 'Prediccion de Fallo'),
        ('coste', 'Estimacion de Costes'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='predicciones_ml')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    confianza = models.FloatField(default=0, verbose_name='Confianza del modelo (%)')
    fecha_predicha = models.DateField(verbose_name='Fecha estimada del evento')
    probabilidad = models.FloatField(default=0, verbose_name='Probabilidad de ocurrencia (%)')
    impacto_financiero = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    accion_recomendada = models.TextField(blank=True)
    datos_entrada = models.JSONField(default=dict, blank=True)
    resultado = models.JSONField(default=dict, blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Prediccion ML'
        verbose_name_plural = 'Predicciones ML'
        ordering = ['fecha_predicha']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo} ({self.probabilidad}%)'


class Donacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='donaciones')
    donador_nombre = models.CharField(max_length=200)
    donador_email = models.EmailField()
    donador_telefono = models.CharField(max_length=20, blank=True)
    donador_mensaje = models.TextField(blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default='EUR')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    es_anonima = models.BooleanField(default=False)
    es_recurrente = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    referencia_pago = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Donacion'
        verbose_name_plural = 'Donaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.donador_nombre} - {self.monto} {self.moneda} - {self.edificio.nombre}'


class ReporteCiudadano(models.Model):
    ESTADO_CHOICES = [
        ('nuevo', 'Nuevo'),
        ('revisado', 'Revisado'),
        ('en_progreso', 'En Progreso'),
        ('resuelto', 'Resuelto'),
        ('rechazado', 'Rechazado'),
    ]
    TIPO_CHOICES = [
        ('dano', 'Dano Estructural'),
        ('vandalismo', 'Vandalismo'),
        ('limpieza', 'Necesita Limpieza'),
        ('iluminacion', 'Problema de Iluminacion'),
        ('accesibilidad', 'Problema de Accesibilidad'),
        ('otro', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='reportes_ciudadanos')
    ciudadano_nombre = models.CharField(max_length=200)
    ciudadano_email = models.EmailField()
    ciudadano_telefono = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='reportes/', null=True, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='nuevo')
    respuesta_admin = models.TextField(blank=True)
    respondido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    votos = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Reporte Ciudadano'
        verbose_name_plural = 'Reportes Ciudadanos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre} ({self.get_estado_display()})'


class Seguro(models.Model):
    TIPO_CHOICES = [
        ('todo_riesgo', 'Todo Riesgo'),
        ('incendio', 'Incendio'),
        ('terremoto', 'Terremoto'),
        ('inundacion', 'Inundacion'),
        ('responsabilidad', 'Responsabilidad Civil'),
        ('otro', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='seguros')
    compania = models.CharField(max_length=200, verbose_name='Compania de Seguros')
    poliza_numero = models.CharField(max_length=100, verbose_name='Numero de Poliza')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cobertura_monto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto de Cobertura')
    prima_anual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Prima Anual')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    contacto_nombre = models.CharField(max_length=200, blank=True)
    contacto_telefono = models.CharField(max_length=20, blank=True)
    contacto_email = models.EmailField(blank=True)
    documento = models.FileField(upload_to='seguros/', null=True, blank=True)
    activo = models.BooleanField(default=True)
    renovacion_automatica = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguro'
        verbose_name_plural = 'Seguros'
        ordering = ['-fecha_fin']

    def __str__(self):
        return f'{self.compania} - {self.poliza_numero} - {self.edificio.nombre}'

    @property
    def dias_para_vencer(self):
        delta = self.fecha_fin - timezone.now().date()
        return delta.days

    @property
    def esta_vigente(self):
        today = timezone.now().date()
        return self.fecha_inicio <= today <= self.fecha_fin


class EficienciaEnergetica(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='eficiencia_energetica')
    fecha = models.DateField(default=timezone.now)
    consumo_electricidad = models.FloatField(default=0, verbose_name='Consumo electricidad (kWh)')
    consumo_gas = models.FloatField(default=0, verbose_name='Consumo gas (m3)')
    consumo_agua = models.FloatField(default=0, verbose_name='Consumo agua (litros)')
    produccion_solar = models.FloatField(default=0, verbose_name='Produccion solar (kWh)')
    emisiones_co2 = models.FloatField(default=0, verbose_name='Emisiones CO2 (kg)')
    temp_exterior = models.FloatField(null=True, blank=True)
    temp_interior = models.FloatField(null=True, blank=True)
    coste_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    certificado_energetico = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D'),('E','E'),('F','F'),('G','G')], default='D')
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Eficiencia Energetica'
        verbose_name_plural = 'Eficiencia Energetica'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.edificio.nombre} - {self.fecha} ({self.certificado_energetico})'


class CumplimientoLegal(models.Model):
    ESTADO_CHOICES = [
        ('cumple', 'Cumple'),
        ('no_cumple', 'No Cumple'),
        ('en_proceso', 'En Proceso'),
        ('exento', 'Exento'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='cumplimiento_legal')
    normativa = models.CharField(max_length=300, verbose_name='Nombre de la Normativa')
    referencia = models.CharField(max_length=100, verbose_name='Referencia legal')
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='en_proceso')
    fecha_inspeccion = models.DateField(null=True, blank=True)
    proxima_inspeccion = models.DateField(null=True, blank=True)
    documento_certificado = models.FileField(upload_to='legal/', null=True, blank=True)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cumplimiento Legal'
        verbose_name_plural = 'Cumplimiento Legal'
        ordering = ['proxima_inspeccion']

    def __str__(self):
        return f'{self.normativa} - {self.edificio.nombre} ({self.get_estado_display()})'


class CertificadoBlockchain(models.Model):
    TIPO_CHOICES = [
        ('propiedad', 'Certificado de Propiedad'),
        ('restauracion', 'Certificado de Restauracion'),
        ('inspeccion', 'Certificado de Inspeccion'),
        ('historico', 'Registro Historico'),
        ('nft', 'NFT Heritage'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='certificados_blockchain')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    hash_transaccion = models.CharField(max_length=200, verbose_name='Hash de Transaccion')
    direccion_wallet = models.CharField(max_length=100, verbose_name='Direccion Wallet')
    nft_token_id = models.CharField(max_length=100, blank=True, verbose_name='Token ID NFT')
    nft_url = models.URLField(blank=True, verbose_name='URL del NFT')
    metadatos = models.JSONField(default=dict, blank=True)
    emisor = models.ForeignKey(User, on_delete=models.CASCADE)
    validado = models.BooleanField(default=False)
    fecha_emision = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Certificado Blockchain'
        verbose_name_plural = 'Certificados Blockchain'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo}'


class TourVirtual(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='tours_virtuales')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    imagen_panoramica = models.ImageField(upload_to='tours/', null=True, blank=True)
    video_360 = models.URLField(blank=True, verbose_name='URL Video 360')
    coordenadas_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    coordenadas_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    puntos_interes = models.JSONField(default=list, blank=True, verbose_name='Puntos de Interes')
    activo = models.BooleanField(default=True)
    vistas = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tour Virtual'
        verbose_name_plural = 'Tours Virtuales'

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre}'


class VisitaQR(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='visitas_qr')
    visitante_nombre = models.CharField(max_length=200, blank=True)
    visitante_ip = models.GenericIPAddressField(null=True, blank=True)
    dispositivo = models.CharField(max_length=200, blank=True)
    idioma = models.CharField(max_length=10, default='es')
    fecha_visita = models.DateTimeField(auto_now_add=True)
    duracion_segundos = models.PositiveIntegerField(default=0)
    accion = models.CharField(max_length=50, default='escaneo_qr')

    class Meta:
        verbose_name = 'Visita QR'
        verbose_name_plural = 'Visitas QR'
        ordering = ['-fecha_visita']

    def __str__(self):
        return f'Visita QR: {self.edificio.nombre} - {self.fecha_visita}'


class Evento(models.Model):
    TIPO_CHOICES = [
        ('visita', 'Visita Guiada'),
        ('conferencia', 'Conferencia'),
        ('restauracion', 'Evento de Restauracion'),
        ('inauguracion', 'Inauguracion'),
        ('taller', 'Taller/Educacion'),
        ('otro', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='eventos')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    capacidad_maxima = models.PositiveIntegerField(default=50)
    precio = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    organizador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos_creados')
    participantes = models.ManyToManyField(User, blank=True, related_name='eventos_participacion')
    imagen = models.ImageField(upload_to='eventos/', null=True, blank=True)
    ubicacion_detalle = models.CharField(max_length=300, blank=True)
    activo = models.BooleanField(default=True)
    publicado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['fecha_inicio']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre}'

    @property
    def plazas_disponibles(self):
        return self.capacidad_maxima - self.participantes.count()

    @property
    def esta_lleno(self):
        return self.participantes.count() >= self.capacidad_maxima


class TiendaPatrimonio(models.Model):
    CATEGORIA_CHOICES = [
        ('reproduccion', 'Reproducciones'),
        ('libro', 'Libros'),
        ('arte', 'Arte'),
        ('souvenirs', 'Souvenirs'),
        ('exclusivo', 'Piezas Exclusivas'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='productos_tienda')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default='EUR')
    imagen = models.ImageField(upload_to='tienda/', null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    vendidos = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Producto Tienda'
        verbose_name_plural = 'Tienda Patrimonio'
        ordering = ['-destacado', '-vendidos']

    def __str__(self):
        return f'{self.nombre} - {self.precio} {self.moneda}'

    @property
    def agotado(self):
        return self.stock <= 0


class ChatMensajeIA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_ia')
    mensaje = models.TextField()
    respuesta = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chat IA'
        verbose_name_plural = 'Chats IA'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario.username}: {self.mensaje[:50]}'


class ComentarioEdificio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    fecha = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.autor.username}: {self.texto[:50]}'


class GaleriaFoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='galeria')
    titulo = models.CharField(max_length=200)
    imagen_antes = models.ImageField(upload_to='galeria/antes/')
    imagen_despues = models.ImageField(upload_to='galeria/despues/')
    descripcion = models.TextField(blank=True)
    fecha_antes = models.DateField(null=True, blank=True)
    fecha_despues = models.DateField(null=True, blank=True)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Galeria Antes/Despues'
        verbose_name_plural = 'Galeria Antes/Despues'

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre}'


class MedicionRuido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='mediciones_ruido')
    ubicacion = models.CharField(max_length=200)
    nivel_db = models.FloatField(verbose_name='Nivel en dB')
    fecha = models.DateTimeField(auto_now_add=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = 'Medicion de Ruido'
        verbose_name_plural = 'Mediciones de Ruido'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.ubicacion}: {self.nivel_db} dB'


class CalidadAire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='calidad_aire')
    co2 = models.FloatField(default=0, verbose_name='CO2 (ppm)')
    no2 = models.FloatField(default=0, verbose_name='NO2 (ug/m3)')
    pm25 = models.FloatField(default=0, verbose_name='PM2.5 (ug/m3)')
    pm10 = models.FloatField(default=0, verbose_name='PM10 (ug/m3)')
    o3 = models.FloatField(default=0, verbose_name='O3 (ug/m3)')
    calidad = models.CharField(max_length=20, default='buena')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Calidad del Aire'
        verbose_name_plural = 'Calidad del Aire'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.edificio.nombre} - CO2: {self.co2} ppm'


class BackupLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    archivo = models.CharField(max_length=500)
    tipo = models.CharField(max_length=20, default='completo')
    tamano_kb = models.FloatField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)
    exitoso = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Backup'
        verbose_name_plural = 'Backups'
        ordering = ['-fecha']

    def __str__(self):
        return f'Backup {self.tipo} - {self.fecha}'


class DocumentoEdificio(models.Model):
    CATEGORIA_CHOICES = [
        ('plano', 'Plano'),
        ('permiso', 'Permiso'),
        ('contrato', 'Contrato'),
        ('informe_tecnico', 'Informe Tecnico'),
        ('historico', 'Documento Historico'),
        ('fotografia', 'Fotografia'),
        ('otro', 'Otro'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='documentos')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    archivo = models.FileField(upload_to='documentos/')
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_documento = models.DateField(null=True, blank=True)
    tamaño_kb = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre}'


class Herramienta(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_uso', 'En Uso'),
        ('mantenimiento', 'En Mantenimiento'),
        ('dada_baja', 'Dada de Baja'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=100)
    numero_serie = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    edificio_asignado = models.ForeignKey(Edificio, on_delete=models.SET_NULL, null=True, blank=True, related_name='herramientas')
    ubicacion = models.CharField(max_length=200, blank=True)
    fecha_compra = models.DateField(null=True, blank=True)
    fecha_ultimo_mantenimiento = models.DateField(null=True, blank=True)
    proximo_mantenimiento = models.DateField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foto = models.ImageField(upload_to='herramientas/', null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Herramienta'
        verbose_name_plural = 'Herramientas'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_estado_display()})'


class FormularioInspeccion(models.Model):
    RESULTADO_CHOICES = [
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('pendiente', 'Pendiente'),
        ('con_observaciones', 'Con Observaciones'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='inspecciones')
    titulo = models.CharField(max_length=200)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_inspeccion = models.DateField(default=timezone.now)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default='pendiente')
    checklist = models.JSONField(default=list, verbose_name='Checklist items')
    observaciones = models.TextField(blank=True)
    firma_digital = models.TextField(blank=True, verbose_name='Firma digital (base64)')
    foto_evidencia = models.ImageField(upload_to='inspecciones/', null=True, blank=True)
    proxima_inspeccion = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Inspeccion'
        verbose_name_plural = 'Inspecciones'
        ordering = ['-fecha_inspeccion']

    def __str__(self):
        return f'{self.titulo} - {self.edificio.nombre} ({self.get_resultado_display()})'


class TimelineHistorico(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='timeline_historico')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_evento = models.DateField()
    categoria = models.CharField(max_length=50, default='restauracion')
    imagen = models.ImageField(upload_to='timeline_historico/', null=True, blank=True)
    fuente = models.CharField(max_length=300, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento Historico'
        verbose_name_plural = 'Timeline Historico'
        ordering = ['fecha_evento']

    def __str__(self):
        return f'{self.fecha_evento.year}: {self.titulo}'


class RecomendacionIA(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='recomendaciones')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    categoria = models.CharField(max_length=50)
    confianza = models.FloatField(default=0)
    accion_recomendada = models.TextField()
    implementada = models.BooleanField(default=False)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recomendacion IA'
        verbose_name_plural = 'Recomendaciones IA'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f'{self.titulo} ({self.get_prioridad_display()})'


class AnomaliaDetectada(models.Model):
    TIPO_CHOICES = [
        ('temperatura', 'Anomalia de Temperatura'),
        ('humedad', 'Anomalia de Humedad'),
        ('vibracion', 'Anomalia de Vibracion'),
        ('estructural', 'Anomalia Estructural'),
        ('consumo', 'Anomalia de Consumo'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='anomalias')
    sensor = models.ForeignKey(Sensor, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    valor_esperado = models.FloatField(default=0)
    valor_detectado = models.FloatField(default=0)
    desviacion = models.FloatField(default=0)
    gravedad = models.CharField(max_length=10, choices=[('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta')])
    revisada = models.BooleanField(default=False)
    fecha_deteccion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anomalia Detectada'
        verbose_name_plural = 'Anomalias Detectadas'
        ordering = ['-fecha_deteccion']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo}'


class Voluntario(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('pendiente', 'Pendiente'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voluntariados')
    edificios = models.ManyToManyField(Edificio, blank=True, related_name='voluntarios')
    habilidades = models.TextField(blank=True, verbose_name='Habilidades y experiencia')
    disponibilidad = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    horas_voluntariado = models.FloatField(default=0)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Voluntario'
        verbose_name_plural = 'Voluntarios'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'{self.usuario.username} ({self.get_estado_display()})'


class ReporteAutomatico(models.Model):
    TIPO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='semanal')
    contenido = models.TextField()
    archivo_pdf = models.FileField(upload_to='reportes_automaticos/', null=True, blank=True)
    enviado = models.BooleanField(default=False)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Reporte Automatico'
        verbose_name_plural = 'Reportes Automaticos'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.fecha_generacion}'


class MantenimientoPredictivo(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='predicciones_mantenimiento')
    sensor = models.ForeignKey(Sensor, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    probabilidad_fallo = models.FloatField(default=0, verbose_name='Probabilidad de fallo (%)')
    dias_estimados = models.IntegerField(default=30, verbose_name='Dias hasta fallo estimado')
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    accion_recomendada = models.TextField()
    implementada = models.BooleanField(default=False)
    fecha_prediccion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mantenimiento Predictivo'
        verbose_name_plural = 'Mantenimientos Predictivos'
        ordering = ['-probabilidad_fallo']

    def __str__(self):
        return f'{self.titulo} ({self.probabilidad_fallo}%)'


class RegistroROI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='registros_roi')
    ahorro_energetico = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ahorro_multas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ahorro_restauraciones = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    donaciones_recibidas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    inversion_smartheritage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro ROI'
        verbose_name_plural = 'Registros ROI'
        ordering = ['-fecha']

    @property
    def total_ahorro(self):
        return self.ahorro_energetico + self.ahorro_multas + self.ahorro_restauraciones + self.donaciones_recibidas

    @property
    def roi_porcentaje(self):
        if self.inversion_smartheritage > 0:
            return ((self.total_ahorro - self.inversion_smartheritage) / self.inversion_smartheritage) * 100
        return 0

    def __str__(self):
        return f'ROI {self.edificio.nombre} - {self.fecha}'


class ConfiguracionIdioma(models.Model):
    IDIOMA_CHOICES = [
        ('es', 'Espanol'),
        ('en', 'English'),
        ('ar', 'العربية'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='idioma_config')
    idioma = models.CharField(max_length=5, choices=IDIOMA_CHOICES, default='es')

    class Meta:
        verbose_name = 'Configuracion de Idioma'
        verbose_name_plural = 'Configuraciones de Idioma'

    def __str__(self):
        return f'{self.usuario.username} - {self.get_idioma_display()}'


class ModoEmergencia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='modos_emergencia')
    activado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    motivo = models.TextField()
    email_enviado = models.BooleanField(default=False)
    pdf_generado = models.BooleanField(default=False)
    fecha_activacion = models.DateTimeField(auto_now_add=True)
    desactivado = models.BooleanField(default=False)
    fecha_desactivacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Modo Emergencia'
        verbose_name_plural = 'Modos de Emergencia'
        ordering = ['-fecha_activacion']

    def __str__(self):
        return f'EMERGENCIA - {self.edificio.nombre} ({self.fecha_activacion})'


class ComparativaCiudad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ciudad = models.CharField(max_length=100)
    edificio_tipo = models.CharField(max_length=100)
    media_salud = models.FloatField(default=0)
    media_sensores = models.IntegerField(default=0)
    media_alertas = models.IntegerField(default=0)
    total_edificios = models.IntegerField(default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comparativa Ciudad'
        verbose_name_plural = 'Comparativas Ciudad'
        ordering = ['ciudad']

    def __str__(self):
        return f'{self.ciudad} - {self.edificio_tipo}'


class CategoriaIngreso(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#28a745')

    class Meta:
        verbose_name = 'Categoria de Ingreso'
        verbose_name_plural = 'Categorias de Ingreso'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CategoriaGasto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#dc3545')

    class Meta:
        verbose_name = 'Categoria de Gasto'
        verbose_name_plural = 'Categorias de Gasto'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ingreso(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('cobrado', 'Cobrado'),
        ('cancelado', 'Cancelado'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='ingresos')
    categoria = models.ForeignKey(CategoriaIngreso, on_delete=models.SET_NULL, null=True, blank=True)
    concepto = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default='EUR')
    fecha = models.DateField()
    fecha_cobro = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    cliente_nombre = models.CharField(max_length=200, blank=True)
    cliente_email = models.EmailField(blank=True)
    cliente_nif = models.CharField(max_length=20, blank=True)
    recurrente = models.BooleanField(default=False)
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ingreso'
        verbose_name_plural = 'Ingresos'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.concepto} - {self.monto} EUR'


class Gasto(models.Model):
    FORMA_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('domiciliado', 'Domiciliado'),
        ('cheque', 'Cheque'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='gastos')
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.SET_NULL, null=True, blank=True)
    concepto = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default='EUR')
    fecha = models.DateField()
    fecha_pago = models.DateField(null=True, blank=True)
    pagado = models.BooleanField(default=False)
    proveedor = models.CharField(max_length=200, blank=True)
    proveedor_nif = models.CharField(max_length=20, blank=True)
    forma_pago = models.CharField(max_length=15, choices=FORMA_PAGO_CHOICES, default='transferencia')
    numero_factura_proveedor = models.CharField(max_length=50, blank=True)
    deducible = models.BooleanField(default=False, verbose_name='Deducible de IRPF')
    notas = models.TextField(blank=True)
    archivo_adjunto = models.FileField(upload_to='gastos/adjuntos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.concepto} - {self.monto} EUR'


class Factura(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]
    TIPO_CHOICES = [
        ('emitted', 'Emitida'),
        ('received', 'Recibida'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='emitted')
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='facturas')
    cliente_proveedor = models.CharField(max_length=200)
    cliente_nif = models.CharField(max_length=20, blank=True)
    cliente_direccion = models.TextField(blank=True)
    cliente_email = models.EmailField(blank=True)
    concepto = models.CharField(max_length=300)
    base_imponible = models.DecimalField(max_digits=12, decimal_places=2)
    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=21)
    importe_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='borrador')
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_pago = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True)
    archivo_pdf = models.FileField(upload_to='facturas/pdfs/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha_emision']

    def save(self, *args, **kwargs):
        self.importe_iva = self.base_imponible * self.porcentaje_iva / 100
        self.total = self.base_imponible + self.importe_iva
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.numero} - {self.cliente_proveedor} - {self.total} EUR'


class Nomina(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empleado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nominas')
    edificio = models.ForeignKey(Edificio, on_delete=models.SET_NULL, null=True, blank=True)
    salario_base = models.DecimalField(max_digits=10, decimal_places=2)
    complemento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Bonus/Incentivos')
    retenciones = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    seguridad_social = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    neto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    periodo = models.CharField(max_length=20, verbose_name='Periodo (Ej: Enero 2025)')
    fecha_pago = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    notas = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Nomina'
        verbose_name_plural = 'Nominas'
        ordering = ['-fecha_pago']

    def save(self, *args, **kwargs):
        self.neto = (self.salario_base + self.complemento + self.bonus) - self.retenciones - self.seguridad_social
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.empleado.username} - {self.periodo} - {self.neto} EUR'


class Presupuesto(models.Model):
    PERIODO_CHOICES = [
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='presupuestos')
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.SET_NULL, null=True, blank=True)
    monto_asignado = models.DecimalField(max_digits=12, decimal_places=2)
    monto_gastado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    periodo = models.CharField(max_length=15, choices=PERIODO_CHOICES, default='mensual')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    alerta_porcentaje = models.IntegerField(default=80, verbose_name='Alertar al % gastado')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        ordering = ['-fecha_inicio']

    @property
    def porcentaje_gastado(self):
        if self.monto_asignado > 0:
            return (self.monto_gastado / self.monto_asignado) * 100
        return 0

    @property
    def disponible(self):
        return self.monto_asignado - self.monto_gastado

    @property
    def estado_color(self):
        pct = self.porcentaje_gastado
        if pct >= 100: return '#dc3545'
        if pct >= self.alerta_porcentaje: return '#ffc107'
        return '#28a745'

    def __str__(self):
        return f'{self.nombre} ({self.get_periodo_display()}) - {self.monto_gastado}/{self.monto_asignado}'


class CuentaContable(models.Model):
    TIPO_CHOICES = [
        ('activo', 'Activo'),
        ('pasivo', 'Pasivo'),
        ('ingreso', 'Ingreso'),
        ('gasto', 'Gasto'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cuenta Contable'
        verbose_name_plural = 'Cuentas Contables'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class ChatAsistenteIA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_ia_historial')
    mensaje_usuario = models.TextField()
    respuesta_ia = models.TextField()
    edificio_contexto = models.ForeignKey(Edificio, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chat Asistente IA'
        verbose_name_plural = 'Chats Asistente IA'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario.username}: {self.mensaje_usuario[:50]}'


class DigitalTwin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.OneToOneField(Edificio, on_delete=models.CASCADE, related_name='digital_twin')
    modelo_3d_url = models.URLField(blank=True, help_text='URL del modelo GLB/GLTF')
    estado_color = models.CharField(max_length=7, default='#28a745')
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Digital Twin'
        verbose_name_plural = 'Digital Twins'

    def __str__(self):
        return f'Digital Twin: {self.edificio.nombre}'


class FotoInspeccion(models.Model):
    RESULTADO_CHOICES = [
        ('ok', 'Sin problemas'),
        ('grietas', 'Grietas detectadas'),
        ('humedad', 'Humedad detectada'),
        ('dano_estructural', 'Dano estructural'),
        ('desgaste', 'Desgaste general'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='fotos_inspeccion')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='inspeccion_ia/')
    resultado_ia = models.CharField(max_length=20, choices=RESULTADO_CHOICES, blank=True)
    confianza_ia = models.FloatField(default=0)
    detalles_ia = models.TextField(blank=True)
    subida_por = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto Inspeccion IA'
        verbose_name_plural = 'Fotos Inspeccion IA'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.titulo} - {self.get_resultado_ia_display()}'


class Cita(models.Model):
    ESTADO_CHOICES = [
        ('programada', 'Programada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('reprogramada', 'Reprogramada'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='citas')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    participantes = models.ManyToManyField(User, blank=True, related_name='citas')
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    ubicacion = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='programada')
    recordatorio_horas = models.IntegerField(default=24, verbose_name='Recordatorio (horas antes)')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['fecha_inicio']

    def __str__(self):
        return f'{self.titulo} - {self.fecha_inicio}'


class TareaKanban(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('revision', 'En Revision'),
        ('completada', 'Completada'),
    ]
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='tareas_kanban')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tareas_asignadas')
    fecha_limite = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    orden = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Tarea Kanban'
        verbose_name_plural = 'Tareas Kanban'
        ordering = ['orden', '-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} ({self.get_estado_display()})'


class NotificacionWhatsApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telefono = models.CharField(max_length=20)
    mensaje = models.TextField()
    enviado = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificacion WhatsApp'
        verbose_name_plural = 'Notificaciones WhatsApp'
        ordering = ['-fecha']

    def __str__(self):
        return f'WA a {self.telefono}: {self.mensaje[:30]}'


class ContratoDigital(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviado', 'Enviado'),
        ('firmado', 'Firmado'),
        ('vencido', 'Vencido'),
        ('cancelado', 'Cancelado'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='contratos')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    partes = models.TextField(help_text='Nombres de las partes involucradas, separados por coma')
    condiciones = models.TextField()
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='borrador')
    firma_contratista = models.TextField(blank=True, help_text='Base64 de la firma')
    firma_empresa = models.TextField(blank=True, help_text='Base64 de la firma')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    archivo_pdf = models.FileField(upload_to='contratos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contrato Digital'
        verbose_name_plural = 'Contratos Digitales'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} - {self.get_estado_display()}'


class ItemInventario(models.Model):
    ESTADO_CHOICES = [
        ('bueno', 'Bueno'),
        ('regular', 'Regular'),
        ('malo', 'Malo'),
        ('deteriorado', 'Deteriorado'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='inventario')
    categoria = models.CharField(max_length=100)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    cantidad = models.IntegerField(default=1)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='bueno')
    ubicacion = models.CharField(max_length=200, blank=True)
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_adquisicion = models.DateField(null=True, blank=True)
    imagen = models.ImageField(upload_to='inventario/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item de Inventario'
        verbose_name_plural = 'Items de Inventario'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f'{self.nombre} ({self.categoria})'


class BitacoraObra(models.Model):
    TIPO_CHOICES = [
        ('inicio', 'Inicio de Obra'),
        ('avance', 'Avance'),
        ('problema', 'Problema Detectado'),
        ('solucion', 'Solucion Aplicada'),
        ('material', 'Material Recibido'),
        ('inspeccion', 'Inspeccion'),
        ('fin', 'Fin de Obra'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='bitacora_obras')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default='avance')
    fotos = models.ManyToManyField(FotoInspeccion, blank=True)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    coste = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bitacora de Obra'
        verbose_name_plural = 'Bitacoras de Obras'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo}'


class RolSistema(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    puede_ver_edificios = models.BooleanField(default=True)
    puede_editar_edificios = models.BooleanField(default=False)
    puede_ver_alertas = models.BooleanField(default=True)
    puede_resolver_alertas = models.BooleanField(default=False)
    puede_ver_finanzas = models.BooleanField(default=False)
    puede_editar_finanzas = models.BooleanField(default=False)
    puede_ver_sensores = models.BooleanField(default=True)
    puede_editar_sensores = models.BooleanField(default=False)
    puede_ver_inventario = models.BooleanField(default=True)
    puede_editar_inventario = models.BooleanField(default=False)
    puede_aprobar = models.BooleanField(default=False)
    puede_exportar = models.BooleanField(default=True)
    puede_ver_reportes = models.BooleanField(default=True)
    es_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Rol del Sistema'
        verbose_name_plural = 'Roles del Sistema'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class PermisosUsuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permisos_sistema')
    rol = models.ForeignKey(RolSistema, on_delete=models.SET_NULL, null=True, blank=True)
    edificios_asignados = models.ManyToManyField(Edificio, blank=True, related_name='edificios_permisos')
    notificaciones_email = models.BooleanField(default=True)
    notificaciones_push = models.BooleanField(default=True)
    notificaciones_whatsapp = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Permisos de Usuario'
        verbose_name_plural = 'Permisos de Usuarios'

    def __str__(self):
        return f'{self.usuario.username} - {self.rol}'


class Comentario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mis_comentarios')
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='comentarios_edificio')
    modelo_tipo = models.CharField(max_length=50, blank=True, help_text='Modelo relacionado (ej: Alerta, Factura)')
    modelo_id = models.CharField(max_length=100, blank=True, help_text='ID del objeto relacionado')
    texto = models.TextField()
    padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='respuestas')
    fecha = models.DateTimeField(auto_now_add=True)
    editado = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.autor.username}: {self.texto[:50]}'


class Recordatorio(models.Model):
    TIPO_CHOICES = [
        ('mantenimiento', 'Mantenimiento'),
        ('inspeccion', 'Inspeccion'),
        ('pago', 'Pago'),
        ('vencimiento', 'Vencimiento'),
        ('reunion', 'Reunion'),
        ('personal', 'Personal'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recordatorios')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default='personal')
    edificio = models.ForeignKey(Edificio, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_recordatorio = models.DateTimeField()
    leido = models.BooleanField(default=False)
    enviado_email = models.BooleanField(default=False)
    repetir = models.BooleanField(default=False)
    intervalo_dias = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Recordatorio'
        verbose_name_plural = 'Recordatorios'
        ordering = ['fecha_recordatorio']

    def __str__(self):
        return f'{self.titulo} - {self.fecha_recordatorio}'


class CalculadoraRestauracion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    edificio = models.ForeignKey(Edificio, on_delete=models.CASCADE, related_name='calculos_restauracion')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mano_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    materiales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    permisos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    imprevistos_pct = models.IntegerField(default=10, verbose_name='% Imprevistos')
    total_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_calculo = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Calculo de Restauracion'
        verbose_name_plural = 'Calculos de Restauracion'
        ordering = ['-fecha_calculo']

    def save(self, *args, **kwargs):
        subtotal = (self.area_m2 * self.costo_m2) + self.mano_obra + self.materiales + self.permisos
        self.total_estimado = subtotal + (subtotal * self.imprevistos_pct / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.titulo} - {self.total_estimado} EUR'


class ExportacionLog(models.Model):
    FORMATO_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    formato = models.CharField(max_length=10, choices=FORMATO_CHOICES)
    modelo_tipo = models.CharField(max_length=50)
    registros = models.IntegerField(default=0)
    archivo = models.FileField(upload_to='exportaciones/', null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Exportacion'
        verbose_name_plural = 'Logs de Exportacion'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario.username} - {self.get_formato_display()} - {self.modelo_tipo}'


class WebhookConfig(models.Model):
    EVENTO_CHOICES = [
        ('alerta_nueva', 'Nueva Alerta'),
        ('alerta_resuelta', 'Alerta Resuelta'),
        ('mantenimiento', 'Nuevo Mantenimiento'),
        ('factura', 'Nueva Factura'),
        ('sensor_fallo', 'Fallo de Sensor'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    url = models.URLField()
    evento = models.CharField(max_length=20, choices=EVENTO_CHOICES)
    activo = models.BooleanField(default=True)
    secreto = models.CharField(max_length=100, blank=True)
    ultimo_envio = models.DateTimeField(null=True, blank=True)
    exitoso = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooks'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} - {self.get_evento_display()}'


class DashboardWidget(models.Model):
    WIDGET_CHOICES = [
        ('alertas', 'Alertas Activas'),
        ('sensores', 'Estado Sensores'),
        ('finanzas', 'Resumen Financiero'),
        ('mantenimiento', 'Mantenimientos'),
        ('grafica_ingresos', 'Grafica Ingresos'),
        ('grafica_alertas', 'Grafica Alertas'),
        ('mapa', 'Mapa'),
        ('calendario', 'Calendario'),
        ('ultimas_acciones', 'Ultimas Acciones'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_widgets')
    widget_tipo = models.CharField(max_length=20, choices=WIDGET_CHOICES)
    titulo = models.CharField(max_length=100)
    posicion = models.IntegerField(default=0)
    ancho = models.IntegerField(default=6, help_text='Columnas (1-12)')
    alto = models.IntegerField(default=3, help_text='Filas')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Widget del Dashboard'
        verbose_name_plural = 'Widgets del Dashboard'
        ordering = ['posicion']

    def __str__(self):
        return f'{self.usuario.username} - {self.titulo}'


class TextoMultiidioma(models.Model):
    clave = models.CharField(max_length=200, unique=True)
    es = models.TextField(blank=True)
    en = models.TextField(blank=True)
    ar = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Texto Multiidioma'
        verbose_name_plural = 'Textos Multiidioma'
        ordering = ['clave']

    def __str__(self):
        return self.clave

    def traduccion(self, idioma='es'):
        return getattr(self, idioma, self.es) or self.es


class NotificacionPush(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones_push_real')
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()
    url = models.URLField(blank=True)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificacion Push'
        verbose_name_plural = 'Notificaciones Push'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.titulo} - {self.usuario.username}'
