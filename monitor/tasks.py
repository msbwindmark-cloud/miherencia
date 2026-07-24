import json
import csv
import io
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Avg, Count, Sum


@shared_task(bind=True, max_retries=3)
def generar_reporte_semanal_task(self):
    from .models import Edificio, Sensor, Lectura, Alerta, Mantenimiento
    try:
        hace_una_semana = timezone.now() - timedelta(days=7)
        edificios = Edificio.objects.filter(activo=True)
        for edificio in edificios:
            lecturas = Lectura.objects.filter(
                sensor__edificio=edificio,
                fecha_hora__gte=hace_una_semana
            )
            stats = lecturas.aggregate(
                total=Count('id'),
                promedio_temperatura=Avg('valor', filter=lecturas.filter(sensor__tipo='temperatura')),
            )
            alertas = Alerta.objects.filter(
                sensor__edificio=edificio,
                fecha_creacion__gte=hace_una_semana
            ).count()
            mantenimientos = Mantenimiento.objects.filter(
                edificio=edificio,
                fecha_programada__gte=hace_una_semana
            ).count()
            print(f'[Reporte] {edificio.nombre}: {stats["total"]} lecturas, {alertas} alertas, {mantenimientos} mantenimientos')
        return 'Reporte semanal generado exitosamente'
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def verificar_alertas_task(self):
    from .models import Sensor, Alerta
    try:
        sensores = Sensor.objects.filter(activo=True)
        alertas_generadas = 0
        for sensor in sensores:
            ultima = sensor.lecturas.order_by('-fecha_hora').first()
            if ultima:
                if sensor.umbral_max is not None and ultima.valor > sensor.umbral_max:
                    alerta, created = Alerta.objects.get_or_create(
                        sensor=sensor,
                        lectura=ultima,
                        resuelta=False,
                        defaults={
                            'mensaje': f'{sensor.nombre}: {ultima.valor} {sensor.unidad_medida} supera umbral maximo ({sensor.umbral_max})',
                            'nivel': 'critica' if ultima.valor > sensor.umbral_max * 1.5 else 'alta',
                        }
                    )
                    if created:
                        alertas_generadas += 1
                elif sensor.umbral_min is not None and ultima.valor < sensor.umbral_min:
                    alerta, created = Alerta.objects.get_or_create(
                        sensor=sensor,
                        lectura=ultima,
                        resuelta=False,
                        defaults={
                            'mensaje': f'{sensor.nombre}: {ultima.valor} {sensor.unidad_medida} inferior a umbral minimo ({sensor.umbral_min})',
                            'nivel': 'alta',
                        }
                    )
                    if created:
                        alertas_generadas += 1
        print(f'[Alertas] {alertas_generadas} nuevas alertas generadas')
        return f'{alertas_generadas} alertas generadas'
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=3)
def backup_database_task(self):
    import shutil
    import os
    from .models import BackupLog
    try:
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sqlite3')
        shutil.copy2(db_path, backup_file)
        size_kb = os.path.getsize(backup_file) / 1024
        BackupLog.objects.create(
            archivo=backup_file,
            tamano_kb=round(size_kb, 2),
            descripcion=f'Backup automatico {timestamp}',
        )
        print(f'[Backup] Creado: {backup_file} ({size_kb:.1f} KB)')
        return f'Backup creado: {backup_file}'
    except Exception as exc:
        self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=3)
def enviar_email_alerta_task(self, alerta_id):
    from .models import Alerta
    try:
        alerta = Alerta.objects.select_related('sensor', 'sensor__edificio').get(id=alerta_id)
        asunto = f'[SmartHeritage] Alerta: {alerta.sensor.nombre}'
        mensaje = f"""
        Alerta detectada en {alerta.sensor.edificio.nombre}
        Sensor: {alerta.sensor.nombre}
        Nivel: {alerta.nivel}
        Mensaje: {alerta.mensaje}
        Fecha: {alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M')}
        """
        email_admins = [a[1] for a in settings.ADMINS] if hasattr(settings, 'ADMINS') else []
        if not email_admins and settings.EMAIL_HOST_USER:
            email_admins = [settings.EMAIL_HOST_USER]
        if email_admins:
            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                email_admins,
                fail_silently=True,
            )
        print(f'[Email Alerta] Enviado: {asunto}')
        return f'Email enviado para alerta {alerta_id}'
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def mantenimiento_predictivo_task(self):
    from .models import Sensor, Mantenimiento
    from django.db.models import Avg, Count
    try:
        sensores = Sensor.objects.filter(activo=True)
        mantenimientos_creados = 0
        for sensor in sensores:
            lecturas = sensor.lecturas.order_by('-fecha_hora')[:50]
            if lecturas.count() < 20:
                continue
            variaciones = []
            valores = list(lecturas.values_list('valor', flat=True))
            for i in range(1, len(valores)):
                variaciones.append(abs(valores[i] - valores[i-1]))
            if variaciones:
                variacion_media = sum(variaciones) / len(variaciones)
                if variacion_media > 5:
                    Mantenimiento.objects.create(
                        edificio=sensor.edificio,
                        titulo=f'Mantenimiento preventivo: {sensor.nombre}',
                        descripcion=f'Sensor {sensor.nombre} muestra variacion inusual ({variacion_media:.2f} promedio). Se recomienda revision.',
                        estado='pendiente',
                        fecha_programada=timezone.now().date() + timedelta(days=7),
                        prioridad='alta',
                    )
                    mantenimientos_creados += 1
        print(f'[Predictivo] {mantenimientos_creados} mantenimientos preventivos creados')
        return f'{mantenimientos_creados} mantenimientos preventivos creados'
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def limpiar_datos_antiguos_task(self, dias=365):
    from .models import Lectura, AuditLog
    try:
        fecha_limite = timezone.now() - timedelta(days=dias)
        lecturas_eliminadas = Lectura.objects.filter(fecha_hora__lt=fecha_limite).delete()[0]
        logs_eliminados = AuditLog.objects.filter(fecha__lt=fecha_limite).delete()[0]
        print(f'[Limpieza] {lecturas_eliminadas} lecturas y {logs_eliminados} logs eliminados')
        return f'{lecturas_eliminadas} lecturas y {logs_eliminados} logs eliminados'
    except Exception as exc:
        self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def exportar_datos_task(self, edificio_id=None, formato='csv'):
    from .models import Edificio, Lectura
    try:
        if edificio_id:
            edificio = Edificio.objects.get(id=edificio_id)
            lecturas = Lectura.objects.filter(sensor__edificio=edificio).select_related('sensor')
        else:
            edificio = None
            lecturas = Lectura.objects.all().select_related('sensor')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Sensor', 'Tipo', 'Valor', 'Unidad', 'Alerta'])
        for l in lecturas[:10000]:
            writer.writerow([
                l.fecha_hora.strftime('%Y-%m-%d %H:%M:%S'),
                l.sensor.nombre,
                l.sensor.get_tipo_display(),
                l.valor,
                l.sensor.unidad_medida,
                'Si' if l.es_alerta else 'No',
            ])
        print(f'[Exportar] {lecturas.count()} lecturas exportadas')
        return output.getvalue()[:500]
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
