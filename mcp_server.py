#!/usr/bin/env python
"""
SmartHeritage MCP Server - Model Context Protocol
Conecta asistentes IA (Claude, etc.) con los datos de SmartHeritage.

Uso:
    python mcp_server.py

Requiere: pip install mcp
"""
import os
import sys
import json
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_heritage.settings')

import django
django.setup()

from mcp.server.fastmcp import FastMCP
from django.contrib.auth.models import User
from monitor.models import (
    Edificio, Sensor, Lectura, Alerta, Mantenimiento,
    Presupuesto, SensorFoto, Informe, Cotizacion,
)

mcp = FastMCP(
    name="SmartHeritage",
    instructions="Servidor MCP de SmartHeritage. Consulta edificios históricos, sensores IoT, alertas y más.",
)


@mcp.tool()
def listar_edificios(ciudad: str = "") -> str:
    """Lista todos los edificios históricos monitorizados, opcionalmente filtrados por ciudad."""
    qs = Edificio.objects.filter(activo=True)
    if ciudad:
        qs = qs.filter(ciudad__icontains=ciudad)
    if not qs.exists():
        return "No se encontraron edificios."
    result = []
    for e in qs:
        result.append({
            "nombre": e.nombre,
            "ciudad": e.ciudad,
            "categoria": e.get_categoria_display(),
            "salud": f"{e.salud_score}%",
            "sensores": e.sensores.count(),
            "año_construccion": str(e.anno_construccion) if e.anno_construccion else "Desconocido",
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def sensores_edificio(nombre_edificio: str) -> str:
    """Obtiene los sensores y últimas lecturas de un edificio por nombre."""
    try:
        edificio = Edificio.objects.get(nombre__icontains=nombre_edificio)
    except Edificio.DoesNotExist:
        return f"No se encontró el edificio '{nombre_edificio}'."
    except Edificio.MultipleObjectsReturned:
        return f"Múltiples edificios coinciden con '{nombre_edificio}'. Sé más específico."

    sensores = edificio.sensores.filter(activo=True)
    result = {
        "edificio": edificio.nombre,
        "salud": f"{edificio.salud_score}%",
        "sensores": [],
    }
    for s in sensores:
        ultima = s.lecturas.order_by('-fecha_hora').first()
        sensor_data = {
            "nombre": s.nombre,
            "tipo": s.get_tipo_display(),
            "ubicacion": s.ubicacion,
            "activo": s.activo,
        }
        if ultima:
            sensor_data["ultima_lectura"] = {
                "valor": ultima.valor,
                "unidad": s.unidad_medida,
                "fecha": ultima.fecha_hora.strftime('%Y-%m-%d %H:%M:%S'),
                "es_alerta": ultima.es_alerta,
            }
        result["sensores"].append(sensor_data)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def alertas_activas(severidad: str = "", limite: int = 20) -> str:
    """Lista alertas activas (sin resolver). Filtra por severidad: low, medium, high, critical."""
    qs = Alerta.objects.filter(resuelta=False).select_related('sensor__edificio').order_by('-fecha_creacion')
    if severidad:
        qs = qs.filter(severidad=severidad)
    qs = qs[:limite]
    if not qs.exists():
        return "No hay alertas activas."
    result = []
    for a in qs:
        result.append({
            "id": str(a.pk)[:8],
            "edificio": a.sensor.edificio.nombre if a.sensor and a.sensor.edificio else "N/A",
            "sensor": a.sensor.nombre if a.sensor else "N/A",
            "mensaje": a.mensaje,
            "severidad": a.get_severidad_display(),
            "fecha": a.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def estadisticas_dashboard() -> str:
    """Obtiene las estadísticas generales del dashboard principal."""
    from django.db.models import Avg
    edificios = Edificio.objects.filter(activo=True)
    salud_scores = [e.salud_score for e in edificios]
    stats = {
        "edificios_activos": edificios.count(),
        "sensores_totales": Sensor.objects.filter(activo=True).count(),
        "lecturas_hoy": Lectura.objects.filter(fecha_hora__date=datetime.date.today()).count(),
        "alertas_activas": Alerta.objects.filter(resuelta=False).count(),
        "alertas_criticas": Alerta.objects.filter(resuelta=False, severidad='critical').count(),
        "mantenimientos_pendientes": Mantenimiento.objects.filter(estado__in=['pendiente', 'en_progreso']).count(),
        "salud_promedio": round(sum(salud_scores) / len(salud_scores), 1) if salud_scores else 0,
    }
    return json.dumps(stats, ensure_ascii=False, indent=2)


@mcp.tool()
def buscar_edificio(termino: str) -> str:
    """Busca edificios por nombre, ciudad o dirección."""
    qs = Edificio.objects.filter(
        Q(nombre__icontains=termino) |
        Q(ciudad__icontains=termino) |
        Q(direccion__icontains=termino)
    )
    if not qs.exists():
        return f"No se encontraron edificios para '{termino}'."
    result = []
    for e in qs:
        result.append({
            "nombre": e.nombre,
            "ciudad": e.ciudad,
            "direccion": e.direccion,
            "salud": f"{e.salud_score}%",
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def historial_lecturas(nombre_sensor: str, horas: int = 24) -> str:
    """Obtiene el historial de lecturas de un sensor en las últimas N horas."""
    from datetime import timedelta
    desde = datetime.datetime.now() - timedelta(hours=horas)
    sensores = Sensor.objects.filter(nombre__icontains=nombre_sensor, activo=True)
    if not sensores.exists():
        return f"No se encontró el sensor '{nombre_sensor}'."
    result = []
    for s in sensores:
        lecturas = s.lecturas.filter(fecha_hora__gte=desde).order_by('fecha_hora')
        sensor_data = {
            "sensor": s.nombre,
            "edificio": s.edificio.nombre,
            "tipo": s.get_tipo_display(),
            "lecturas": [],
        }
        for l in lecturas:
            sensor_data["lecturas"].append({
                "valor": l.valor,
                "fecha": l.fecha_hora.strftime('%Y-%m-%d %H:%M'),
                "es_alerta": l.es_alerta,
            })
        result.append(sensor_data)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def resumen_cotizaciones() -> str:
    """Obtiene un resumen de todas las cotizaciones."""
    cotizaciones = Cotizacion.objects.all().order_by('-fecha_creacion')[:10]
    if not cotizaciones.exists():
        return "No hay cotizaciones registradas."
    result = []
    for c in cotizaciones:
        result.append({
            "titulo": c.titulo,
            "cliente": c.cliente_nombre,
            "total": f"€{c.total:.2f}",
            "estado": c.get_estado_display(),
            "fecha": c.fecha_creacion.strftime('%d/%m/%Y'),
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    print("SmartHeritage MCP Server iniciado")
    print("Herramientas disponibles:")
    print("  - listar_edificios(ciudad)")
    print("  - sensores_edificio(nombre_edificio)")
    print("  - alertas_activas(severidad, limite)")
    print("  - estadisticas_dashboard()")
    print("  - buscar_edificio(termino)")
    print("  - historial_lecturas(nombre_sensor, horas)")
    print("  - resumen_cotizaciones()")
    print()
    mcp.run()
