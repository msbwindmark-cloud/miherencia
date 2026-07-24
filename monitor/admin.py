from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Edificio, Sensor, SensorFoto, Lectura, Alerta, Mantenimiento, Equipo, Informe,
    Notificacion, AuditLog, PerfilUsuario,
    AnalisisIA, PrediccionML, Donacion, ReporteCiudadano, Seguro,
    EficienciaEnergetica, CumplimientoLegal, CertificadoBlockchain,
    TourVirtual, VisitaQR, Evento, TiendaPatrimonio,
    ChatMensajeIA, ComentarioEdificio, GaleriaFoto, MedicionRuido,
    CalidadAire, BackupLog,
    DocumentoEdificio, Herramienta, FormularioInspeccion,
    TimelineHistorico, RecomendacionIA, AnomaliaDetectada, Voluntario,
    ReporteAutomatico, MantenimientoPredictivo, RegistroROI,
    ConfiguracionIdioma, ModoEmergencia, ComparativaCiudad,
    CategoriaIngreso, CategoriaGasto, Ingreso, Gasto, Factura, Nomina, Presupuesto, CuentaContable,
    ChatAsistenteIA, DigitalTwin, FotoInspeccion, Cita, TareaKanban,
    NotificacionWhatsApp, ContratoDigital, ItemInventario, BitacoraObra,
    RolSistema, PermisosUsuario, Comentario, Recordatorio, CalculadoraRestauracion,
    ExportacionLog, WebhookConfig, DashboardWidget, TextoMultiidioma, NotificacionPush
)


class SensorInline(admin.TabularInline):
    model = Sensor
    extra = 0
    readonly_fields = ('fecha_creacion',)
    fields = ('nombre', 'tipo', 'ubicacionDescripcion', 'activo', 'umbral_min', 'umbral_max')


