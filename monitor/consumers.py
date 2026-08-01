import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class AlertaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'alertas_global'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        alertas = await self.get_alertas_activas()
        await self.send(text_data=json.dumps({
            'type': 'alertas_iniciales',
            'alertas': alertas,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def nueva_alerta(self, event):
        await self.send(text_data=json.dumps({
            'type': 'nueva_alerta',
            'alerta': event['alerta'],
        }))

    async def alerta_resuelta(self, event):
        await self.send(text_data=json.dumps({
            'type': 'alerta_resuelta',
            'alerta_id': event['alerta_id'],
        }))

    @database_sync_to_async
    def get_alertas_activas(self):
        from .models import Alerta
        alertas = Alerta.objects.filter(resuelta=False).select_related('sensor', 'sensor__edificio')[:20]
        return [{
            'id': str(a.id),
            'sensor': a.sensor.nombre,
            'edificio': a.sensor.edificio.nombre,
            'mensaje': a.mensaje,
            'severidad': a.severidad,
            'fecha': a.fecha_creacion.isoformat(),
        } for a in alertas]


class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'sensores_global'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def nueva_lectura(self, event):
        await self.send(text_data=json.dumps({
            'type': 'nueva_lectura',
            'lectura': event['lectura'],
        }))


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'dashboard_global'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        stats = await self.get_dashboard_stats()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_stats',
            'stats': stats,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def dashboard_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'stats': event['stats'],
        }))

    @database_sync_to_async
    def get_dashboard_stats(self):
        from .models import Edificio, Sensor, Lectura, Alerta
        return {
            'total_edificios': Edificio.objects.filter(activo=True).count(),
            'total_sensores': Sensor.objects.filter(activo=True).count(),
            'lecturas_hoy': Lectura.objects.filter(fecha_hora__date=timezone.now().date()).count(),
            'alertas_activas': Alerta.objects.filter(resuelta=False).count(),
        }


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'chat_global'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        mensaje = data.get('mensaje', '')
        if mensaje:
            await self.save_message(mensaje)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'mensaje': mensaje,
                    'usuario': self.scope['user'].username if self.scope['user'].is_authenticated else 'Anonimo',
                    'timestamp': timezone.now().isoformat(),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'mensaje': event['mensaje'],
            'usuario': event['usuario'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def save_message(self, mensaje):
        from .models import ChatMensaje
        if self.scope['user'].is_authenticated:
            ChatMensaje.objects.create(
                usuario=self.scope['user'],
                mensaje=mensaje,
            )
