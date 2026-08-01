from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import (Edificio, Sensor, Lectura, Informe, SensorFoto, Equipo, Mantenimiento, TimelineFoto,
    AnalisisIA, PrediccionML, Donacion, ReporteCiudadano, Seguro, EficienciaEnergetica,
    CumplimientoLegal, CertificadoBlockchain, TourVirtual, Evento, TiendaPatrimonio,
    CamaraVigilancia, HeritageNFT, SmartContract, CarbonCredit, DNAEdificio,
    GuardianRule, TourVR, Desafio, TimeMachineRequest, SimulacionDesastre)


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'tu@email.com'
    }))
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Nombre'
    }))
    last_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Apellidos'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['username', 'password1', 'password2']:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})
            if field_name == 'username':
                self.fields[field_name].widget.attrs['placeholder'] = 'Nombre de usuario'


class UserLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Usuario', 'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Contraseña'
    }))


class EdificioForm(forms.ModelForm):
    class Meta:
        model = Edificio
        fields = [
            'nombre', 'direccion', 'ciudad', 'provincia', 'codigo_postal',
            'latitud', 'longitud', 'categoria', 'descripcion', 'anno_construccion',
            'proteccion_oficial', 'imagen_principal', 'estado_general'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del edificio'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'provincia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Provincia'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '28001'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '40.4168'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '-3.7038'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción histórica del edificio...'}),
            'anno_construccion': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1500'}),
            'proteccion_oficial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'imagen_principal': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'estado_general': forms.Select(attrs={'class': 'form-select'}),
        }


class SensorForm(forms.ModelForm):
    class Meta:
        model = Sensor
        fields = [
            'nombre', 'tipo', 'ubicacionDescripcion', 'latitud', 'longitud',
            'umbral_min', 'umbral_max', 'unidad_medida', 'activo', 'fecha_instalacion'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del sensor'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'ubicacionDescripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Nave lateral derecha, techos a 3m'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '40.4168'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '-3.7038'}),
            'umbral_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo aceptable'}),
            'umbral_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Máximo aceptable'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '°C, %, g, lux, ppm...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fecha_instalacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class LecturaForm(forms.ModelForm):
    class Meta:
        model = Lectura
        fields = ['valor', 'fecha_hora']
        widgets = {
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Valor medido', 'step': '0.01'}),
            'fecha_hora': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_hora'].initial = None


class AlertaResolucionForm(forms.Form):
    notas_resolucion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Describe cómo se resolvió la alerta...'
        }),
        label='Notas de resolución'
    )


class InformeForm(forms.ModelForm):
    class Meta:
        model = Informe
        fields = ['titulo', 'contenido', 'periodo_desde', 'periodo_hasta']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del informe'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Contenido del informe...'}),
            'periodo_desde': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periodo_hasta': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class SensorFotoForm(forms.ModelForm):
    class Meta:
        model = SensorFoto
        fields = ['imagen', 'descripcion']
        widgets = {
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción de la foto'}),
        }


class BusquedaForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Buscar edificios...'
        })
    )


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre', 'descripcion', 'edificios', 'miembros']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del equipo'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del equipo...'}),
            'edificios': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'miembros': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }


class MantenimientoForm(forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = ['titulo', 'descripcion', 'sensor', 'estado', 'prioridad', 'asignado_a', 'fecha_limite']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del mantenimiento'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción...'}),
            'sensor': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'asignado_a': forms.Select(attrs={'class': 'form-select'}),
            'fecha_limite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class ImportarCSVForm(forms.Form):
    sensor = forms.ModelChoiceField(
        queryset=Sensor.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Sensor destino'
    )
    archivo = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx'}),
        label='Archivo CSV/Excel'
    )

    def __init__(self, *args, edificio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if edificio:
            self.fields['sensor'].queryset = edificio.sensores.all()


class TimelineFotoForm(forms.ModelForm):
    class Meta:
        model = TimelineFoto
        fields = ['imagen', 'titulo', 'descripcion', 'fecha_toma', 'latitud', 'longitud']
        widgets = {
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la foto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción...'}),
            'fecha_toma': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '40.4168'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '-3.7038'}),
        }


class AnalisisIAForm(forms.ModelForm):
    class Meta:
        model = AnalisisIA
        fields = ['imagen', 'titulo']
        widgets = {
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripcion del analisis'}),
        }


class DonacionForm(forms.ModelForm):
    class Meta:
        model = Donacion
        fields = ['donador_nombre', 'donador_email', 'donador_telefono', 'monto', 'donador_mensaje', 'es_anonima']
        widgets = {
            'donador_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
            'donador_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
            'donador_telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+34 600 000 000'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '25.00', 'step': '0.01'}),
            'donador_mensaje': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mensaje opcional...'}),
            'es_anonima': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ReporteCiudadanoForm(forms.ModelForm):
    class Meta:
        model = ReporteCiudadano
        fields = ['ciudadano_nombre', 'ciudadano_email', 'ciudadano_telefono', 'tipo', 'titulo', 'descripcion', 'imagen', 'latitud', 'longitud']
        widgets = {
            'ciudadano_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
            'ciudadano_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
            'ciudadano_telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefono (opcional)'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titulo del reporte'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe el problema...'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitud'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitud'}),
        }


