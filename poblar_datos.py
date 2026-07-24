import os
import sys
import django
import random
from datetime import timedelta, date, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_heritage.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from monitor.models import *

print("=" * 60)
print("  SMARTHERITAGE - POBLADOR DE BASE DE DATOS")
print("=" * 60)

admin, _ = User.objects.get_or_create(
    username='admin',
    defaults={'email': 'admin@smartheritage.com', 'first_name': 'Admin', 'last_name': 'SmartHeritage', 'is_staff': True, 'is_superuser': True}
)
admin.set_password('admin123')
admin.save()
print("  [OK] Usuario admin creado")

users_data = [
    ('maria.garcia', 'Maria', 'Garcia Lopez', 'maria@patrimonio.es'),
    ('carlos.ruiz', 'Carlos', 'Ruiz Martinez', 'carlos@patrimonio.es'),
    ('ana.fernandez', 'Ana', 'Fernandez Sanchez', 'ana@patrimonio.es'),
    ('pedro.sanchez', 'Pedro', 'Sanchez Vega', 'pedro@patrimonio.es'),
    ('laura.martin', 'Laura', 'Martin Torres', 'laura@patrimonio.es'),
]
usuarios = [admin]
for uname, fname, lname, email in users_data:
    u, _ = User.objects.get_or_create(username=uname, defaults={'first_name': fname, 'last_name': lname, 'email': email})
    u.set_password('admin123')
    u.save()
    usuarios.append(u)
print(f"  [OK] {len(usuarios)} usuarios creados")

perfiles_rol = ['admin', 'conservador', 'tecnico', 'visualizador', 'tecnico']
for i, u in enumerate(usuarios):
    PerfilUsuario.objects.get_or_create(user=u, defaults={'rol': perfiles_rol[i % len(perfiles_rol)], 'organizacion': 'SmartHeritage'})
print("  [OK] Perfiles creados")

edificios_data = [
    {'nombre': 'Catedral de Toledo', 'ciudad': 'Toledo', 'provincia': 'Toledo', 'codigo_postal': '45001', 'latitud': 39.8628, 'longitud': -4.0273, 'categoria': 'iglesia', 'anno_construccion': 1227, 'proteccion_oficial': True, 'estado_general': 'bueno', 'descripcion': 'Catedral gotica del siglo XIII, una de las mas importantes de Espana.'},
    {'nombre': 'Alhambra de Granada', 'ciudad': 'Granada', 'provincia': 'Granada', 'codigo_postal': '18001', 'latitud': 37.1760, 'longitud': -3.5881, 'categoria': 'monumento', 'anno_construccion': 1238, 'proteccion_oficial': True, 'estado_general': 'excelente', 'descripcion': 'Palacio fortaleza de la epoca nazarita, Patrimonio de la Humanidad.'},
    {'nombre': 'Museo del Prado', 'ciudad': 'Madrid', 'provincia': 'Madrid', 'codigo_postal': '28014', 'latitud': 40.4138, 'longitud': -3.6924, 'categoria': 'museo', 'anno_construccion': 1785, 'proteccion_oficial': True, 'estado_general': 'excelente', 'descripcion': 'Museo de arte universal, uno de los mas importantes del mundo.'},
    {'nombre': 'Casa Batllo', 'ciudad': 'Barcelona', 'provincia': 'Barcelona', 'codigo_postal': '08007', 'latitud': 41.3916, 'longitud': 2.1650, 'categoria': 'casa_historica', 'anno_construccion': 1877, 'proteccion_oficial': True, 'estado_general': 'bueno', 'descripcion': 'Obra maestra de Antoni Gaudi en el Passeig de Gracia.'},
    {'nombre': 'Archivo de Indias', 'ciudad': 'Sevilla', 'provincia': 'Sevilla', 'codigo_postal': '41004', 'latitud': 37.3861, 'longitud': -5.9927, 'categoria': 'archivo', 'anno_construccion': 1584, 'proteccion_oficial': True, 'estado_general': 'regular', 'descripcion': 'Archivo historico con documentos de la colonizacion americana.'},
    {'nombre': 'Mezquita de Cordoba', 'ciudad': 'Cordoba', 'provincia': 'Cordoba', 'codigo_postal': '14003', 'latitud': 37.8799, 'longitud': -4.7794, 'categoria': 'iglesia', 'anno_construccion': 784, 'proteccion_oficial': True, 'estado_general': 'bueno', 'descripcion': 'Mezquita-catedral, ejemplo unico de arte islammico y cristiano.'},
    {'nombre': 'Guggenheim Bilbao', 'ciudad': 'Bilbao', 'provincia': 'Vizcaya', 'codigo_postal': '48009', 'latitud': 43.2677, 'longitud': -2.9339, 'categoria': 'museo', 'anno_construccion': 1997, 'proteccion_oficial': False, 'estado_general': 'excelente', 'descripcion': 'Museo de arte contemporanio disenhado por Frank Gehry.'},
    {'nombre': 'Torre de Hércules', 'ciudad': 'A Coruna', 'provincia': 'A Coruna', 'codigo_postal': '15001', 'latitud': 43.3857, 'longitud': -8.4065, 'categoria': 'monumento', 'anno_construccion': 100, 'proteccion_oficial': True, 'estado_general': 'bueno', 'descripcion': 'Faro romano activo mas antiguo del mundo.'},
]