@admin.register(Edificio)
class EdificioAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'ciudad', 'categoria', 'estado_badge',
        'num_sensores_display', 'alertas_display', 'salud_display',
        'proteccion_oficial', 'activo'
    )
    list_filter = ('categoria', 'estado_general', 'ciudad', 'provincia', 'proteccion_oficial', 'activo')
    search_fields = ('nombre', 'direccion', 'ciudad', 'descripcion')
    readonly_fields = ('id', 'fecha_creacion', 'fecha_actualizacion', 'salud_score_display')
    list_editable = ('activo',)
    inlines = [SensorInline]
    fieldsets = (
        ('Información General', {
            'fields': ('id', 'nombre', 'direccion', 'ciudad', 'provincia', 'codigo_postal', 'activo')
        }),
        ('Geolocalización', {
            'fields': ('latitud', 'longitud'),
            'classes': ('collapse',)
        }),
        ('Detalles Patrimoniales', {
            'fields': ('categoria', 'anno_construccion', 'proteccion_oficial', 'descripcion', 'estado_general')
        }),
        ('Multimedia', {
            'fields': ('imagen_principal',)
        }),
        ('Propietario', {
            'fields': ('propietario',)
        }),
        ('Métricas', {
            'fields': ('salud_score_display', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    def estado_badge(self, obj):
        colors = {
            'excelente': '#28a745',
            'bueno': '#17a2b8',
            'regular': '#ffc107',
            'malo': '#fd7e14',
            'critico': '#dc3545',
        }
        color = colors.get(obj.estado_general, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_estado_general_display()
        )
    estado_badge.short_description = 'Estado'

    def num_sensores_display(self, obj):
        return obj.num_sensores
    num_sensores_display.short_description = 'Sensores'

    def alertas_display(self, obj):
        count = obj.alertas_activas
        if count > 0:
            return format_html(
                '<span style="color:#dc3545;font-weight:700;">{} alertas</span>', count
            )
        return format_html('<span style="color:#28a745;">Sin alertas</span>')
    alertas_display.short_description = 'Alertas'

    def salud_display(self, obj):
        score = obj.salud_score
        if score >= 80:
            color = '#28a745'
        elif score >= 60:
            color = '#ffc107'
        elif score >= 40:
            color = '#fd7e14'
        else:
            color = '#dc3545'
        return format_html(
            '<div style="width:100%;background:#e9ecef;border-radius:10px;height:20px;">'
            '<div style="width:{}%;background:{};height:100%;border-radius:10px;text-align:center;'
            'color:white;font-size:11px;font-weight:700;line-height:20px;">{}</div></div>',
            max(score, 5), color, f'{score}/100'
        )
    salud_display.short_description = 'Salud'

    def salud_score_display(self, obj):
        return f'{obj.salud_score}/100'
    salud_score_display.short_description = 'Puntuación de Salud'


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'edificio', 'tipo_display', 'ubicacionDescripcion',
        'activo', 'umbral_display', 'ultima_lectura_display',
        'lecturas_hoy_display', 'fecha_instalacion'
    )
    list_filter = ('tipo', 'activo', 'edificio__ciudad')
    search_fields = ('nombre', 'ubicacionDescripcion', 'edificio__nombre')
    readonly_fields = ('id', 'fecha_creacion', 'qr_preview')
    list_editable = ('activo',)
    raw_id_fields = ('edificio',)
    fieldsets = (
        ('Información del Sensor', {
            'fields': ('id', 'edificio', 'nombre', 'tipo', 'ubicacionDescripcion', 'activo')
        }),
        ('Geolocalización', {
            'fields': ('latitud', 'longitud'),
            'classes': ('collapse',)
        }),
        ('Umbrales y Medición', {
            'fields': ('umbral_min', 'umbral_max', 'unidad_medida')
        }),
        ('QR Code', {
            'fields': ('qr_preview',),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_instalacion', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )

    def tipo_display(self, obj):
        colors = {
            'temperatura': '#e74c3c',
            'humedad': '#3498db',
            'vibracion': '#f39c12',
            'luz': '#f1c40f',
            'co2': '#27ae60',
            'ruido': '#9b59b6',
            'grieta': '#e67e22',
            'presion': '#1abc9c',
        }
        color = colors.get(obj.tipo, '#95a5a6')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:8px;font-size:11px;">{}</span>',
            color, obj.get_tipo_display()
        )
    tipo_display.short_description = 'Tipo'

    def umbral_display(self, obj):
        parts = []
        if obj.umbral_min is not None:
            parts.append(f'Min: {obj.umbral_min}')
        if obj.umbral_max is not None:
            parts.append(f'Max: {obj.umbral_max}')
        return ' | '.join(parts) if parts else '-'
    umbral_display.short_description = 'Umbrales'

    def ultima_lectura_display(self, obj):
        ultima = obj.ultima_lectura
        if ultima:
            return f'{ultima.valor} {obj.unidad_medida}'
        return '-'
    ultima_lectura_display.short_description = 'Última Lectura'

    def lecturas_hoy_display(self, obj):
        return obj.lecturas_hoy
    lecturas_hoy_display.short_description = 'Lecturas Hoy'

    def qr_preview(self, obj):
        return format_html(
            '<img src="data:image/png;base64,{}" style="width:150px;height:150px;border:2px solid #dee2e6;border-radius:8px;" />',
            obj.qr_code_b64
        )
    qr_preview.short_description = 'QR Code del Sensor'


@admin.register(Lectura)
class LecturaAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'valor_display', 'fecha_hora', 'alerta_badge')
    list_filter = ('sensor__tipo', 'es_alerta', 'fecha_hora')
    search_fields = ('sensor__nombre', 'sensor__edificio__nombre')
    readonly_fields = ('id', 'es_alerta')
    raw_id_fields = ('sensor',)
    date_hierarchy = 'fecha_hora'

    def valor_display(self, obj):
        color = '#dc3545' if obj.es_alerta else '#28a745'
        return format_html(
            '<span style="color:{};font-weight:700;">{} {}</span>',
            color, obj.valor, obj.sensor.unidad_medida
        )
    valor_display.short_description = 'Valor'

    def alerta_badge(self, obj):
        if obj.es_alerta:
            return format_html('<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:8px;font-size:11px;">ALERTA</span>')
        return format_html('<span style="background:#28a745;color:white;padding:2px 8px;border-radius:8px;font-size:11px;">OK</span>')
    alerta_badge.short_description = 'Estado'


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'tipo_alerta', 'severidad_badge', 'valor_detectado', 'resuelta', 'fecha_creacion')
    list_filter = ('severidad', 'resuelta', 'tipo_alerta', 'fecha_creacion')
    search_fields = ('sensor__nombre', 'mensaje', 'sensor__edificio__nombre')
    readonly_fields = ('id', 'fecha_creacion', 'fecha_resolucion', 'resuelta_por')
    raw_id_fields = ('sensor', 'lectura', 'resuelta_por')
    list_editable = ('resuelta',)
    actions = ['marcar_como_resueltas']

    def severidad_badge(self, obj):
        colors = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'critical': '#dc3545',
        }
        color = colors.get(obj.severidad, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_severidad_display()
        )
    severidad_badge.short_description = 'Severidad'

    @admin.action(description='Marcar seleccionadas como resueltas')
    def marcar_como_resueltas(self, request, queryset):
        count = queryset.update(resuelta=True, fecha_resolucion=timezone.now(), resuelta_por=request.user)
        self.message_user(request, f'{count} alertas marcadas como resueltas.')


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'autor', 'periodo_desde', 'periodo_hasta', 'fecha_generacion')
    list_filter = ('edificio', 'autor', 'fecha_generacion')
    search_fields = ('titulo', 'contenido', 'edificio__nombre')
    readonly_fields = ('id', 'fecha_generacion')
    raw_id_fields = ('edificio', 'autor')


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'rol_badge', 'telefono', 'organizacion', 'notificaciones_email')
    list_filter = ('rol', 'notificaciones_email')
    search_fields = ('user__username', 'user__email', 'organizacion')
    raw_id_fields = ('user',)
    filter_horizontal = ('edificios_asignados',)

    def rol_badge(self, obj):
        colors = {
            'admin': '#dc3545',
            'conservador': '#28a745',
            'tecnico': '#ffc107',
            'visualizador': '#6c757d',
        }
        color = colors.get(obj.rol, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_rol_display()
        )
    rol_badge.short_description = 'Rol'


