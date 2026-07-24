from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/alertas/$', consumers.AlertaConsumer.as_asgi()),
    re_path(r'ws/sensores/$', consumers.SensorConsumer.as_asgi()),
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]
