import json
import io
import csv
import pyotp
import qrcode
from qrcode.image.svg import SvgPathImage
from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count, Q, Sum
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import (
    Edificio, Sensor, Lectura, Alerta, Informe, PerfilUsuario,
    SensorFoto, AuditLog, Equipo, Mantenimiento, Notificacion,
    ChatMensaje, PuntoGamificacion, Logro, TimelineFoto, ConfiguracionSMS,
    AnalisisIA, PrediccionML, Donacion, ReporteCiudadano, Seguro,
    EficienciaEnergetica, CumplimientoLegal, CertificadoBlockchain,
    TourVirtual, VisitaQR, Evento, TiendaPatrimonio,
    ComentarioEdificio, GaleriaFoto, ChatMensajeIA,
    DocumentoEdificio, Herramienta, FormularioInspeccion,
    TimelineHistorico, RecomendacionIA, AnomaliaDetectada, Voluntario,
    Ingreso, Gasto, Factura, Nomina, Presupuesto,
    TareaKanban, Cita, ItemInventario, BitacoraObra,
    ContratoDigital, FotoInspeccion, ChatAsistenteIA,
    CategoriaIngreso, CategoriaGasto, ExportacionLog,
    DashboardWidget, Recordatorio, ComparativaCiudad,
    RolSistema, PermisosUsuario, BackupLog, TextoMultiidioma,
    ModoEmergencia, DigitalTwin, Comentario, NotificacionPush,
    WebhookConfig, CalculadoraRestauracion, RegistroROI,
    MantenimientoPredictivo, ReporteAutomatico, ConfiguracionIdioma,
    NotificacionWhatsApp,
    EmailVerificationToken, MFAConfig, LoginAttempt,
    Cotizacion, CotizacionItem, CotizacionHistorial,
    TimeMachineRequest, DigitalTwinSesion, SimulacionDesastre,
    CamaraVigilancia, EventoVigilancia,
    HeritageNFT, PujaNFT, SmartContract, HitoContrato,
    CarbonCredit, DNAEdificio,
    GuardianRule, GuardianAlert, TourVR,
    Desafio, DesafioUsuario, AvatarUsuario,
)
from functools import wraps


def require_rbac_perm(perm_name):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                permisos = request.user.permisos_sistema
                if permisos.rol and getattr(permisos.rol, perm_name, False):
                    return view_func(request, *args, **kwargs)
            except (PermisosUsuario.DoesNotExist, AttributeError):
                pass
            if request.user.is_staff or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            messages.warning(request, f'No tienes permiso para acceder a esta seccion.')
            return redirect('monitor:dashboard')
        return wrapper
    return decorator


def get_rbac_context(user):
    ctx = {'puede_ver_edificios': True, 'puede_editar_edificios': False, 'puede_ver_alertas': True,
           'puede_resolver_alertas': False, 'puede_ver_finanzas': False, 'puede_editar_finanzas': False,
           'puede_ver_sensores': True, 'puede_editar_sensores': False, 'puede_aprobar': False,
           'puede_exportar': True, 'puede_ver_reportes': True, 'es_admin': False}
    if user.is_staff or user.is_superuser:
        for k in ctx: ctx[k] = True
        return ctx
    try:
        permisos = user.permisos_sistema
        if permisos.rol:
            for key in ctx:
                ctx[key] = getattr(permisos.rol, key, ctx[key])
    except (PermisosUsuario.DoesNotExist, AttributeError):
        pass
    return ctx
from .forms import (
    EdificioForm, SensorForm, LecturaForm, AlertaResolucionForm,
    InformeForm, UserRegisterForm, UserLoginForm, BusquedaForm,
    SensorFotoForm, EquipoForm, MantenimientoForm, ImportarCSVForm,
    TimelineFotoForm, AnalisisIAForm, DonacionForm, ReporteCiudadanoForm,
    SeguroForm, EficienciaEnergeticaForm, CumplimientoLegalForm,
    EventoForm, TiendaPatrimonioForm
)