edificios = []
for data in edificios_data:
    e, _ = Edificio.objects.get_or_create(
        nombre=data['nombre'],
        defaults={**data, 'direccion': data['ciudad'], 'propietario': admin}
    )
    edificios.append(e)
print(f"  [OK] {len(edificios)} edificios creados")

tipos_sensor = ['temperatura', 'humedad', 'vibracion', 'luz', 'co2', 'ruido', 'grieta', 'presion']
sensores = []
for edificio in edificios:
    for tipo in random.sample(tipos_sensor, k=random.randint(3, 6)):
        s, _ = Sensor.objects.get_or_create(
            edificio=edificio,
            tipo=tipo,
            defaults={
                'nombre': f'Sensor {tipo.title()} - {edificio.nombre[:20]}',
                'ubicacionDescripcion': f'Ubicado en {edificio.ciudad}',
                'umbral_min': random.uniform(0, 10),
                'umbral_max': random.uniform(50, 100),
                'unidad_medida': {'temperatura': '°C', 'humedad': '%', 'vibracion': 'g', 'luz': 'lux', 'co2': 'ppm', 'ruido': 'dB', 'grieta': 'mm', 'presion': 'hPa'}.get(tipo, 'unidades'),
            }
        )
        sensores.append(s)
print(f"  [OK] {len(sensores)} sensores creados")

print("  Generando lecturas...")
lecturas_creadas = 0
for sensor in sensores:
    for i in range(20):
        fecha = timezone.now() - timedelta(hours=random.randint(0, 168))
        if sensor.tipo == 'temperatura':
            valor = round(random.uniform(15, 35), 1)
        elif sensor.tipo == 'humedad':
            valor = round(random.uniform(30, 85), 1)
        elif sensor.tipo == 'vibracion':
            valor = round(random.uniform(0, 8), 2)
        elif sensor.tipo == 'co2':
            valor = round(random.uniform(300, 800), 0)
        elif sensor.tipo == 'ruido':
            valor = round(random.uniform(30, 75), 1)
        elif sensor.tipo == 'grieta':
            valor = round(random.uniform(0, 5), 2)
        else:
            valor = round(random.uniform(950, 1050), 1)
        Lectura.objects.create(sensor=sensor, valor=valor, fecha_hora=fecha)
        lecturas_creadas += 1
print(f"  [OK] {lecturas_creadas} lecturas creadas")

print("  Generando alertas...")
alertas_creadas = 0
for sensor in random.sample(sensores, k=min(15, len(sensores))):
    lecturas = sensor.lecturas.order_by('-fecha_hora')[:3]
    for lectura in lecturas:
        if lectura.es_alerta or random.random() > 0.7:
            Alerta.objects.get_or_create(
                sensor=sensor,
                lectura=lectura,
                defaults={
                    'tipo_alerta': 'alto' if random.random() > 0.5 else 'bajo',
                    'severidad': random.choice(['info', 'warning', 'critical']),
                    'mensaje': f'Alerta de {sensor.get_tipo_display()} en {sensor.edificio.nombre}',
                    'valor_detectado': lectura.valor,
                    'resuelta': random.random() > 0.5,
                }
            )
            alertas_creadas += 1
print(f"  [OK] {alertas_creadas} alertas creadas")

print("  Generando informes...")
for edificio in random.sample(edificios, k=4):
    Informe.objects.create(
        edificio=edificio,
        titulo=f'Informe de estado - {edificio.nombre}',
        contenido=f'Analisis completo del estado del edificio {edificio.nombre}. Se recomienda seguimiento continuo.',
        autor=admin,
        periodo_desde=date.today() - timedelta(days=30),
        periodo_hasta=date.today(),
    )
