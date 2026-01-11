# MQTT Dashboard

Panel de control web para gestión de dispositivos IoT via MQTT.

## Descripción

MQTT Dashboard es una aplicación web que permite gestionar y monitorizar dispositivos IoT conectados a través del protocolo MQTT. Proporciona una interfaz moderna y responsive para:

- **Gestión de servidores MQTT** - Múltiples conexiones simultáneas
- **Monitorización en tiempo real** - Estado de dispositivos, latencia, sensores
- **Sistema de alertas** - Notificaciones configurables
- **Tareas programadas** - Envío automático de comandos MQTT
- **Disparadores automáticos** - Respuesta automática a eventos
- **Backup automático** - Copias de seguridad con compresión

## Características

- Interfaz web responsive (desktop y móvil)
- Comunicación bidireccional en tiempo real (WebSocket)
- Soporte para múltiples grupos de dispositivos
- Persistencia de datos con SQLite
- Configuración completa desde la interfaz
- Búsqueda de dispositivos en tiempo real
- Visualización de gráficos de sensores

## Tecnologías

### Backend
- **Flask** - Framework web
- **Flask-SocketIO** - Comunicación WebSocket
- **gevent** - Programación asíncrona
- **APScheduler** - Tareas programadas
- **paho-mqtt** - Cliente MQTT
- **Flask-SQLAlchemy** - ORM para base de datos
- **Flask-Compress** - Compresión de respuestas

### Frontend
- Vanilla JavaScript ES6+
- CSS moderno con variables
- Socket.IO client
- Chart.js para gráficos

### Base de datos
- **SQLite** - Base de datos embebida

## Instalación

### Requisitos previos
- Python 3.8 o superior
- pip

### Pasos de instalación

```bash
# Clonar el repositorio
git clone https://github.com/basajaundev/MQTT_Dashboard.git
cd MQTT_Dashboard

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Estructura del proyecto

```
MQTT_Dashboard/
├── app.py                    # Punto de entrada de la aplicación
├── requirements.txt          # Dependencias Python
├── AGENTS.md                # Guía de desarrollo
├── backup_db.py             # Sistema de backup con compresión
├── docs/
│   ├── ARCHITECTURE.md      # Documentación de arquitectura
│   └── COMMUNICATION.md     # Protocolo de comunicación MQTT
├── src/
│   ├── database.py          # Inicialización de base de datos
│   ├── models.py            # Modelos SQLAlchemy
│   ├── persistence.py       # Operaciones de base de datos
│   ├── routes.py            # Rutas HTTP
│   ├── socket_handlers.py   # Manejadores Socket.IO
│   ├── mqtt_callbacks.py    # Callbacks MQTT
│   ├── globals.py           # Variables globales
│   ├── validation.py        # Validación de entrada
│   └── task_utils.py        # Utilidades de tareas
├── static/
│   ├── css/                 # Estilos CSS
│   └── js/                  # JavaScript del frontend
├── templates/
│   ├── layout.html          # Layout base
│   ├── dashboard.html       # Panel de dispositivos
│   ├── config.html          # Configuración
│   └── *.html               # Otras páginas
└── tests/                   # Tests
```

## Configuración

###添加伺服idores MQTT

1. Ir a la sección "Configuración"
2. En la pestaña "Servidores", hacer clic en "Añadir Servidor"
3. Completar los datos:
   - Nombre del servidor
   - Broker (IP o hostname)
   - Puerto (por defecto 1883)
   - Usuario y contraseña (opcional)

### Whitelist de dispositivos

Los dispositivos deben estar en la whitelist para aparecer en el dashboard:

1. Ir a "Configuración" > "Gestión de Dispositivos"
2. Añadir dispositivos por ID y ubicación
3. Asignar a grupos (opcional)

### Ajustes del sistema

- **Intervalo de refresco**: Tiempo entre refrescos automáticos (segundos)
- **Tolerancia a fallos**: Número de PINGs perdidos antes de marcar offline

### Configuración MQTT

- **Keepalive**: Intervalo de keepalive en segundos
- **Delay de reconexión**: Delay antes de reconectar
- **Clean session**: Sesión limpia al conectar
- **QoS por defecto**: Calidad de servicio para mensajes

## Uso

### Conectar a un servidor

1. Seleccionar un servidor de la lista
2. Hacer clic en "Conectar"

### Ver dispositivos

Los dispositivos aparecen agrupados por grupo en el dashboard. Cada tarjeta muestra:
- Nombre y ID del dispositivo
- Estado (online/offline)
- Latencia
- Datos de sensores (temperatura, humedad)

### Buscar dispositivos

Usar el campo de búsqueda para filtrar dispositivos por nombre, ID o ubicación.

### Enviar comandos

1. Ir a la página del dispositivo
2. Usar los botones de acción o enviar comandos personalizados

### Crear tareas programadas

1. Ir a "Tareas"
2. Hacer clic en "Nueva Tarea"
3. Configurar topic, payload y programación

## Sistema de Backup

### Backup manual

Hacer clic en "Backup Ahora" en la sección de configuración.

### Backup automático

1. Habilitar "Backup Automático"
2. Configurar intervalo en horas
3. Definir número de backups a mantener

Los backups se guardan comprimidos en formato gzip en la carpeta `backups/`.

## Documentación adicional

| Documento | Descripción |
|-----------|-------------|
| `AGENTS.md` | Guía de desarrollo y convenciones |
| `docs/ARCHITECTURE.md` | Diagramas de arquitectura del sistema |
| `docs/COMMUNICATION.md` | Protocolo de comunicación MQTT |

## Licencia

MIT License

## Autor

basajaundev