@admin.register(SensorFoto)
class SensorFotoAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'descripcion', 'fecha_subida', 'imagen_preview')
    search_fields = ('sensor__nombre', 'descripcion')
    readonly_fields = ('fecha_subida',)

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-height:80px;border-radius:8px;" />', obj.imagen.url)
        return '-'
    imagen_preview.short_description = 'Vista Previa'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'accion_badge', 'modelo', 'objeto_id', 'descripcion_corta', 'ip_address', 'fecha')
    list_filter = ('accion', 'modelo', 'fecha')
    search_fields = ('usuario__username', 'descripcion', 'modelo')
    readonly_fields = ('id', 'usuario', 'accion', 'modelo', 'objeto_id', 'descripcion', 'ip_address', 'fecha', 'datos_previos', 'datos_nuevos')
    date_hierarchy = 'fecha'

    def accion_badge(self, obj):
        colors = {
            'crear': '#28a745', 'editar': '#ffc107', 'eliminar': '#dc3545',
            'login': '#17a2b8', 'logout': '#6c757d', 'resolver_alerta': '#28a745',
            'exportar': '#0f3460', 'importar': '#e94560', 'generar_informe': '#d4a853',
            'asignar_usuario': '#9b59b6',
        }
        color = colors.get(obj.accion, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_accion_display()
        )
    accion_badge.short_description = 'Acción'

    def descripcion_corta(self, obj):
        return obj.descripcion[:80] + '...' if len(obj.descripcion) > 80 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'num_miembros', 'num_edificios', 'activo', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
    filter_horizontal = ('miembros', 'edificios')


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'estado_badge', 'prioridad_badge', 'asignado_a', 'fecha_limite', 'dias_restantes_display')
    list_filter = ('estado', 'prioridad', 'fecha_creacion')
    search_fields = ('titulo', 'descripcion', 'edificio__nombre')
    readonly_fields = ('id', 'fecha_creacion', 'fecha_completado')
    raw_id_fields = ('edificio', 'sensor', 'asignado_a')

    def estado_badge(self, obj):
        colors = {'pendiente': '#ffc107', 'en_progreso': '#17a2b8', 'completado': '#28a745', 'cancelado': '#6c757d'}
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def prioridad_badge(self, obj):
        colors = {'baja': '#28a745', 'media': '#ffc107', 'alta': '#fd7e14', 'urgente': '#dc3545'}
        color = colors.get(obj.prioridad, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_prioridad_display()
        )
    prioridad_badge.short_description = 'Prioridad'

    def dias_restantes_display(self, obj):
        dias = obj.dias_restantes
        if dias is None:
            return '-'
        if dias < 0:
            return format_html('<span style="color:#dc3545;font-weight:700;">Vencido ({}d)</span>', abs(dias))
        if dias <= 3:
            return format_html('<span style="color:#fd7e14;font-weight:700;">{}d</span>', dias)
        return f'{dias}d'
    dias_restantes_display.short_description = 'Días Restantes'