print("  [OK] Informes creados")

print("  Generando equipos...")
equipo1, _ = Equipo.objects.get_or_create(nombre='Equipo Restauracion', defaults={'descripcion': 'Equipo especializado en restauracion'})
equipo1.miembros.set(usuarios[:3])
equipo1.edificios.set(edificios[:3])
equipo2, _ = Equipo.objects.get_or_create(nombre='Equipo Monitoreo', defaults={'descripcion': 'Equipo de monitoreo sensores'})
equipo2.miembros.set(usuarios[2:5])
equipo2.edificios.set(edificios[3:6])
print("  [OK] Equipos creados")

print("  Generando mantenimientos...")
for edificio in random.sample(edificios, k=5):
    Mantenimiento.objects.create(
        edificio=edificio,
        titulo=f'Mantenimiento preventivo - {edificio.nombre}',
        descripcion='Revision general de estructura y sensores.',
        estado=random.choice(['pendiente', 'en_progreso', 'completado']),
        prioridad=random.choice(['baja', 'media', 'alta']),
        asignado_a=random.choice(usuarios),
        fecha_limite=date.today() + timedelta(days=random.randint(7, 60)),
    )
print("  [OK] Mantenimientos creados")

print("  Generando chat...")
for edificio in edificios[:4]:
    for i in range(5):
        ChatMensaje.objects.create(
            edificio=edificio,
            autor=random.choice(usuarios),
            texto=random.choice([
                'Revisar sensores de humedad urgentemente.',
                'El informe esta listo para revision.',
                'Nueva foto en el timeline del edificio.',
                'Mantenimiento programado para la proxima semana.',
                'Alerta resuelta correctamente.',
            ]),
        )
print("  [OK] Mensajes de chat creados")

print("  Generando gamificacion...")
acciones = ['resolver_alerta', 'crear_edificio', 'crear_sensor', 'registrar_lectura', 'generar_informe', 'login_diario']
for u in usuarios:
    for _ in range(random.randint(3, 10)):
        PuntoGamificacion.objects.create(
            usuario=u,
            accion=random.choice(acciones),
            puntos=random.randint(5, 50),
        )
print("  [OK] Gamificacion creada")

print("  Generando logros...")
logros_data = [
    ('Primer Paso', 'Resolver tu primera alerta', 'bolt', 10),
    ('Guardian', 'Resolver 10 alertas', 'shield', 50),
    ('Experto', 'Generar 5 informes', 'star', 100),
    ('Lider', 'Crear 3 edificios', 'crown', 150),
    ('Maestro', 'Alcanzar 500 puntos', 'gem', 500),
]
for nombre, desc, icono, pts in logros_data:
    logro, _ = Logro.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc, 'icono': icono, 'puntos_necesarios': pts})
    if random.random() > 0.5:
        logro.usuarios.set(random.sample(usuarios, k=random.randint(1, 3)))
print("  [OK] Logros creados")

print("  Generando timeline...")
for edificio in edificios[:5]:
    for i in range(3):
        TimelineFoto.objects.create(
            edificio=edificio,
            titulo=f'Estado {edificio.nombre} - Mes {i+1}',
            descripcion=f'Foto del estado del edificio en el mes {i+1}.',
            autor=random.choice(usuarios),
            fecha_toma=date.today() - timedelta(days=30*i),
        )
print("  [OK] Timeline creado")

print("  Generando notificaciones...")
for u in usuarios[:3]:
    for i in range(5):
        Notificacion.objects.create(
            usuario=u,
            titulo=random.choice(['Nueva alerta', 'Mantenimiento pendiente', 'Informe listo', 'Bienvenido']),
            mensaje='Tienes una nueva accion pendiente en tu dashboard.',
            tipo=random.choice(['alerta', 'mantenimiento', 'sistema', 'equipo']),
        )
print("  [OK] Notificaciones creadas")

print("  Generando nuevas funcionalidades...")

print("  Generando analisis IA...")
for edificio in random.sample(edificios, k=3):
    AnalisisIA.objects.create(
        edificio=edificio,
        titulo=f'Analisis estructural - {edificio.nombre}',
        estado='completado',
        severidad_detectada=random.choice(['sin_dano', 'leve', 'moderado']),
        confianza=round(random.uniform(80, 98), 1),
        grietas_detectadas=random.randint(0, 3),
        costo_estimado=round(random.uniform(1000, 25000), 2),
        prioridad_ia=random.choice(['media', 'alta']),
        recomendaciones='Se recomienda inspeccion periodica.',
        analyst=admin,
        fecha_completado=timezone.now(),
    )
