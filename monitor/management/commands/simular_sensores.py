import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from monitor.models import Sensor, Lectura, Alerta


class Command(BaseCommand):
    help = 'Simula lecturas IoT de todos los sensores activos y envia por WebSocket'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1, help='Lecturas por sensor')
        parser.add_argument('--interval', type=int, default=0, help='Segundos entre lotes')

    def handle(self, *args, **options):
        count = options['count']
        sensores = Sensor.objects.filter(activo=True)
        total = 0
        alertas = 0

        for _ in range(count):
            for sensor in sensores:
                valor = self._generar_valor(sensor.tipo)
                lectura = Lectura.objects.create(
                    sensor=sensor,
                    valor=valor,
                    fecha_hora=timezone.now(),
                )
                total += 1
                if lectura.es_alerta:
                    alertas += 1

        self.stdout.write(self.style.SUCCESS(
            f'Simulacion completada: {total} lecturas, {alertas} alertas generadas'
        ))
        return f'{total} lecturas simuladas, {alertas} alertas'

    def _generar_valor(self, tipo):
        ranges = {
            'temperatura': (15.0, 35.0),
            'humedad': (30.0, 85.0),
            'vibracion': (0.0, 8.0),
            'luz': (0.0, 1000.0),
            'co2': (300.0, 800.0),
            'ruido': (20.0, 90.0),
            'grieta': (0.0, 5.0),
            'presion': (1000.0, 1030.0),
        }
        r = ranges.get(tipo, (0.0, 100.0))
        return round(random.uniform(r[0], r[1]), 2)
