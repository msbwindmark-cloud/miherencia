from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from .models import (
    Edificio, Sensor, Lectura, Alerta, Mantenimiento, Equipo,
    Ingreso, Gasto, Factura, Nomina, Presupuesto,
    TareaKanban, Cita, ItemInventario, BitacoraObra,
    ContratoDigital, FotoInspeccion, ChatAsistenteIA,
    CategoriaIngreso, CategoriaGasto, ComparativaCiudad,
)
from .serializers import (
    EdificioSerializer, SensorSerializer, LecturaSerializer,
    AlertaSerializer, MantenimientoSerializer, EquipoSerializer,
    IngresoSerializer, GastoSerializer, FacturaSerializer,
    NominaSerializer, PresupuestoSerializer, TareaKanbanSerializer,
    CitaSerializer, ItemInventarioSerializer, BitacoraObraSerializer,
    ContratoDigitalSerializer, FotoInspeccionSerializer,
    ChatAsistenteIASerializer, CategoriaIngresoSerializer,
    CategoriaGastoSerializer, ComparativaCiudadSerializer,
)


class EdificioViewSet(viewsets.ModelViewSet):
    queryset = Edificio.objects.filter(activo=True)
    serializer_class = EdificioSerializer
    permission_classes = [permissions.IsAuthenticated]


class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    permission_classes = [permissions.IsAuthenticated]


class LecturaViewSet(viewsets.ModelViewSet):
    queryset = Lectura.objects.all()
    serializer_class = LecturaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def recientes(self, request):
        lecturas = Lectura.objects.order_by('-fecha_hora')[:20]
        serializer = self.get_serializer(lecturas, many=True)
        return Response(serializer.data)


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def activas(self, request):
        alertas = Alerta.objects.filter(resuelta=False).order_by('-fecha_creacion')
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)


class MantenimientoViewSet(viewsets.ModelViewSet):
    queryset = Mantenimiento.objects.all()
    serializer_class = MantenimientoSerializer
    permission_classes = [permissions.IsAuthenticated]


class EquipoViewSet(viewsets.ModelViewSet):
    queryset = Equipo.objects.all()
    serializer_class = EquipoSerializer
    permission_classes = [permissions.IsAuthenticated]


class IngresoViewSet(viewsets.ModelViewSet):
    queryset = Ingreso.objects.all()
    serializer_class = IngresoSerializer
    permission_classes = [permissions.IsAuthenticated]


class GastoViewSet(viewsets.ModelViewSet):
    queryset = Gasto.objects.all()
    serializer_class = GastoSerializer
    permission_classes = [permissions.IsAuthenticated]


class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
    permission_classes = [permissions.IsAuthenticated]


class NominaViewSet(viewsets.ModelViewSet):
    queryset = Nomina.objects.all()
    serializer_class = NominaSerializer
    permission_classes = [permissions.IsAuthenticated]


class PresupuestoViewSet(viewsets.ModelViewSet):
    queryset = Presupuesto.objects.all()
    serializer_class = PresupuestoSerializer
    permission_classes = [permissions.IsAuthenticated]


class TareaKanbanViewSet(viewsets.ModelViewSet):
    queryset = TareaKanban.objects.all()
    serializer_class = TareaKanbanSerializer
    permission_classes = [permissions.IsAuthenticated]


class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer
    permission_classes = [permissions.IsAuthenticated]


class ItemInventarioViewSet(viewsets.ModelViewSet):
    queryset = ItemInventario.objects.all()
    serializer_class = ItemInventarioSerializer
    permission_classes = [permissions.IsAuthenticated]


class BitacoraObraViewSet(viewsets.ModelViewSet):
    queryset = BitacoraObra.objects.all()
    serializer_class = BitacoraObraSerializer
    permission_classes = [permissions.IsAuthenticated]


class ContratoDigitalViewSet(viewsets.ModelViewSet):
    queryset = ContratoDigital.objects.all()
    serializer_class = ContratoDigitalSerializer
    permission_classes = [permissions.IsAuthenticated]


class FotoInspeccionViewSet(viewsets.ModelViewSet):
    queryset = FotoInspeccion.objects.all()
    serializer_class = FotoInspeccionSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChatAsistenteIAViewSet(viewsets.ModelViewSet):
    queryset = ChatAsistenteIA.objects.all()
    serializer_class = ChatAsistenteIASerializer
    permission_classes = [permissions.IsAuthenticated]


class ComparativaCiudadViewSet(viewsets.ModelViewSet):
    queryset = ComparativaCiudad.objects.all()
    serializer_class = ComparativaCiudadSerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoriaIngresoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaIngreso.objects.all()
    serializer_class = CategoriaIngresoSerializer
    permission_classes = [permissions.IsAuthenticated]


class CategoriaGastoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaGasto.objects.all()
    serializer_class = CategoriaGastoSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_api(request):
    hoy = timezone.now().date()
    mes_inicio = hoy.replace(day=1)
    edificios = Edificio.objects.filter(activo=True)
    total_ingresos = Ingreso.objects.filter(fecha__gte=mes_inicio, estado='cobrado').aggregate(total=Sum('monto'))['total'] or 0
    total_gastos = Gasto.objects.filter(fecha__gte=mes_inicio, pagado=True).aggregate(total=Sum('monto'))['total'] or 0
    alertas_activas = Alerta.objects.filter(resuelta=False).count()
    return Response({
        'edificios_activos': edificios.count(),
        'salud_promedio': round(edificios.aggregate(avg=Avg('salud_score'))['avg'] or 0, 1),
        'ingresos_mes': float(total_ingresos),
        'gastos_mes': float(total_gastos),
        'balance': float(total_ingresos - total_gastos),
        'alertas_activas': alertas_activas,
        'sensores_totales': Sensor.objects.count(),
        'mantenimientos_pendientes': Mantenimiento.objects.filter(estado__in=['pendiente', 'en_progreso']).count(),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def estadisticas_api(request):
    hoy = timezone.now().date()
    desde = hoy - timedelta(days=30)
    return Response({
        'lecturas_30d': Lectura.objects.filter(fecha_hora__gte=desde).count(),
        'alertas_30d': Alerta.objects.filter(fecha_creacion__gte=desde).count(),
        'alertas_resueltas_30d': Alerta.objects.filter(fecha_creacion__gte=desde, resuelta=True).count(),
        'mantenimientos_30d': Mantenimiento.objects.filter(fecha_creacion__gte=desde).count(),
        'ingresos_30d': float(Ingreso.objects.filter(fecha__gte=desde, estado='cobrado').aggregate(total=Sum('monto'))['total'] or 0),
        'gastos_30d': float(Gasto.objects.filter(fecha__gte=desde, pagado=True).aggregate(total=Sum('monto'))['total'] or 0),
    })