print("  [OK] Analisis IA creados")

print("  Generando predicciones ML...")
for edificio in random.sample(edificios, k=4):
    PrediccionML.objects.create(
        edificio=edificio,
        tipo=random.choice(['mantenimiento', 'deterioro', 'fallo']),
        titulo=f'Prediccion {edificio.nombre}',
        descripcion='Basado en datos historicos de sensores.',
        confianza=round(random.uniform(65, 92), 1),
        fecha_predicha=date.today() + timedelta(days=random.randint(30, 180)),
        probabilidad=round(random.uniform(30, 85), 1),
        impacto_financiero=round(random.uniform(5000, 80000), 2),
        accion_recomendada='Programar inspeccion preventiva.',
    )
print("  [OK] Predicciones ML creadas")

print("  Generando donaciones...")
donadores = [('Ahmad Al-Rashid', 'ahmad@email.com'), ('Sofia Martinez', 'sofia@email.com'), ('Jean Pierre', 'jean@email.com')]
for edificio in random.sample(edificios, k=3):
    for nombre, email in donadores:
        Donacion.objects.create(
            edificio=edificio,
            donador_nombre=nombre,
            donador_email=email,
            monto=round(random.uniform(25, 500), 2),
            estado='completada',
            donador_mensaje='Para la preservacion del patrimonio.',
            fecha_completada=timezone.now(),
        )
print("  [OK] Donaciones creadas")

print("  Generando reportes ciudadanos...")
for edificio in random.sample(edificios, k=4):
    ReporteCiudadano.objects.create(
        edificio=edificio,
        ciudadano_nombre='Ciudadano Anonimo',
        ciudadano_email='ciudadano@email.com',
        tipo=random.choice(['dano', 'vandalismo', 'limpieza']),
        titulo=f'Reporte sobre {edificio.nombre}',
        descripcion='He detectado un problema en la fachada del edificio.',
        estado=random.choice(['nuevo', 'revisado', 'resuelto']),
        votos=random.randint(1, 25),
    )
print("  [OK] Reportes ciudadanos creados")

print("  Generando seguros...")
companias = ['MAPFRE', 'Allianz', 'AXA', 'Zurich']
for edificio in edificios[:4]:
    Seguro.objects.create(
        edificio=edificio,
        compania=random.choice(companias),
        poliza_numero=f'POL-{random.randint(10000, 99999)}',
        tipo=random.choice(['todo_riesgo', 'incendio', 'responsabilidad']),
        cobertura_monto=round(random.uniform(500000, 2000000), 2),
        prima_anual=round(random.uniform(800, 5000), 2),
        fecha_inicio=date.today() - timedelta(days=random.randint(30, 300)),
        fecha_fin=date.today() + timedelta(days=random.randint(30, 300)),
    )
print("  [OK] Seguros creados")

print("  Generando eficiencia energetica...")
for edificio in edificios[:5]:
    for i in range(4):
        EficienciaEnergetica.objects.create(
            edificio=edificio,
            fecha=date.today() - timedelta(days=90*i),
            consumo_electricidad=round(random.uniform(200, 800), 1),
            consumo_gas=round(random.uniform(50, 200), 1),
            consumo_agua=round(random.uniform(1000, 5000), 0),
            produccion_solar=round(random.uniform(0, 100), 1),
            emisiones_co2=round(random.uniform(100, 500), 1),
            certificado_energetico=random.choice(['A', 'B', 'C', 'D', 'E']),
            coste_total=round(random.uniform(200, 1200), 2),
        )
print("  [OK] Eficiencia energetica creada")

print("  Generando cumplimiento legal...")
normativas = ['Ley 16/1985 Patrimonio Historical', 'RD 111/2015 Seguridad', 'Ley 12/2007 Urbanismo']
for edificio in edificios[:4]:
    for norm in random.sample(normativas, k=2):
        CumplimientoLegal.objects.create(
            edificio=edificio,
            normativa=norm,
            referencia=f'REF-{random.randint(100, 999)}',
            descripcion=f'Cumplimiento de {norm} para {edificio.nombre}.',
            estado=random.choice(['cumple', 'en_proceso', 'no_cumple']),
            fecha_inspeccion=date.today() - timedelta(days=random.randint(10, 100)),
            proxima_inspeccion=date.today() + timedelta(days=random.randint(30, 180)),
            responsable=admin,
        )
print("  [OK] Cumplimiento legal creado")

