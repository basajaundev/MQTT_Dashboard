import json
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir: str = "logs"):
    """Configura el logging para mostrar mensajes en consola y en un archivo rotativo."""
    
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            logging.error(f"No se pudo crear el directorio de logs '{log_dir}': {e}")
            logging.basicConfig(
                level=logging.INFO,
                format="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            return

    log_formatter = logging.Formatter(
        fmt="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # --- Logging a consola ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # --- Logging a archivo rotativo ---
    log_file_path = os.path.join(log_dir, 'mqtt_client.log')
    
    try:
        file_handler = RotatingFileHandler(
            log_file_path, 
            maxBytes=1024 * 1024, # 1 MB
            backupCount=5
        )
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        logging.error(f"No se pudo configurar el logging a archivo en '{log_file_path}': {e}")


class Config:
    """Carga la configuración desde un archivo .json."""
    def __init__(self, filename="config.json"):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"El archivo de configuración '{filename}' no se encontró.")
        
        with open(filename, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Error al decodificar {filename}: {e}")

        # MQTT section
        mqtt_config = config.get('mqtt', {})
        self.BROKER = mqtt_config.get('broker', "127.0.0.1")
        self.BROKER_PORT = mqtt_config.get('port', 1883)
        self.DEVICE = mqtt_config.get('device_id', "generic-device")
        self.LOCATION = mqtt_config.get('location', "default-location")
        self.USERNAME = mqtt_config.get('username', None)
        self.PASSWORD = mqtt_config.get('password', None)
        
        # Logging section
        logging_config = config.get('logging', {})
        self.LOG_DIR = logging_config.get('log_dir', 'logs')

        # Tópicos MQTT (generados dinámicamente)
        self.PING_TOPIC = "iot/ping/all"
        self.PONG_TOPIC = f"iot/pong/{self.DEVICE}/{self.LOCATION}"
        self.CMD_TOPIC = f"iot/cmd/{self.DEVICE}/{self.LOCATION}"
        self.STATUS_TOPIC = f"iot/status/{self.DEVICE}/{self.LOCATION}"
        self.CONFIG_TOPIC = f"iot/config/{self.DEVICE}/{self.LOCATION}"
        
        # GPIO section
        gpio_config = config.get('gpio', {})
        self.LED_GPIO_PIN = gpio_config.get('led_pin', None)
        
        # Settings section
        settings_config = config.get('settings', {})
        self.RECONNECT_DELAY = settings_config.get('reconnect_delay', 5)
