#!/usr/bin/env python3
"""
Punto de entrada principal para el Cliente MQTT.

Este script inicializa la configuración, el logging y ejecuta el cliente MQTT.
"""

import sys
import logging

from src.config import Config, setup_logging
from src.client import MQTTDeviceClient

def main():
    """Función principal que inicia el cliente."""
    try:
        app_config = Config("config.json")
    except (FileNotFoundError, ValueError) as e:
        # Si la configuración falla, el logging no se puede configurar desde el archivo.
        # Usar una configuración básica para mostrar el error.
        logging.basicConfig(level=logging.CRITICAL)
        logging.critical(f"Error de configuración: {e}. Asegúrate de que 'config.json' exista y sea válido.")
        return 1
    
    # Configurar el logging usando la ruta del archivo de configuración
    setup_logging(log_dir=app_config.LOG_DIR)

    client = MQTTDeviceClient(app_config)
    client.run()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