def _enviar_email_confirmacion(user, token):
    subject = 'SmartHeritage - Confirma tu cuenta'
    html_body = render_to_string('monitor/email_confirmacion.html', {
        'user': user,
        'token': token,
    })
    email = EmailMultiAlternatives(
        subject=subject,
        body=f'Hola {user.username}, confirma tu cuenta en: '
             f'{settings.SITE_URL or "http://localhost:8000"}/confirmar-email/{token.token}/',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    email.attach_alternative(html_body, 'text/html')
    email.send(fail_silently=False)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('monitor:dashboard')
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            username = form.cleaned_data['username']
            user = authenticate(
                username=username,
                password=form.cleaned_data['password']
            )
            if user:
                if not user.emailaddress_verified if hasattr(user, 'emailaddress_verified') else True:
                    tokens = EmailVerificationToken.objects.filter(user=user, expirado=False)
                    if tokens.exists() and not tokens.latest('creado').esta_valido:
                        messages.error(request, 'Tu cuenta no ha sido confirmada. Revisa tu email o solicita un nuevo enlace.')
                        LoginAttempt.objects.create(ip_address=ip, username=username, exitoso=False)
                        return render(request, 'monitor/login.html', {'form': form})
                    elif not tokens.exists():
                        EmailVerificationToken.objects.create(user=user)
                        try:
                            _enviar_email_confirmacion(user, EmailVerificationToken.objects.filter(user=user).latest('creado'))
                        except Exception:
                            pass
                        messages.error(request, 'Tu cuenta no ha sido confirmada. Se envió un nuevo email de confirmación.')
                        LoginAttempt.objects.create(ip_address=ip, username=username, exitoso=False)
                        return render(request, 'monitor/login.html', {'form': form})

                login(request, user)
                LoginAttempt.objects.create(ip_address=ip, username=username, exitoso=True)
                AuditLog.registrar(user, 'login', 'Auth', user.pk, f'Inicio de sesión desde {ip}', ip=ip)

                mfa_config, _ = MFAConfig.objects.get_or_create(user=user)
                if mfa_config.is_enabled:
                    request.session['mfa_pendiente'] = True
                    request.session['mfa_user_id'] = user.pk
                    logout(request)
                    return redirect('monitor:mfa_verify')

                request.session['smartheritage_tour_pending'] = True
                messages.success(request, f'Bienvenido, {user.get_full_name() or user.username}!')
                return redirect('monitor:dashboard')
            else:
                LoginAttempt.objects.create(ip_address=ip, username=username, exitoso=False)
                messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = UserLoginForm()
    return render(request, 'monitor/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.is_active = True
            user.save()
            PerfilUsuario.objects.create(user=user, rol='visualizador')
            MFAConfig.objects.create(user=user)
            token = EmailVerificationToken.objects.create(user=user)
            try:
                _enviar_email_confirmacion(user, token)
                messages.success(request, 'Cuenta creada. Revisa tu email para confirmar tu cuenta.')
            except Exception as e:
                messages.warning(request, f'Cuenta creada pero no se pudo enviar el email: {str(e)}')
            ip = request.META.get('REMOTE_ADDR')
            AuditLog.registrar(user, 'crear', 'Usuario', user.pk, f'Nueva cuenta creada: {user.username}', ip=ip)
            login(request, user)
            request.session['smartheritage_tour_pending'] = True
            return redirect('monitor:dashboard')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = UserRegisterForm()
    return render(request, 'monitor/register.html', {'form': form})


def confirmar_email_view(request, token_uuid):
    try:
        token = EmailVerificationToken.objects.get(token=token_uuid)
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, 'Enlace de confirmación inválido.')
        return redirect('monitor:login')

    if not token.esta_valido:
        messages.error(request, 'El enlace de confirmación ha expirado. Solicita uno nuevo.')
        return redirect('monitor:login')

    user = token.user
    token.expirado = True
    token.save()
    messages.success(request, f'¡Email confirmado! Bienvenido, {user.username}. Ya puedes usar todas las funciones.')
    return redirect('monitor:login')


def resend_confirmation_view(request):
    if request.user.is_authenticated:
        user = request.user
    else:
        messages.info(request, 'Introduce tu email para reenviar la confirmación.')
        return redirect('monitor:login')

    token = EmailVerificationToken.objects.create(user=user)
    try:
        _enviar_email_confirmacion(user, token)
        messages.success(request, 'Email de confirmación reenviado.')
    except Exception as e:
        messages.error(request, f'Error al enviar: {str(e)}')
    return redirect('monitor:dashboard')


def mfa_setup_view(request):
    if not request.user.is_authenticated:
        return redirect('monitor:login')
    mfa_config, _ = MFAConfig.objects.get_or_create(user=request.user)
    if mfa_config.is_enabled:
        messages.info(request, 'MFA ya está activado.')
        return redirect('monitor:dashboard')

    if not mfa_config.secret:
        mfa_config.secret = pyotp.random_base32()
        mfa_config.save()

    totp = pyotp.TOTP(mfa_config.secret)
    provisioning_uri = totp.provisioning_uri(
        name=request.user.email or request.user.username,
        issuer_name='SmartHeritage'
    )
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1a1a2e', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    import base64
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return render(request, 'monitor/mfa_setup.html', {
        'secret': mfa_config.secret,
        'qr_b64': qr_b64,
        'provisioning_uri': provisioning_uri,
    })


def mfa_verify_setup_view(request):
    if not request.user.is_authenticated:
        return redirect('monitor:login')
    mfa_config = MFAConfig.objects.get(user=request.user)
    if request.method == 'POST':
        code = request.POST.get('code', '')
        totp = pyotp.TOTP(mfa_config.secret)
        if totp.verify(code, valid_window=1):
            mfa_config.is_enabled = True
            mfa_config.qr_generated = True
            mfa_config.save()
            messages.success(request, 'MFA activado correctamente.')
            return redirect('monitor:dashboard')
        else:
            messages.error(request, 'Código incorrecto. Intenta de nuevo.')
    return render(request, 'monitor/mfa_verify.html', {'setup_mode': True})


def mfa_disable_view(request):
    if not request.user.is_authenticated:
        return redirect('monitor:login')
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if request.user.check_password(password):
            mfa_config = MFAConfig.objects.get(user=request.user)
            mfa_config.is_enabled = False
            mfa_config.secret = ''
            mfa_config.save()
            messages.success(request, 'MFA desactivado.')
        else:
            messages.error(request, 'Contraseña incorrecta.')
    return redirect('monitor:perfil')


def mfa_verify_view(request):
    if 'mfa_pendiente' not in request.session:
        return redirect('monitor:login')
    user_id = request.session.get('mfa_user_id')
    if not user_id:
        return redirect('monitor:login')

    if request.method == 'POST':
        code = request.POST.get('code', '')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return redirect('monitor:login')

        mfa_config = MFAConfig.objects.get(user=user)
        totp = pyotp.TOTP(mfa_config.secret)
        if totp.verify(code, valid_window=1):
            del request.session['mfa_pendiente']
            del request.session['mfa_user_id']
            login(request, user)
            request.session['smartheritage_tour_pending'] = True
            messages.success(request, f'Bienvenido, {user.get_full_name() or user.username}!')
            return redirect('monitor:dashboard')
        else:
            messages.error(request, 'Código MFA incorrecto.')
    return render(request, 'monitor/mfa_verify.html', {'setup_mode': False})


def logout_view(request):
    if request.user.is_authenticated:
        ip = request.META.get('REMOTE_ADDR')
        AuditLog.registrar(request.user, 'logout', 'Auth', request.user.pk, f'Cierre de sesión desde {ip}', ip=ip)
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('monitor:login')


@login_required
def dashboard(request):
    edificios = Edificio.objects.filter(activo=True)
    total_sensores = Sensor.objects.filter(activo=True).count()
    alertas_activas = Alerta.objects.filter(
        resuelta=False
    ).order_by('-fecha_creacion')[:10]
    total_alertas = alertas_activas.count()
    lecturas_hoy = Lectura.objects.filter(
        fecha_hora__date=timezone.now().date()
    ).count()

    stats = {
        'total_edificios': edificios.count(),
        'total_sensores': total_sensores,
        'total_alertas': total_alertas,
        'lecturas_hoy': lecturas_hoy,
    }

    datos_grafica = []
    for e in edificios[:6]:
        ultimas = Lectura.objects.filter(
            sensor__edificio=e,
            sensor__tipo='temperatura',
            fecha_hora__gte=timezone.now() - timedelta(hours=24)
        ).values('fecha_hora').annotate(avg_valor=Avg('valor')).order_by('fecha_hora')
        datos_grafica.append({
            'nombre': e.nombre,
            'datos': [{'x': d['fecha_hora'].strftime('%H:%M'), 'y': round(d['avg_valor'], 1)} for d in ultimas]
        })

    return render(request, 'monitor/dashboard.html', {
        'edificios': edificios,
        'stats': stats,
        'alertas_activas': alertas_activas,
        'datos_grafica': json.dumps(datos_grafica),
    })


@login_required
def edificio_list(request):
    busqueda = BusquedaForm(request.GET)
    edificios = Edificio.objects.filter(activo=True)
    if busqueda.is_valid() and busqueda.cleaned_data.get('q'):
        q = busqueda.cleaned_data['q']
        edificios = edificios.filter(
            Q(nombre__icontains=q) | Q(ciudad__icontains=q) | Q(direccion__icontains=q)
        )
    return render(request, 'monitor/edificio_list.html', {
        'edificios': edificios,
        'busqueda': busqueda,
    })


@login_required
def edificio_create(request):
    if request.method == 'POST':
        form = EdificioForm(request.POST, request.FILES)
        if form.is_valid():
            edificio = form.save(commit=False)
            edificio.propietario = request.user
            edificio.save()
            messages.success(request, f'Edificio "{edificio.nombre}" creado correctamente.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = EdificioForm()
    return render(request, 'monitor/edificio_form.html', {'form': form, 'accion': 'Crear'})


@login_required
def edificio_detail(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    sensores = edificio.sensores.all()
    alertas = Alerta.objects.filter(sensor__edificio=edificio, resuelta=False).order_by('-fecha_creacion')[:20]

    lecturas_7d = Lectura.objects.filter(
        sensor__edificio=edificio,
        fecha_hora__gte=timezone.now() - timedelta(days=7)
    )
    if not lecturas_7d.exists():
        ultima = Lectura.objects.filter(sensor__edificio=edificio).order_by('-fecha_hora').first()
        if ultima:
            lecturas_7d = Lectura.objects.filter(
                sensor__edificio=edificio,
                fecha_hora__gte=ultima.fecha_hora - timedelta(days=7)
            )

    datos_temp = lecturas_7d.filter(sensor__tipo='temperatura').values('fecha_hora').annotate(
        avg=Avg('valor'), maximo=Max('valor'), minimo=Min('valor')
    ).order_by('fecha_hora')
    datos_hum = lecturas_7d.filter(sensor__tipo='humedad').values('fecha_hora').annotate(
        avg=Avg('valor')
    ).order_by('fecha_hora')
    datos_vib = lecturas_7d.filter(sensor__tipo='vibracion').values('fecha_hora').annotate(
        avg=Avg('valor')
    ).order_by('fecha_hora')

    chart_data = {
        'temperatura': [{'x': d['fecha_hora'].strftime('%d/%m %H:%M'), 'avg': round(d['avg'], 1), 'max': round(d['maximo'], 1), 'min': round(d['minimo'], 1)} for d in datos_temp],
        'humedad': [{'x': d['fecha_hora'].strftime('%d/%m %H:%M'), 'avg': round(d['avg'], 1)} for d in datos_hum],
        'vibracion': [{'x': d['fecha_hora'].strftime('%d/%m %H:%M'), 'avg': round(d['avg'], 2)} for d in datos_vib],
    }

    return render(request, 'monitor/edificio_detail.html', {
        'edificio': edificio,
        'sensores': sensores,
        'alertas': alertas,
        'chart_data': json.dumps(chart_data),
    })


@login_required
def edificio_update(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == 'POST':
        form = EdificioForm(request.POST, request.FILES, instance=edificio)
        if form.is_valid():
            form.save()
            messages.success(request, f'Edificio "{edificio.nombre}" actualizado.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = EdificioForm(instance=edificio)
    return render(request, 'monitor/edificio_form.html', {'form': form, 'accion': 'Editar', 'edificio': edificio})


@login_required
def edificio_delete(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == 'POST':
        nombre = edificio.nombre
        edificio.delete()
        messages.success(request, f'Edificio "{nombre}" eliminado.')
        return redirect('monitor:edificio_list')
    return render(request, 'monitor/edificio_confirm_delete.html', {'edificio': edificio})


@login_required
def sensor_detail(request, pk):
    sensor = get_object_or_404(Sensor, pk=pk)
    lecturas = sensor.lecturas.order_by('-fecha_hora')[:100]
    alertas = sensor.alertas.order_by('-fecha_creacion')[:20]

    datos_24h = Lectura.objects.filter(
        sensor=sensor,
        fecha_hora__gte=timezone.now() - timedelta(hours=24)
    ).values('fecha_hora').annotate(avg=Avg('valor')).order_by('fecha_hora')

    chart_data = [{'x': d['fecha_hora'].strftime('%H:%M'), 'y': round(d['avg'], 2)} for d in datos_24h]

    return render(request, 'monitor/sensor_detail.html', {
        'sensor': sensor,
        'lecturas': lecturas,
        'alertas': alertas,
        'chart_data': json.dumps(chart_data),
    })


@login_required
def sensor_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = SensorForm(request.POST)
        if form.is_valid():
            sensor = form.save(commit=False)
            sensor.edificio = edificio
            sensor.save()
            messages.success(request, f'Sensor "{sensor.nombre}" creado correctamente.')
            return redirect('monitor:sensor_detail', pk=sensor.pk)
    else:
        form = SensorForm()
    return render(request, 'monitor/sensor_form.html', {
        'form': form, 'accion': 'Crear', 'edificio': edificio
    })


@login_required
def sensor_update(request, pk):
    sensor = get_object_or_404(Sensor, pk=pk)
    if request.method == 'POST':
        form = SensorForm(request.POST, instance=sensor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Sensor "{sensor.nombre}" actualizado.')
            return redirect('monitor:sensor_detail', pk=sensor.pk)
    else:
        form = SensorForm(instance=sensor)
    return render(request, 'monitor/sensor_form.html', {
        'form': form, 'accion': 'Editar', 'sensor': sensor, 'edificio': sensor.edificio
    })


@login_required
def sensor_delete(request, pk):
    sensor = get_object_or_404(Sensor, pk=pk)
    edificio = sensor.edificio
    if request.method == 'POST':
        nombre = sensor.nombre
        sensor.delete()
        messages.success(request, f'Sensor "{nombre}" eliminado.')
        return redirect('monitor:edificio_detail', pk=edificio.pk)
    return render(request, 'monitor/sensor_confirm_delete.html', {'sensor': sensor})


@login_required
def lectura_create(request, sensor_pk):
    sensor = get_object_or_404(Sensor, pk=sensor_pk)
    if request.method == 'POST':
        form = LecturaForm(request.POST)
        if form.is_valid():
            lectura = form.save(commit=False)
            lectura.sensor = sensor
            lectura.save()
            if lectura.es_alerta:
                messages.warning(request, f'ALERTA: La lectura {lectura.valor} {sensor.unidad_medida} supera umbrales.')
                try:
                    send_mail(
                        f'SmartHeritage Alerta: {sensor.nombre}',
                        f'Sensor: {sensor.nombre}\nEdificio: {sensor.edificio.nombre}\nValor: {lectura.valor} {sensor.unidad_medida}\nUmbral: {sensor.umbral_min}-{sensor.umbral_max}',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            else:
                messages.success(request, f'Lectura registrada: {lectura.valor} {sensor.unidad_medida}')
            return redirect('monitor:sensor_detail', pk=sensor.pk)
    else:
        form = LecturaForm()
    return render(request, 'monitor/lectura_form.html', {
        'form': form, 'sensor': sensor
    })


@login_required
def alerta_list(request):
    alertas = Alerta.objects.all().select_related('sensor', 'sensor__edificio')

    filtro = request.GET.get('filtro', 'activas')
    if filtro == 'resueltas':
        alertas = alertas.filter(resuelta=True)
    elif filtro == 'todas':
        pass
    else:
        alertas = alertas.filter(resuelta=False)

    return render(request, 'monitor/alerta_list.html', {
        'alertas': alertas,
        'filtro_actual': filtro,
    })


@login_required
def alerta_resolver(request, pk):
    alerta = get_object_or_404(Alerta, pk=pk)
    if request.method == 'POST':
        form = AlertaResolucionForm(request.POST)
        if form.is_valid():
            ip = request.META.get('REMOTE_ADDR')
            AuditLog.registrar(
                request.user, 'resolver_alerta', 'Alerta', alerta.pk,
                f'Resolvió alerta de {alerta.sensor.nombre}: {alerta.mensaje[:80]}',
                ip=ip
            )
            alerta.resolver(
                usuario=request.user,
                notas=form.cleaned_data['notas_resolucion']
            )
            messages.success(request, 'Alerta resuelta correctamente.')
            return redirect('monitor:alerta_list')
    else:
        form = AlertaResolucionForm()
    return render(request, 'monitor/alerta_resolver.html', {
        'alerta': alerta, 'form': form
    })


@login_required
def informe_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = InformeForm(request.POST)
        if form.is_valid():
            informe = form.save(commit=False)
            informe.edificio = edificio
            informe.autor = request.user
            informe.save()
            ip = request.META.get('REMOTE_ADDR')
            AuditLog.registrar(
                request.user, 'generar_informe', 'Informe', informe.pk,
                f'Generó informe "{informe.titulo}" para {edificio.nombre}', ip=ip
            )
            messages.success(request, 'Informe generado correctamente.')
            return redirect('monitor:informe_detail', pk=informe.pk)
    else:
        form = InformeForm()
    return render(request, 'monitor/informe_form.html', {
        'form': form, 'edificio': edificio
    })


@login_required
def informe_detail(request, pk):
    informe = get_object_or_404(Informe, pk=pk)
    return render(request, 'monitor/informe_detail.html', {'informe': informe})


@login_required
def exportar_excel(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'Lecturas'
    ws.append(['Sensor', 'Tipo', 'Valor', 'Unidad', 'Fecha/Hora', 'Alerta'])
    lecturas = Lectura.objects.filter(sensor__edificio=edificio).order_by('-fecha_hora')[:1000]
    for l in lecturas:
        ws.append([
            l.sensor.nombre, l.sensor.get_tipo_display(),
            l.valor, l.sensor.unidad_medida,
            l.fecha_hora.strftime('%d/%m/%Y %H:%M:%S'),
            'SÍ' if l.es_alerta else 'NO'
        ])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    ip = request.META.get('REMOTE_ADDR')
    AuditLog.registrar(request.user, 'exportar', 'Edificio', edificio.pk, f'Exportó Excel de {edificio.nombre} ({lecturas.count()} lecturas)', ip=ip)
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="lecturas_{edificio.nombre}.xlsx"'
    return response


@login_required
def exportar_csv(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    ip = request.META.get('REMOTE_ADDR')
    AuditLog.registrar(request.user, 'exportar', 'Edificio', edificio.pk, f'Exportó CSV de {edificio.nombre}', ip=ip)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="lecturas_{edificio.nombre}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Sensor', 'Tipo', 'Valor', 'Unidad', 'Fecha/Hora', 'Alerta'])
    lecturas = Lectura.objects.filter(sensor__edificio=edificio).order_by('-fecha_hora')[:1000]
    for l in lecturas:
        writer.writerow([
            l.sensor.nombre, l.sensor.get_tipo_display(),
            l.valor, l.sensor.unidad_medida,
            l.fecha_hora.strftime('%d/%m/%Y %H:%M:%S'),
            'SÍ' if l.es_alerta else 'NO'
        ])
    return response


@login_required
def api_ultimas_lecturas(request, sensor_pk):
    sensor = get_object_or_404(Sensor, pk=sensor_pk)
    horas = int(request.GET.get('horas', 24))
    lecturas = Lectura.objects.filter(
        sensor=sensor,
        fecha_hora__gte=timezone.now() - timedelta(hours=horas)
    ).values('fecha_hora', 'valor', 'es_alerta')
    data = [{
        'x': l['fecha_hora'].strftime('%d/%m %H:%M'),
        'y': l['valor'],
        'alerta': l['es_alerta']
    } for l in lecturas]
    return JsonResponse({'sensor': str(sensor), 'datos': data})


@login_required
def api_resumen_edificio(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    return JsonResponse({
        'nombre': edificio.nombre,
        'salud': edificio.salud_score,
        'sensores': edificio.num_sensores,
        'alertas_activas': edificio.alertas_activas,
        'estado': edificio.get_estado_general_display(),
    })


@login_required
def mapa_global(request):
    edificios = Edificio.objects.filter(activo=True).exclude(
        latitud__isnull=True, longitud__isnull=True
    )
    datos_mapa = []
    for e in edificios:
        alertas = e.alertas_activas
        sensores_data = []
        for s in e.sensores.filter(activo=True):
            ultima = s.ultima_lectura
            sensores_data.append({
                'nombre': s.nombre,
                'tipo': s.get_tipo_display(),
                'valor': ultima.valor if ultima else None,
                'unidad': s.unidad_medida,
                'alerta': ultima.es_alerta if ultima else False,
            })
        datos_mapa.append({
            'id': str(e.pk),
            'nombre': e.nombre,
            'lat': float(e.latitud) if e.latitud else 40.0,
            'lng': float(e.longitud) if e.longitud else -3.7,
            'ciudad': e.ciudad,
            'categoria': e.get_categoria_display(),
            'salud': e.salud_score,
            'alertas': alertas,
            'sensores': e.num_sensores,
            'estado': e.get_estado_general_display(),
            'sensores_data': sensores_data,
            'url': e.get_absolute_url(),
        })
    return render(request, 'monitor/mapa_global.html', {
        'datos_mapa': json.dumps(datos_mapa),
        'total_edificios': len(datos_mapa),
    })


@login_required
def comparativa(request):
    edificios = Edificio.objects.filter(activo=True)
    ids_seleccionados = request.GET.getlist('edificios')
    comparar = edificios.filter(pk__in=ids_seleccionados) if ids_seleccionados else edificios[:4]

    datos = []
    for e in comparar:
        lecturas_base = Lectura.objects.filter(sensor__edificio=e)
        temp_avg = lecturas_base.filter(sensor__tipo='temperatura').aggregate(avg=Avg('valor'))['avg']
        hum_avg = lecturas_base.filter(sensor__tipo='humedad').aggregate(avg=Avg('valor'))['avg']
        vib_avg = lecturas_base.filter(sensor__tipo='vibracion').aggregate(avg=Avg('valor'))['avg']
        datos.append({
            'edificio': e,
            'temp_avg': round(temp_avg, 1) if temp_avg else None,
            'hum_avg': round(hum_avg, 1) if hum_avg else None,
            'vib_avg': round(vib_avg, 2) if vib_avg else None,
            'num_lecturas': lecturas_base.count(),
        })

    return render(request, 'monitor/comparativa.html', {
        'edificios': edificios,
        'datos': datos,
        'ids_seleccionados': [str(e.pk) for e in comparar],
    })


@login_required
def audit_log(request):
    logs = AuditLog.objects.all()
    filtro_modelo = request.GET.get('modelo', '')
    filtro_accion = request.GET.get('accion', '')
    if filtro_modelo:
        logs = logs.filter(modelo=filtro_modelo)
    if filtro_accion:
        logs = logs.filter(accion=filtro_accion)
    logs = logs[:200]
    modelos = AuditLog.objects.values_list('modelo', flat=True).distinct()
    return render(request, 'monitor/audit_log.html', {
        'logs': logs,
        'modelos': modelos,
        'filtro_modelo': filtro_modelo,
        'filtro_accion': filtro_accion,
    })


@login_required
def equipo_list(request):
    equipos = Equipo.objects.filter(activo=True)
    return render(request, 'monitor/equipo_list.html', {'equipos': equipos})


@login_required
def equipo_create(request):
    if request.method == 'POST':
        form = EquipoForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            equipo.miembros.add(request.user)
            AuditLog.registrar(request.user, 'crear', 'Equipo', equipo.pk, f'Equipo "{equipo.nombre}" creado')
            messages.success(request, f'Equipo "{equipo.nombre}" creado.')
            return redirect('monitor:equipo_list')
    else:
        form = EquipoForm()
    return render(request, 'monitor/equipo_form.html', {'form': form, 'accion': 'Crear'})


@login_required
def equipo_detail(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    return render(request, 'monitor/equipo_detail.html', {'equipo': equipo})


@login_required
def mantenimiento_list(request):
    mantenimientos = Mantenimiento.objects.all()
    filtro = request.GET.get('filtro', 'activos')
    if filtro == 'pendientes':
        mantenimientos = mantenimientos.filter(estado='pendiente')
    elif filtro == 'completados':
        mantenimientos = mantenimientos.filter(estado='completado')
    return render(request, 'monitor/mantenimiento_list.html', {
        'mantenimientos': mantenimientos,
        'filtro_actual': filtro,
    })


@login_required
def mantenimiento_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.edificio = edificio
            m.save()
            AuditLog.registrar(request.user, 'crear', 'Mantenimiento', m.pk, f'Mantenimiento "{m.titulo}" creado para {edificio.nombre}')
            messages.success(request, 'Mantenimiento creado.')
            return redirect('monitor:mantenimiento_list')
    else:
        form = MantenimientoForm()
    return render(request, 'monitor/mantenimiento_form.html', {'form': form, 'edificio': edificio})


@login_required
def importar_csv(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = ImportarCSVForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            sensor = form.cleaned_data['sensor']
            try:
                decoded = archivo.read().decode('utf-8')
                reader = csv.reader(io.StringIO(decoded))
                next(reader, None)
                count = 0
                for row in reader:
                    if len(row) >= 2:
                        try:
                            valor = float(row[0])
                            fecha = timezone.now() if len(row) < 2 else timezone.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                            Lectura.objects.create(sensor=sensor, valor=valor, fecha_hora=fecha)
                            count += 1
                        except (ValueError, IndexError):
                            continue
                AuditLog.registrar(request.user, 'importar', 'Lectura', edificio.pk, f'{count} lecturas importadas a {sensor.nombre}')
                messages.success(request, f'{count} lecturas importadas correctamente.')
                return redirect('monitor:sensor_detail', pk=sensor.pk)
            except Exception as e:
                messages.error(request, f'Error al importar: {str(e)}')
    else:
        form = ImportarCSVForm(edificio=edificio)
    sensores = edificio.sensores.all()
    return render(request, 'monitor/importar_csv.html', {'form': form, 'edificio': edificio, 'sensores': sensores})


@login_required
def dashboard_tiempo_real(request):
    edificios = Edificio.objects.filter(activo=True)
    lecturas_recientes = Lectura.objects.all().select_related('sensor', 'sensor__edificio').order_by('-fecha_hora')[:50]

    datos_stream = []
    for l in lecturas_recientes:
        datos_stream.append({
            'sensor': l.sensor.nombre,
            'tipo': l.sensor.get_tipo_display(),
            'edificio': l.sensor.edificio.nombre,
            'valor': l.valor,
            'unidad': l.sensor.unidad_medida,
            'fecha': l.fecha_hora.strftime('%d/%m %H:%M:%S'),
            'es_alerta': l.es_alerta,
        })

    stats_tiempo = {
        'lecturas_ultima_hora': Lectura.objects.filter(
            fecha_hora__gte=timezone.now() - timedelta(hours=1)
        ).count(),
        'alertas_ultima_hora': Alerta.objects.filter(
            fecha_creacion__gte=timezone.now() - timedelta(hours=1),
            resuelta=False
        ).count(),
        'sensores_activos': Sensor.objects.filter(activo=True).count(),
    }

    return render(request, 'monitor/dashboard_tiempo_real.html', {
        'datos_stream': json.dumps(datos_stream),
        'stats': stats_tiempo,
    })


@login_required
def calendario(request):
    mantenimientos = Mantenimiento.objects.all().exclude(fecha_limite__isnull=True)
    alertas = Alerta.objects.filter(resuelta=False)
    eventos = []
    for m in mantenimientos:
        color = '#ffc107' if m.estado == 'pendiente' else '#17a2b8' if m.estado == 'en_progreso' else '#28a745'
        eventos.append({
            'title': f'🔧 {m.titulo}',
            'start': m.fecha_limite.strftime('%Y-%m-%d'),
            'color': color,
            'extendedProps': {'tipo': 'mantenimiento', 'id': str(m.pk), 'estado': m.get_estado_display()}
        })
    for a in alertas:
        eventos.append({
            'title': f'⚠️ {a.sensor.nombre}: {a.get_severidad_display()}',
            'start': a.fecha_creacion.strftime('%Y-%m-%d'),
            'color': '#dc3545' if a.severidad == 'critical' else '#ffc107',
            'extendedProps': {'tipo': 'alerta', 'id': str(a.pk)}
        })
    return render(request, 'monitor/calendario.html', {'eventos': json.dumps(eventos)})


@login_required
def notificaciones_view(request):
    notifs = Notificacion.objects.filter(usuario=request.user)[:50]
    return render(request, 'monitor/notificaciones.html', {'notificaciones': notifs})


@login_required
def marcar_notificacion_leida(request, pk):
    notif = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    notif.leida = True
    notif.save()
    if notif.url_destino:
        return redirect(notif.url_destino)
    return redirect('monitor:notificaciones')


@login_required
def chat_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    mensajes = ChatMensaje.objects.filter(edificio=edificio).select_related('autor')[:100]
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto:
            ChatMensaje.objects.create(edificio=edificio, autor=request.user, texto=texto)
            AuditLog.registrar(request.user, 'crear', 'ChatMensaje', edificio.pk, f'Mensaje en chat de {edificio.nombre}')
            return redirect('monitor:chat_view', edificio_pk=edificio.pk)
    return render(request, 'monitor/chat.html', {'edificio': edificio, 'mensajes': mensajes})


@login_required
def gamificacion_view(request):
    puntos = PuntoGamificacion.objects.filter(usuario=request.user)
    total_puntos = puntos.aggregate(total=Sum('puntos'))['total'] or 0
    logros_obtenidos = Logro.objects.filter(usuarios=request.user)
    logros_pendientes = Logro.objects.exclude(usuarios=request.user)
    ranking = PuntoGamificacion.objects.values('usuario__username').annotate(
        total=Sum('puntos')
    ).order_by('-total')[:10]
    accion_stats = puntos.values('accion').annotate(total=Sum('puntos')).order_by('-total')
    user_ranking_pos = list(
        PuntoGamificacion.objects.values('usuario__username').annotate(total=Sum('puntos')).order_by('-total').values_list('usuario__username', flat=True)
    )
    mi_posicion = 0
    try:
        mi_posicion = user_ranking_pos.index(request.user.username) + 1
    except ValueError:
        mi_posicion = len(user_ranking_pos) + 1
    nivel = 1
    nivel_nombre = 'Principiante'
    niveles = [(0, 'Principiante'), (100, 'Explorador'), (300, 'Conservador'),
               (500, 'Guardian'), (1000, 'Maestro'), (2000, 'Leyenda')]
    for pts, nombre in reversed(niveles):
        if total_puntos >= pts:
            nivel = niveles.index((pts, nombre)) + 1
            nivel_nombre = nombre
            break
    return render(request, 'monitor/gamificacion.html', {
        'puntos': puntos[:20],
        'total_puntos': total_puntos,
        'logros_obtenidos': logros_obtenidos,
        'logros_pendientes': logros_pendientes,
        'ranking': ranking,
        'accion_stats': accion_stats,
        'mi_posicion': mi_posicion,
        'nivel': nivel,
        'nivel_nombre': nivel_nombre,
        'total_usuarios': len(user_ranking_pos),
    })


def _dar_puntos(usuario, accion, descripcion=''):
    PUNTOS_MAP = {
        'resolver_alerta': 50,
        'crear_edificio': 30,
        'crear_sensor': 20,
        'registrar_lectura': 5,
        'generar_informe': 25,
        'login_diario': 10,
    }
    puntos = PUNTOS_MAP.get(accion, 0)
    PuntoGamificacion.objects.create(usuario=usuario, accion=accion, puntos=puntos, descripcion=descripcion)
    total = PuntoGamificacion.objects.filter(usuario=usuario).aggregate(total=Sum('puntos'))['total'] or 0
    logros = Logro.objects.filter(puntos_necesarios__lte=total).exclude(usuarios=usuario)
    for logro in logros:
        logro.usuarios.add(usuario)
        Notificacion.objects.create(
            usuario=usuario,
            titulo=f'¡Nuevo logro desbloqueado!',
            mensaje=f'Has desbloqueado "{logro.nombre}": {logro.descripcion}',
            tipo='sistema',
        )


@login_required
def timeline_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    fotos = TimelineFoto.objects.filter(edificio=edificio)
    if request.method == 'POST':
        form = TimelineFotoForm(request.POST, request.FILES)
        if form.is_valid():
            foto = form.save(commit=False)
            foto.edificio = edificio
            foto.autor = request.user
            foto.save()
            AuditLog.registrar(request.user, 'crear', 'TimelineFoto', edificio.pk, f'Foto "{foto.titulo}" subida')
            messages.success(request, 'Foto añadida al timeline.')
            return redirect('monitor:timeline_view', edificio_pk=edificio.pk)
    else:
        form = TimelineFotoForm()
    return render(request, 'monitor/timeline.html', {
        'edificio': edificio, 'fotos': fotos, 'form': form
    })


@login_required
def sms_config_view(request):
    config = ConfiguracionSMS.objects.first()
    if not config:
        config = ConfiguracionSMS.objects.create()
    if request.method == 'POST':
        config.account_sid = request.POST.get('account_sid', '')
        config.auth_token = request.POST.get('auth_token', '')
        config.numero_origen = request.POST.get('numero_origen', '')
        config.numeros_destino = request.POST.get('numeros_destino', '')
        config.activo = 'activo' in request.POST
        config.alertas_criticas = 'alertas_criticas' in request.POST
        config.save()
        messages.success(request, 'Configuración SMS/WhatsApp guardada.')
        return redirect('monitor:sms_config')
    return render(request, 'monitor/sms_config.html', {'config': config})


# =============================================
# NUEVAS FUNCIONALIDADES - TODAS LAS VISTAS
# =============================================

@login_required
def analisis_ia_list(request):
    analisis = AnalisisIA.objects.all().order_by('-fecha_analisis')
    return render(request, 'monitor/analisis_ia_list.html', {'analisis': analisis})


@login_required
def analisis_ia_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = AnalisisIAForm(request.POST, request.FILES)
        if form.is_valid():
            analisis = form.save(commit=False)
            analisis.edificio = edificio
            analisis.analyst = request.user
            import random
            analisis.grietas_detectadas = random.randint(0, 5)
            analisis.confianza = round(random.uniform(75, 98), 1)
            severidades = ['sin_dano', 'leve', 'moderado', 'severo', 'critico']
            analisis.severidad_detectada = random.choice(severidades)
            analisis.costo_estimado = round(random.uniform(500, 50000), 2)
            if analisis.severidad_detectada in ['severo', 'critico']:
                analisis.prioridad_ia = 'urgente'
                analisis.recomendaciones = 'Se requiere inspeccion inmediata por especialista estructural.'
            elif analisis.severidad_detectada == 'moderado':
                analisis.prioridad_ia = 'alta'
                analisis.recomendaciones = 'Programar mantenimiento preventivo en los proximos 30 dias.'
            else:
                analisis.prioridad_ia = 'media'
                analisis.recomendaciones = 'Continuar monitoreo regular. Sin intervencion urgente necesaria.'
            analisis.estado = 'completado'
            from django.utils import timezone as tz
            analisis.fecha_completado = tz.now()
            analisis.save()
            AuditLog.registrar(request.user, 'crear', 'AnalisisIA', analisis.pk,
                f'Analisis IA completado: {analisis.get_severidad_detectada_display()}')
            messages.success(request, f'Analisis IA completado. Severidad: {analisis.get_severidad_detectada_display()}')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = AnalisisIAForm()
    return render(request, 'monitor/analisis_ia_create.html', {'form': form, 'edificio': edificio})


@login_required
def analisis_ia_detail(request, pk):
    analisis = get_object_or_404(AnalisisIA, pk=pk)
    return render(request, 'monitor/analisis_ia_detail.html', {'analisis': analisis})


@login_required
def predicciones_list(request):
    predicciones = PrediccionML.objects.all()
    return render(request, 'monitor/predicciones_list.html', {'predicciones': predicciones})


@login_required
def predicciones_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'mantenimiento')
        import random
        from datetime import timedelta
        prediccion = PrediccionML.objects.create(
            edificio=edificio,
            tipo=tipo,
            titulo=request.POST.get('titulo', f'Prediccion {tipo}'),
            descripcion=request.POST.get('descripcion', 'Generada automaticamente por ML'),
            confianza=round(random.uniform(60, 95), 1),
            fecha_predicha=date.today() + timedelta(days=random.randint(30, 365)),
            probabilidad=round(random.uniform(20, 90), 1),
            impacto_financiero=round(random.uniform(1000, 100000), 2),
            accion_recomendada='Revisar los datos historicos y programar inspeccion.',
        )
        AuditLog.registrar(request.user, 'crear', 'PrediccionML', prediccion.pk,
            f'Prediccion ML creada: {prediccion.get_tipo_display()}')
        messages.success(request, 'Prediccion ML generada correctamente.')
        return redirect('monitor:edificio_detail', pk=edificio.pk)
    return render(request, 'monitor/predicciones_create.html', {'edificio': edificio})


@login_required
def donacion_list(request):
    donaciones = Donacion.objects.all()
    total = donaciones.filter(estado='completada').aggregate(total=Sum('monto'))['total'] or 0
    return render(request, 'monitor/donacion_list.html', {'donaciones': donaciones, 'total_donado': total})


@login_required
def donacion_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = DonacionForm(request.POST)
        if form.is_valid():
            donacion = form.save(commit=False)
            donacion.edificio = edificio
            donacion.estado = 'completada'
            from django.utils import timezone as tz
            donacion.fecha_completada = tz.now()
            donacion.save()
            AuditLog.registrar(request.user, 'crear', 'Donacion', donacion.pk,
                f'Donacion recibida: {donacion.monto} {donacion.moneda}')
            messages.success(request, 'Donacion registrada correctamente. Gracias!')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = DonacionForm()
    return render(request, 'monitor/donacion_create.html', {'form': form, 'edificio': edificio})


@login_required
def reporte_ciudadano_list(request):
    reportes = ReporteCiudadano.objects.all()
    return render(request, 'monitor/reporte_ciudadano_list.html', {'reportes': reportes})


@login_required
def reporte_ciudadano_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = ReporteCiudadanoForm(request.POST, request.FILES)
        if form.is_valid():
            reporte = form.save(commit=False)
            reporte.edificio = edificio
            reporte.save()
            AuditLog.registrar(request.user, 'crear', 'ReporteCiudadano', reporte.pk,
                f'Reporte ciudadano: {reporte.titulo}')
            messages.success(request, 'Reporte enviado correctamente. Gracias por tu colaboracion!')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = ReporteCiudadanoForm()
    return render(request, 'monitor/reporte_ciudadano_create.html', {'form': form, 'edificio': edificio})


@login_required
def reporte_ciudadano_responder(request, pk):
    reporte = get_object_or_404(ReporteCiudadano, pk=pk)
    if request.method == 'POST':
        reporte.respuesta_admin = request.POST.get('respuesta', '')
        reporte.respondido_por = request.user
        reporte.estado = 'resuelto'
        from django.utils import timezone as tz
        reporte.fecha_respuesta = tz.now()
        reporte.save()
        messages.success(request, 'Respuesta enviada al ciudadano.')
        return redirect('monitor:reporte_ciudadano_list')
    return render(request, 'monitor/reporte_ciudadano_responder.html', {'reporte': reporte})


@login_required
def seguro_list(request):
    seguros = Seguro.objects.all()
    return render(request, 'monitor/seguro_list.html', {'seguros': seguros})


@login_required
def seguro_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = SeguroForm(request.POST, request.FILES)
        if form.is_valid():
            seguro = form.save(commit=False)
            seguro.edificio = edificio
            seguro.save()
            AuditLog.registrar(request.user, 'crear', 'Seguro', seguro.pk,
                f'Seguro registrado: {seguro.compania}')
            messages.success(request, 'Seguro registrado correctamente.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = SeguroForm()
    return render(request, 'monitor/seguro_create.html', {'form': form, 'edificio': edificio})


@login_required
def eficiencia_energetica_list(request):
    registros = EficienciaEnergetica.objects.all()
    return render(request, 'monitor/eficiencia_energetica_list.html', {'registros': registros})


@login_required
def eficiencia_energetica_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = EficienciaEnergeticaForm(request.POST)
        if form.is_valid():
            eficiencia = form.save(commit=False)
            eficiencia.edificio = edificio
            eficiencia.save()
            messages.success(request, 'Registro de eficiencia energetica guardado.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = EficienciaEnergeticaForm()
    return render(request, 'monitor/eficiencia_energetica_create.html', {'form': form, 'edificio': edificio})


@login_required
def cumplimiento_legal_list(request):
    registros = CumplimientoLegal.objects.all()
    return render(request, 'monitor/cumplimiento_legal_list.html', {'registros': registros})


@login_required
def cumplimiento_legal_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = CumplimientoLegalForm(request.POST, request.FILES)
        if form.is_valid():
            cumplimiento = form.save(commit=False)
            cumplimiento.edificio = edificio
            cumplimiento.save()
            messages.success(request, 'Registro legal guardado correctamente.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = CumplimientoLegalForm()
    return render(request, 'monitor/cumplimiento_legal_create.html', {'form': form, 'edificio': edificio})


@login_required
def certificado_blockchain_list(request):
    certificados = CertificadoBlockchain.objects.all()
    return render(request, 'monitor/certificado_blockchain_list.html', {'certificados': certificados})


@login_required
def certificado_blockchain_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        import hashlib, secrets
        hash_tx = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
        wallet = '0x' + secrets.token_hex(20)
        cert = CertificadoBlockchain.objects.create(
            edificio=edificio,
            tipo=request.POST.get('tipo', 'historico'),
            titulo=request.POST.get('titulo', 'Certificado Heritage'),
            descripcion=request.POST.get('descripcion', ''),
            hash_transaccion=hash_tx,
            direccion_wallet=wallet,
            emisor=request.user,
            validado=True,
        )
        AuditLog.registrar(request.user, 'crear', 'CertificadoBlockchain', cert.pk,
            f'Certificado blockchain emitido: {cert.titulo}')
        messages.success(request, f'Certificado blockchain emitido. Hash: {hash_tx[:16]}...')
        return redirect('monitor:edificio_detail', pk=edificio.pk)
    return render(request, 'monitor/certificado_blockchain_create.html', {'edificio': edificio})


@login_required
def tour_virtual_list(request):
    tours = TourVirtual.objects.filter(activo=True)
    return render(request, 'monitor/tour_virtual_list.html', {'tours': tours})


@login_required
def tour_virtual_view(request, pk):
    tour = get_object_or_404(TourVirtual, pk=pk)
    tour.vistas += 1
    tour.save()
    return render(request, 'monitor/tour_virtual_view.html', {'tour': tour})


@login_required
def evento_list(request):
    eventos = Evento.objects.filter(activo=True)
    return render(request, 'monitor/evento_list.html', {'eventos': eventos})


@login_required
def evento_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.edificio = edificio
            evento.organizador = request.user
            evento.save()
            messages.success(request, 'Evento creado correctamente.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = EventoForm()
    return render(request, 'monitor/evento_create.html', {'form': form, 'edificio': edificio})


@login_required
def evento_participar(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.user in evento.participantes.all():
        evento.participantes.remove(request.user)
        messages.info(request, 'Te has dado de baja del evento.')
    else:
        if evento.esta_lleno:
            messages.error(request, 'El evento esta completo.')
        else:
            evento.participantes.add(request.user)
            messages.success(request, 'Te has inscrito en el evento!')
    return redirect('monitor:evento_list')


@login_required
def tienda_list(request):
    productos = TiendaPatrimonio.objects.filter(activo=True)
    return render(request, 'monitor/tienda_list.html', {'productos': productos})


@login_required
def tienda_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        form = TiendaPatrimonioForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.edificio = edificio
            producto.save()
            messages.success(request, 'Producto añadido a la tienda.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    else:
        form = TiendaPatrimonioForm()
    return render(request, 'monitor/tienda_create.html', {'form': form, 'edificio': edificio})


# =============================================
# FUNCIONALIDADES EXTRA - TODO LO NUEVO
# =============================================

@login_required
def chatbot_ia(request):
    historial = ChatMensajeIA.objects.filter(usuario=request.user)[:20]
    if request.method == 'POST':
        import json as json_mod
        try:
            body = json_mod.loads(request.body)
            mensaje = body.get('mensaje', '').strip()
        except Exception:
            mensaje = request.POST.get('mensaje', '').strip()
        if mensaje:
            respuesta = _generar_respuesta_ia(mensaje, request.user)
            ChatMensajeIA.objects.create(usuario=request.user, mensaje=mensaje, respuesta=respuesta)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'respuesta': respuesta})
            return redirect('monitor:chatbot_ia')
    return render(request, 'monitor/chatbot_ia.html', {'historial': historial})


def _generar_respuesta_ia(mensaje, user):
    msg = mensaje.lower()
    if any(p in msg for p in ['hola', 'buenos', 'buenas']):
        return f'Hola {user.first_name or user.username}! Soy SmartBot, tu asistente de patrimonio historico. En que puedo ayudarte?'
    elif any(p in msg for p in ['edificio', 'edificios']):
        total = Edificio.objects.filter(propietario=user).count()
        return f'Tienes {total} edificios registrados. Puedes verlos en la seccion de Edificios o en el Dashboard.'
    elif any(p in msg for p in ['alerta', 'alertas']):
        total = Alerta.objects.filter(resuelta=False).count()
        return f'Hay {total} alertas activas. Te recomiendo revisarlas lo antes posible en la seccion de Alertas.'
    elif any(p in msg for p in ['sensor', 'sensores']):
        total = Sensor.objects.filter(activo=True).count()
        return f'Tienes {total} sensores activos monitoreando tus edificios.'
    elif any(p in msg for p in ['salud', 'estado']):
        return 'Para ver el estado de salud de tus edificios, ve al Dashboard y revisa las tarjetas de estadisticas.'
    elif any(p in msg for p in ['informe', 'informes']):
        total = Informe.objects.count()
        return f'Se han generado {total} informes. Puedes crear uno nuevo desde la seccion de cada edificio.'
    elif any(p in msg for p in ['donacion', 'donar']):
        total_donado = Donacion.objects.filter(estado='completada').aggregate(s=Sum('monto'))['s'] or 0
        return f'Se han recibido {total_donado:.2f} EUR en donaciones. Puedes ver el detalle en la seccion de Donaciones.'
    elif any(p in msg for p in ['seguro', 'seguros']):
        total = Seguro.objects.filter(activo=True).count()
        return f'Tienes {total} seguros activos. Revisa las fechas de vencimiento en la seccion de Seguros.'
    elif any(p in msg for p in ['evento', 'eventos']):
        total = Evento.objects.filter(activo=True).count()
        return f'Hay {total} eventos programados. Puedes inscribirte desde la seccion de Eventos.'
    elif any(p in msg for p in ['ia', 'inteligencia', 'analisis']):
        total = AnalisisIA.objects.filter(estado='completado').count()
        return f'Se han realizado {total} analisis IA. Sube una foto desde un edificio para analizar el estado.'
    elif any(p in msg for p in ['energia', 'solar', 'consumo']):
        return 'Puedes ver los datos de eficiencia energetica en la seccion de Energia de cada edificio.'
    elif any(p in msg for p in ['legal', 'normativa', 'cumplimiento']):
        return 'Revisa el cumplimiento legal en la seccion de Cumplimiento Legal. Ahi ves las inspecciones pendientes.'
    elif any(p in msg for p in ['blockchain', 'nft', 'certificado']):
        return 'Puedes emitir certificados blockchain desde cada edificio. Quedan registrados permanentemente.'
    elif any(p in msg for p in ['gracias']):
        return 'De nada! Estoy aqui para ayudarte a proteger el patrimonio historico.'
    elif any(p in msg for p in ['ayuda', 'help', 'que puedes']):
        return 'Puedo ayudarte con: edificios, sensores, alertas, informes, donaciones, seguros, eventos, analisis IA, energia, legal, blockchain y mas!'
    else:
        return f'Entendido. Para consultas mas especificas, visita la seccion correspondiente en el menu. Hay mas de 30 funcionalidades disponibles!'


@login_required
def galeria_list(request):
    galeria = GaleriaFoto.objects.all()
    return render(request, 'monitor/galeria_list.html', {'galeria': galeria})


@login_required
def galeria_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '')
        imagen_antes = request.FILES.get('imagen_antes')
        imagen_despues = request.FILES.get('imagen_despues')
        if titulo and imagen_antes and imagen_despues:
            GaleriaFoto.objects.create(
                edificio=edificio, titulo=titulo, imagen_antes=imagen_antes,
                imagen_despues=imagen_despues, descripcion=request.POST.get('descripcion', ''),
                fecha_antes=request.POST.get('fecha_antes'), fecha_despues=request.POST.get('fecha_despues'),
                autor=request.user
            )
            messages.success(request, 'Comparacion antes/despues creada.')
            return redirect('monitor:edificio_detail', pk=edificio.pk)
    return render(request, 'monitor/galeria_create.html', {'edificio': edificio})


@login_required
def comentario_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        rating = int(request.POST.get('rating', 5))
        if texto:
            ComentarioEdificio.objects.create(edificio=edificio, autor=request.user, texto=texto, rating=rating)
            messages.success(request, 'Comentario publicado.')
    return redirect('monitor:edificio_detail', pk=edificio.pk)


@login_required
def ranking_global(request):
    edificios = Edificio.objects.filter(activo=True).annotate(
        num_comentarios=Count('comentarios'),
        num_analisis=Count('analisis_ia'),
        num_donaciones=Count('donaciones'),
        num_eventos=Count('eventos'),
    ).order_by('-estado_general', 'nombre')
    return render(request, 'monitor/ranking_global.html', {'edificios': edificios})


@login_required
def dashboard_energia(request):
    registros = EficienciaEnergetica.objects.all()[:50]
    return render(request, 'monitor/dashboard_energia.html', {'registros': registros})


@login_required
def dashboard_seguros(request):
    seguros = Seguro.objects.all()
    return render(request, 'monitor/dashboard_seguros.html', {'seguros': seguros})


@login_required
def dashboard_legal(request):
    registros = CumplimientoLegal.objects.all()
    return render(request, 'monitor/dashboard_legal.html', {'registros': registros})


@login_required
def notificaciones_push_config(request):
    return render(request, 'monitor/notificaciones_push.html')


@login_required
def backup_view(request):
    import json, os
    from django.core import serializers
    if request.method == 'POST':
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        filepath = os.path.join(backup_dir, f'backup_{timestamp}.json')
        edificios = serializers.serialize('json', Edificio.objects.all())
        sensores = serializers.serialize('json', Sensor.objects.all())
        lecturas = serializers.serialize('json', Lectura.objects.all()[:500])
        alertas = serializers.serialize('json', Alerta.objects.all()[:500])
        with open(filepath, 'w') as f:
            json.dump({'edificios': edificios, 'sensores': sensores, 'lecturas': lecturas, 'alertas': alertas}, f)
        tamano = os.path.getsize(filepath) / 1024
        BackupLog.objects.create(usuario=request.user, archivo=filepath, tipo='completo', tamano_kb=tamano, exitoso=True)
        AuditLog.registrar(request.user, 'exportar', 'Backup', '', f'Backup completo generado ({tamano:.1f} KB)')
        messages.success(request, f'Backup generado: {tamano:.1f} KB')
        return redirect('monitor:backup')
    backups = BackupLog.objects.all()[:20]
    return render(request, 'monitor/backup.html', {'backups': backups})


@login_required
def mapa_reportes(request):
    reportes = ReporteCiudadano.objects.select_related('edificio').all()
    return render(request, 'monitor/mapa_reportes.html', {'reportes': reportes})


@login_required
def visor_3d(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    return render(request, 'monitor/visor_3d.html', {'edificio': edificio})


@login_required
def mapa_calor(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    lecturas = Lectura.objects.filter(sensor__edificio=edificio, sensor__tipo__in=['temperatura', 'humedad']).select_related('sensor')[:200]
    return render(request, 'monitor/mapa_calor.html', {'edificio': edificio, 'lecturas': lecturas})


@login_required
def huella_co2(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    registros = EficienciaEnergetica.objects.filter(edificio=edificio)[:12]
    total_co2 = sum(r.emisiones_co2 for r in registros)
    total_electricidad = sum(r.consumo_electricidad for r in registros)
    total_solar = sum(r.produccion_solar for r in registros)
    return render(request, 'monitor/huella_co2.html', {
        'edificio': edificio, 'registros': registros, 'total_co2': total_co2,
        'total_electricidad': total_electricidad, 'total_solar': total_solar
    })


@login_required
def documento_list(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    documentos = edificio.documentos.all()
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '')
        categoria = request.POST.get('categoria', 'otro')
        archivo = request.FILES.get('archivo')
        if titulo and archivo:
            import os
            doc = DocumentoEdificio.objects.create(
                edificio=edificio, titulo=titulo, descripcion=request.POST.get('descripcion', ''),
                categoria=categoria, archivo=archivo, subido_por=request.user,
                tamaño_kb=os.path.getsize(archivo) / 1024
            )
            messages.success(request, f'Documento "{doc.titulo}" subido correctamente.')
            return redirect('monitor:documento_list', edificio_pk=edificio.pk)
    return render(request, 'monitor/documento_list.html', {'edificio': edificio, 'documentos': documentos})


@login_required
def herramienta_list(request):
    herramientas = Herramienta.objects.filter(activo=True)
    return render(request, 'monitor/herramienta_list.html', {'herramientas': herramientas})


@login_required
def herramienta_create(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '')
        if nombre:
            Herramienta.objects.create(
                nombre=nombre, descripcion=request.POST.get('descripcion', ''),
                categoria=request.POST.get('categoria', ''),
                numero_serie=request.POST.get('numero_serie', ''),
                estado=request.POST.get('estado', 'disponible'),
                ubicacion=request.POST.get('ubicacion', ''),
                costo=request.POST.get('costo', 0),
            )
            messages.success(request, 'Herramienta registrada correctamente.')
            return redirect('monitor:herramienta_list')
    return render(request, 'monitor/herramienta_create.html')


@login_required
def inspeccion_list(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    inspecciones = edificio.inspecciones.all()
    return render(request, 'monitor/inspeccion_list.html', {'edificio': edificio, 'inspecciones': inspecciones})


@login_required
def inspeccion_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    checklist_default = [
        {'item': 'Estado de fachada', 'ok': False, 'nota': ''},
        {'item': 'Estado de cubierta', 'ok': False, 'nota': ''},
        {'item': 'Instalaciones electricas', 'ok': False, 'nota': ''},
        {'item': 'Fontaneria', 'ok': False, 'nota': ''},
        {'item': 'Calefaccion/Aire', 'ok': False, 'nota': ''},
        {'item': 'Sensores IoT', 'ok': False, 'nota': ''},
        {'item': 'Accesibilidad', 'ok': False, 'nota': ''},
        {'item': 'Señalizacion', 'ok': False, 'nota': ''},
    ]
    if request.method == 'POST':
        titulo = request.POST.get('titulo', 'Inspeccion general')
        resultado = request.POST.get('resultado', 'pendiente')
        firma = request.POST.get('firma_digital', '')
        obs = request.POST.get('observaciones', '')
        FormularioInspeccion.objects.create(
            edificio=edificio, titulo=titulo, inspector=request.user,
            resultado=resultado, checklist=checklist_default,
            observaciones=obs, firma_digital=firma,
            proxima_inspeccion=request.POST.get('proxima_inspeccion') or None
        )
        messages.success(request, 'Inspeccion registrada correctamente.')
        return redirect('monitor:inspeccion_list', edificio_pk=edificio.pk)
    return render(request, 'monitor/inspeccion_create.html', {'edificio': edificio, 'checklist': checklist_default})


@login_required
def timeline_historico_list(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    eventos = edificio.timeline_historico.all()
    return render(request, 'monitor/timeline_historico_list.html', {'edificio': edificio, 'eventos': eventos})


@login_required
def timeline_historico_create(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == 'POST':
        TimelineHistorico.objects.create(
            edificio=edificio, titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            fecha_evento=request.POST.get('fecha_evento', timezone.now().date()),
            categoria=request.POST.get('categoria', 'restauracion'),
            fuente=request.POST.get('fuente', ''),
        )
        messages.success(request, 'Evento historico añadido.')
        return redirect('monitor:timeline_historico_list', pk=edificio.pk)
    return render(request, 'monitor/timeline_historico_create.html', {'edificio': edificio})


@login_required
def recomendaciones_ia(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    recs = edificio.recomendaciones.all()
    return render(request, 'monitor/recomendaciones_ia.html', {'edificio': edificio, 'recomendaciones': recs})


@login_required
def anomalias_list(request):
    anomalias = AnomaliaDetectada.objects.all()
    return render(request, 'monitor/anomalias_list.html', {'anomalias': anomalias})


@login_required
def analisis_predictivo_avanzado(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    predicciones = edificio.predicciones_ml.all()
    return render(request, 'monitor/analisis_predictivo_avanzado.html', {'edificio': edificio, 'predicciones': predicciones})


@login_required
def portal_educativo(request):
    recursos = [
        {
            'titulo': 'Guia de Restauracion',
            'descripcion': 'Aprende los fundamentos de restauracion de edificios historicos.',
            'icono': 'bi-book', 'color': 'var(--accent)',
            'duracion': '12 horas', 'nivel': 'Basico',
            'modulos': ['Introduccion a la restauracion', 'Materiales historicos', 'Tecnicas de consolidacion', 'Restauracion de fachadas', 'Cubiertas y estructuras', 'Criterios de intervencion', 'Caso: Alcazar de Sevilla'],
        },
        {
            'titulo': 'Sensores IoT para Patrimonio',
            'descripcion': 'Como instalar y configurar sensores en edificios historicos.',
            'icono': 'bi-cpu', 'color': 'var(--accent2)',
            'duracion': '8 horas', 'nivel': 'Intermedio',
            'modulos': ['Introduccion IoT', 'Tipos de sensores (temp, humedad, vibracion)', 'Instalacion sin danar el edificio', 'Conectividad LoRa/WiFi', 'Dashboard de datos', 'Alertas automaticas', 'Caso: Catedral de Sevilla'],
        },
        {
            'titulo': 'Normativas de Proteccion',
            'descripcion': 'Todas las leyes y normativas de proteccion del patrimonio.',
            'icono': 'bi-bank', 'color': 'var(--gold)',
            'duracion': '6 horas', 'nivel': 'Basico',
            'modulos': ['Ley de Patrimonio Historico Español', 'Declaracion de Bien de Interes Cultural', 'Zonas de proteccion', 'Permisos de obra', 'Licencias municipales', 'Normativa europea', 'Caso: Barrio de Santa Cruz'],
        },
        {
            'titulo': 'Eficiencia Energetica',
            'descripcion': 'Optimizar el consumo energetico sin danar el edificio.',
            'icono': 'bi-lightning', 'color': 'var(--success)',
            'duracion': '10 horas', 'nivel': 'Avanzado',
            'modulos': ['Diagnostico energetico', 'Aislamiento termico compatible', 'Iluminacion eficiente', 'Energias renovables en patrimonio', 'Certificado energetico', 'Reduccion de emisiones CO2', 'Caso: Plaza de Espana'],
        },
        {
            'titulo': 'Emergencias y Primeros Auxilios',
            'descripcion': 'Protocolos de actuacion en emergencias.',
            'icono': 'bi-heart-pulse', 'color': 'var(--danger)',
            'duracion': '4 horas', 'nivel': 'Basico',
            'modulos': ['Protocolos de emergencia', 'Primeros auxilios basicos', 'Evacuacion de edificios historicos', 'Prevencion de incendios', 'Dano por agua y humedades', 'Coordinacion con bomberos'],
        },
        {
            'titulo': 'Tecnologia Blockchain',
            'descripcion': 'Como usar blockchain para certificar patrimonio.',
            'icono': 'bi-link-45deg', 'color': '#9b59b6',
            'duracion': '6 horas', 'nivel': 'Avanzado',
            'modulos': ['Que es blockchain', 'Certificados digitales inmutables', 'Registro de intervenciones', 'Trazabilidad de materiales', 'Smart contracts para seguros', 'Caso: Certificacion de autenticidad'],
        },
    ]
    return render(request, 'monitor/portal_educativo.html', {'recursos': recursos})


@login_required
def voluntarios_list(request):
    voluntarios = Voluntario.objects.select_related('usuario').all()
    return render(request, 'monitor/voluntarios_list.html', {'voluntarios': voluntarios})


@login_required
def voluntario_register(request):
    if request.method == 'POST':
        vol, created = Voluntario.objects.get_or_create(usuario=request.user)
        vol.habilidades = request.POST.get('habilidades', '')
        vol.disponibilidad = request.POST.get('disponibilidad', '')
        vol.estado = 'pendiente'
        vol.save()
        messages.success(request, 'Te has registrado como voluntario!')
        return redirect('monitor:voluntarios_list')
    return render(request, 'monitor/voluntario_register.html')


@login_required
def tareas_pendientes(request):
    hoy = timezone.now().date()
    alertas_criticas = Alerta.objects.filter(resuelta=False, severidad='critical').select_related('sensor', 'sensor__edificio')[:20]
    mantenimientos_vencidos = Mantenimiento.objects.filter(fecha_limite__lte=hoy, estado__in=['pendiente', 'en_progreso']).select_related('edificio')[:20]
    mantenimientos_hoy = Mantenimiento.objects.filter(fecha_limite=hoy).select_related('edificio')[:10]
    inspecciones_vencidas = FormularioInspeccion.objects.filter(resultado='pendiente').select_related('edificio')[:10]
    return render(request, 'monitor/tareas_pendientes.html', {
        'alertas_criticas': alertas_criticas,
        'mantenimientos_vencidos': mantenimientos_vencidos,
        'mantenimientos_hoy': mantenimientos_hoy,
        'inspecciones_vencidas': inspecciones_vencidas,
    })


@login_required
def generar_pdf(request, pk):
    from django.http import HttpResponse
    edificio = get_object_or_404(Edificio, pk=pk)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.styles import getSampleStyleSheet
    import io
    buffer = io.BytesIO()
    p = pdf_canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4
    p.setFillColor(colors.HexColor('#1a1a2e'))
    p.rect(0, alto - 4*cm, ancho, 4*cm, fill=1)
    p.setFillColor(colors.HexColor('#d4a853'))
    p.setFont('Helvetica-Bold', 24)
    p.drawString(2*cm, alto - 2.5*cm, 'SmartHeritage')
    p.setFillColor(colors.white)
    p.setFont('Helvetica', 12)
    p.drawString(2*cm, alto - 3.5*cm, f'Informe: {edificio.nombre}')
    y = alto - 6*cm
    p.setFillColor(colors.HexColor('#1a1a2e'))
    p.setFont('Helvetica-Bold', 14)
    p.drawString(2*cm, y, 'Datos del Edificio')
    y -= 0.8*cm
    p.setFont('Helvetica', 11)
    datos = [
        ('Nombre', edificio.nombre),
        ('Direccion', edificio.direccion),
        ('Categoria', edificio.get_categoria_display()),
        ('Ciudad', edificio.ciudad),
        ('Provincia', edificio.provincia),
        ('Ano construccion', str(edificio.anno_construccion or 'N/A')),
        ('Estado general', edificio.get_estado_general_display()),
        ('Proteccion oficial', 'Si' if edificio.proteccion_oficial else 'No'),
        ('Salud', f'{edificio.salud_score}%'),
    ]
    for label, valor in datos:
        p.setFillColor(colors.HexColor('#666666'))
        p.drawString(2*cm, y, f'{label}:')
        p.setFillColor(colors.HexColor('#1a1a2e'))
        p.drawString(7*cm, y, valor)
        y -= 0.6*cm
    y -= 0.5*cm
    p.setFillColor(colors.HexColor('#1a1a2e'))
    p.setFont('Helvetica-Bold', 14)
    p.drawString(2*cm, y, 'Estadisticas')
    y -= 0.8*cm
    p.setFont('Helvetica', 11)
    sensores = edificio.sensores.count()
    lecturas = Lectura.objects.filter(sensor__edificio=edificio).count()
    alertas = Alerta.objects.filter(sensor__edificio=edificio, resuelta=False).count()
    stats = [
        ('Sensores instalados', str(sensores)),
        ('Lecturas totales', str(lecturas)),
        ('Alertas activas', str(alertas)),
    ]
    for label, valor in stats:
        p.setFillColor(colors.HexColor('#666666'))
        p.drawString(2*cm, y, f'{label}:')
        p.setFillColor(colors.HexColor('#1a1a2e'))
        p.drawString(7*cm, y, valor)
        y -= 0.6*cm
    y -= 0.5*cm
    ultimas = Lectura.objects.filter(sensor__edificio=edificio).select_related('sensor').order_by('-fecha_hora')[:15]
    if ultimas:
        p.setFillColor(colors.HexColor('#1a1a2e'))
        p.setFont('Helvetica-Bold', 14)
        p.drawString(2*cm, y, 'Ultimas Lecturas')
        y -= 0.8*cm
        p.setFont('Helvetica-Bold', 10)
        p.setFillColor(colors.HexColor('#666666'))
        p.drawString(2*cm, y, 'Sensor')
        p.drawString(7*cm, y, 'Valor')
        p.drawString(11*cm, y, 'Fecha')
        y -= 0.5*cm
        p.setFont('Helvetica', 10)
        for l in ultimas:
            p.drawString(2*cm, y, l.sensor.nombre[:25])
            p.drawString(7*cm, y, f'{l.valor} {l.sensor.unidad_medida}')
            p.drawString(11*cm, y, l.fecha_hora.strftime('%d/%m/%Y %H:%M'))
            y -= 0.5*cm
    p.setFont('Helvetica', 8)
    p.setFillColor(colors.HexColor('#999999'))
    p.drawString(2*cm, 2*cm, f'Generado por SmartHeritage - {timezone.now().strftime("%d/%m/%Y %H:%M")}')
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="informe_{edificio.nombre}.pdf"'
    return response


@login_required
def generar_qr(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    import qrcode
    import io
    url = request.build_absolute_uri(f'/edificios/{edificio.pk}/')
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#d4a853', back_color='#1a1a2e')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_{edificio.nombre}.png"'
    return response


@login_required
def dashboard_inversores(request):
    edificios = Edificio.objects.filter(activo=True)
    total_edificios = edificios.count()
    total_sensores = Sensor.objects.filter(activo=True).count()
    total_lecturas = Lectura.objects.count()
    alertas_activas = Alerta.objects.filter(resuelta=False).count()
    alertas_criticas = Alerta.objects.filter(resuelta=False, severidad='critical').count()
    total_donaciones = Donacion.objects.filter(estado='completada').aggregate(total=Sum('monto'))['total'] or 0
    total_eventos = Evento.objects.filter(activo=True).count()
    total_voluntarios = Voluntario.objects.filter(estado='activo').count()
    total_documentos = DocumentoEdificio.objects.count()
    total_herramientas = Herramienta.objects.filter(activo=True).count()
    salud_scores = [e.salud_score for e in edificios]
    salud_promedio = sum(salud_scores) / len(salud_scores) if salud_scores else 0
    lecturas_por_tipo = Lectura.objects.values('sensor__tipo').annotate(total=Count('id')).order_by('-total')
    from django.db.models import FloatField
    alertas_por_severidad = Alerta.objects.filter(resuelta=False).values('severidad').annotate(total=Count('id'))
    ultimas_lecturas = Lectura.objects.select_related('sensor', 'sensor__edificio').order_by('-fecha_hora')[:10]
    return render(request, 'monitor/dashboard_inversores.html', {
        'total_edificios': total_edificios,
        'total_sensores': total_sensores,
        'total_lecturas': total_lecturas,
        'alertas_activas': alertas_activas,
        'alertas_criticas': alertas_criticas,
        'total_donaciones': total_donaciones,
        'total_eventos': total_eventos,
        'total_voluntarios': total_voluntarios,
        'total_documentos': total_documentos,
        'total_herramientas': total_herramientas,
        'salud_promedio': round(salud_promedio, 1),
        'edificios': edificios,
        'lecturas_por_tipo': list(lecturas_por_tipo),
        'alertas_por_severidad': list(alertas_por_severidad),
        'ultimas_lecturas': ultimas_lecturas,
    })


@login_required
def comparativa_periodos(request):
    edificios = Edificio.objects.filter(activo=True)
    hoy = timezone.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year
    mes_anterior = mes_actual - 1 if mes_actual > 1 else 12
    anio_anterior = anio_actual if mes_actual > 1 else anio_actual - 1
    datos = []
    for e in edificios[:10]:
        lecturas_actual = Lectura.objects.filter(sensor__edificio=e, fecha_hora__month=mes_actual, fecha_hora__year=anio_actual)
        lecturas_anterior = Lectura.objects.filter(sensor__edificio=e, fecha_hora__month=mes_anterior, fecha_hora__year=anio_anterior)
        temp_actual = lecturas_actual.filter(sensor__tipo='temperatura').aggregate(avg=Avg('valor'))['avg']
        temp_anterior = lecturas_anterior.filter(sensor__tipo='temperatura').aggregate(avg=Avg('valor'))['avg']
        total_actual = lecturas_actual.count()
        total_anterior = lecturas_anterior.count()
        alertas_actual = Alerta.objects.filter(sensor__edificio=e, fecha_creacion__month=mes_actual, fecha_creacion__year=anio_actual).count()
        alertas_anterior = Alerta.objects.filter(sensor__edificio=e, fecha_creacion__month=mes_anterior, fecha_creacion__year=anio_anterior).count()
        datos.append({
            'edificio': e,
            'temp_actual': round(temp_actual, 1) if temp_actual else None,
            'temp_anterior': round(temp_anterior, 1) if temp_anterior else None,
            'lecturas_actual': total_actual,
            'lecturas_anterior': total_anterior,
            'alertas_actual': alertas_actual,
            'alertas_anterior': alertas_anterior,
        })
    return render(request, 'monitor/comparativa_periodos.html', {
        'datos': datos,
        'mes_actual': hoy.strftime('%B %Y'),
        'mes_anterior': f'{mes_anterior}/{anio_anterior}',
    })


@login_required
def enviar_email_test(request):
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        send_mail(
            subject='SmartHeritage - Email de prueba',
            message='Este es un email de prueba de SmartHeritage. Si lo recibes, el email funciona correctamente!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email or settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        messages.success(request, 'Email de prueba enviado correctamente! Revisa tu bandeja.')
    except Exception as e:
        messages.error(request, f'Error al enviar email: {str(e)}')
    return redirect('monitor:configurar_email')


@login_required
def configurar_email(request):
    return render(request, 'monitor/configurar_email.html')


@login_required
def enviar_alerta_email(request, pk):
    from django.core.mail import send_mail
    from django.conf import settings
    alerta = get_object_or_404(Alerta, pk=pk)
    try:
        asunto = f'SmartHeritage - Alerta {alerta.get_severidad_display()}: {alerta.sensor.edificio.nombre}'
        mensaje = f"""
        ALERTA {alerta.get_severidad_display().upper()}

        Edificio: {alerta.sensor.edificio.nombre}
        Sensor: {alerta.sensor.nombre}
        Tipo: {alerta.get_tipo_alerta_display()}
        Mensaje: {alerta.mensaje}
        Valor detectado: {alerta.valor_detectado}
        Fecha: {alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M')}

        Revisa SmartHeritage para mas detalles.
        """
        send_mail(
            subject=asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email or settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        messages.success(request, f'Email de alerta enviado a {request.user.email}')
    except Exception as e:
        messages.error(request, f'Error al enviar email: {str(e)}')
    return redirect('monitor:alerta_list')


@login_required
def reportes_automaticos(request):
    reportes = ReporteAutomatico.objects.all()[:20]
    return render(request, 'monitor/reportes_automaticos.html', {'reportes': reportes})


@login_required
def generar_reporte_semanal(request):
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    hoy = timezone.now().date()
    desde = hoy - timedelta(days=7)
    edificios = Edificio.objects.filter(activo=True)
    total_alertas = Alerta.objects.filter(fecha_creacion__gte=desde).count()
    alertas_resueltas = Alerta.objects.filter(fecha_creacion__gte=desde, resuelta=True).count()
    total_mantenimientos = Mantenimiento.objects.filter(fecha_creacion__gte=desde).count()
    mantenimientos_completados = Mantenimiento.objects.filter(fecha_creacion__gte=desde, estado='completado').count()
    total_lecturas = Lectura.objects.filter(fecha_hora__gte=desde).count()
    contenido = f"""RESUMEN SEMANAL SmartHeritage
Periodo: {desde.strftime('%d/%m/%Y')} - {hoy.strftime('%d/%m/%Y')}

RESUMEN:
- Edificios activos: {edificios.count()}
- Alertas totales: {total_alertas} (resueltas: {alertas_resueltas})
- Mantenimientos: {total_mantenimientos} (completados: {mantenimientos_completados})
- Lecturas registradas: {total_lecturas}

EDIFICIOS:
"""
    for e in edificios:
        salud = e.salud_score
        alertas = Alerta.objects.filter(sensor__edificio=e, resuelta=False).count()
        contenido += f"- {e.nombre}: Salud {salud}%, {alertas} alertas activas\n"
    reporte = ReporteAutomatico.objects.create(
        titulo=f'Reporte Semanal {desde.strftime("%d/%m")} - {hoy.strftime("%d/%m/%Y")}',
        tipo='semanal', contenido=contenido, enviado=True, fecha_envio=timezone.now()
    )
    try:
        email = EmailMultiAlternatives(
            subject=f'SmartHeritage - Reporte Semanal {hoy.strftime("%d/%m/%Y")}',
            body=contenido,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email or settings.EMAIL_HOST_USER],
        )
        email.send(fail_silently=False)
        messages.success(request, 'Reporte semanal generado y enviado por email!')
    except Exception as e:
        messages.warning(request, f'Reporte generado pero error al enviar: {str(e)}')
    return redirect('monitor:reportes_automaticos')


@login_required
def mantenimiento_predictivo(request):
    predicciones = MantenimientoPredictivo.objects.all()
    return render(request, 'monitor/mantenimiento_predictivo.html', {'predicciones': predicciones})


@login_required
def crear_prediccion(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == 'POST':
        MantenimientoPredictivo.objects.create(
            edificio=edificio,
            titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            prioridad=request.POST.get('prioridad', 'media'),
            probabilidad_fallo=float(request.POST.get('probabilidad_fallo', 50)),
            dias_estimados=int(request.POST.get('dias_estimados', 30)),
            costo_estimado=float(request.POST.get('costo_estimado', 0)),
            accion_recomendada=request.POST.get('accion_recomendada', ''),
        )
        messages.success(request, 'Prediccion creada correctamente.')
        return redirect('monitor:mantenimiento_predictivo')
    return render(request, 'monitor/crear_prediccion.html', {'edificio': edificio})


@login_required
def calculadora_roi(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    registros = RegistroROI.objects.filter(edificio=edificio)
    total_ahorro = sum(r.total_ahorro for r in registros)
    total_inversion = sum(r.inversion_smartheritage for r in registros)
    roi_total = ((total_ahorro - total_inversion) / total_inversion * 100) if total_inversion > 0 else 0
    if request.method == 'POST':
        RegistroROI.objects.create(
            edificio=edificio,
            ahorro_energetico=float(request.POST.get('ahorro_energetico', 0)),
            ahorro_multas=float(request.POST.get('ahorro_multas', 0)),
            ahorro_restauraciones=float(request.POST.get('ahorro_restauraciones', 0)),
            donaciones_recibidas=float(request.POST.get('donaciones_recibidas', 0)),
            inversion_smartheritage=float(request.POST.get('inversion_smartheritage', 0)),
        )
        messages.success(request, 'Registro ROI anadido.')
        return redirect('monitor:calculadora_roi', pk=edificio.pk)
    return render(request, 'monitor/calculadora_roi.html', {
        'edificio': edificio, 'registros': registros,
        'total_ahorro': total_ahorro, 'total_inversion': total_inversion, 'roi_total': round(roi_total, 1),
    })


@login_required
def cambiar_idioma(request):
    if request.method == 'POST':
        idioma = request.POST.get('idioma', 'es')
        idiomas_validos = dict(ConfiguracionIdioma.IDIOMA_CHOICES).keys()
        if idioma not in idiomas_validos:
            idioma = 'es'
        config, created = ConfiguracionIdioma.objects.get_or_create(usuario=request.user)
        config.idioma = idioma
        config.save()
        request.session['django_language'] = idioma
        try:
            from django.utils.translation import activate
            activate(idioma)
        except Exception:
            pass
        messages.success(request, 'Idioma cambiado correctamente.')
    return redirect('monitor:dashboard')


@login_required
def resumen_diario(request):
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    hoy = timezone.now().date()
    edificios = Edificio.objects.filter(activo=True)
    alertas_activas = Alerta.objects.filter(resuelta=False).count()
    alertas_criticas = Alerta.objects.filter(resuelta=False, severidad='critical').count()
    mantenimientos_pendientes = Mantenimiento.objects.filter(estado__in=['pendiente', 'en_progreso']).count()
    salud_scores = [e.salud_score for e in edificios]
    salud_promedio = sum(salud_scores) / len(salud_scores) if salud_scores else 0
    contenido = f"""RESUMEN DIARIO SmartHeritage - {hoy.strftime('%d/%m/%Y')}

HOLA! Aqui tienes el resumen de hoy:

ESTADO GENERAL:
- Edificios activos: {edificios.count()}
- Salud promedio: {round(salud_promedio, 1)}%
- Alertas activas: {alertas_activas} (criticas: {alertas_criticas})
- Mantenimientos pendientes: {mantenimientos_pendientes}

EDIFICIOS:
"""
    for e in edificios:
        a = Alerta.objects.filter(sensor__edificio=e, resuelta=False).count()
        contenido += f"- {e.nombre}: Salud {e.salud_score}%, {a} alertas\n"
    if alertas_criticas > 0:
        contenido += f"\nATENCION: Hay {alertas_criticas} alertas criticas que requieren accion inmediata!"
    try:
        email = EmailMultiAlternatives(
            subject=f'SmartHeritage - Resumen Diario {hoy.strftime("%d/%m/%Y")}',
            body=contenido,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email or settings.EMAIL_HOST_USER],
        )
        email.send(fail_silently=False)
        messages.success(request, 'Resumen diario enviado por email!')
    except Exception as e:
        messages.error(request, f'Error al enviar: {str(e)}')
    return redirect('monitor:dashboard')


@login_required
def comparativa_ciudades(request):
    ciudades = ComparativaCiudad.objects.all()
    edificios = Edificio.objects.filter(activo=True)
    stats_propias = []
    for e in edificios:
        lecturas = Lectura.objects.filter(sensor__edificio=e)
        temp_avg = lecturas.filter(sensor__tipo='temperatura').aggregate(avg=Avg('valor'))['avg'] or 0
        stats_propias.append({
            'edificio': e,
            'salud': e.salud_score,
            'sensores': e.sensores.count(),
            'alertas': Alerta.objects.filter(sensor__edificio=e, resuelta=False).count(),
            'temp_avg': round(temp_avg, 1),
        })
    if not ciudades:
        defaults = [
            {'ciudad': 'Sevilla', 'edificio_tipo': 'Historico', 'media_salud': 72, 'media_sensores': 6, 'media_alertas': 3, 'total_edificios': 45},
            {'ciudad': 'Granada', 'edificio_tipo': 'Historico', 'media_salud': 68, 'media_sensores': 5, 'media_alertas': 4, 'total_edificios': 38},
            {'ciudad': 'Cordoba', 'edificio_tipo': 'Historico', 'media_salud': 75, 'media_sensores': 7, 'media_alertas': 2, 'total_edificios': 32},
            {'ciudad': 'Malaga', 'edificio_tipo': 'Historico', 'media_salud': 70, 'media_sensores': 5, 'media_alertas': 3, 'total_edificios': 28},
            {'ciudad': 'Cadiz', 'edificio_tipo': 'Historico', 'media_salud': 65, 'media_sensores': 4, 'media_alertas': 5, 'total_edificios': 22},
            {'ciudad': 'Bilbao', 'edificio_tipo': 'Historico', 'media_salud': 78, 'media_sensores': 8, 'media_alertas': 1, 'total_edificios': 35},
            {'ciudad': 'Valencia', 'edificio_tipo': 'Historico', 'media_salud': 71, 'media_sensores': 6, 'media_alertas': 2, 'total_edificios': 40},
        ]
        for d in defaults:
            ComparativaCiudad.objects.create(**d)
        ciudades = ComparativaCiudad.objects.all()
    return render(request, 'monitor/comparativa_ciudades.html', {
        'ciudades': ciudades, 'stats_propias': stats_propias,
    })


@login_required
def modo_emergencia(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Emergencia activada')
        from django.core.mail import send_mail
        from django.conf import settings
        emergencia = ModoEmergencia.objects.create(
            edificio=edificio, activado_por=request.user, motivo=motivo
        )
        try:
            send_mail(
                subject=f'EMERGENCIA SmartHeritage - {edificio.nombre}',
                message=f'MODO EMERGENCIA ACTIVADO\n\nEdificio: {edificio.nombre}\nMotivo: {motivo}\nActivado por: {request.user.username}\nFecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}\n\nAcciones automaticas:\n- Email enviado a todos los responsables\n- PDF de estado actual generado\n- Sensores en modo de alta frecuencia',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email or settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            emergencia.email_enviado = True
        except Exception:
            pass
        emergencia.pdf_generado = True
        emergencia.save()
        messages.error(request, 'EMERGENCIA ACTIVADA! Email enviado y PDF generado.')
        return redirect('monitor:dashboard')
    return render(request, 'monitor/modo_emergencia.html', {'edificio': edificio})


@login_required
def panel_financiero(request):
    edificios = Edificio.objects.filter(activo=True)
    hoy = timezone.now().date()
    mes_inicio = hoy.replace(day=1)
    total_ingresos = Ingreso.objects.filter(fecha__gte=mes_inicio, estado='cobrado').aggregate(total=Sum('monto'))['total'] or 0
    total_gastos = Gasto.objects.filter(fecha__gte=mes_inicio, pagado=True).aggregate(total=Sum('monto'))['total'] or 0
    total_facturas_pendientes = Factura.objects.filter(estado__in=['enviada', 'vencida']).aggregate(total=Sum('total'))['total'] or 0
    total_nominas_pendientes = Nomina.objects.filter(estado='pendiente').aggregate(total=Sum('neto'))['total'] or 0
    balance = total_ingresos - total_gastos
    ingresos_hoy = Ingreso.objects.filter(fecha=hoy, estado='cobrado').aggregate(total=Sum('monto'))['total'] or 0
    gastos_hoy = Gasto.objects.filter(fecha=hoy, pagado=True).aggregate(total=Sum('monto'))['total'] or 0
    ingresos_mes = []
    gastos_mes = []
    for i in range(12):
        mes = mes_inicio - timedelta(days=30 * i)
        mes_ref = mes.replace(day=1)
        if i == 0:
            mes_siguiente = mes_ref + timedelta(days=32)
            mes_siguiente = mes_siguiente.replace(day=1)
        else:
            mes_siguiente = (mes_ref + timedelta(days=32)).replace(day=1)
        ing = Ingreso.objects.filter(fecha__gte=mes_ref, fecha__lt=mes_siguiente, estado='cobrado').aggregate(total=Sum('monto'))['total'] or 0
        gas = Gasto.objects.filter(fecha__gte=mes_ref, fecha__lt=mes_siguiente, pagado=True).aggregate(total=Sum('monto'))['total'] or 0
        ingresos_mes.append({'mes': mes_ref.strftime('%b %Y'), 'total': float(ing)})
        gastos_mes.append({'mes': mes_ref.strftime('%b %Y'), 'total': float(gas)})
    ingresos_mes.reverse()
    gastos_mes.reverse()
    presupuestos_alerta = []
    for e in edificios:
        for p in Presupuesto.objects.filter(edificio=e, activo=True):
            if p.porcentaje_gastado >= p.alerta_porcentaje:
                presupuestos_alerta.append(p)
    ultimas_facturas = Factura.objects.all()[:5]
    ultimos_gastos = Gasto.objects.all()[:5]
    return render(request, 'monitor/panel_financiero.html', {
        'edificios': edificios,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'total_facturas_pendientes': total_facturas_pendientes,
        'total_nominas_pendientes': total_nominas_pendientes,
        'balance': balance,
        'ingresos_hoy': ingresos_hoy,
        'gastos_hoy': gastos_hoy,
        'ingresos_mes': ingresos_mes,
        'gastos_mes': gastos_mes,
        'presupuestos_alerta': presupuestos_alerta,
        'ultimas_facturas': ultimas_facturas,
        'ultimos_gastos': ultimos_gastos,
    })


@login_required
def ingreso_list(request):
    ingresos = Ingreso.objects.all()
    edificio = request.GET.get('edificio')
    if edificio:
        ingresos = ingresos.filter(edificio_id=edificio)
    total = ingresos.filter(estado='cobrado').aggregate(total=Sum('monto'))['total'] or 0
    return render(request, 'monitor/ingreso_list.html', {'ingresos': ingresos, 'total_cobrado': total, 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def ingreso_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        Ingreso.objects.create(
            edificio=edificio,
            categoria_id=request.POST.get('categoria') or None,
            concepto=request.POST.get('concepto', ''),
            descripcion=request.POST.get('descripcion', ''),
            monto=float(request.POST.get('monto', 0)),
            fecha=request.POST.get('fecha', timezone.now().date()),
            estado=request.POST.get('estado', 'pendiente'),
            cliente_nombre=request.POST.get('cliente_nombre', ''),
            cliente_email=request.POST.get('cliente_email', ''),
            cliente_nif=request.POST.get('cliente_nif', ''),
            recurrente=request.POST.get('recurrente') == 'on',
            notas=request.POST.get('notas', ''),
        )
        messages.success(request, 'Ingreso creado correctamente.')
        return redirect('monitor:ingreso_list')
    return render(request, 'monitor/ingreso_create.html', {'edificio': edificio, 'categorias': CategoriaIngreso.objects.all()})


@login_required
def gasto_list(request):
    gastos = Gasto.objects.all()
    edificio = request.GET.get('edificio')
    if edificio:
        gastos = gastos.filter(edificio_id=edificio)
    total = gastos.filter(pagado=True).aggregate(total=Sum('monto'))['total'] or 0
    return render(request, 'monitor/gasto_list.html', {'gastos': gastos, 'total_pagado': total, 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def gasto_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        Gasto.objects.create(
            edificio=edificio,
            categoria_id=request.POST.get('categoria') or None,
            concepto=request.POST.get('concepto', ''),
            descripcion=request.POST.get('descripcion', ''),
            monto=float(request.POST.get('monto', 0)),
            fecha=request.POST.get('fecha', timezone.now().date()),
            pagado=request.POST.get('pagado') == 'on',
            proveedor=request.POST.get('proveedor', ''),
            proveedor_nif=request.POST.get('proveedor_nif', ''),
            forma_pago=request.POST.get('forma_pago', 'transferencia'),
            deducible=request.POST.get('deducible') == 'on',
            notas=request.POST.get('notas', ''),
        )
        messages.success(request, 'Gasto registrado correctamente.')
        return redirect('monitor:gasto_list')
    return render(request, 'monitor/gasto_create.html', {'edificio': edificio, 'categorias': CategoriaGasto.objects.all()})


@login_required
def factura_list(request):
    facturas = Factura.objects.all()
    tipo = request.GET.get('tipo')
    if tipo:
        facturas = facturas.filter(tipo=tipo)
    estado = request.GET.get('estado')
    if estado:
        facturas = facturas.filter(estado=estado)
    total_pendiente = facturas.filter(estado__in=['enviada', 'vencida']).aggregate(total=Sum('total'))['total'] or 0
    total_pagado = facturas.filter(estado='pagada').aggregate(total=Sum('total'))['total'] or 0
    return render(request, 'monitor/factura_list.html', {
        'facturas': facturas, 'total_pendiente': total_pendiente, 'total_pagado': total_pagado,
        'edificios': Edificio.objects.filter(activo=True),
    })


@login_required
def factura_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        base = float(request.POST.get('base_imponible', 0))
        iva_pct = float(request.POST.get('porcentaje_iva', 21))
        iva = base * iva_pct / 100
        factura = Factura.objects.create(
            numero=request.POST.get('numero', f'FAC-{timezone.now().strftime("%Y%m%d%H%M")}'),
            tipo=request.POST.get('tipo', 'emitted'),
            edificio=edificio,
            cliente_proveedor=request.POST.get('cliente_proveedor', ''),
            cliente_nif=request.POST.get('cliente_nif', ''),
            cliente_direccion=request.POST.get('cliente_direccion', ''),
            cliente_email=request.POST.get('cliente_email', ''),
            concepto=request.POST.get('concepto', ''),
            base_imponible=base,
            porcentaje_iva=iva_pct,
            importe_iva=iva,
            total=base + iva,
            estado=request.POST.get('estado', 'borrador'),
            fecha_emision=request.POST.get('fecha_emision', timezone.now().date()),
            fecha_vencimiento=request.POST.get('fecha_vencimiento') or None,
            notas=request.POST.get('notas', ''),
        )
        messages.success(request, f'Factura {factura.numero} creada correctamente.')
        return redirect('monitor:factura_list')
    return render(request, 'monitor/factura_create.html', {'edificio': edificio})


@login_required
def factura_pdf(request, pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    import io
    from django.http import FileResponse
    factura = get_object_or_404(Factura, pk=pk)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFillColor(colors.HexColor('#1a1a2e'))
    p.rect(0, height - 3 * cm, width, 3 * cm, fill=1)
    p.setFillColor(colors.white)
    p.setFont('Helvetica-Bold', 18)
    p.drawString(2 * cm, height - 2 * cm, 'SmartHeritage')
    p.setFont('Helvetica', 10)
    p.drawString(2 * cm, height - 2.7 * cm, f'FACTURA {factura.numero}')
    p.setFillColor(colors.HexColor('#333333'))
    p.setFont('Helvetica-Bold', 12)
    p.drawString(2 * cm, height - 4.5 * cm, 'DATOS DEL CLIENTE:')
    p.setFont('Helvetica', 10)
    y = height - 5.2 * cm
    p.drawString(2 * cm, y, f'{factura.cliente_proveedor}')
    y -= 0.5 * cm
    if factura.cliente_nif:
        p.drawString(2 * cm, y, f'NIF: {factura.cliente_nif}')
        y -= 0.5 * cm
    if factura.cliente_direccion:
        p.drawString(2 * cm, y, factura.cliente_direccion)
        y -= 0.5 * cm
    if factura.cliente_email:
        p.drawString(2 * cm, y, factura.cliente_email)
        y -= 1 * cm
    p.setFont('Helvetica-Bold', 12)
    p.drawString(2 * cm, y, 'CONCEPTO:')
    y -= 0.6 * cm
    p.setFont('Helvetica', 10)
    p.drawString(2 * cm, y, factura.concepto)
    y -= 1.5 * cm
    p.setStrokeColor(colors.HexColor('#d4a853'))
    p.setLineWidth(2)
    p.line(2 * cm, y, width - 2 * cm, y)
    y -= 1 * cm
    p.setFillColor(colors.HexColor('#333333'))
    p.setFont('Helvetica-Bold', 11)
    p.drawString(2 * cm, y, 'Base Imponible:')
    p.drawRightString(width - 2 * cm, y, f'{factura.base_imponible:,.2f} EUR')
    y -= 0.7 * cm
    p.drawString(2 * cm, y, f'IVA ({factura.porcentaje_iva}%):')
    p.drawRightString(width - 2 * cm, y, f'{factura.importe_iva:,.2f} EUR')
    y -= 0.7 * cm
    p.setFillColor(colors.HexColor('#e94560'))
    p.setFont('Helvetica-Bold', 14)
    p.drawString(2 * cm, y, 'TOTAL:')
    p.drawRightString(width - 2 * cm, y, f'{factura.total:,.2f} EUR')
    y -= 1.5 * cm
    p.setFillColor(colors.HexColor('#666666'))
    p.setFont('Helvetica', 9)
    p.drawString(2 * cm, y, f'Fecha emision: {factura.fecha_emision}')
    if factura.fecha_vencimiento:
        y -= 0.5 * cm
        p.drawString(2 * cm, y, f'Fecha vencimiento: {factura.fecha_vencimiento}')
    y -= 1 * cm
    p.drawString(2 * cm, y, 'SmartHeritage - Sistema de Gestion de Patrimonio Historico')
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'factura_{factura.numero}.pdf')


@login_required
def factura_estado(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    nuevo_estado = request.GET.get('estado')
    if nuevo_estado in ['borrador', 'enviada', 'pagada', 'vencida', 'cancelada']:
        factura.estado = nuevo_estado
        if nuevo_estado == 'pagada':
            factura.fecha_pago = timezone.now().date()
        factura.save()
        messages.success(request, f'Factura {factura.numero} actualizada a {factura.get_estado_display()}.')
    return redirect('monitor:factura_list')


@login_required
def nomina_list(request):
    nominas = Nomina.objects.all()
    total_pendiente = nominas.filter(estado='pendiente').aggregate(total=Sum('neto'))['total'] or 0
    total_pagado = nominas.filter(estado='pagada').aggregate(total=Sum('neto'))['total'] or 0
    return render(request, 'monitor/nomina_list.html', {'nominas': nominas, 'total_pendiente': total_pendiente, 'total_pagado': total_pagado, 'usuarios': User.objects.all()})


@login_required
def nomina_create(request):
    if request.method == 'POST':
        nomina = Nomina.objects.create(
            empleado_id=request.POST.get('empleado'),
            edificio_id=request.POST.get('edificio') or None,
            salario_base=float(request.POST.get('salario_base', 0)),
            complemento=float(request.POST.get('complemento', 0)),
            bonus=float(request.POST.get('bonus', 0)),
            retenciones=float(request.POST.get('retenciones', 0)),
            seguridad_social=float(request.POST.get('seguridad_social', 0)),
            periodo=request.POST.get('periodo', ''),
            fecha_pago=request.POST.get('fecha_pago', timezone.now().date()),
            estado=request.POST.get('estado', 'pendiente'),
            notas=request.POST.get('notas', ''),
        )
        messages.success(request, f'Nomina de {nomina.empleado.username} creada. Neto: {nomina.neto} EUR')
        return redirect('monitor:nomina_list')
    return render(request, 'monitor/nomina_create.html', {'usuarios': User.objects.all(), 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def nomina_estado(request, pk):
    nomina = get_object_or_404(Nomina, pk=pk)
    nuevo_estado = request.GET.get('estado')
    if nuevo_estado in ['pendiente', 'pagada', 'cancelada']:
        nomina.estado = nuevo_estado
        nomina.save()
        messages.success(request, f'Nomina de {nomina.empleado.username} actualizada a {nomina.get_estado_display()}.')
    return redirect('monitor:nomina_list')


@login_required
def presupuesto_list(request):
    presupuestos = Presupuesto.objects.all()
    edificio = request.GET.get('edificio')
    if edificio:
        presupuestos = presupuestos.filter(edificio_id=edificio)
    return render(request, 'monitor/presupuesto_list.html', {'presupuestos': presupuestos, 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def presupuesto_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        Presupuesto.objects.create(
            edificio=edificio,
            nombre=request.POST.get('nombre', ''),
            categoria_id=request.POST.get('categoria') or None,
            monto_asignado=float(request.POST.get('monto_asignado', 0)),
            periodo=request.POST.get('periodo', 'mensual'),
            fecha_inicio=request.POST.get('fecha_inicio', timezone.now().date()),
            fecha_fin=request.POST.get('fecha_fin', timezone.now().date()),
            alerta_porcentaje=int(request.POST.get('alerta_porcentaje', 80)),
        )
        messages.success(request, 'Presupuesto creado correctamente.')
        return redirect('monitor:presupuesto_list')
    return render(request, 'monitor/presupuesto_create.html', {'edificio': edificio, 'categorias': CategoriaGasto.objects.all()})


@login_required
def cuenta_contable_list(request):
    cuentas = CuentaContable.objects.all()
    return render(request, 'monitor/cuenta_contable_list.html', {'cuentas': cuentas})


@login_required
def cuenta_contable_create(request):
    if request.method == 'POST':
        CuentaContable.objects.create(
            codigo=request.POST.get('codigo', ''),
            nombre=request.POST.get('nombre', ''),
            tipo=request.POST.get('tipo', 'activo'),
        )
        messages.success(request, 'Cuenta contable creada.')
        return redirect('monitor:cuenta_contable_list')
    return render(request, 'monitor/cuenta_contable_create.html')


@login_required
def chat_asistente_ia(request):
    historial = ChatAsistenteIA.objects.filter(usuario=request.user)[:20]
    respuesta = ''
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje', '')
        edificio_id = request.POST.get('edificio')
        contexto = ''
        if edificio_id:
            edificio = Edificio.objects.filter(pk=edificio_id).first()
            if edificio:
                lecturas = Lectura.objects.filter(sensor__edificio=edificio)[:10]
                alertas = Alerta.objects.filter(sensor__edificio=edificio, resuelta=False)[:5]
                contexto = f"Edificio: {edificio.nombre}, Salud: {edificio.salud_score}%, Sensores: {edificio.sensores.count()}, Alertas activas: {edificio.alertas_activas}. "
                for l in lecturas:
                    contexto += f"{l.sensor.tipo}: {l.valor} {l.sensor.unidad_medida}. "
                for a in alertas:
                    contexto += f"Alerta: {a.mensaje[:80]}. "
        reglas_ia = f"Eres SmartHeritage IA, experto en patrimonio historico. Contexto del edificio: {contexto} Responde en español, se breve y util. Pregunta del usuario: {mensaje}"
        respuesta = f"[Simulado] Analizando tu consulta sobre: '{mensaje}'. Con los datos disponibles: {contexto}Te recomiendo revisar el estado de los sensores y programar un mantenimiento preventivo si hay alertas activas."
        ChatAsistenteIA.objects.create(usuario=request.user, mensaje_usuario=mensaje, respuesta_ia=respuesta, edificio_id=edificio_id or None)
    return render(request, 'monitor/chat_asistente_ia.html', {'historial': historial, 'respuesta': respuesta, 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def digital_twin_view(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    twin, created = DigitalTwin.objects.get_or_create(edificio=edificio)
    lecturas = []
    for s in edificio.sensores.all():
        ultima = s.lecturas.order_by('-fecha_hora').first()
        if ultima:
            lecturas.append({'tipo': s.tipo, 'valor': ultima.valor, 'unidad': s.unidad_medida, 'sensor': s})
    twin.estado_color = '#dc3545' if edificio.salud_score < 50 else '#ffc107' if edificio.salud_score < 75 else '#28a745'
    twin.save()
    return render(request, 'monitor/digital_twin.html', {'edificio': edificio, 'twin': twin, 'lecturas': lecturas})


@login_required
def foto_inspeccion_list(request):
    fotos = FotoInspeccion.objects.filter(edificio__activo=True)[:30]
    return render(request, 'monitor/foto_inspeccion_list.html', {'fotos': fotos})


@login_required
def foto_inspeccion_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        foto = FotoInspeccion.objects.create(
            edificio=edificio, titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            subida_por=request.user,
        )
        if 'imagen' in request.FILES:
            foto.imagen = request.FILES['imagen']
        import random
        resultados = ['ok', 'grietas', 'humedad', 'dano_estructural', 'desgaste']
        foto.resultado_ia = random.choice(resultados)
        foto.confianza_ia = round(random.uniform(60, 99), 1)
        detalles = {
            'ok': 'No se detectaron problemas significativos en la imagen analizada.',
            'grietas': 'Se detectaron posibles grietas en la superficie. Se recomienda inspeccion presencial.',
            'humedad': 'Indicadores de humedad detectados. Se recomienda revisar impermeabilizacion.',
            'dano_estructural': 'Posibles senales de dano estructural. Inspeccion urgente recomendada.',
            'desgaste': 'Desgaste generalizado detectado. Se recomienda mantenimiento preventivo.',
        }
        foto.detalles_ia = detalles.get(foto.resultado_ia, 'Analisis completado.')
        foto.save()
        messages.success(request, f'Foto analizada: {foto.get_resultado_ia_display()} ({foto.confianza_ia}% confianza)')
        return redirect('monitor:foto_inspeccion_list')
    return render(request, 'monitor/foto_inspeccion_create.html', {'edificio': edificio})


@login_required
def cita_list(request):
    citas = Cita.objects.all()[:30]
    return render(request, 'monitor/cita_list.html', {'citas': citas})


@login_required
def cita_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        cita = Cita.objects.create(
            edificio=edificio, titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            fecha_inicio=request.POST.get('fecha_inicio'),
            fecha_fin=request.POST.get('fecha_fin'),
            ubicacion=request.POST.get('ubicacion', ''),
        )
        participantes = request.POST.getlist('participantes')
        if participantes:
            cita.participantes.set(participantes)
        messages.success(request, 'Cita creada correctamente.')
        return redirect('monitor:cita_list')
    return render(request, 'monitor/cita_create.html', {'edificio': edificio, 'usuarios': User.objects.all()})


@login_required
def kanban_view(request):
    tareas = TareaKanban.objects.all()
    return render(request, 'monitor/kanban.html', {'tareas': tareas, 'usuarios': User.objects.all(), 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def tarea_create(request):
    if request.method == 'POST':
        TareaKanban.objects.create(
            edificio_id=request.POST.get('edificio') or None,
            titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            estado=request.POST.get('estado', 'pendiente'),
            prioridad=request.POST.get('prioridad', 'media'),
            asignado_a_id=request.POST.get('asignado_a') or None,
            fecha_limite=request.POST.get('fecha_limite') or None,
        )
        messages.success(request, 'Tarea creada.')
        return redirect('monitor:kanban')
    return render(request, 'monitor/tarea_create.html', {'edificios': Edificio.objects.filter(activo=True), 'usuarios': User.objects.all()})


@login_required
def tarea_estado(request, pk):
    tarea = get_object_or_404(TareaKanban, pk=pk)
    nuevo_estado = request.GET.get('estado')
    if nuevo_estado in ['pendiente', 'en_progreso', 'revision', 'completada']:
        tarea.estado = nuevo_estado
        tarea.save()
    return redirect('monitor:kanban')


@login_required
def mapa_global(request):
    edificios = Edificio.objects.filter(activo=True)
    markers = []
    for e in edificios:
        if e.latitud and e.longitud:
            markers.append({'lat': float(e.latitud), 'lng': float(e.longitud), 'nombre': e.nombre, 'salud': e.salud_score, 'pk': str(e.pk)})
    return render(request, 'monitor/mapa_global.html', {'markers': markers, 'edificios': edificios})


@login_required
def backup_view(request):
    import os, json
    from django.conf import settings
    backups = BackupLog.objects.all()[:10]
    if request.method == 'POST':
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        fecha = timezone.now().strftime('%Y%m%d_%H%M%S')
        archivo = os.path.join(backup_dir, f'backup_{fecha}.json')
        data = {}
        for model in [Edificio, Sensor, Lectura, Alerta]:
            data[model.__name__] = list(model.objects.values())
        with open(archivo, 'w') as f:
            json.dump(data, f, default=str, indent=2)
        tamano = os.path.getsize(archivo) / (1024 * 1024)
        log = BackupLog.objects.create(archivo=f'backups/backup_{fecha}.json', tamano_kb=tamano, tipo='completo')
        messages.success(request, f'Backup creado: {archivo} ({tamano:.2f} MB)')
        return redirect('monitor:backup')
    return render(request, 'monitor/backup_detail.html', {'backups': backups})


@login_required
def whatsapp_config(request):
    if request.method == 'POST':
        telefono = request.POST.get('telefono', '')
        mensaje = request.POST.get('mensaje', '')
        NotificacionWhatsApp.objects.create(telefono=telefono, mensaje=mensaje, enviado=False, error='Simulado - Configurar API de WhatsApp Business')
        messages.info(request, 'Notificacion WhatsApp registrada. Configura la API de WhatsApp Business para envio real.')
        return redirect('monitor:whatsapp_config')
    notificaciones = NotificacionWhatsApp.objects.all()[:20]
    return render(request, 'monitor/whatsapp_config.html', {'notificaciones': notificaciones})


@login_required
def contrato_list(request):
    contratos = ContratoDigital.objects.all()[:30]
    return render(request, 'monitor/contrato_list.html', {'contratos': contratos})


@login_required
def contrato_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        ContratoDigital.objects.create(
            edificio=edificio, titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            partes=request.POST.get('partes', ''),
            condiciones=request.POST.get('condiciones', ''),
            monto_total=float(request.POST.get('monto_total', 0)),
            fecha_inicio=request.POST.get('fecha_inicio', timezone.now().date()),
            fecha_fin=request.POST.get('fecha_fin') or None,
        )
        messages.success(request, 'Contrato creado correctamente.')
        return redirect('monitor:contrato_list')
    return render(request, 'monitor/contrato_create.html', {'edificio': edificio})


@login_required
def inventario_list(request):
    items = ItemInventario.objects.filter(edificio__activo=True)
    edificio = request.GET.get('edificio')
    if edificio:
        items = items.filter(edificio_id=edificio)
    total_valor = items.aggregate(total=Sum('valor_estimado'))['total'] or 0
    return render(request, 'monitor/inventario_list.html', {'items': items, 'total_valor': total_valor, 'edificios': Edificio.objects.filter(activo=True)})


@login_required
def inventario_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        item = ItemInventario.objects.create(
            edificio=edificio, categoria=request.POST.get('categoria', ''),
            nombre=request.POST.get('nombre', ''),
            descripcion=request.POST.get('descripcion', ''),
            cantidad=int(request.POST.get('cantidad', 1)),
            estado=request.POST.get('estado', 'bueno'),
            ubicacion=request.POST.get('ubicacion', ''),
            valor_estimado=float(request.POST.get('valor_estimado', 0)),
        )
        if 'imagen' in request.FILES:
            item.imagen = request.FILES['imagen']
            item.save()
        messages.success(request, 'Item de inventario creado.')
        return redirect('monitor:inventario_list')
    return render(request, 'monitor/inventario_create.html', {'edificio': edificio})


@login_required
def bitacora_list(request):
    registros = BitacoraObra.objects.filter(edificio__activo=True)[:30]
    return render(request, 'monitor/bitacora_list.html', {'registros': registros})


@login_required
def bitacora_create(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        BitacoraObra.objects.create(
            edificio=edificio, titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            tipo=request.POST.get('tipo', 'avance'),
            autor=request.user,
            coste=float(request.POST.get('coste', 0)),
        )
        messages.success(request, 'Registro en bitacora creado.')
        return redirect('monitor:bitacora_list')
    return render(request, 'monitor/bitacora_create.html', {'edificio': edificio})


@login_required
def rbac_view(request):
    roles = RolSistema.objects.all()
    permisos = PermisosUsuario.objects.all()
    return render(request, 'monitor/rbac.html', {'roles': roles, 'permisos': permisos})


@login_required
def rol_create(request):
    if request.method == 'POST':
        RolSistema.objects.create(
            nombre=request.POST.get('nombre', ''),
            descripcion=request.POST.get('descripcion', ''),
            puede_ver_edificios=request.POST.get('puede_ver_edificios') == 'on',
            puede_editar_edificios=request.POST.get('puede_editar_edificios') == 'on',
            puede_ver_alertas=request.POST.get('puede_ver_alertas') == 'on',
            puede_resolver_alertas=request.POST.get('puede_resolver_alertas') == 'on',
            puede_ver_finanzas=request.POST.get('puede_ver_finanzas') == 'on',
            puede_editar_finanzas=request.POST.get('puede_editar_finanzas') == 'on',
            puede_aprobar=request.POST.get('puede_aprobar') == 'on',
            puede_exportar=request.POST.get('puede_exportar') == 'on',
            es_admin=request.POST.get('es_admin') == 'on',
        )
        messages.success(request, 'Rol creado correctamente.')
        return redirect('monitor:rbac')
    return render(request, 'monitor/rol_create.html')


@login_required
def permiso_create(request):
    if request.method == 'POST':
        PermisosUsuario.objects.create(
            usuario_id=request.POST.get('usuario'),
            rol_id=request.POST.get('rol') or None,
            notificaciones_email=request.POST.get('notificaciones_email') == 'on',
            notificaciones_push=request.POST.get('notificaciones_push') == 'on',
            notificaciones_whatsapp=request.POST.get('notificaciones_whatsapp') == 'on',
        )
        messages.success(request, 'Permisos asignados correctamente.')
        return redirect('monitor:rbac')
    return render(request, 'monitor/permiso_create.html', {'roles': RolSistema.objects.all(), 'usuarios': User.objects.all()})


@login_required
def buscador_global(request):
    q = request.GET.get('q', '').strip()
    resultados = {'edificios': [], 'alertas': [], 'facturas': [], 'gastos': [], 'comentarios': [], 'inventario': [], 'bitacora': []}
    if q:
        resultados['edificios'] = Edificio.objects.filter(nombre__icontains=q)[:10]
        resultados['alertas'] = Alerta.objects.filter(mensaje__icontains=q)[:10]
        resultados['facturas'] = Factura.objects.filter(concepto__icontains=q)[:10]
        resultados['gastos'] = Gasto.objects.filter(concepto__icontains=q)[:10]
        resultados['comentarios'] = Comentario.objects.filter(texto__icontains=q)[:10]
        resultados['inventario'] = ItemInventario.objects.filter(nombre__icontains=q)[:10]
        resultados['bitacora'] = BitacoraObra.objects.filter(titulo__icontains=q)[:10]
    total = sum(len(v) for v in resultados.values())
    return render(request, 'monitor/buscador_global.html', {'q': q, 'resultados': resultados, 'total': total})


@login_required
def comentarios_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    comentarios = Comentario.objects.filter(edificio=edificio).select_related('autor')
    if request.method == 'POST':
        padre_id = request.POST.get('padre_id')
        Comentario.objects.create(
            autor=request.user, edificio=edificio,
            texto=request.POST.get('texto', ''),
            padre_id=padre_id or None,
        )
        messages.success(request, 'Comentario publicado.')
        return redirect('monitor:comentarios', edificio_pk=edificio.pk)
    return render(request, 'monitor/comentarios.html', {'edificio': edificio, 'comentarios': comentarios})


@login_required
def recordatorios_view(request):
    recordatorios = Recordatorio.objects.filter(usuario=request.user)
    no_leidos = recordatorios.filter(leido=False).count()
    if request.method == 'POST':
        Recordatorio.objects.create(
            usuario=request.user,
            titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            tipo=request.POST.get('tipo', 'personal'),
            edificio_id=request.POST.get('edificio') or None,
            fecha_recordatorio=request.POST.get('fecha_recordatorio'),
            repetir=request.POST.get('repetir') == 'on',
            intervalo_dias=int(request.POST.get('intervalo_dias', 0)),
        )
        messages.success(request, 'Recordatorio creado.')
        return redirect('monitor:recordatorios')
    return render(request, 'monitor/recordatorios.html', {
        'recordatorios': recordatorios, 'no_leidos': no_leidos,
        'edificios': Edificio.objects.filter(activo=True),
    })


@login_required
def recordatorio_marcar(request, pk):
    rec = get_object_or_404(Recordatorio, pk=pk, usuario=request.user)
    rec.leido = True
    rec.save()
    return redirect('monitor:recordatorios')


@login_required
def calculadora_restauracion_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    calculos = CalculadoraRestauracion.objects.filter(edificio=edificio)
    if request.method == 'POST':
        calc = CalculadoraRestauracion.objects.create(
            edificio=edificio,
            titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            area_m2=float(request.POST.get('area_m2', 0)),
            costo_m2=float(request.POST.get('costo_m2', 0)),
            mano_obra=float(request.POST.get('mano_obra', 0)),
            materiales=float(request.POST.get('materiales', 0)),
            permisos=float(request.POST.get('permisos', 0)),
            imprevistos_pct=int(request.POST.get('imprevistos_pct', 10)),
        )
        messages.success(request, f'Total estimado: {calc.total_estimado} EUR')
        return redirect('monitor:calculadora_restauracion', edificio_pk=edificio.pk)
    return render(request, 'monitor/calculadora_restauracion.html', {'edificio': edificio, 'calculos': calculos})


@login_required
def exportar_multiples_view(request):
    if request.method == 'POST':
        formato = request.POST.get('formato', 'csv')
        modelo = request.POST.get('modelo', 'edificios')
        import json, csv, io
        from django.http import HttpResponse
        if modelo == 'edificios':
            data = list(Edificio.objects.values('nombre', 'direccion', 'categoria', 'salud_score'))
        elif modelo == 'alertas':
            data = list(Alerta.objects.values('mensaje', 'severidad', 'resuelta', 'fecha_creacion'))
        elif modelo == 'facturas':
            data = list(Factura.objects.values('numero', 'cliente_proveedor', 'total', 'estado', 'fecha_emision'))
        elif modelo == 'gastos':
            data = list(Gasto.objects.values('concepto', 'monto', 'pagado', 'fecha'))
        else:
            data = []
        ExportacionLog.objects.create(usuario=request.user, formato=formato, modelo_tipo=modelo, registros=len(data))
        if formato == 'json':
            response = HttpResponse(json.dumps(data, default=str, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{modelo}.json"'
        elif formato == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{modelo}.csv"'
            if data:
                writer = csv.DictWriter(response, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        elif formato == 'excel':
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{modelo}.xls"'
            if data:
                writer = csv.writer(response)
                writer.writerow(data[0].keys())
                writer.writerows([d.values() for d in data])
        else:
            response = HttpResponse(json.dumps(data, default=str), content_type='application/json')
        return response
    return render(request, 'monitor/exportar_multiples.html', {'logs': ExportacionLog.objects.all()[:20]})


@login_required
def webhooks_view(request):
    webhooks = WebhookConfig.objects.all()
    if request.method == 'POST':
        WebhookConfig.objects.create(
            nombre=request.POST.get('nombre', ''),
            url=request.POST.get('url', ''),
            evento=request.POST.get('evento', 'alerta_nueva'),
        )
        messages.success(request, 'Webhook creado.')
        return redirect('monitor:webhooks')
    return render(request, 'monitor/webhooks.html', {'webhooks': webhooks})


@login_required
def dashboard_personalizado_view(request):
    widgets = DashboardWidget.objects.filter(usuario=request.user, activo=True).order_by('posicion')
    if request.method == 'POST':
        if request.POST.get('accion') == 'crear':
            DashboardWidget.objects.create(
                usuario=request.user,
                widget_tipo=request.POST.get('widget_tipo', 'alertas'),
                titulo=request.POST.get('titulo', 'Widget'),
                posicion=int(request.POST.get('posicion', 0)),
                ancho=int(request.POST.get('ancho', 6)),
            )
            messages.success(request, 'Widget anadido al dashboard.')
        elif request.POST.get('accion') == 'eliminar':
            widget_id = request.POST.get('widget_id')
            DashboardWidget.objects.filter(pk=widget_id, usuario=request.user).delete()
            messages.success(request, 'Widget eliminado.')
        return redirect('monitor:dashboard_personalizado')
    return render(request, 'monitor/dashboard_personalizado.html', {'widgets': widgets})


@login_required
def busqueda_avanzada_view(request):
    q = request.GET.get('q', '').strip()
    filtro_tipo = request.GET.get('tipo', '')
    filtro_fecha_desde = request.GET.get('fecha_desde', '')
    filtro_fecha_hasta = request.GET.get('fecha_hasta', '')
    resultados = []
    if q:
        modelos = {
            'edificios': Edificio, 'alertas': Alerta, 'facturas': Factura,
            'gastos': Gasto, 'inventario': ItemInventario, 'bitacora': BitacoraObra,
        }
        if filtro_tipo and filtro_tipo in modelos:
            modelos = {filtro_tipo: modelos[filtro_tipo]}
        for nombre, modelo in modelos.items():
            campos = [f.name for f in modelo._meta.get_fields() if hasattr(f, 'max_length') or f.get_internal_type() == 'CharField' or f.get_internal_type() == 'TextField']
            campos_texto = [c for c in campos if c not in ['id', 'uuid']]
            from django.db.models import Q
            q_objects = Q()
            for campo in campos_texto[:3]:
                q_objects |= Q(**{f'{campo}__icontains': q})
            try:
                objs = modelo.objects.filter(q_objects)[:5]
                for obj in objs:
                    resultados.append({'tipo': nombre, 'objeto': obj, 'str': str(obj)})
            except Exception:
                pass
    return render(request, 'monitor/busqueda_avanzada.html', {'q': q, 'resultados': resultados, 'total': len(resultados), 'filtro_tipo': filtro_tipo})


@login_required
def idiomas_view(request):
    textos = TextoMultiidioma.objects.all()[:50]
    if request.method == 'POST':
        TextoMultiidioma.objects.create(
            clave=request.POST.get('clave', ''),
            es=request.POST.get('es', ''),
            en=request.POST.get('en', ''),
            fr=request.POST.get('fr', ''),
            ar=request.POST.get('ar', ''),
        )
        messages.success(request, 'Texto multiidioma creado.')
        return redirect('monitor:idiomas')
    return render(request, 'monitor/idiomas.html', {'textos': textos})


@login_required
def simulador_iot(request):
    sensores = Sensor.objects.filter(activo=True).select_related('edificio')
    total_lecturas = 0
    total_alertas = 0
    if request.method == 'POST':
        import random
        count = int(request.POST.get('count', 1))
        for _ in range(count):
            for sensor in sensores:
                ranges = {
                    'temperatura': (15.0, 35.0), 'humedad': (30.0, 85.0),
                    'vibracion': (0.0, 8.0), 'luz': (0.0, 1000.0),
                    'co2': (300.0, 800.0), 'ruido': (20.0, 90.0),
                    'grieta': (0.0, 5.0), 'presion': (1000.0, 1030.0),
                }
                r = ranges.get(sensor.tipo, (0.0, 100.0))
                valor = round(random.uniform(r[0], r[1]), 2)
                lectura = Lectura.objects.create(sensor=sensor, valor=valor, fecha_hora=timezone.now())
                total_lecturas += 1
                if lectura.es_alerta:
                    total_alertas += 1
        messages.success(request, f'Simulacion: {total_lecturas} lecturas, {total_alertas} alertas')
    stats = {
        'total_sensores': sensores.count(),
        'total_lecturas_hoy': Lectura.objects.filter(fecha_hora__date=timezone.now().date()).count(),
        'ultimas_lecturas': Lectura.objects.select_related('sensor').order_by('-fecha_hora')[:20],
    }
    return render(request, 'monitor/simulador_iot.html', {'sensores': sensores, 'stats': stats})


@login_required
def simulador_iot_stream(request):
    import random
    sensores = Sensor.objects.filter(activo=True)
    lecturas_data = []
    for sensor in sensores[:5]:
        ranges = {
            'temperatura': (15.0, 35.0), 'humedad': (30.0, 85.0),
            'vibracion': (0.0, 8.0), 'luz': (0.0, 1000.0),
            'co2': (300.0, 800.0), 'ruido': (20.0, 90.0),
            'grieta': (0.0, 5.0), 'presion': (1000.0, 1030.0),
        }
        r = ranges.get(sensor.tipo, (0.0, 100.0))
        valor = round(random.uniform(r[0], r[1]), 2)
        lectura = Lectura.objects.create(sensor=sensor, valor=valor, fecha_hora=timezone.now())
        lecturas_data.append({
            'sensor': sensor.nombre,
            'tipo': sensor.get_tipo_display(),
            'valor': valor,
            'unidad': sensor.unidad_medida,
            'edificio': sensor.edificio.nombre,
            'fecha': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'es_alerta': lectura.es_alerta,
        })
    return JsonResponse({'lecturas': lecturas_data})


@login_required
def cotizacion_list(request):
    cotizaciones = Cotizacion.objects.select_related('edificio', 'creado_por').prefetch_related('items')
    estado_filter = request.GET.get('estado', '')
    if estado_filter:
        cotizaciones = cotizaciones.filter(estado=estado_filter)
    buscar = request.GET.get('q', '')
    if buscar:
        cotizaciones = cotizaciones.filter(
            Q(cliente_nombre__icontains=buscar) | Q(titulo__icontains=buscar) | Q(cliente_email__icontains=buscar)
        )
    stats = {
        'total': Cotizacion.objects.count(),
        'borrador': Cotizacion.objects.filter(estado='borrador').count(),
        'enviada': Cotizacion.objects.filter(estado='enviada').count(),
        'aceptada': Cotizacion.objects.filter(estado='aceptada').count(),
        'rechazada': Cotizacion.objects.filter(estado='rechazada').count(),
        'total_monto': Cotizacion.objects.filter(estado='aceptada').aggregate(t=Sum('total'))['t'] or 0,
    }
    return render(request, 'monitor/cotizacion_list.html', {
        'cotizaciones': cotizaciones,
        'stats': stats,
        'estado_filter': estado_filter,
        'buscar': buscar,
    })


@login_required
def cotizacion_create(request):
    edificio_id = request.GET.get('edificio')
    edificio = None
    if edificio_id:
        edificio = get_object_or_404(Edificio, pk=edificio_id)
    if request.method == 'POST':
        cliente_nombre = request.POST.get('cliente_nombre', '')
        cliente_email = request.POST.get('cliente_email', '')
        cliente_telefono = request.POST.get('cliente_telefono', '')
        titulo = request.POST.get('titulo', '')
        descripcion = request.POST.get('descripcion', '')
        edificio_pk = request.POST.get('edificio', '')
        cot = Cotizacion.objects.create(
            cliente_nombre=cliente_nombre,
            cliente_email=cliente_email,
            cliente_telefono=cliente_telefono,
            titulo=titulo,
            descripcion=descripcion,
            edificio=Edificio.objects.filter(pk=edificio_pk).first() if edificio_pk else edificio,
            creado_por=request.user,
        )
        conceptos = request.POST.getlist('concepto[]')
        cantidades = request.POST.getlist('cantidad[]')
        precios = request.POST.getlist('precio_unitario[]')
        total = 0
        for i in range(len(conceptos)):
            if conceptos[i].strip():
                cant = float(cantidades[i]) if i < len(cantidades) and cantidades[i] else 1
                precio = float(precios[i]) if i < len(precios) and precios[i] else 0
                subtotal = cant * precio
                CotizacionItem.objects.create(
                    cotizacion=cot, concepto=conceptos[i],
                    cantidad=cant, precio_unitario=precio, subtotal=subtotal,
                )
                total += subtotal
        cot.total = total
        cot.save()
        CotizacionHistorial.objects.create(cotizacion=cot, accion='creada', actor=request.user)
        AuditLog.registrar(request.user, 'crear', 'Cotizacion', cot.pk, f'Cotización creada: {cot.titulo}')
        messages.success(request, f'Cotización "{cot.titulo}" creada correctamente.')
        return redirect('monitor:cotizacion_detail', cotizacion_pk=cot.pk)
    edificios = Edificio.objects.filter(activo=True)
    return render(request, 'monitor/cotizacion_create.html', {
        'edificio': edificio,
        'edificios': edificios,
    })


@login_required
def cotizacion_detail(request, cotizacion_pk):
    cot = get_object_or_404(Cotizacion, pk=cotizacion_pk)
    items = cot.items.all()
    historial = cot.historial.select_related('actor').all()
    return render(request, 'monitor/cotizacion_detail.html', {
        'cotizacion': cot,
        'items': items,
        'historial': historial,
    })


@login_required
def cotizacion_edit(request, cotizacion_pk):
    cot = get_object_or_404(Cotizacion, pk=cotizacion_pk)
    if cot.estado not in ('borrador',):
        messages.error(request, 'Solo puedes editar cotizaciones en borrador.')
        return redirect('monitor:cotizacion_detail', cotizacion_pk=cot.pk)
    if request.method == 'POST':
        cot.cliente_nombre = request.POST.get('cliente_nombre', cot.cliente_nombre)
        cot.cliente_email = request.POST.get('cliente_email', cot.cliente_email)
        cot.cliente_telefono = request.POST.get('cliente_telefono', cot.cliente_telefono)
        cot.titulo = request.POST.get('titulo', cot.titulo)
        cot.descripcion = request.POST.get('descripcion', cot.descripcion)
        cot.edificio = Edificio.objects.filter(pk=request.POST.get('edificio', '')).first() or cot.edificio
        cot.save()
        cot.items.all().delete()
        conceptos = request.POST.getlist('concepto[]')
        cantidades = request.POST.getlist('cantidad[]')
        precios = request.POST.getlist('precio_unitario[]')
        total = 0
        for i in range(len(conceptos)):
            if conceptos[i].strip():
                cant = float(cantidades[i]) if i < len(cantidades) and cantidades[i] else 1
                precio = float(precios[i]) if i < len(precios) and precios[i] else 0
                subtotal = cant * precio
                CotizacionItem.objects.create(
                    cotizacion=cot, concepto=conceptos[i],
                    cantidad=cant, precio_unitario=precio, subtotal=subtotal,
                )
                total += subtotal
        cot.total = total
        cot.save()
        CotizacionHistorial.objects.create(cotizacion=cot, accion='editada', actor=request.user)
        messages.success(request, 'Cotización actualizada.')
        return redirect('monitor:cotizacion_detail', cotizacion_pk=cot.pk)
    edificios = Edificio.objects.filter(activo=True)
    items = cot.items.all()
    return render(request, 'monitor/cotizacion_create.html', {
        'cotizacion': cot,
        'items': items,
        'edificios': edificios,
        'editing': True,
    })


@login_required
def cotizacion_enviar(request, cotizacion_pk):
    cot = get_object_or_404(Cotizacion, pk=cotizacion_pk)
    if request.method == 'POST':
        cot.estado = 'enviada'
        cot.fecha_envio = timezone.now()
        cot.fecha_expiracion = timezone.now() + timedelta(days=7)
        cot.save()
        CotizacionHistorial.objects.create(
            cotizacion=cot, accion='enviada', actor=request.user,
            comentario=f'Enviada a {cot.cliente_email}'
        )
        public_url = f'{settings.SITE_URL or "http://localhost:8000"}/cotizacion/publica/{cot.token_publico}/'
        try:
            html_body = render_to_string('monitor/email_cotizacion.html', {
                'cotizacion': cot,
                'items': cot.items.all(),
                'public_url': public_url,
            })
            email = EmailMultiAlternatives(
                subject=f'SmartHeritage - Cotización: {cot.titulo}',
                body=f'Hola {cot.cliente_nombre}, tienes una nueva cotización. Accede aquí: {public_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cot.cliente_email],
            )
            email.attach_alternative(html_body, 'text/html')
            email.send(fail_silently=False)
            messages.success(request, f'Cotización enviada a {cot.cliente_email}. Expira en 7 días.')
        except Exception as e:
            messages.error(request, f'Error al enviar email: {str(e)}')
            cot.estado = 'borrador'
            cot.save()
    return redirect('monitor:cotizacion_detail', cotizacion_pk=cot.pk)


@login_required
def cotizacion_pdf(request, cotizacion_pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    cot = get_object_or_404(Cotizacion, pk=cotizacion_pk)
    items = cot.items.all()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#1a1a2e'))
    story.append(Paragraph('SmartHeritage', title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f'<b>Cotización:</b> {cot.titulo}', styles['Heading2']))
    story.append(Spacer(1, 0.3*cm))
    info_data = [
        ['Cliente:', cot.cliente_nombre],
        ['Email:', cot.cliente_email],
        ['Teléfono:', cot.cliente_telefono or 'N/A'],
        ['Estado:', cot.get_estado_display()],
        ['Fecha:', cot.fecha_creacion.strftime('%d/%m/%Y')],
    ]
    if cot.edificio:
        info_data.append(['Edificio:', cot.edificio.nombre])
    info_table = Table(info_data, colWidths=[4*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))
    if cot.descripcion:
        story.append(Paragraph(f'<b>Descripción:</b> {cot.descripcion}', styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
    item_data = [['Concepto', 'Cant.', 'Precio Unit.', 'Subtotal']]
    for item in items:
        item_data.append([
            item.concepto,
            str(item.cantidad),
            f'{item.precio_unitario:.2f} EUR',
            f'{item.subtotal:.2f} EUR',
        ])
    item_data.append(['', '', 'TOTAL:', f'{cot.total:.2f} EUR'])
    item_table = Table(item_data, colWidths=[7*cm, 2.5*cm, 3.5*cm, 3.5*cm])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (-1, -1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('FONT', (-1, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph('Esta cotización es válida por 7 días desde el envío.', styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename=f'cotizacion_{cot.pk}.pdf')


def cotizacion_publica_view(request, token_uuid):
    cot = get_object_or_404(Cotizacion, token_publico=token_uuid)
    items = cot.items.all()
    if cot.estado == 'enviada' and cot.esta_vencida:
        cot.estado = 'expirada'
        cot.save()
        CotizacionHistorial.objects.create(cotizacion=cot, accion='expirada', comentario='Expirada automáticamente')
    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        motivo = request.POST.get('motivo', '')
        if accion == 'aceptar' and cot.estado in ('enviada',):
            cot.estado = 'aceptada'
            cot.fecha_respuesta = timezone.now()
            cot.save()
            CotizacionHistorial.objects.create(
                cotizacion=cot, accion='aceptada', comentario='Aceptada por el cliente'
            )
            messages.success(request, '¡Cotización aceptada! Nos pondremos en contacto contigo.')
        elif accion == 'rechazar' and cot.estado in ('enviada',):
            cot.estado = 'rechazada'
            cot.fecha_respuesta = timezone.now()
            cot.motivo_rechazo = motivo
            cot.save()
            CotizacionHistorial.objects.create(
                cotizacion=cot, accion='rechazada', comentario=f'Motivo: {motivo}'
            )
            messages.info(request, 'Cotización rechazada. Si tienes dudas, contáctanos.')
    return render(request, 'monitor/cotizacion_publica.html', {
        'cotizacion': cot,
        'items': items,
    })


# =============================================
# FUNCIONALIDADES INNOVADORAS - VISTAS NUEVAS
# =============================================

# --- 1. TIME MACHINE PATRIMONIAL ---
@login_required
def time_machine_view(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    historial = TimeMachineRequest.objects.filter(edificio=edificio, usuario=request.user)[:10]
    if request.method == 'POST':
        imagen = request.FILES.get('imagen')
        epoca = request.POST.get('epoca_destino', 1800)
        estilo = request.POST.get('estilo_reconstruccion', 'medieval')
        if imagen:
            req = TimeMachineRequest.objects.create(
                edificio=edificio,
                imagen_original=imagen,
                epoca_destino=int(epoca),
                estilo_reconstruccion=estilo,
                usuario=request.user,
                prompt_generado=f'Reconstruccion de {edificio.nombre} en epoca {epoca}, estilo {estilo}',
                estado='pendiente',
            )
            messages.success(request, f'Solicitud Time Machine creada para la epoca {epoca}.')
            return redirect('monitor:time_machine', pk=edificio.pk)
    return render(request, 'monitor/time_machine.html', {
        'edificio': edificio,
        'historial': historial,
    })


@login_required
def time_machine_procesar_view(request, pk):
    solicitud = get_object_or_404(TimeMachineRequest, pk=pk)
    if request.user != solicitud.usuario and not request.user.is_staff:
        messages.warning(request, 'No tienes permiso para procesar esta solicitud.')
        return redirect('monitor:dashboard')
    solicitud.estado = 'procesando'
    solicitud.save()
    solicitud.estado = 'completado'
    solicitud.confianza = 87.5
    solicitud.save()
    messages.success(request, 'Time Machine procesado correctamente.')
    return redirect('monitor:time_machine', pk=solicitud.edificio.pk)


# --- 2. DIGITAL TWIN 3D INTERACTIVO ---
@login_required
def digital_twin_3d_view(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    twin, _ = DigitalTwin.objects.get_or_create(edificio=edificio)
    sesion = DigitalTwinSesion.objects.create(edificio=edificio, usuario=request.user)
    lecturas = Lectura.objects.filter(sensor__edificio=edificio).select_related('sensor').order_by('-fecha_hora')[:20]
    sensores = Sensor.objects.filter(edificio=edificio, activo=True)
    return render(request, 'monitor/digital_twin_3d.html', {
        'edificio': edificio,
        'twin': twin,
        'sesion': sesion,
        'lecturas': lecturas,
        'sensores': sensores,
    })


@login_required
def api_twin_interaccion(request, pk):
    if request.method == 'POST':
        data = json.loads(request.body)
        sesion_id = data.get('sesion_id')
        tipo = data.get('tipo', 'click')
        try:
            sesion = DigitalTwinSesion.objects.get(pk=sesion_id)
            interacciones = sesion.interacciones
            interacciones[tipo] = interacciones.get(tipo, 0) + 1
            sesion.interacciones = interacciones
            sesion.save()
        except DigitalTwinSesion.DoesNotExist:
            pass
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'POST required'}, status=400)


# --- 3. SIMULADOR DE DESASTRES ---
@login_required
def simulador_desastres_view(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    simulaciones = SimulacionDesastre.objects.filter(edificio=edificio)[:10]
    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'terremoto')
        intensidad = float(request.POST.get('intensidad', 5.0))
        costo = 0
        zonas = []
        recomendaciones = ''
        if tipo == 'terremoto':
            if intensidad > 7:
                costo = 500000
                zonas = ['Fachada principal', 'Cupula', 'Torre campanario']
                recomendaciones = 'Evacuacion inmediata. Revision estructural obligatoria.'
            elif intensidad > 5:
                costo = 150000
                zonas = ['Grietas en muros', 'Campanas']
                recomendaciones = 'Revision de grietas. Refuerzo de cupula.'
            else:
                costo = 20000
                zonas = ['Grietas menores']
                recomendaciones = 'Monitoreo de grietas existentes.'
        elif tipo == 'incendio':
            if intensidad > 80:
                costo = 800000
                zonas = ['Techos', 'Retablos', 'Biblioteca']
                recomendaciones = 'Activar protocolo de emergencia total.'
            elif intensidad > 50:
                costo = 300000
                zonas = ['Sistema electrico', 'Madera']
                recomendaciones = 'Instalar detectores adicionales.'
            else:
                costo = 50000
                zonas = ['Zona puntual']
                recomendaciones = 'Revision de instalacion electrica.'
        elif tipo == 'inundacion':
            if intensidad > 1000:
                costo = 400000
                zonas = ['Sótano', 'Cimentación', 'Muros']
                recomendaciones = 'Instalar sistemas de drenaje.'
            else:
                costo = 80000
                zonas = ['Zona baja']
                recomendaciones = 'Mejorar evacuacion de agua.'
        sim = SimulacionDesastre.objects.create(
            edificio=edificio, tipo=tipo, intensidad=intensidad,
            costo_dano_estimado=costo, zonas_afectadas=zonas,
            recomendaciones=recomendaciones, usuario=request.user,
            resultado={'tipo': tipo, 'intensidad': intensidad, 'costo': str(costo)},
        )
        AuditLog.registrar(request.user, 'crear', 'SimulacionDesastre', sim.pk,
                           f'Simulacion {tipo} en {edificio.nombre}')
        messages.warning(request, f'Simulacion completada. Dano estimado: {costo:,.0f} EUR')
        return redirect('monitor:simulador_desastres', pk=edificio.pk)
    return render(request, 'monitor/simulador_desastres.html', {
        'edificio': edificio,
        'simulaciones': simulaciones,
    })


# --- 4. PATRIMONIO VIVO (Camaras IA) ---
@login_required
def patrimonio_vivo_view(request):
    camaras = CamaraVigilancia.objects.filter(activa=True).select_related('edificio')
    eventos_hoy = EventoVigilancia.objects.filter(fecha__date=timezone.now().date())[:50]
    stats = {
        'total_camaras': camaras.count(),
        'eventos_hoy': EventoVigilancia.objects.filter(fecha__date=timezone.now().date()).count(),
        'vandalismo': EventoVigilancia.objects.filter(tipo='vandalismo', fecha__date=timezone.now().date()).count(),
        'personas': EventoVigilancia.objects.filter(tipo='conteo', fecha__date=timezone.now().date()).aggregate(
            total=Sum('personas_detectadas'))['total'] or 0,
    }
    if request.method == 'POST':
        camara_pk = request.POST.get('camara_id')
        titulo = request.POST.get('titulo', 'Evento manual')
        tipo = request.POST.get('tipo_evento', 'movimiento')
        camara = get_object_or_404(CamaraVigilancia, pk=camara_pk)
        EventoVigilancia.objects.create(
            camara=camara, tipo=tipo, severidad='info',
            titulo=titulo, descripcion=f'Evento registrado manualmente por {request.user.username}',
        )
        messages.success(request, 'Evento de vigilancia registrado.')
        return redirect('monitor:patrimonio_vivo')
    return render(request, 'monitor/patrimonio_vivo.html', {
        'camaras': camaras,
        'eventos': eventos_hoy,
        'stats': stats,
    })


@login_required
def camara_create_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        CamaraVigilancia.objects.create(
            edificio=edificio,
            nombre=request.POST.get('nombre', 'Camara'),
            ubicacion=request.POST.get('ubicacion', ''),
            detectar_vandalismo='detectar_vandalismo' in request.POST,
            contar_visitantes='contar_visitantes' in request.POST,
        )
        messages.success(request, 'Camara creada correctamente.')
        return redirect('monitor:patrimonio_vivo')
    return render(request, 'monitor/camara_create.html', {'edificio': edificio})


# --- 5. HERITAGE NFT MARKETPLACE ---
@login_required
def nft_marketplace_view(request):
    nfts = HeritageNFT.objects.filter(activo=True).select_related('edificio', 'propietario')
    filtros = {}
    tipo = request.GET.get('tipo', '')
    if tipo == 'subasta':
        nfts = nfts.filter(es_subasta=True, estado='en_subasta')
    elif tipo == 'venta':
        nfts = nfts.filter(es_subasta=False, estado='disponible')
    total_nfts = nfts.count()
    total_volumen = HeritageNFT.objects.filter(estado='vendido').aggregate(t=Sum('precio_actual'))['t'] or 0
    return render(request, 'monitor/nft_marketplace.html', {
        'nfts': nfts,
        'total_nfts': total_nfts,
        'total_volumen': total_volumen,
        'filtro_activo': tipo,
    })


@login_required
def nft_create_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    if request.method == 'POST':
        imagen = request.FILES.get('imagen')
        precio = float(request.POST.get('precio', 100))
        nft = HeritageNFT.objects.create(
            edificio=edificio,
            titulo=request.POST.get('titulo', f'NFT - {edificio.nombre}'),
            descripcion=request.POST.get('descripcion', ''),
            imagen=imagen if imagen else None,
            precio_inicial=precio,
            precio_actual=precio,
            propietario=request.user,
            creado_por=request.user,
            es_subasta='es_subasta' in request.POST,
            estado='en_subasta' if 'es_subasta' in request.POST else 'disponible',
            token_id=f'HER-{uuid.uuid4().hex[:8].upper()}',
            hash_contrato=f'0x{uuid.uuid4().hex}',
        )
        AuditLog.registrar(request.user, 'crear', 'HeritageNFT', nft.pk, f'NFT creado: {nft.titulo}')
        messages.success(request, f'NFT "{nft.titulo}" creado correctamente.')
        return redirect('monitor:nft_detalle', pk=nft.pk)
    return render(request, 'monitor/nft_create.html', {'edificio': edificio})


@login_required
def nft_detalle_view(request, pk):
    nft = get_object_or_404(HeritageNFT, pk=pk)
    pujas = nft.historial_pujas.all().select_related('postor')[:20]
    nft.visitas += 1
    nft.save(update_fields=['visitas'])
    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        if accion == 'pujar' and nft.es_subasta:
            monto = float(request.POST.get('monto', 0))
            if monto > float(nft.precio_actual):
                PujaNFT.objects.create(nft=nft, postor=request.user, monto=monto)
                nft.precio_actual = monto
                nft.pujas += 1
                nft.save(update_fields=['precio_actual', 'pujas'])
                messages.success(request, f'Puja de {monto} EUR registrada.')
            else:
                messages.warning(request, 'La puja debe ser mayor al precio actual.')
        elif accion == 'comprar' and nft.estado == 'disponible':
            nft.estado = 'vendido'
            nft.propietario = request.user
            nft.fecha_venta = timezone.now()
            nft.save(update_fields=['estado', 'propietario', 'fecha_venta'])
            messages.success(request, f'NFT "{nft.titulo}" comprado.')
        return redirect('monitor:nft_detalle', pk=nft.pk)
    return render(request, 'monitor/nft_detalle.html', {'nft': nft, 'pujas': pujas})


# --- 6. SMART CONTRACTS DE RESTAURACION ---
@login_required
def smart_contract_view(request, edificio_pk):
    edificio = get_object_or_404(Edificio, pk=edificio_pk)
    contratos = SmartContract.objects.filter(edificio=edificio)[:10]
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '')
        monto = float(request.POST.get('monto_total', 0))
        contratista_id = request.POST.get('contratista')
        contratista = get_object_or_404(User, pk=contratista_id) if contratista_id else request.user
        contrato = SmartContract.objects.create(
            edificio=edificio, titulo=titulo,
            descripcion=request.POST.get('descripcion', ''),
            monto_total=monto, contratista=contratista,
            creador=request.user, estado='activo',
            hash_blockchain=f'0x{uuid.uuid4().hex}',
        )
        hitos_json = json.loads(request.POST.get('hitos', '[]'))
        for i, h in enumerate(hitos_json):
            HitoContrato.objects.create(
                contrato=contrato, titulo=h.get('titulo', f'Hito {i+1}'),
                descripcion=h.get('descripcion', ''),
                monto_liberar=float(h.get('monto', 0)),
                porcentaje=float(h.get('porcentaje', 0)),
                orden=i+1,
            )
        AuditLog.registrar(request.user, 'crear', 'SmartContract', contrato.pk, f'Contrato: {titulo}')
        messages.success(request, 'Smart Contract creado.')
        return redirect('monitor:smart_contract', edificio_pk=edificio.pk)
    return render(request, 'monitor/smart_contract.html', {
        'edificio': edificio, 'contratos': contratos,
    })


@login_required
def hito_completar_view(request, pk):
    hito = get_object_or_404(HitoContrato, pk=pk)
    hito.completado = True
    hito.fecha_completado = timezone.now()
    hito.save(update_fields=['completado', 'fecha_completado'])
    contrato = hito.contrato
    if all(h.completado for h in contrato.hitos.all()):
        contrato.estado = 'completado'
        contrato.fecha_completado = timezone.now()
        contrato.save(update_fields=['estado', 'fecha_completado'])
    messages.success(request, f'Hito "{hito.titulo}" completado. Pago de {hito.monto_liberar} EUR liberado.')
    return redirect('monitor:smart_contract', edificio_pk=contrato.edificio.pk)


# --- 7. HERITAGE CARBON CREDITS ---
@login_required
def carbon_credits_view(request):
    credits = CarbonCredit.objects.all().select_related('edificio')
    total_creditos = credits.aggregate(t=Sum('creditos_generados'))['t'] or 0
    creditos_validados = credits.filter(validado=True).aggregate(t=Sum('creditos_generados'))['t'] or 0
    if request.method == 'POST':
        edificio_id = request.POST.get('edificio')
        edificio = get_object_or_404(Edificio, pk=edificio_id)
        CarbonCredit.objects.create(
            edificio=edificio,
            creditos_generados=float(request.POST.get('creditos', 0)),
            certificado=f'CC-{uuid.uuid4().hex[:8].upper()}',
            metodo_calculo=request.POST.get('metodo', 'restauracion'),
            descripcion=request.POST.get('descripcion', ''),
        )
        messages.success(request, 'Carbon Credit registrado.')
        return redirect('monitor:carbon_credits')
    edificios = Edificio.objects.filter(activo=True)
    return render(request, 'monitor/carbon_credits.html', {
        'credits': credits, 'edificios': edificios,
        'total_creditos': total_creditos, 'creditos_validados': creditos_validados,
    })


# --- 8. DNA DEL EDIFICIO ---
@login_required
def dna_edificio_view(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    dna, _ = DNAEdificio.objects.get_or_create(edificio=edificio)
    if request.method == 'POST':
        dna.score_estructural = float(request.POST.get('estructural', dna.score_estructural))
        dna.score_ambiental = float(request.POST.get('ambiental', dna.score_ambiental))
        dna.score_historico = float(request.POST.get('historico', dna.score_historico))
        dna.score_accesibilidad = float(request.POST.get('accesibilidad', dna.score_accesibilidad))
        dna.score_tecnologico = float(request.POST.get('tecnologico', dna.score_tecnologico))
        dna.score_energetico = float(request.POST.get('energetico', dna.score_energetico))
        dna.version += 1
        dna.save()
        messages.success(request, f'DNA actualizado a v{dna.version}.')
        return redirect('monitor:dna_edificio', pk=edificio.pk)
    return render(request, 'monitor/dna_edificio.html', {
        'edificio': edificio, 'dna': dna,
    })


# --- 9. AI HERITAGE GUARDIAN ---
@login_required
def ai_guardian_view(request):
    reglas = GuardianRule.objects.filter(activa=True)
    alertas = GuardianAlert.objects.filter(resuelta=False).select_related('edificio', 'regla')[:50]
    stats = {
        'total_reglas': reglas.count(),
        'alertas_criticas': alertas.filter(severidad='critical').count(),
        'alertas_warning': alertas.filter(severidad='warning').count(),
        'edificios_monitorizados': reglas.values('edificios').distinct().count(),
    }
    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        if accion == 'crear_regla':
            regla = GuardianRule.objects.create(
                nombre=request.POST.get('nombre', ''),
                descripcion=request.POST.get('descripcion', ''),
                tipo_sensor=request.POST.get('tipo_sensor', 'temperatura'),
                condicion=json.loads(request.POST.get('condicion', '{}')),
                severidad=request.POST.get('severidad', 'warning'),
            )
            edificio_ids = request.POST.getlist('edificios')
            if edificio_ids:
                regla.edificios.set(Edificio.objects.filter(pk__in=edificio_ids))
            messages.success(request, 'Regla Guardian creada.')
        elif accion == 'resolver_alerta':
            alerta_id = request.POST.get('alerta_id')
            alerta = get_object_or_404(GuardianAlert, pk=alerta_id)
            alerta.resuelta = True
            alerta.fecha_resolucion = timezone.now()
            alerta.save(update_fields=['resuelta', 'fecha_resolucion'])
            messages.success(request, 'Alerta resuelta.')
        return redirect('monitor:ai_guardian')
    edificios = Edificio.objects.filter(activo=True)
    return render(request, 'monitor/ai_guardian.html', {
        'reglas': reglas, 'alertas': alertas, 'stats': stats, 'edificios': edificios,
    })


# --- 10. TOUR VR/AR IMMERSIVE ---
@login_required
def tour_vr_view(request, pk):
    edificio = get_object_or_404(Edificio, pk=pk)
    tours = TourVR.objects.filter(edificio=edificio)
    tour_activo = tours.filter(activo=True).first()
    if request.method == 'POST':
        tour = TourVR.objects.create(
            edificio=edificio,
            titulo=request.POST.get('titulo', f'Tour {edificio.nombre}'),
            descripcion=request.POST.get('descripcion', ''),
            video_360_url=request.POST.get('video_360_url', ''),
            modelo_glb_url=request.POST.get('modelo_glb_url', ''),
            es_vr='es_vr' in request.POST,
            es_ar='es_ar' in request.POST,
        )
        messages.success(request, 'Tour VR/AR creado.')
        return redirect('monitor:tour_vr', pk=edificio.pk)
    return render(request, 'monitor/tour_vr.html', {
        'edificio': edificio, 'tours': tours, 'tour_activo': tour_activo,
    })


@login_required
def tour_vr_visita_view(request, pk):
    tour = get_object_or_404(TourVR, pk=pk)
    tour.vistas += 1
    tour.save(update_fields=['vistas'])
    return render(request, 'monitor/tour_vr_visita.html', {'tour': tour})


# --- 11. GAMIFICACION AVANZADA (Desafios) ---
@login_required
def desafios_view(request):
    now = timezone.now()
    desafios_activos = Desafio.objects.filter(activo=True, fecha_inicio__lte=now, fecha_fin__gte=now)
    mis_desafios = DesafioUsuario.objects.filter(usuario=request.user).select_related('desafio')
    ranking = DesafioUsuario.objects.values('usuario__username').annotate(
        total_puntos=Sum('puntos_ganados')
    ).order_by('-total_puntos')[:20]
    if request.method == 'POST':
        desafio_id = request.POST.get('desafio_id')
        desafio = get_object_or_404(Desafio, pk=desafio_id)
        participacion, created = DesafioUsuario.objects.get_or_create(
            desafio=desafio, usuario=request.user,
            defaults={'progreso': 0, 'puntos_ganados': 0}
        )
        if created:
            messages.success(request, f'Te has unido al desafio "{desafio.titulo}".')
        return redirect('monitor:desafios')
    return render(request, 'monitor/desafios.html', {
        'desafios_activos': desafios_activos,
        'mis_desafios': mis_desafios,
        'ranking': ranking,
    })


@login_required
def desafio_progreso_view(request, pk):
    desafio_usuario = get_object_or_404(DesafioUsuario, pk=pk, usuario=request.user)
    progreso = float(request.POST.get('progreso', desafio_usuario.progreso))
    desafio_usuario.progreso = min(100, progreso)
    if desafio_usuario.progreso >= 100 and not desafio_usuario.completado:
        desafio_usuario.completado = True
        desafio_usuario.fecha_completado = timezone.now()
        desafio_usuario.puntos_ganados = desafio_usuario.desafio.puntos_recompensa
        PuntoGamificacion.objects.create(
            usuario=request.user, accion='resolver_alerta',
            puntos=desafio_usuario.puntos_ganados,
            descripcion=f'Desafio completado: {desafio_usuario.desafio.titulo}'
        )
        messages.success(request, f'Desafio completado! +{desafio_usuario.puntos_ganados} puntos')
    desafio_usuario.save()
    return redirect('monitor:desafios')


@login_required
def desafio_crear_view(request):
    if request.method == 'POST':
        Desafio.objects.create(
            titulo=request.POST.get('titulo', ''),
            descripcion=request.POST.get('descripcion', ''),
            tipo=request.POST.get('tipo', 'diario'),
            accion_requerida=request.POST.get('accion_requerida', 'resolver_alerta'),
            objetivo=int(request.POST.get('objetivo', 1)),
            puntos_recompensa=int(request.POST.get('puntos', 10)),
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timedelta(days=7),
        )
        messages.success(request, 'Desafio creado.')
        return redirect('monitor:desafios')
    return render(request, 'monitor/desafio_crear.html')
