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
                fecha_limite__gte=hace_una_semana.date()
            ).count()

            asunto = f'[SmartHeritage] Reporte Semanal - {edificio.nombre}'
            mensaje = (
                f'Reporte semanal de {edificio.nombre}\n\n'
                f'Total lecturas: {stats["total"]}\n'
                f'Temperatura media: {round(stats["promedio_temperatura"] or 0, 1)}\n'
                f'Alertas: {alertas}\n'
                f'Mantenimientos: {mantenimientos}\n'
                f'Salud actual: {edificio.salud_score}%\n'
            )
            email_admins = [a[1] for a in settings.ADMINS] if hasattr(settings, 'ADMINS') and settings.ADMINS else []
            if not email_admins and settings.EMAIL_HOST_USER:
                email_admins = [settings.EMAIL_HOST_USER]
            if email_admins:
                send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, email_admins, fail_silently=True)
        return 'Reporte semanal generado y enviado'
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
                            'tipo_alerta': 'alto',
                            'mensaje': f'{sensor.nombre}: {ultima.valor} {sensor.unidad_medida} supera umbral maximo ({sensor.umbral_max})',
                            'valor_detectado': ultima.valor,
                        }
                    )
                    if created:
                        alertas_generadas += 1
                        enviar_email_alerta_task.delay(str(alerta.id))
                elif sensor.umbral_min is not None and ultima.valor < sensor.umbral_min:
                    alerta, created = Alerta.objects.get_or_create(
                        sensor=sensor,
                        lectura=ultima,
                        resuelta=False,
                        defaults={
                            'tipo_alerta': 'bajo',
                            'mensaje': f'{sensor.nombre}: {ultima.valor} {sensor.unidad_medida} inferior a umbral minimo ({sensor.umbral_min})',
                            'valor_detectado': ultima.valor,
                        }
                    )
                    if created:
                        alertas_generadas += 1
                        enviar_email_alerta_task.delay(str(alerta.id))
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
        email_admins = [a[1] for a in settings.ADMINS] if hasattr(settings, 'ADMINS') and settings.ADMINS else []
        if not email_admins and settings.EMAIL_HOST_USER:
            email_admins = [settings.EMAIL_HOST_USER]
        if email_admins:
            send_mail(
                '[SmartHeritage] Backup Completado',
                f'Backup creado: {backup_file}\nTamano: {size_kb:.1f} KB',
                settings.DEFAULT_FROM_EMAIL,
                email_admins,
                fail_silently=True,
            )
        return f'Backup creado: {backup_file}'
    except Exception as exc:
        self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=3)
def enviar_email_alerta_task(self, alerta_id):
    from .models import Alerta
    try:
        alerta = Alerta.objects.select_related('sensor', 'sensor__edificio').get(id=alerta_id)
        asunto = f'[SmartHeritage] Alerta {alerta.get_severidad_display()}: {alerta.sensor.nombre}'
        mensaje = (
            f'Alerta detectada en {alerta.sensor.edificio.nombre}\n\n'
            f'Sensor: {alerta.sensor.nombre}\n'
            f'Tipo: {alerta.sensor.get_tipo_display()}\n'
            f'Severidad: {alerta.get_severidad_display()}\n'
            f'Mensaje: {alerta.mensaje}\n'
            f'Valor detectado: {alerta.valor_detectado} {alerta.sensor.unidad_medida}\n'
            f'Fecha: {alerta.fecha_creacion.strftime("%d/%m/%Y %H:%M")}\n'
        )
        email_admins = [a[1] for a in settings.ADMINS] if hasattr(settings, 'ADMINS') and settings.ADMINS else []
        if not email_admins and settings.EMAIL_HOST_USER:
            email_admins = [settings.EMAIL_HOST_USER]
        if email_admins:
            send_mail(
                asunto, mensaje,
                settings.DEFAULT_FROM_EMAIL,
                email_admins,
                fail_silently=True,
            )
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
                        fecha_limite=(timezone.now() + timedelta(days=7)).date(),
                        prioridad='alta',
                    )
                    mantenimientos_creados += 1
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
        return f'{lecturas_eliminadas} lecturas y {logs_eliminados} logs eliminados'
    except Exception as exc:
        self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def exportar_datos_task(self, edificio_id=None, formato='csv'):
    from .models import Edificio, Lectura
    try:
        if edificio_id:
            lecturas = Lectura.objects.filter(sensor__edificio_id=edificio_id).select_related('sensor')
        else:
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
        email_admins = [a[1] for a in settings.ADMINS] if hasattr(settings, 'ADMINS') and settings.ADMINS else []
        if not email_admins and settings.EMAIL_HOST_USER:
            email_admins = [settings.EMAIL_HOST_USER]
        if email_admins:
            send_mail(
                '[SmartHeritage] Datos Exportados',
                f'Se exportaron {lecturas.count()} lecturas en formato {formato.upper()}',
                settings.DEFAULT_FROM_EMAIL,
                email_admins,
                fail_silently=True,
            )
        return output.getvalue()[:500]
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=1)
def simular_lecturas_task(self):
    import random
    from .models import Sensor, Lectura
    try:
        sensores = Sensor.objects.filter(activo=True)
        lecturas_creadas = 0
        for sensor in sensores:
            if sensor.tipo == 'temperatura':
                valor = round(random.uniform(15.0, 35.0), 1)
            elif sensor.tipo == 'humedad':
                valor = round(random.uniform(30.0, 85.0), 1)
            elif sensor.tipo == 'vibracion':
                valor = round(random.uniform(0.0, 8.0), 2)
            elif sensor.tipo == 'luz':
                valor = round(random.uniform(0.0, 1000.0), 0)
            elif sensor.tipo == 'co2':
                valor = round(random.uniform(300.0, 800.0), 0)
            elif sensor.tipo == 'ruido':
                valor = round(random.uniform(20.0, 90.0), 1)
            elif sensor.tipo == 'grieta':
                valor = round(random.uniform(0.0, 5.0), 3)
            elif sensor.tipo == 'presion':
                valor = round(random.uniform(1000.0, 1030.0), 1)
            else:
                valor = round(random.uniform(0.0, 100.0), 1)

            Lectura.objects.create(sensor=sensor, valor=valor, fecha_hora=timezone.now())
            lecturas_creadas += 1

        return f'{lecturas_creadas} lecturas simuladas'
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=1)
def verificar_cotizaciones_expiradas_task(self):
    from .models import Cotizacion, CotizacionHistorial
    try:
        ahora = timezone.now()
        expiradas = Cotizacion.objects.filter(
            estado='enviada',
            fecha_expiracion__lt=ahora
        )
        count = 0
        for cot in expiradas:
            cot.estado = 'expirada'
            cot.save()
            CotizacionHistorial.objects.create(
                cotizacion=cot, accion='expirada',
                comentario='Expirada automáticamente por el sistema'
            )
            count += 1
        return f'{count} cotizaciones expiradas'
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
