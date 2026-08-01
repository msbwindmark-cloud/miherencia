from django.conf import settings


class LocalhostLiveReloadScript:
    def __init__(self, get_response):
        self.get_response = get_response
        try:
            from livereload.middleware import LiveReloadScript
            self._live_reload = LiveReloadScript(get_response)
        except ImportError:
            self._live_reload = None

    def __call__(self, request):
        response = self.get_response(request)
        if not self._live_reload:
            return response
        host = request.get_host().split(':')[0].lower()
        localhost_hosts = getattr(settings, 'LIVERELOAD_HOSTS', ['localhost', '127.0.0.1'])
        if host not in localhost_hosts:
            return response
        return self._live_reload.process_response(request, response)