admin.site.site_header = 'SmartHeritage - Panel de Administración'
admin.site.site_title = 'SmartHeritage Admin'
admin.site.index_title = 'Gestión del Patrimonio Histórico'


@admin.register(AnalisisIA)
class AnalisisIAAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'estado', 'severidad_badge', 'confianza', 'grietas_detectadas', 'fecha_analisis')
    list_filter = ('estado', 'severidad_detectada', 'prioridad_ia')
    search_fields = ('titulo', 'edificio__nombre')
    readonly_fields = ('id', 'fecha_analisis', 'fecha_completado')

    def severidad_badge(self, obj):
        colors = {'sin_dano': '#28a745', 'leve': '#17a2b8', 'moderado': '#ffc107', 'severo': '#fd7e14', 'critico': '#dc3545'}
        color = colors.get(obj.severidad_detectada, '#6c757d')
        return format_html('<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>', color, obj.get_severidad_detectada_display())
    severidad_badge.short_description = 'Severidad'


@admin.register(PrediccionML)
class PrediccionMLAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'tipo', 'probabilidad', 'fecha_predicha', 'impacto_financiero', 'activa')
    list_filter = ('tipo', 'activa')
    search_fields = ('titulo', 'edificio__nombre')


@admin.register(Donacion)
class DonacionAdmin(admin.ModelAdmin):
    list_display = ('donador_nombre', 'edificio', 'monto', 'moneda', 'estado', 'es_anonima', 'fecha_creacion')
    list_filter = ('estado', 'moneda', 'es_anonima')
    search_fields = ('donador_nombre', 'donador_email', 'edificio__nombre')


@admin.register(ReporteCiudadano)
class ReporteCiudadanoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'tipo', 'estado_badge', 'votos', 'fecha_creacion')
    list_filter = ('estado', 'tipo')
    search_fields = ('titulo', 'ciudadano_nombre', 'edificio__nombre')

    def estado_badge(self, obj):
        colors = {'nuevo': '#17a2b8', 'revisado': '#ffc107', 'en_progreso': '#fd7e14', 'resuelto': '#28a745', 'rechazado': '#dc3545'}
        color = colors.get(obj.estado, '#6c757d')
        return format_html('<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>', color, obj.get_estado_display())
    estado_badge.short_description = 'Estado'


