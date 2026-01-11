# MQTT Dashboard

Panel de control web para gestion de dispositivos IoT via MQTT.

## Descripcion

MQTT Dashboard es una aplicacion web que permite gestionar y monitorizar dispositivos IoT conectados a traves del protocolo MQTT. Proporciona una interfaz moderna y responsive para:

- **Gestion de servidores MQTT** - Multiple conexiones simultaneas
- **Monitorizacion en tiempo real** - Estado de dispositivos, latencia, sensores
- **Sistema de alertas** - Notificaciones configurables
- **Tareas programadas** - Envio automatico de comandos MQTT
- **Disparadores automaticos** - Respuesta automatica a eventos
- **Backup automatico** - Copias de seguridad con compresion

## Caracteristicas

- Interfaz web responsive (desktop y movil)
- Comunicacion bidireccional en tiempo real (WebSocket)
- Soporte para multiples grupos de dispositivos
- Persistencia de datos con SQLite
- Configuracion completa desde la interfaz
- Busqueda de dispositivos en tiempo real
- Visualizacion de graficos de sensores

## tecnologias

### Backend
- **Flask** - Framework web
- **Flask-SocketIO** - Comunicacion WebSocket
- **gevent** - Programacion asincrona
- **APScheduler** - Tareas programadas
- **paho-mqtt** - Cliente MQTT
- **Flask-SQLAlchemy** - ORM para base de datos
- **Flask-Compress** - Compresion de respuestas

### Frontend
- Vanilla JavaScript ES6+
- CSS moderno con variables
- Socket.IO client
- Chart.js para graficos

### Base de datos
- **SQLite** - Base de datos embebida

## Creado con Inteligencia Artificial

Este proyecto ha sido integramente creado utilizando inteligencia artificial:

- **Fase inicial:** Gemini (Google)
- **Fase actual:** MiniMax

Agradecimiento especial a **OpenCode** (https://github.com/anomalyco/opencode) por proporcionar la plataforma deIA que facilita el desarrollo de este tipo de proyectos.

## Instalacion

### Requisitos previos
- Python 3.8 o superior
- pip

### Pasos de instalacion

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

# Ejecutar la aplicacion
python app.py
```

La aplicacion estara disponible en `http://localhost:5000`

## Estructura del proyecto

```
MQTT_Dashboard/
├── app.py                    # Punto de entrada de la aplicacion
├── requirements.txt          # Dependencias Python
├── AGENTS.md                # Guia de desarrollo
├── backup_db.py             # Sistema de backup con compresion
├── docs/
│   ├── ARCHITECTURE.md      # Documentacion de arquitectura
│   └── COMMUNICATION.md     # Protocolo de comunicacion MQTT
├── src/
│   ├── database.py          # Inicializacion de base de datos
│   ├── models.py            # Modelos SQLAlchemy
│   ├── persistence.py       # Operaciones de base de datos
│   ├── routes.py            # Rutas HTTP
│   ├── socket_handlers.py   # Manejadores Socket.IO
│   ├── mqtt_callbacks.py    # Callbacks MQTT
│   ├── globals.py           # Variables globales
│   ├── validation.py        # Validacion de entrada
│   └── task_utils.py        # Utilidades de tareas
├── static/
│   ├── css/                 # Estilos CSS
│   └── js/                  # JavaScript del frontend
├── templates/
│   ├── layout.html          # Layout base
│   ├── dashboard.html       # Panel de dispositivos
│   ├── config.html          # Configuracion
│   └── *.html               # Otras paginas
└── tests/                   # Tests
```

## Configuracion

### Agregar servidores MQTT

1. Ir a la seccion "Configuracion"
2. En la pesta?a "Servidores", hacer clic en "Anadir Servidor"
3. Completar los datos:
   - Nombre del servidor
   - Broker (IP o hostname)
   - Puerto (por defecto 1883)
   - Usuario y contrasena (opcional)

### Whitelist de dispositivos

Los dispositivos deben estar en la whitelist para aparecer en el dashboard:

1. Ir a "Configuracion" > "Gestion de Dispositivos"
2. Anadir dispositivos por ID y ubicacion
3. Asignar a grupos (opcional)

### Ajustes del sistema

- **Intervalo de refresco:** Tiempo entre refrescos automaticos (segundos)
- **Tolerancia a fallos:** Numero de PINGs perdidos antes de marcar offline

### Configuracion MQTT

- **Keepalive:** Intervalo de keepalive en segundos
- **Delay de reconexion:** Delay antes de reconectar
- **Clean session:** Sesion limpia al conectar
- **QoS por defecto:** Calidad de servicio para mensajes

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

Usar el campo de busqueda para filtrar dispositivos por nombre, ID o ubicacion.

### Enviar comandos

1. Ir a la pagina del dispositivo
2. Usar los botones de accion o enviar comandos personalizados

### Crear tareas programadas

1. Ir a "Tareas"
2. Hacer clic en "Nueva Tarea"
3. Configurar topic, payload y programacion

## Sistema de Backup

### Backup manual

Hacer clic en "Backup Ahora" en la seccion de configuracion.

### Backup automatico

1. Habilitar "Backup Automatico"
2. Configurar intervalo en horas
3. Definir numero de backups a mantener

Los backups se guardan comprimidos en formato gzip en la carpeta `backups/`.

## Documentacion adicional

| Documento | Descripcion |
|-----------|-------------|
| `AGENTS.md` | Guia de desarrollo y convenciones |
| `docs/ARCHITECTURE.md` | Diagramas de arquitectura del sistema |
| `docs/COMMUNICATION.md` | Protocolo de comunicacion MQTT |

## Licencia

MIT License

## Autor

GallaZ
