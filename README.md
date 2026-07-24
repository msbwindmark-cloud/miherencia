apikey e69cb590c80c637674e70d52ce590e3f


https://home.openweathermap.org/api_keys



.\venv\Scripts\activate
python -c "import requests; r=requests.get('https://api.openweathermap.org/data/2.5/weather?q=Sevilla&appid=7e57a475c044edaa9e25fd1b0757bfc0&units=metric&lang=es', timeout=10); print(r.status_code)"



 con admin / admin123 y vera todo funcionando!


# SmartHeritage

**Aplicacion unica en el mundo para monitorizacion y preservacion de edificios historicos con IoT, widget islámico y tour guiado.**

![Django](https://img.shields.io/badge/Django-5.x-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Funcionalidades

| Modulo | Descripcion |
|--------|-------------|
| **Dashboard** | Vista general con estadisticas, acceso rapido y widget islámico |
| **Edificios** | CRUD completo con fotos, estado, proteccion oficial |
| **Sensores** | IoT: temperatura, humedad, vibracion, inclinacion |
| **Lecturas** | Historial de datos con graficos Chart.js |
| **Alertas** | Sistema automatico con notificaciones y SMS |
| **Informes** | Generacion automatica de PDF y exportacion |
| **Mapa Global** | Visualizacion interactiva con Leaflet |
| **Comparativa** | Analisis comparativo entre edificios |
| **Tiempo Real** | Dashboard en vivo con datos de sensores |
| **Calendario** | FullCalendar con mantenimientos y alertas |
| **Gamificacion** | Puntos, logros y ranking del equipo |
| **Chat** | Comunicacion interna por edificio |
| **Timeline** | Historial fotografico con antes/despues |
| **Mantenimientos** | Planificacion y seguimiento de mantenimientos |
| **Equipos** | Gestion de equipos de trabajo |
| **SMS/WhatsApp** | Configuracion de notificaciones externas |
| **Audit Log** | Registro completo de todas las acciones |
| **API REST** | 12+ endpoints con Django REST Framework |
| **Widget Islamico** | Fecha Hijri, horarios de Salat, temperatura |
| **Tour Guiado** | Recorrido interactivo por la aplicacion |

---

## Requisitos

- Python 3.11 o superior
- pip
- Git

---

## Instalacion

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/smartheritage.git
cd smartheritage
```

### 2. Crear entorno virtual

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar el ejemplo
cp .env.example .env

# Editar .env con tus valores
# SECRET_KEY=tu_clave_secreta
# OPENWEATHERMAP_API_KEY=tu_api_key (opcional)
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
# Usuario: admin
# Password: admin123
```

### 7. Ejecutar el servidor

```bash
python manage.py runserver
```

### 8. Abrir en el navegador

```
http://localhost:8000/
```

**Credenciales por defecto:**
- Usuario: `admin`
- Contrasena: `admin123`

---

## Variables de Entorno (.env)

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `DEBUG` | Modo desarrollo | `True` |
| `SECRET_KEY` | Clave secreta de Django | `tu-clave-secreta` |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1` |
| `DEFAULT_LAT` | Latitud por defecto | `40.4168` |
| `DEFAULT_LNG` | Longitud por defecto | `-3.7038` |
| `DEFAULT_CITY` | Ciudad por defecto | `Madrid` |
| `OPENWEATHERMAP_API_KEY` | API del clima | `abc123...` |
| `CELERY_BROKER_URL` | Broker de Celery | `redis://localhost:6379/0` |
| `EMAIL_BACKEND` | Backend de email | `console` |

---

## Estructura del Proyecto

```
smartheritage/
├── manage.py
├── .env                    # Variables de entorno (NO subir a Git)
├── .env.example            # Ejemplo de variables
├── .gitignore              # Archivos ignorados
├── requirements.txt        # Dependencias
├── db.sqlite3              # Base de datos (NO subir a Git)
├── smart_heritage/         # Configuracion del proyecto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── monitor/                # Aplicacion principal
│   ├── models.py           # 16 modelos
│   ├── views.py            # 20+ vistas
│   ├── forms.py            # Formularios
│   ├── urls.py             # URLs
│   ├── admin.py            # Admin personalizado
│   ├── api_views.py        # API REST
│   ├── api_urls.py         # URLs de API
│   ├── serializers.py      # Serializadores DRF
│   ├── middleware.py        # Audit middleware
│   └── context_processors.py # Widget islámico
├── templates/              # Plantillas HTML
│   ├── base.html           # Plantilla base
│   └── monitor/            # Plantillas de la app
├── static/                 # Archivos estaticos
└── media/                  # Archivos multimedia
```

---

## API REST

Endpoints disponibles en `/api/v1/`:

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/api/v1/edificios/` | GET/POST | Lista y crea edificios |
| `/api/v1/sensores/` | GET/POST | Lista y crea sensores |
| `/api/v1/lecturas/` | GET/POST | Lista y crea lecturas |
| `/api/v1/alertas/` | GET/POST | Lista y crea alertas |
| `/api/v1/informes/` | GET/POST | Lista y crea informes |
| `/api/v1/equipos/` | GET/POST | Lista y crea equipos |
| `/api/v1/mantenimientos/` | GET/POST | Lista y crea mantenimientos |
| `/api/v1/notificaciones/` | GET | Lista notificaciones |
| `/api/v1/chat/` | GET/POST | Mensajes de chat |
| `/api/v1/gamificacion/` | GET | Puntos y logros |
| `/api/v1/timeline/` | GET/POST | Timeline fotografico |
| `/api/v1/sms-config/` | GET/POST | Configuracion SMS |

---

## Tour Guiado

La aplicacion incluye un tour guiado interactivo que:
- Se ejecuta automaticamente la primera vez
- Puede reiniciarse con el boton "Tour Guiado" (esquina inferior derecha)
- Navega con flechas del teclado o botones
- Presiona `Esc` para salir

---

## Widget Islamico

Caracteristicas:
- **Fecha Hijri**: Dia, mes y anio en calendario islámico
- **Hora en vivo**: Reloj con actualizacion cada segundo
- **Clima**: Temperatura, humedad, viento (requiere API key)
- **Horarios de Salat**: Fajr, Shuruq, Dhuhr, Asr, Maghrib, Isha
- **Proxima oracion**: Resaltada en el widget

### Configurar API del Clima

1. Crear cuenta en [OpenWeatherMap](https://openweathermap.org/api)
2. Obtener API key gratuita
3. Añadir en `.env`:
   ```
   OPENWEATHERMAP_API_KEY=tu_api_key
   ```

---

## Despliegue en Produccion

### 1. Configurar `.env`

```env
DEBUG=False
SECRET_KEY=tu_clave_secreta_segura
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
```

### 2. Recopilar archivos estaticos

```bash
python manage.py collectstatic
```

### 3. Usar un servidor WSGI

```bash
pip install gunicorn
gunicorn smart_heritage.wsgi:application
```

### 4. Configurar HTTPS

Usar Nginx o Apache como proxy inverso con SSL.

---

## Subir a GitHub

```bash
# Inicializar repositorio
git init
git add .
git commit -m "Initial commit: SmartHeritage"

# Conectar con GitHub
git remote add origin https://github.com/TU_USUARIO/smartheritage.git
git branch -M main
git push -u origin main
```

**IMPORTANTE**: El archivo `.env` esta en `.gitignore` y NO se sube nunca.

---

## Solucion de Problemas

### Error: "No module named 'django'"
```bash
.\venv\Scripts\activate
pip install django
```

### Error: "DATABASE ERROR"
```bash
python manage.py migrate
```

### Error: "Static files not found"
```bash
python manage.py collectstatic
```

### El clima no aparece
- Verifica que `OPENWEATHERMAP_API_KEY` este configurado en `.env`
- La API gratuita permite 1000 llamadas/dia

---

## Tecnologias

- **Backend**: Django 5.x, Python 3.11+
- **Frontend**: Bootstrap 5.3, Chart.js, Leaflet, FullCalendar
- **API**: Django REST Framework
- **Seguridad**: Audit middleware, SweetAlert2
- **Extras**: hijridate (fecha islámica), Whitenoise (static files)

---

## Licencia

MIT License - Ver `LICENSE` para detalles.

---

**SmartHeritage** - Protegiendo el patrimonio historico con tecnologia
