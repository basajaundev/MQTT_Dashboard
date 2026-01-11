import logging
import json
from datetime import datetime
from src.globals import db, app
from src.models import Server, Setting

logger = logging.getLogger(__name__)

def init_db():
    """Inicializa la base de datos usando SQLAlchemy."""
    try:
        # Verificar si las tablas existen, si no, crearlas
        from sqlalchemy import inspect
        
        with app.app_context():
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                logger.info("🗄️ No se detectaron tablas. Creando estructura de base de datos...")
                db.create_all()
                logger.info("🗄️ Tablas creadas correctamente.")
            
            # Crear todas las tablas definidas en los modelos (por si acaso)
            db.create_all()
        
        # Comprobar si hay servidores, si no, insertar por defecto
        if not Server.query.first():
            logger.info("🗄️ Base de datos vacía. Insertando servidores por defecto.")
            default_servers = [
                Server(name='Localhost', broker='localhost', port=1883, username='', password=''),
                Server(name='HiveMQ Public', broker='broker.hivemq.com', port=1883, username='', password=''),
                Server(name='Mosquitto Test', broker='test.mosquitto.org', port=1883, username='', password='')
            ]
            db.session.add_all(default_servers)
            
            # Configuración por defecto
            default_settings = [
                Setting(key='last_selected_server', value='Localhost'),
                Setting(key='admin_password', value='21232f297a57a5a743894a0e4a801fc3'), # MD5 de 'admin'
                Setting(key='refresh_interval', value='30'),
                Setting(key='max_missed_pings', value='2'),
                Setting(key='auto_backup_enabled', value='true'),
                Setting(key='auto_backup_interval', value='24'),
                Setting(key='auto_backup_keep', value='7')
            ]
            db.session.add_all(default_settings)
            
            db.session.commit()
            logger.info("🗄️ Datos por defecto insertados.")
        
        # Asegurar que los ajustes nuevos existan incluso si la BD no estaba vacía (migración simple)
        else:
            settings_to_check = {
                'refresh_interval': '30',
                'max_missed_pings': '2',
                'auto_backup_enabled': 'true',
                'auto_backup_interval': '24',
                'auto_backup_keep': '7',
                'toast_enabled': 'true',
                'toast_duration': '5',
                'toast_position': 'top-right',
                'toast_animation': 'fade',
                'toast_types': 'all',
                'mqtt_keepalive': '60',
                'mqtt_reconnect_delay': '5',
                'mqtt_default_qos': '1',
                'mqtt_clean_session': 'true'
            }
            changes = False
            for key, default_val in settings_to_check.items():
                if not Setting.query.get(key):
                    db.session.add(Setting(key=key, value=default_val))
                    changes = True
            
            if changes:
                db.session.commit()
                logger.info("🗄️ Nuevos ajustes por defecto añadidos a la base de datos existente.")

        logger.info("🗄️ Base de datos inicializada correctamente con SQLAlchemy.")
    except Exception as e:
        logger.error(f"❌ Error al inicializar la base de datos: {e}")
        raise

# Funciones de ayuda para JSON
def serialize_schedule_data(data):
    return json.dumps(data)

def deserialize_schedule_data(json_str):
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}
