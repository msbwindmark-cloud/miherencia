from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="SmartHeritage API",
        default_version='v1',
        description="""
## SmartHeritage - API REST para Gestion de Patrimonio Historico

### Autenticacion
Para usar la API, necesitas estar autenticado. Usa el boton **"Authorize"** en la parte superior del Swagger.

Credenciales de prueba:
- **Usuario:** admin
- **Password:** admin123

### Endpoints principales
- **Edificios:** CRUD completo de edificios historicos
- **Sensores:** Gestion de sensores IoT
- **Lecturas:** Datos de sensores en tiempo real
- **Alertas:** Sistema de alertas y notificaciones
- **Financiero:** Ingresos, gastos, facturas, nominas
- **Kanban:** Sistema de tareas
- **Inventario:** Control de inventario
- **Dashboard:** KPIs y estadisticas

### Formato
Todos los endpoints aceptan y devuelven JSON.
""",
        terms_of_service="https://www.smartheritage.com/terms/",
        contact=openapi.Contact(email="api@smartheritage.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('monitor.urls')),
    path('api/v1/', include('monitor.api_urls')),

    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
