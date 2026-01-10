import json
import logging
import signal
import sys
import time
import threading
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt

from src.config import Config
from src.system import SystemController, PERIPHERY_AVAILABLE

class MQTTDeviceClient:
    def __init__(self, config: Config):
        self.config = config
        self.system = SystemController(
            led_gpio_pin=self.config.LED_GPIO_PIN
        )
        self.client = self._setup_mqtt_client()
        self.running = True
        self.is_connected = False

        self.command_handlers = {
            "PING": self._handle_ping,
            "STATUS": self._handle_status,
            "REBOOT": self._handle_reboot,
            "LED_ON": self._handle_led_on,
            "LED_OFF": self._handle_led_off,
            "LED_TOGGLE": self._handle_led_toggle,
            "GET_CONFIG": self._handle_get_config,
        }

    def _setup_mqtt_client(self) -> mqtt.Client:
        """Configura y devuelve una instancia del cliente MQTT."""
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.config.DEVICE)
            logging.info("Usando API MQTT v2.")
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=self.config.DEVICE)
            logging.info("Usando API MQTT v1 (fallback).")

        if self.config.USERNAME and self.config.PASSWORD:
            client.username_pw_set(self.config.USERNAME, self.config.PASSWORD)
            logging.info(f"Autenticación configurada para el usuario '{self.config.USERNAME}'.")
        else:
            logging.info("Conexión anónima (sin autenticación).")

        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        
        return client

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        rc = reason_code if isinstance(reason_code, int) else reason_code.value
        if rc == 0:
            logging.info("Conectado al broker MQTT.")
            self.is_connected = True
            client.subscribe(self.config.PING_TOPIC, qos=1)
            client.subscribe(self.config.CMD_TOPIC, qos=1)
            logging.info(f"Suscrito a '{self.config.PING_TOPIC}' y '{self.config.CMD_TOPIC}'.")
            
            self.publish_status()
            self._handle_get_config({})
        else:
            logging.error(f"Error de conexión MQTT: {mqtt.connack_string(rc)}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None) -> None:
        self.is_connected = False
        if reason_code != 0:
            logging.warning(f"Desconexión inesperada. Código: {reason_code}. Reintentando conexión...")

    def _on_message(self, client, userdata, msg) -> None:
        """Callback para procesar mensajes entrantes."""
        try:
            payload = msg.payload.decode('utf-8')
            logging.info(f"Mensaje recibido en '{msg.topic}': {payload}")
            data = json.loads(payload)
            cmd = data.get("cmd")

            if handler := self.command_handlers.get(cmd):
                handler(data)
            else:
                logging.warning(f"Comando desconocido: {cmd}")

        except json.JSONDecodeError:
            logging.error("Error al decodificar JSON del payload.")
        except Exception as e:
            logging.error(f"Error procesando mensaje: {e}")

    def _handle_ping(self, data: Dict[str, Any]) -> None:
        ping_time = data.get("time")
        if ping_time is None:
            logging.warning("Comando PING recibido sin 'time'.")
            return

        pong_msg = {
            "cmd": "PONG",
            "time": ping_time
        }
        self._publish_json(self.config.PONG_TOPIC, pong_msg)

    def _handle_status(self, data: Dict[str, Any]) -> None:
        self.publish_status()

    def _handle_reboot(self, data: Dict[str, Any]) -> None:
        self._publish_json(self.config.STATUS_TOPIC, {"status": "rebooting"})
        threading.Timer(3.0, self.system.reboot).start()

    def _handle_led_on(self, data: Dict[str, Any]) -> None:
        self.system.led_on()
        self._publish_status_update({"led_state": self.system.led_state})

    def _handle_led_off(self, data: Dict[str, Any]) -> None:
        self.system.led_off()
        self._publish_status_update({"led_state": self.system.led_state})

    def _handle_led_toggle(self, data: Dict[str, Any]) -> None:
        self.system.toggle_led()
        self._publish_status_update({"led_state": self.system.led_state})

    def _handle_get_config(self, data: Dict[str, Any]) -> None:
        """Publica la configuración del dispositivo."""
        config_msg = {
            "firmware": "1.0.0-Python",
            "ip": self.system.get_ip_address(),
            "mac": self.system.get_mac_address(),
            "heap": self.system.get_free_memory(),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        }
        self._publish_json(self.config.CONFIG_TOPIC, config_msg)

    def _publish_json(self, topic: str, data: Dict[str, Any]) -> None:
        """Publica un diccionario como JSON en un tópico MQTT."""
        if not self.is_connected:
            logging.warning(f"No conectado. No se puede enviar mensaje a '{topic}'.")
            return

        try:
            payload = json.dumps(data)
            result = self.client.publish(topic, payload, qos=1, retain=False)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"Error al enviar mensaje: {mqtt.error_string(result.rc)}")
            else:
                logging.info(f"Mensaje enviado a '{topic}': {payload}")
        except Exception as e:
            logging.error(f"Error publicando mensaje: {e}")

    def _publish_status_update(self, data: Dict[str, Any]) -> None:
        """Publica una actualización parcial del estado."""
        self._publish_json(self.config.STATUS_TOPIC, data)

    def publish_status(self) -> None:
        """Publica el estado completo del dispositivo."""
        status_msg = {
            "status": "online",
            "device": self.config.DEVICE,
            "location": self.config.LOCATION,
            "ip": self.system.get_ip_address(),
            "uptime": self.system.get_uptime(),
            "firmware": "1.0.0-Python",
            "mac": self.system.get_mac_address(),
            "heap": self.system.get_free_memory(),
        }

        status_msg_cleaned = {k: v for k, v in status_msg.items() if v is not None}
        self._publish_json(self.config.STATUS_TOPIC, status_msg_cleaned)

    def run(self) -> None:
        """Inicia la conexión y el bucle principal del cliente."""
        self._show_system_info()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.client.loop_start()

        max_reconnect_delay = 60
        current_delay = self.config.RECONNECT_DELAY

        while self.running:
            try:
                if not self.is_connected:
                    logging.info(f"Intentando conectar al broker en {self.config.BROKER}:{self.config.BROKER_PORT}...")
                    self.client.connect(self.config.BROKER, self.config.BROKER_PORT, 60)
                
                time.sleep(current_delay)
                
                if not self.is_connected:
                    current_delay = min(current_delay * 1.5, max_reconnect_delay)

            except ConnectionRefusedError:
                logging.warning("Conexión rechazada. Reintentando en unos segundos...")
                current_delay = min(current_delay * 1.5, max_reconnect_delay)
                time.sleep(current_delay)
            except OSError as e:
                logging.warning(f"Error de conexión: {e}. Reintentando...")
                current_delay = min(current_delay * 1.5, max_reconnect_delay)
                time.sleep(current_delay)
            except KeyboardInterrupt:
                logging.info("Interrupción por teclado detectada.")
                self.running = False
            except Exception as e:
                logging.error(f"Error inesperado en el bucle principal: {e}")
                current_delay = min(current_delay * 1.5, max_reconnect_delay)
                time.sleep(current_delay)
        
        self.stop()

    def stop(self) -> None:
        """Detiene el cliente de forma limpia."""
        if not self.running:
            return
        logging.info("Deteniendo el cliente MQTT...")
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        self.system.cleanup()
        logging.info("Cliente detenido.")

    def _signal_handler(self, signum, frame) -> None:
        logging.info(f"Señal {signal.Signals(signum).name} recibida. Cerrando...")
        self.stop()

    def _show_system_info(self) -> None:
        """Muestra información del sistema al inicio."""
        print("=" * 60)
        print("MQTT Device Client (Refactorizado)")
        print(f"  Dispositivo: {self.config.DEVICE} @ {self.config.LOCATION}")
        print(f"  Broker: mqtt://{self.config.BROKER}:{self.config.BROKER_PORT}")
        if self.config.USERNAME:
            print(f"  Usuario: {self.config.USERNAME}")
        print(f"  GPIO para LED: {self.config.LED_GPIO_PIN if self.config.LED_GPIO_PIN else 'No configurado'}")
        print(f"  Periphery disponible: {PERIPHERY_AVAILABLE}")
        print(f"  LED disponible: {self.system.led_available}")
        print("=" * 60)
