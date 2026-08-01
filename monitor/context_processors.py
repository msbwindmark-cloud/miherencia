from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
import requests
import json

MESES_HIJRI = {
    1: 'Muharram', 2: 'Safar', 3: 'Rabi al-Awwal', 4: 'Rabi al-Thani',
    5: 'Jumada al-Ula', 6: 'Jumada al-Thani', 7: 'Rajab', 8: 'Sha\'ban',
    9: 'Ramadan', 10: 'Shawwal', 11: 'Dhu al-Qi\'dah', 12: 'Dhu al-Hijjah'
}

MESES_HIJRI_ES = {
    1: 'Muharram', 2: 'Safar', 3: 'Rabi\' al-Awwal', 4: 'Rabi\' al-Thani',
    5: 'Jumada al-Ula', 6: 'Jumada al-Thani', 7: 'Rajab', 8: 'Sha\'ban',
    9: 'Ramadán', 10: 'Shawwal', 11: 'Dhu al-Qi\'dah', 12: 'Dhu al-Hijjah'
}

DIAS_SEMANA_HIJRI = {
    0: 'Al-Ahad', 1: 'Al-Ithnayn', 2: 'Al-Thulatha\'', 3: 'Al-Arbi\'a\'',
    4: 'Al-Khamis', 5: 'Al-Jumu\'ah', 6: 'Al-Sabt'
}

DIAS_SEMANA_ES = {
    0: 'Domingo', 1: 'Lunes', 2: 'Martes', 3: 'Miércoles',
    4: 'Jueves', 5: 'Viernes', 6: 'Sábado'
}


def get_hijri_date():
    cache_key = f'hijri_{datetime.now().strftime("%Y-%m-%d")}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        from hijridate import Gregorian
        today = datetime.now()
        g = Gregorian(today.year, today.month, today.day)
        h = g.to_hijri()
        result = {
            'dia': h.day,
            'mes': h.month_name(),
            'mes_es': MESES_HIJRI_ES.get(h.month, ''),
            'anio': h.year,
            'completa': f'{h.day} {MESES_HIJRI_ES.get(h.month, "")} {h.year} AH',
            'completa_en': f'{h.day} {h.month_name()} {h.year} AH',
        }
    except Exception:
        result = {
            'dia': '', 'mes': '', 'mes_es': '', 'anio': '',
            'completa': '', 'completa_en': ''
        }
    cache.set(cache_key, result, 86400)
    return result


def get_prayer_times(lat=40.4168, lng=-3.7038, city='Madrid'):
    cache_key = f'prayer_{city}_{datetime.now().strftime("%Y-%m-%d")}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        url = f'https://api.aladhan.com/v1/timings/{datetime.now().strftime("%d-%m-%Y")}'
        params = {
            'latitude': lat,
            'longitude': lng,
            'method': 1,
            'shafpiaq': 1,
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get('code') == 200:
            timings = data['data']['timings']
            result = {
                'fajr': timings.get('Fajr', '--:--'),
                'sunrise': timings.get('Sunrise', '--:--'),
                'dhuhr': timings.get('Dhuhr', '--:--'),
                'asr': timings.get('Asr', '--:--'),
                'maghrib': timings.get('Maghrib', '--:--'),
                'isha': timings.get('Isha', '--:--'),
                'imsak': timings.get('Imsak', '--:--'),
                'midnight': timings.get('Midnight', '--:--'),
                'hijri': data['data']['date']['hijri'] if data['data'].get('date') else {},
                'method': data['data']['meta']['method']['name'] if data['data'].get('meta') else '',
            }
            now = datetime.now()
            prayers_order = [
                ('Fajr', result['fajr']), ('Shuruq', result['sunrise']),
                ('Dhuhr', result['dhuhr']), ('Asr', result['asr']),
                ('Maghrib', result['maghrib']), ('Isha', result['isha']),
            ]
            for name, time_str in prayers_order:
                if time_str and time_str != '--:--':
                    try:
                        h, m = time_str.split(':')
                        prayer_time = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                        if prayer_time > now:
                            result['next_prayer'] = name
                            result['next_prayer_name'] = name
                            result['next_prayer_time'] = time_str
                            break
                    except Exception:
                        pass
            if 'next_prayer' not in result:
                result['next_prayer'] = 'Fajr'
                result['next_prayer_name'] = 'Fajr'
                result['next_prayer_time'] = result['fajr']
            cache.set(cache_key, result, 3600)
            return result
    except Exception:
        pass
    result = {
        'fajr': '--:--', 'sunrise': '--:--', 'dhuhr': '--:--',
        'asr': '--:--', 'maghrib': '--:--', 'isha': '--:--',
        'imsak': '--:--', 'midnight': '--:--', 'hijri': {}, 'method': '',
        'next_prayer': '', 'next_prayer_name': '', 'next_prayer_time': ''
    }
    cache.set(cache_key, result, 300)
    return result


def get_weather(city='Madrid', lat=None, lng=None):
    api_key = getattr(settings, 'OPENWEATHERMAP_API_KEY', '')
    if not api_key:
        return None

    cache_key = f'weather_{city}_{datetime.now().strftime("%Y-%m-%d_%H")}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        if lat and lng:
            url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={api_key}&units=metric&lang=es'
        else:
            url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=es'
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('cod') == 200:
            result = {
                'temperatura': round(data['main']['temp']),
                'sensacion': round(data['main']['feels_like']),
                'humedad': data['main']['humidity'],
                'descripcion': data['weather'][0]['description'].title(),
                'icono': data['weather'][0]['icon'],
                'viento': round(data['wind']['speed'] * 3.6),
                'ciudad': data.get('name', city),
                'pais': data['sys'].get('country', ''),
            }
            cache.set(cache_key, result, 1800)
            return result
    except Exception:
        pass
    return None


def show_tour_context(request):
    show_tour = request.session.pop('smartheritage_tour_pending', False)
    return {'show_tour': show_tour}


def IslamicWidgetContext(request):
    context = {}

    hijri = get_hijri_date()
    context['hijri'] = hijri

    now = datetime.now()
    context['fecha_completa'] = {
        'dia_semana': DIAS_SEMANA_ES.get(now.weekday(), ''),
        'dia': now.day,
        'mes': now.strftime('%B'),
        'anio': now.year,
        'hora': now.strftime('%H:%M:%S'),
        'fecha': now.strftime('%d/%m/%Y'),
        'completa': f"{DIAS_SEMANA_ES.get(now.weekday(), '')}, {now.day} de {now.strftime('%B')} de {now.year} - {now.strftime('%H:%M:%S')}",
    }

    lat = getattr(settings, 'DEFAULT_LAT', 40.4168)
    lng = getattr(settings, 'DEFAULT_LNG', -3.7038)
    city = getattr(settings, 'DEFAULT_CITY', 'Madrid')

    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            perfil = request.user.perfil
            if perfil.edificios_asignados.exists():
                edificio = perfil.edificios_asignados.first()
                if edificio.latitud and edificio.longitud:
                    lat = float(edificio.latitud)
                    lng = float(edificio.longitud)
                    city = edificio.ciudad
        except Exception:
            pass

    prayer_times = get_prayer_times(lat, lng, city)
    context['prayer_times'] = prayer_times

    weather = get_weather(city, lat, lng)
    context['weather'] = weather
    context['weather_city'] = city

    return context