@admin.register(Seguro)
class SeguroAdmin(admin.ModelAdmin):
    list_display = ('compania', 'poliza_numero', 'edificio', 'tipo', 'cobertura_monto', 'prima_anual', 'fecha_fin', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('compania', 'poliza_numero', 'edificio__nombre')


@admin.register(EficienciaEnergetica)
class EficienciaEnergeticaAdmin(admin.ModelAdmin):
    list_display = ('edificio', 'fecha', 'consumo_electricidad', 'produccion_solar', 'certificado_energetico', 'coste_total')
    list_filter = ('certificado_energetico', 'fecha')
    search_fields = ('edificio__nombre',)


@admin.register(CumplimientoLegal)
class CumplimientoLegalAdmin(admin.ModelAdmin):
    list_display = ('normativa', 'edificio', 'referencia', 'estado', 'fecha_inspeccion', 'proxima_inspeccion')
    list_filter = ('estado',)
    search_fields = ('normativa', 'referencia', 'edificio__nombre')


@admin.register(CertificadoBlockchain)
class CertificadoBlockchainAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'tipo', 'hash_transaccion_corto', 'validado', 'fecha_emision')
    list_filter = ('tipo', 'validado')
    search_fields = ('titulo', 'hash_transaccion', 'edificio__nombre')

    def hash_transaccion_corto(self, obj):
        return obj.hash_transaccion[:16] + '...'
    hash_transaccion_corto.short_description = 'Hash'


@admin.register(TourVirtual)
class TourVirtualAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'activo', 'vistas', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('titulo', 'edificio__nombre')


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'tipo', 'fecha_inicio', 'capacidad_maxima', 'plazas_display', 'publicado')
    list_filter = ('tipo', 'publicado', 'activo')
    search_fields = ('titulo', 'edificio__nombre')

    def plazas_display(self, obj):
        count = obj.participantes.count()
        return f'{count}/{obj.capacidad_maxima}'
    plazas_display.short_description = 'Plazas'


@admin.register(TiendaPatrimonio)
class TiendaPatrimonioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edificio', 'categoria', 'precio', 'stock', 'vendidos', 'destacado')
    list_filter = ('categoria', 'destacado', 'activo')
    search_fields = ('nombre', 'edificio__nombre')


@admin.register(VisitaQR)
class VisitaQREAdmin(admin.ModelAdmin):
    list_display = ('edificio', 'visitante_nombre', 'dispositivo', 'idioma', 'fecha_visita')
    list_filter = ('idioma', 'accion')
    search_fields = ('edificio__nombre', 'visitante_nombre')


@admin.register(DocumentoEdificio)
class DocumentoEdificioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'categoria', 'subido_por', 'fecha_subida', 'tamaño_kb')
    list_filter = ('categoria',)


@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'estado', 'edificio_asignado', 'ubicacion', 'costo')
    list_filter = ('estado', 'categoria')


@admin.register(FormularioInspeccion)
class FormularioInspeccionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'inspector', 'fecha_inspeccion', 'resultado')
    list_filter = ('resultado',)


@admin.register(TimelineHistorico)
class TimelineHistoricoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'fecha_evento', 'categoria')
    list_filter = ('categoria',)


@admin.register(RecomendacionIA)
class RecomendacionIAAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'prioridad', 'confianza', 'implementada')
    list_filter = ('prioridad', 'implementada')


@admin.register(AnomaliaDetectada)
class AnomaliaDetectadaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'tipo', 'gravedad', 'revisada', 'fecha_deteccion')
    list_filter = ('tipo', 'gravedad', 'revisada')


@admin.register(Voluntario)
class VoluntarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'estado', 'horas_voluntariado', 'fecha_registro')
    list_filter = ('estado',)


@admin.register(ReporteAutomatico)
class ReporteAutomaticoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'enviado', 'fecha_generacion')
    list_filter = ('tipo', 'enviado')


@admin.register(MantenimientoPredictivo)
class MantenimientoPredictivoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'prioridad', 'probabilidad_fallo', 'dias_estimados', 'implementada')
    list_filter = ('prioridad', 'implementada')
    search_fields = ('titulo', 'edificio__nombre')


@admin.register(RegistroROI)
class RegistroROIAdmin(admin.ModelAdmin):
    list_display = ('edificio', 'ahorro_energetico', 'ahorro_multas', 'total_ahorro', 'roi_porcentaje', 'fecha')
    list_filter = ('edificio',)


@admin.register(ConfiguracionIdioma)
class ConfiguracionIdiomaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'idioma')
    list_filter = ('idioma',)


@admin.register(ModoEmergencia)
class ModoEmergenciaAdmin(admin.ModelAdmin):
    list_display = ('edificio', 'activado_por', 'motivo', 'email_enviado', 'pdf_generado', 'fecha_activacion')
    list_filter = ('email_enviado', 'pdf_generado')


