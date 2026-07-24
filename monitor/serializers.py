from rest_framework import serializers
from .models import (
    Edificio, Sensor, Lectura, Alerta, Mantenimiento, Equipo,
    Ingreso, Gasto, Factura, Nomina, Presupuesto,
    TareaKanban, Cita, ItemInventario, BitacoraObra,
    ContratoDigital, FotoInspeccion, ChatAsistenteIA,
    CategoriaIngreso, CategoriaGasto, ComparativaCiudad,
)


class EdificioSerializer(serializers.ModelSerializer):
    num_sensores = serializers.IntegerField(read_only=True)
    alertas_activas = serializers.IntegerField(read_only=True)
    salud_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Edificio
        fields = '__all__'


class SensorSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Sensor
        fields = '__all__'


class LecturaSerializer(serializers.ModelSerializer):
    sensor_tipo = serializers.CharField(source='sensor.tipo', read_only=True)
    edificio_nombre = serializers.CharField(source='sensor.edificio.nombre', read_only=True)

    class Meta:
        model = Lectura
        fields = '__all__'


class AlertaSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='sensor.edificio.nombre', read_only=True)

    class Meta:
        model = Alerta
        fields = '__all__'


class MantenimientoSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Mantenimiento
        fields = '__all__'


class EquipoSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Equipo
        fields = '__all__'


class CategoriaIngresoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaIngreso
        fields = '__all__'


class CategoriaGastoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaGasto
        fields = '__all__'


class IngresoSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Ingreso
        fields = '__all__'


class GastoSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Gasto
        fields = '__all__'


class FacturaSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Factura
        fields = '__all__'


class NominaSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.username', read_only=True)

    class Meta:
        model = Nomina
        fields = '__all__'


class PresupuestoSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)
    porcentaje_gastado = serializers.FloatField(read_only=True)
    disponible = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Presupuesto
        fields = '__all__'


class TareaKanbanSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)
    asignado_nombre = serializers.CharField(source='asignado_a.username', read_only=True)

    class Meta:
        model = TareaKanban
        fields = '__all__'


class CitaSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = Cita
        fields = '__all__'


class ItemInventarioSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = ItemInventario
        fields = '__all__'


class BitacoraObraSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)
    autor_nombre = serializers.CharField(source='autor.username', read_only=True)

    class Meta:
        model = BitacoraObra
        fields = '__all__'


class ContratoDigitalSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = ContratoDigital
        fields = '__all__'


class FotoInspeccionSerializer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True)

    class Meta:
        model = FotoInspeccion
        fields = '__all__'


class ChatAsistenteIASerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatAsistenteIA
        fields = '__all__'


class ComparativaCiudadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComparativaCiudad
        fields = '__all__'
