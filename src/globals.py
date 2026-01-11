import os
from threading import Lock # Importar Lock
from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler

# Cargar variables de entorno desde .env
load_dotenv()

# --- App Initialization ---
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'una-clave-por-defecto-muy-larga-y-segura-por-si-no-hay-env')

# --- Database Configuration (Ruta Absoluta) ---
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
db_path = os.path.join(basedir, 'dashboard.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Extensions ---
db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='gevent')
scheduler = BackgroundScheduler()

# --- Compression ---
from flask_compress import Compress
compress = Compress(app)
compress.init_app(app)

# --- Global State Variables ---
mqtt_state = {'client': None, 'background_task_started': False, 'connected': False}
config = {'servers': {}, 'settings': {}}
global_state = {'active_server_name': "N/A", 'active_server_config': {}}
subscribed_topics = []
devices = {}
devices_lock = Lock()
scheduled_tasks = {}
message_triggers = {}
alerts = []

# --- Message History ---
MAX_MESSAGES = 100
message_history = []

# --- MQTT Topics ---
DEVICE_STATUS_TOPIC = "iot/status/+/+"
DEVICE_PONG_TOPIC = "iot/pong/+/+"
DEVICE_PING_TOPIC = "iot/ping/all"
DEVICE_CONFIG_TOPIC = "iot/config/+/+"
DEVICE_CMD_TOPIC_PREFIX = "iot/cmd"
DEVICE_CMD_BROADCAST_TOPIC = f"{DEVICE_CMD_TOPIC_PREFIX}/all/all"


def load_subscriptions_to_memory():
    """Carga las suscripciones desde la BD para el servidor activo al iniciar la app."""
    from src.persistence import load_subscriptions
    server_name = global_state.get('active_server_name', 'N/A')
    if server_name and server_name != 'N/A':
        try:
            topics = load_subscriptions(server_name)
            subscribed_topics.clear()
            subscribed_topics.extend(topics)
            import logging
            logger = logging.getLogger()
            logger.info(f"📚 Suscripciones cargadas para '{server_name}': {len(topics)} topics")
        except Exception as e:
            import logging
            logger = logging.getLogger()
            logger.error(f"❌ Error al cargar suscripciones al inicio: {e}")