print("  Generando certificados blockchain...")
for edificio in random.sample(edificios, k=3):
    import hashlib, secrets
    CertificadoBlockchain.objects.create(
        edificio=edificio,
        tipo=random.choice(['propiedad', 'restauracion', 'historico', 'nft']),
        titulo=f'Certificado Heritage - {edificio.nombre}',
        descripcion='Certificado verificado en blockchain.',
        hash_transaccion=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
        direccion_wallet='0x' + secrets.token_hex(20),
        emisor=admin,
        validado=True,
    )
print("  [OK] Certificados blockchain creados")

print("  Generando tours virtuales...")
for edificio in edificios[:3]:
    TourVirtual.objects.create(
        edificio=edificio,
        titulo=f'Tour Virtual {edificio.nombre}',
        descripcion=f'Recorrido virtual por {edificio.nombre}.',
        vistas=random.randint(10, 500),
    )
print("  [OK] Tours virtuales creados")

print("  Generando eventos...")
eventos_tipos = ['visita', 'conferencia', 'taller', 'restauracion']
for edificio in edificios[:4]:
    Evento.objects.create(
        edificio=edificio,
        titulo=f'Visita guiada - {edificio.nombre}',
        descripcion=f'Visita guiada por {edificio.nombre} con expertos en patrimonio.',
        tipo=random.choice(eventos_tipos),
        fecha_inicio=timezone.now() + timedelta(days=random.randint(1, 30)),
        fecha_fin=timezone.now() + timedelta(days=random.randint(1, 30), hours=2),
        capacidad_maxima=random.choice([20, 30, 50, 100]),
        precio=round(random.uniform(0, 25), 2),
        organizador=admin,
        publicado=True,
    )
print("  [OK] Eventos creados")

print("  Generando tienda...")
productos = [
    ('Maqueta Catedral Toledo', 'Maqueta a escala de la catedral', 'reproduccion', 45.00),
    ('Libro Alhambra', 'Guia historica de la Alhambra', 'libro', 22.50),
    ('Cuadro Guggenheim', 'Reproduccion artistica', 'arte', 89.00),
    ('Llavero Mezquita', 'Llavero conmemorativo', 'souvenirs', 8.50),
    ('Fotografia Vintage Prado', 'Foto enmarcada epoca', 'exclusivo', 120.00),
]
for edificio in edificios[:5]:
    for nombre, desc, cat, precio in random.sample(productos, k=2):
        TiendaPatrimonio.objects.create(
            edificio=edificio,
            nombre=f'{nombre} - {edificio.ciudad}',
            descripcion=desc,
            categoria=cat,
            precio=precio,
            stock=random.randint(10, 100),
            vendidos=random.randint(0, 50),
            destacado=random.random() > 0.7,
        )
print("  [OK] Tienda creada")

print("=" * 60)
print("  BASE DE DATOS POBLADA CON EXITO!")
print("=" * 60)
print(f"  Usuarios:      {User.objects.count()}")
print(f"  Edificios:     {Edificio.objects.count()}")
print(f"  Sensores:      {Sensor.objects.count()}")
print(f"  Lecturas:      {Lectura.objects.count()}")
print(f"  Alertas:       {Alerta.objects.count()}")
print(f"  Informes:      {Informe.objects.count()}")
print(f"  Equipos:       {Equipo.objects.count()}")
print(f"  Mantenimientos:{Mantenimiento.objects.count()}")
print(f"  Analisis IA:   {AnalisisIA.objects.count()}")
print(f"  Predicciones:  {PrediccionML.objects.count()}")
print(f"  Donaciones:    {Donacion.objects.count()}")
print(f"  Reportes:      {ReporteCiudadano.objects.count()}")
print(f"  Seguros:       {Seguro.objects.count()}")
print(f"  Energia:       {EficienciaEnergetica.objects.count()}")
print(f"  Legal:         {CumplimientoLegal.objects.count()}")
print(f"  Blockchain:    {CertificadoBlockchain.objects.count()}")
print(f"  Tours:         {TourVirtual.objects.count()}")
print(f"  Eventos:       {Evento.objects.count()}")
print(f"  Tienda:        {TiendaPatrimonio.objects.count()}")
print(f"  Chat:          {ChatMensaje.objects.count()}")
print(f"  Gamificacion:  {PuntoGamificacion.objects.count()}")
print(f"  Logros:        {Logro.objects.count()}")
print(f"  Timeline:      {TimelineFoto.objects.count()}")
print(f"  Notificaciones:{Notificacion.objects.count()}")
print("=" * 60)
