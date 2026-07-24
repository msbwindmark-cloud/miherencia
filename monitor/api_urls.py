from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'edificios', api_views.EdificioViewSet, basename='edificio')
router.register(r'sensores', api_views.SensorViewSet, basename='sensor')
router.register(r'lecturas', api_views.LecturaViewSet, basename='lectura')
router.register(r'alertas', api_views.AlertaViewSet, basename='alerta')
router.register(r'mantenimientos', api_views.MantenimientoViewSet, basename='mantenimiento')
router.register(r'equipos', api_views.EquipoViewSet, basename='equipo')
router.register(r'ingresos', api_views.IngresoViewSet, basename='ingreso')
router.register(r'gastos', api_views.GastoViewSet, basename='gasto')
router.register(r'facturas', api_views.FacturaViewSet, basename='factura')
router.register(r'nominas', api_views.NominaViewSet, basename='nomina')
router.register(r'presupuestos', api_views.PresupuestoViewSet, basename='presupuesto')
router.register(r'tareas', api_views.TareaKanbanViewSet, basename='tareakanban')
router.register(r'citas', api_views.CitaViewSet, basename='cita')
router.register(r'inventario', api_views.ItemInventarioViewSet, basename='inventario')
router.register(r'bitacora', api_views.BitacoraObraViewSet, basename='bitacora')
router.register(r'contratos', api_views.ContratoDigitalViewSet, basename='contrato')
router.register(r'fotos-inspeccion', api_views.FotoInspeccionViewSet, basename='fotainspeccion')
router.register(r'chat-ia', api_views.ChatAsistenteIAViewSet, basename='chatai')
router.register(r'comparativa-ciudades', api_views.ComparativaCiudadViewSet, basename='comparativaciudad')
router.register(r'categorias-ingreso', api_views.CategoriaIngresoViewSet, basename='categorainingreso')
router.register(r'categorias-gasto', api_views.CategoriaGastoViewSet, basename='categoriagasto')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', api_views.dashboard_api, name='api_dashboard'),
    path('estadisticas/', api_views.estadisticas_api, name='api_estadisticas'),
]