@admin.register(ComparativaCiudad)
class ComparativaCiudadAdmin(admin.ModelAdmin):
    list_display = ('ciudad', 'edificio_tipo', 'media_salud', 'media_sensores', 'total_edificios')


@admin.register(CategoriaIngreso)
class CategoriaIngresoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'color')


@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'color')


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'edificio', 'monto', 'estado', 'fecha', 'cliente_nombre')
    list_filter = ('estado', 'recurrente')
    search_fields = ('concepto', 'cliente_nombre')


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'edificio', 'monto', 'pagado', 'fecha', 'proveedor', 'forma_pago')
    list_filter = ('pagado', 'forma_pago', 'deducible')
    search_fields = ('concepto', 'proveedor')


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'edificio', 'cliente_proveedor', 'total', 'estado', 'fecha_emision')
    list_filter = ('tipo', 'estado')
    search_fields = ('numero', 'cliente_proveedor')


@admin.register(Nomina)
class NominaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'periodo', 'salario_base', 'neto', 'estado', 'fecha_pago')
    list_filter = ('estado',)
    search_fields = ('empleado__username', 'periodo')


@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edificio', 'monto_asignado', 'monto_gastado', 'porcentaje_gastado', 'periodo')
    list_filter = ('periodo', 'activo')


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'saldo')
    list_filter = ('tipo',)


@admin.register(ChatAsistenteIA)
class ChatAsistenteIAAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje_usuario', 'fecha')
    search_fields = ('mensaje_usuario',)


@admin.register(DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = ('edificio', 'estado_color', 'ultima_actualizacion')


@admin.register(FotoInspeccion)
class FotoInspeccionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'resultado_ia', 'confianza_ia', 'fecha')
    list_filter = ('resultado_ia',)


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'fecha_inicio', 'estado')
    list_filter = ('estado',)


@admin.register(TareaKanban)
class TareaKanbanAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'estado', 'prioridad', 'asignado_a', 'fecha_limite')
    list_filter = ('estado', 'prioridad')


@admin.register(NotificacionWhatsApp)
class NotificacionWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('telefono', 'mensaje', 'enviado', 'fecha')


@admin.register(ContratoDigital)
class ContratoDigitalAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'estado', 'monto_total', 'fecha_inicio')
    list_filter = ('estado',)


@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edificio', 'categoria', 'cantidad', 'estado', 'valor_estimado')
    list_filter = ('categoria', 'estado')


@admin.register(BitacoraObra)
class BitacoraObraAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'tipo', 'autor', 'coste', 'fecha')
    list_filter = ('tipo',)


@admin.register(RolSistema)
class RolSistemaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'es_admin', 'puede_ver_edificios', 'puede_editar_edificios', 'puede_aprobar')


@admin.register(PermisosUsuario)
class PermisosUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'notificaciones_email', 'notificaciones_push')
    list_filter = ('notificaciones_email', 'notificaciones_push')


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'edificio', 'texto', 'fecha', 'editado')
    search_fields = ('texto',)


@admin.register(Recordatorio)
class RecordatorioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'tipo', 'fecha_recordatorio', 'leido')
    list_filter = ('tipo', 'leido')


@admin.register(CalculadoraRestauracion)
class CalculadoraRestauracionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'edificio', 'area_m2', 'total_estimado', 'fecha_calculo')


@admin.register(ExportacionLog)
class ExportacionLogAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'formato', 'modelo_tipo', 'registros', 'fecha')


@admin.register(WebhookConfig)
class WebhookConfigAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'evento', 'activo', 'ultimo_envio', 'exitoso')
    list_filter = ('evento', 'activo')


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'widget_tipo', 'titulo', 'posicion', 'activo')


@admin.register(TextoMultiidioma)
class TextoMultiidiomaAdmin(admin.ModelAdmin):
    list_display = ('clave', 'es', 'en', 'ar')
    search_fields = ('clave',)


@admin.register(NotificacionPush)
class NotificacionPushAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'leida', 'fecha')
    list_filter = ('leida',)