class SeguroForm(forms.ModelForm):
    class Meta:
        model = Seguro
        fields = ['compania', 'poliza_numero', 'tipo', 'cobertura_monto', 'prima_anual', 'fecha_inicio', 'fecha_fin',
                  'contacto_nombre', 'contacto_telefono', 'contacto_email', 'documento', 'renovacion_automatica']
        widgets = {
            'compania': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la compania'}),
            'poliza_numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numero de poliza'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cobertura_monto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '500000.00'}),
            'prima_anual': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1200.00'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contacto_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contacto'}),
            'contacto_telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefono'}),
            'contacto_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@seguros.com'}),
            'documento': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'renovacion_automatica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EficienciaEnergeticaForm(forms.ModelForm):
    class Meta:
        model = EficienciaEnergetica
        fields = ['fecha', 'consumo_electricidad', 'consumo_gas', 'consumo_agua', 'produccion_solar',
                  'emisiones_co2', 'temp_exterior', 'temp_interior', 'certificado_energetico', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'consumo_electricidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'kWh'}),
            'consumo_gas': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'm3'}),
            'consumo_agua': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'litros'}),
            'produccion_solar': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'kWh'}),
            'emisiones_co2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'kg CO2'}),
            'temp_exterior': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '°C'}),
            'temp_interior': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '°C'}),
            'certificado_energetico': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CumplimientoLegalForm(forms.ModelForm):
    class Meta:
        model = CumplimientoLegal
        fields = ['normativa', 'referencia', 'descripcion', 'estado', 'fecha_inspeccion', 'proxima_inspeccion',
                  'documento_certificado', 'responsable', 'observaciones']
        widgets = {
            'normativa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la normativa'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'REF-2024-001'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inspeccion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proxima_inspeccion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'documento_certificado': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['titulo', 'descripcion', 'tipo', 'fecha_inicio', 'fecha_fin', 'capacidad_maxima', 'precio', 'imagen', 'ubicacion_detalle', 'publicado']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titulo del evento'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '50'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ubicacion_detalle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicacion dentro del edificio'}),
            'publicado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TiendaPatrimonioForm(forms.ModelForm):
    class Meta:
        model = TiendaPatrimonio
        fields = ['nombre', 'descripcion', 'categoria', 'precio', 'imagen', 'stock', 'destacado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '19.99'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
            'destacado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# --- FORMULARIOS FUNCIONALIDADES INNOVADORAS ---

class TimeMachineForm(forms.Form):
    imagen = forms.ImageField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    epoca_destino = forms.IntegerField(min_value=500, max_value=2025, initial=1800,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'epoca-slider'}))
    estilo_reconstruccion = forms.ChoiceField(choices=[
        ('romano', 'Epoca Romana'), ('medieval', 'Medieval'),
        ('renacimiento', 'Renacimiento'), ('barroco', 'Barroco'),
        ('neoclasico', 'Neoclasico'), ('modernista', 'Modernista'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))


class SimuladorDesastreForm(forms.Form):
    TIPO_CHOICES = [('terremoto', 'Terremoto'), ('incendio', 'Incendio'),
                    ('inundacion', 'Inundacion'), ('viento', 'Viento Fuerte')]
    tipo = forms.ChoiceField(choices=TIPO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    intensidad = forms.FloatField(min_value=0, max_value=100, initial=5.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'intensidad-slider'}))


class CamaraVigilanciaForm(forms.ModelForm):
    class Meta:
        model = CamaraVigilancia
        fields = ['nombre', 'ubicacion', 'detectar_vandalismo', 'contar_visitantes']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
        }


class HeritageNFTForm(forms.ModelForm):
    class Meta:
        model = HeritageNFT
        fields = ['titulo', 'descripcion', 'imagen', 'precio_inicial', 'es_subasta']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_inicial': forms.NumberInput(attrs={'class': 'form-control'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class SmartContractForm(forms.ModelForm):
    class Meta:
        model = SmartContract
        fields = ['titulo', 'descripcion', 'monto_total', 'contratista']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CarbonCreditForm(forms.ModelForm):
    class Meta:
        model = CarbonCredit
        fields = ['edificio', 'creditos_generados', 'metodo_calculo', 'descripcion']
        widgets = {
            'creditos_generados': forms.NumberInput(attrs={'class': 'form-control'}),
            'metodo_calculo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DNAEdificioForm(forms.ModelForm):
    class Meta:
        model = DNAEdificio
        fields = ['score_estructural', 'score_ambiental', 'score_historico',
                  'score_accesibilidad', 'score_tecnologico', 'score_energetico']
        widgets = {
            'score_estructural': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 100}),
            'score_ambiental': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 100}),
            'score_historico': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 100}),
            'score_accesibilidad': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 100}),
            'score_tecnologico': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 100}),
            'score_energetico': forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 100}),
        }


class GuardianRuleForm(forms.ModelForm):
    class Meta:
        model = GuardianRule
        fields = ['nombre', 'descripcion', 'tipo_sensor', 'condicion', 'severidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo_sensor': forms.Select(attrs={'class': 'form-select'}),
            'severidad': forms.Select(attrs={'class': 'form-select'}),
        }


class TourVRForm(forms.ModelForm):
    class Meta:
        model = TourVR
        fields = ['titulo', 'descripcion', 'video_360_url', 'modelo_glb_url', 'es_vr', 'es_ar']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'video_360_url': forms.URLInput(attrs={'class': 'form-control'}),
            'modelo_glb_url': forms.URLInput(attrs={'class': 'form-control'}),
        }


class DesafioForm(forms.ModelForm):
    class Meta:
        model = Desafio
        fields = ['titulo', 'descripcion', 'tipo', 'accion_requerida', 'objetivo', 'puntos_recompensa']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'accion_requerida': forms.Select(attrs={'class': 'form-select'}),
            'objetivo': forms.NumberInput(attrs={'class': 'form-control'}),
            'puntos_recompensa': forms.NumberInput(attrs={'class': 'form-control'}),
        }
