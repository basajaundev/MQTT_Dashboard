import logging
import os
import socket
import subprocess
import sys
import time
from typing import Optional

try:
    from periphery import GPIO
    PERIPHERY_AVAILABLE = True
except ImportError:
    PERIPHERY_AVAILABLE = False

class SystemController:
    def __init__(self, led_gpio_pin: Optional[int]):
        self.led_gpio_pin = led_gpio_pin
        self.start_time = time.time()
        self.led_state = False
        self.gpio_led = None
        self.led_available = False
        
        if self.led_gpio_pin is not None:
            self.setup_gpio()
    
    def setup_gpio(self) -> None:
        """Configurar GPIO usando la librería periphery."""
        if not PERIPHERY_AVAILABLE:
            logging.warning("Librería periphery no disponible. Los comandos LED no funcionarán.")
            return
        
        try:
            self.gpio_led = GPIO(self.led_gpio_pin, "out")
            self.set_led(False)
            self.led_available = True
            logging.info(f"GPIO {self.led_gpio_pin} configurado correctamente para LED.")
        except Exception as e:
            logging.error(f"Error configurando GPIO {self.led_gpio_pin}: {e}")
            self.led_available = False
    
    def set_led(self, state: bool) -> None:
        """Controla el estado del LED."""
        if not self.led_available or self.gpio_led is None:
            return
        
        try:
            self.gpio_led.write(state)
            self.led_state = state
        except Exception as e:
            logging.error(f"Error controlando LED en GPIO {self.led_gpio_pin}: {e}")
            self.led_available = False
    
    def led_on(self) -> None:
        self.set_led(True)
        logging.info(f"LED encendido (GPIO {self.led_gpio_pin})")
    
    def led_off(self) -> None:
        self.set_led(False)
        logging.info(f"LED apagado (GPIO {self.led_gpio_pin})")
    
    def toggle_led(self) -> None:
        new_state = not self.led_state
        self.set_led(new_state)
        logging.info(f"LED alternado a {'ON' if new_state else 'OFF'} (GPIO {self.led_gpio_pin})")

    def cleanup(self) -> None:
        """Libera los recursos GPIO."""
        if self.gpio_led is not None:
            try:
                self.set_led(False)
                time.sleep(0.1)
                self.gpio_led.close()
                logging.info("Recursos GPIO liberados.")
            except Exception as e:
                logging.error(f"Error liberando GPIO: {e}")
    
    def get_uptime(self) -> int:
        return int(time.time() - self.start_time)

    def get_mac_address(self) -> str:
        """Obtiene la dirección MAC del dispositivo."""
        try:
            mac = open('/sys/class/net/eth0/address').read().strip()
        except FileNotFoundError:
            try:
                mac = open('/sys/class/net/wlan0/address').read().strip()
            except FileNotFoundError:
                mac = "00:00:00:00:00:00"
        return mac

    def get_free_memory(self) -> int:
        """Obtiene la memoria libre en bytes."""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        return int(line.split()[1]) * 1024
        except Exception:
            pass
        return 0

    def get_ip_address(self) -> str:
        """
        Obtiene la dirección IP local preferida para salir a internet.
        Utiliza un socket UDP sin conexión para determinar la ruta.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def reboot(self) -> None:
        """Reinicia el sistema."""
        logging.warning("Comando de reinicio recibido. Reiniciando en 3 segundos...")
        self.cleanup()
        try:
            subprocess.run(["logger", "MQTT Client: Reiniciando por comando MQTT"], check=False)
            subprocess.run(["sync"], check=False)
            subprocess.run(["sudo", "reboot"], check=False)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error al intentar reiniciar: {e}")
        except FileNotFoundError:
            logging.error("Comando reboot no encontrado. Sistema puede no ser Linux.")
        finally:
            sys.exit(1)
