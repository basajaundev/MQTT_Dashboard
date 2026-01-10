#!/usr/bin/env python3
"""
Dashboard MQTT IoT - Servidor Web con Flask
Script principal de arranque de la aplicación.
"""
# Es CRUCIAL que monkey_patch() se llame ANTES de importar cualquier otra cosa.
from gevent import monkey
monkey.patch_all()

import logging
import os
import warnings
import threading
import signal
import time

from gevent import pywsgi
from flask_compress import Compress

compress = Compress()

# Filtrar advertencia inofensiva de gevent/libuv en Windows
warnings.filterwarnings("ignore", category=UserWarning, module='gevent.timeout')

# Configurar el logging ANTES de importar otros módulos
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importar componentes principales y funciones de inicialización
from src.globals import app, socketio, scheduler, mqtt_state, global_state
from src.database import init_db
from src.persistence import load_config, cleanup_sensor_data, should_run_cleanup, save_scheduler_state
from src.routes import *
from src.socket_handlers import *

# Bandera para controlar el cierre
shutdown_requested = False

def signal_handler(sig, frame):
    """Manejador de señales para cierre limpio."""
    global shutdown_requested
    logger.info(f"senal {sig} recibida, solicitando cierre...")
    shutdown_requested = True

def stop_server():
    """Detiene todos los componentes del servidor de forma limpia."""
    global shutdown_requested
    
    if shutdown_requested:
        return
    
    shutdown_requested = True
    logger.info("Deteniendo servidor...")
    
    # 1. Cerrar servidor WSGI primero (libera el puerto)
    if 'wsgi_server' in globals() and wsgi_server:
        try:
            wsgi_server.stop()
            logger.info("Servidor WSGI detenido")
        except Exception as e:
            logger.error(f"Error deteniendo WSGI: {e}")
    
    # 2. Desconectar cliente MQTT
    client = mqtt_state.get('client')
    if client:
        try:
            if client.is_connected():
                logger.info("Desconectando cliente MQTT...")
                client.loop_stop()
                client.disconnect()
                logger.info("Cliente MQTT desconectado")
        except Exception as e:
            logger.error(f"Error desconectando MQTT: {e}")
    
    # 3. Forzar cierre de threads huérfanos
    logger.info("Cerrando threads huérfanos...")
    active_threads = threading.enumerate()
    for thread in active_threads:
        if thread is not threading.current_thread() and thread.is_alive():
            thread_name = thread.name.lower()
            # Cerrar threads de MQTT y gevent
            if 'paho' in thread_name or 'mqtt' in thread_name or 'gevent' in thread_name or 'background' in thread_name:
                try:
                    logger.info(f"Cerrando thread: {thread.name}")
                    # Los threads de gevent/paho se cierran solos cuando salimos
                except Exception as e:
                    logger.warning(f"Error cerrando thread {thread.name}: {e}")
    
    # 4. Guardar estado del scheduler
    try:
        save_scheduler_state()
        logger.info("Estado del scheduler guardado")
    except Exception as e:
        logger.error(f"Error guardando estado: {e}")
    
    # 5. Shutdown del scheduler
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler detenido")
    except Exception as e:
        logger.error(f"Error deteniendo scheduler: {e}")
    
    logger.info("Servidor detenido correctamente")

def main():
    """Función principal para configurar e iniciar la aplicación."""
    global wsgi_server
    
    print("="*60)
    print("Dashboard MQTT IoT - Python Backend")
    print("="*60)

    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Usar el contexto de la aplicación para operaciones de base de datos
    with app.app_context():
        # 1. Inicializar la base de datos
        init_db()
        # 2. Cargar la configuración inicial
        load_config()
        # 3. Limpieza de datos históricos si es necesario
        if should_run_cleanup():
            deleted = cleanup_sensor_data(days=30)
            from src.persistence import update_cleanup_timestamp
            update_cleanup_timestamp()

    # 4. Cargar la clave secreta desde una variable de entorno si está disponible
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mqtt-dashboard-secret-key-default')

    # 5. Iniciar el scheduler en modo pausado
    scheduler.start(paused=True)
    
    # 6. Configurar backup automático
    def scheduled_backup_job():
        """Función de backup automático llamada por el scheduler."""
        try:
            from backup_db import BackupManager
            manager = BackupManager()
            result = manager.create_backup()
            if result:
                logger.info("Backup automatico completado")
            else:
                logger.warning("Backup automatico falló")
        except Exception as e:
            logger.error(f"Error en backup automatico: {e}")
    
    def configure_backup_job():
        """Configura el job de backup según la configuración en BD."""
        try:
            from src.models import Setting
            from src.globals import db
            
            with app.app_context():
                enabled_setting = Setting.query.filter_by(key='auto_backup_enabled').first()
                interval_setting = Setting.query.filter_by(key='auto_backup_interval').first()
                
                is_enabled = enabled_setting and enabled_setting.value.lower() == 'true'
                hours = int(interval_setting.value) if interval_setting and interval_setting.value.isdigit() else 24
                
                # Remover job existente si hay
                if scheduler.get_job('auto_backup'):
                    scheduler.remove_job('auto_backup')
                
                if is_enabled:
                    scheduler.add_job(
                        scheduled_backup_job,
                        'interval',
                        hours=hours,
                        id='auto_backup',
                        replace_existing=True,
                        name='Backup automático de base de datos'
                    )
                    logger.info(f"Job backup automático configurado cada {hours} horas")
                else:
                    logger.info("Job backup automático deshabilitado")
        except Exception as e:
            logger.error(f"Error configurando job de backup: {e}")
    
    # Configurar backup según BD
    configure_backup_job()

    # Imprimir información de inicio
    broker_info = global_state['active_server_config'].get('broker', 'N/A')
    port_info = global_state['active_server_config'].get('port', 'N/A')
    print(f"Servidor web: http://localhost:5000")
    print(f"Servidor MQTT por defecto: {global_state['active_server_name']} ({broker_info}:{port_info})")
    print(f"Scheduler: Iniciado y en pausa")
    print("="*60)
    print("Presiona Ctrl+C para detener el servidor")
    print("="*60)

    try:
        # Crear servidor WSGI explícito para mejor control del cierre
        wsgi_server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, log=None)
        logger.info("Servidor WSGI iniciado en puerto 5000")
        
        # Iniciar en un hilo para poder monitorear la bandera de cierre
        def serve_forever():
            try:
                wsgi_server.serve_forever()
            except Exception as e:
                if not shutdown_requested:
                    logger.error(f"Error en WSGI server: {e}")
        
        server_thread = threading.Thread(target=serve_forever, daemon=True)
        server_thread.start()
        
        # Monitorear la bandera de cierre
        while not shutdown_requested:
            time.sleep(0.5)
        
        # Si llegamos aquí, se solicitó el cierre
        stop_server()
        
    except KeyboardInterrupt:
        print("Interrupcion por teclado recibida. Cerrando...")
        stop_server()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        stop_server()
        raise

if __name__ == '__main__':
    main()
