import json
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import AuditLog


class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._audit_start_time = timezone.now()
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        request._view_kwargs = view_kwargs
        return None

    def process_response(self, request, response):
        if not hasattr(request, 'user') or not hasattr(request.user, 'is_authenticated'):
            return response
        if not request.user.is_authenticated:
            return response

        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response
        if request.path.startswith('/api/') and request.method == 'GET':
            return response
        if request.method == 'GET':
            return response

        user = request.user
        method = request.method
        path = request.path

        accion_map = {
            'POST': 'crear',
            'PUT': 'editar',
            'PATCH': 'editar',
            'DELETE': 'eliminar',
        }
        accion = accion_map.get(method, method.lower())

        modelo = self._detect_model(path)
        if not modelo:
            return response

        objeto_id = self._extract_id(getattr(request, '_view_kwargs', {})) or ''
        ip = self._get_client_ip(request)

        datos_nuevos = None
        if method in ('POST', 'PUT', 'PATCH') and hasattr(request, '_post'):
            try:
                datos_nuevos = {k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken'}
            except Exception:
                pass

        AuditLog.objects.create(
            usuario=user,
            accion=accion,
            modelo=modelo,
            objeto_id=str(objeto_id),
            descripcion=self._build_descripcion(method, path, modelo, objeto_id),
            ip_address=ip,
            datos_nuevos=datos_nuevos,
        )
        return response

    def _detect_model(self, path):
        path_lower = path.lower()
        if 'edificio' in path_lower:
            return 'Edificio'
        elif 'sensor' in path_lower:
            return 'Sensor'
        elif 'lectura' in path_lower:
            return 'Lectura'
        elif 'alerta' in path_lower:
            return 'Alerta'
        elif 'informe' in path_lower:
            return 'Informe'
        elif 'equipo' in path_lower:
            return 'Equipo'
        elif 'mantenimiento' in path_lower:
            return 'Mantenimiento'
        elif 'importar' in path_lower:
            return 'Lectura'
        elif 'login' in path_lower:
            return 'Auth'
        elif 'logout' in path_lower:
            return 'Auth'
        elif 'register' in path_lower:
            return 'Auth'
        elif 'usuario' in path_lower or 'user' in path_lower:
            return 'Usuario'
        return None

    def _extract_id(self, kwargs):
        return kwargs.get('pk') or kwargs.get('edificio_pk') or kwargs.get('sensor_pk') or ''

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _build_descripcion(self, method, path, modelo, objeto_id):
        method_names = {
            'POST': 'Creó/Registró',
            'PUT': 'Actualizó',
            'PATCH': 'Actualizó',
            'DELETE': 'Eliminó',
        }
        action = method_names.get(method, method)
        desc = f'{action} {modelo}'
        if objeto_id:
            desc += f' (ID: {objeto_id[:8]}...)'

        if 'login' in path:
            desc = 'Inició sesión'
        elif 'logout' in path:
            desc = 'Cerró sesión'
        elif 'register' in path:
            desc = 'Creó nueva cuenta de usuario'
        elif 'resolver' in path:
            desc = f'Resolvió alerta {modelo}'
        elif 'importar' in path:
            desc = f'Importó datos a {modelo}'
        elif 'exportar' in path:
            desc = f'Exportó datos de {modelo}'

        return desc
