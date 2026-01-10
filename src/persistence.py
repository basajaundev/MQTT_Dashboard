import logging
from datetime import datetime, timedelta
import hashlib

from src.globals import (
    db, config, global_state, app,
    scheduled_tasks, scheduler, devices, devices_lock # Importar devices y lock
)
from src.models import Server, Task, Subscription, Setting, SensorData, Alert, Device, Whitelist, DeviceEvent, Group, DeviceLog, MessageTrigger
from src.database import serialize_schedule_data, deserialize_schedule_data
from src.task_utils import _create_task_trigger, execute_scheduled_task

logger = logging.getLogger(__name__)

# --- Admin Authentication ---
def check_admin_password(password):
    """Comprueba si la contraseña proporcionada coincide con la del admin."""
    try:
        stored_setting = Setting.query.filter_by(key='admin_password').first()
        if not stored_setting: return False
        input_hash = hashlib.md5(password.encode()).hexdigest()
        return input_hash == stored_setting.value
    except Exception as e:
        logger.error(f"❌ Error comprobando la contraseña de admin: {e}")
        return False

def update_admin_password(new_password):
    """Actualiza la contraseña del admin en la base de datos."""
    try:
        new_hash = hashlib.md5(new_password.encode()).hexdigest()
        setting = Setting.query.filter_by(key='admin_password').first()
        if setting: setting.value = new_hash
        else: db.session.add(Setting(key='admin_password', value=new_hash))
        db.session.commit()
        logger.info("🔑 Contraseña de administrador actualizada.")
        return True
    except Exception as e:
        logger.error(f"❌ Error actualizando la contraseña de admin: {e}")
        db.session.rollback()
        return False

# --- Server Configuration ---
def load_config():
    """Carga toda la configuración (servidores y ajustes) desde la base de datos."""
    try:
        servers = Server.query.all()
        servers_data = {s.name: {c.name: getattr(s, c.name) for c in s.__table__.columns} for s in servers}
        
        settings = Setting.query.all()
        settings_data = {s.key: s.value for s in settings}
        
        defaults = {
            'refresh_interval': '30',
            'max_missed_pings': '2',
            'auto_backup_enabled': 'false',
            'auto_backup_interval': '24',
            'auto_backup_keep': '7',
            'toast_duration': '5',
            'toast_position': 'top-right',
            'toast_sound': 'true',
            'toast_animation': 'fade',
            'toast_types': 'all'
        }
        for key, default_value in defaults.items():
            if key not in settings_data:
                settings_data[key] = default_value
        
        config['servers'] = servers_data
        config['settings'] = settings_data
        
        last_server = settings_data.get('last_selected_server')
        
        if not last_server or last_server not in servers_data:
            last_server = next(iter(servers_data), None)
        
        global_state['active_server_name'] = last_server
        global_state['active_server_config'] = servers_data.get(last_server, {})
        config['last_selected_server'] = global_state['active_server_name']
        
        logger.info(f"✅ Configuración cargada. Servidor por defecto: {global_state['active_server_name']}")
    except Exception as e:
        logger.error(f"❌ Error al cargar configuración: {e}")

def save_last_selected_server():
    """Guarda solo el último servidor seleccionado en la base de datos."""
    try:
        setting = Setting.query.filter_by(key='last_selected_server').first()
        if setting: setting.value = global_state['active_server_name']
        else: db.session.add(Setting(key='last_selected_server', value=global_state['active_server_name']))
        db.session.commit()
        logger.info(f"💾 Último servidor seleccionado ('{global_state['active_server_name']}') guardado.")
    except Exception as e:
        logger.error(f"❌ Error al guardar configuración: {e}")
        db.session.rollback()

def add_server(server_data):
    """Añade un nuevo servidor a la base de datos."""
    try:
        new_server = Server(name=server_data['name'], broker=server_data['broker'], port=server_data['port'], username=server_data['username'], password=server_data['password'])
        db.session.add(new_server)
        db.session.commit()
        logger.info(f"✅ Servidor '{server_data['name']}' añadido.")
        return True
    except Exception as e:
        logger.error(f"❌ Error añadiendo servidor: {e}")
        db.session.rollback()
        return False

def update_server(server_id, server_data):
    """Actualiza un servidor existente en la base de datos."""
    try:
        server = Server.query.get(server_id)
        if server:
            server.name, server.broker, server.port, server.username, server.password = server_data['name'], server_data['broker'], server_data['port'], server_data['username'], server_data['password']
            db.session.commit()
            logger.info(f"✅ Servidor ID {server_id} actualizado.")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error actualizando servidor: {e}")
        db.session.rollback()
        return False

def delete_server(server_id):
    """Elimina un servidor y todos sus datos asociados de la base de datos."""
    try:
        server = Server.query.get(server_id)
        if server:
            db.session.delete(server)
            db.session.commit()
            logger.info(f"🗑️ Servidor ID {server_id} eliminado.")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error eliminando servidor: {e}")
        db.session.rollback()
        return False

# --- Tasks ---
def load_tasks(server_name):
    """Carga las tareas del servidor especificado desde la base de datos."""
    global scheduled_tasks
    scheduler.remove_all_jobs()
    scheduled_tasks.clear()
    
    try:
        tasks_from_db = Task.query.filter_by(server_name=server_name).all()
        for task in tasks_from_db:
            task_info = {c.name: getattr(task, c.name) for c in task.__table__.columns}
            task_info['schedule_data'] = deserialize_schedule_data(task.schedule_data)
            trigger, schedule_info = _create_task_trigger(task_info['schedule_type'], task_info['schedule_data'])
            task_info['schedule_info'] = schedule_info
            if trigger:
                scheduler.add_job(execute_scheduled_task, trigger, args=[task.id, task_info['topic'], task_info['payload']], id=task.id, name=task_info['name'])
                if not task_info.get('enabled', True): scheduler.pause_job(task.id)
                scheduled_tasks[task.id] = task_info
        logger.info(f"✅ {len(scheduled_tasks)} tarea(s) cargada(s) para '{server_name}'.")
    except Exception as e:
        logger.error(f"❌ Error al cargar tareas: {e}")

def save_tasks(server_name):
    """Guarda todas las tareas en memoria para un servidor en la base de datos."""
    try:
        Task.query.filter_by(server_name=server_name).delete()
        for task_id, task_info in scheduled_tasks.items():
            new_task = Task(
                id=task_id, 
                server_name=server_name, 
                name=task_info['name'], 
                topic=task_info['topic'], 
                payload=task_info['payload'], 
                schedule_type=task_info['schedule_type'], 
                schedule_data=serialize_schedule_data(task_info['schedule_data']), 
                enabled=task_info.get('enabled', True), 
                executions=task_info.get('executions', 0), 
                last_run=task_info.get('last_run', 'Nunca'),
                use_placeholders=task_info.get('use_placeholders', True),
                response_enabled=task_info.get('response_enabled', False),
                response_topic=task_info.get('response_topic'),
                response_timeout=task_info.get('response_timeout', 10),
                response_condition=task_info.get('response_condition'),
                response_action=task_info.get('response_action', 'log')
            )
            db.session.add(new_task)
        db.session.commit()
        logger.info(f"💾 Tareas para '{server_name}' guardadas.")
    except Exception as e:
        logger.error(f"❌ Error al guardar tareas: {e}")
        db.session.rollback()

def update_task_execution(task_id, last_run, new_executions_count):
    """Actualiza solo los campos de ejecución de una tarea específica."""
    try:
        task = Task.query.get(task_id)
        if task:
            task.last_run, task.executions = last_run, new_executions_count
            db.session.commit()
            logger.debug(f"Task {task_id} updated.")
    except Exception as e:
        logger.error(f"Error updating task execution {task_id}: {e}")
        db.session.rollback()


# --- Message Triggers ---
def load_message_triggers(server_name):
    """Carga los MessageTriggers del servidor especificado desde la base de datos."""
    from src.globals import message_triggers
    message_triggers.clear()

    try:
        triggers_from_db = MessageTrigger.query.filter_by(server_name=server_name).all()
        for trigger in triggers_from_db:
            trigger_info = {
                'id': trigger.id,
                'name': trigger.name,
                'topic_pattern': trigger.topic_pattern,
                'trigger_condition': trigger.trigger_condition,
                'action_type': trigger.action_type,
                'action_topic': trigger.action_topic,
                'action_payload': trigger.action_payload,
                'enabled': trigger.enabled,
                'trigger_count': trigger.trigger_count,
                'last_triggered': trigger.last_triggered
            }
            message_triggers[trigger.id] = trigger_info
        logger.info(f"{len(message_triggers)} message trigger(s) loaded for '{server_name}'.")
    except Exception as e:
        logger.error(f"Error loading message triggers: {e}")


def save_message_triggers(server_name):
    """Guarda todos los MessageTriggers en memoria para un servidor en la base de datos."""
    from src.globals import message_triggers

    try:
        MessageTrigger.query.filter_by(server_name=server_name).delete()
        for trigger_id, trigger_info in message_triggers.items():
            new_trigger = MessageTrigger(
                id=trigger_id,
                server_name=server_name,
                name=trigger_info['name'],
                topic_pattern=trigger_info['topic_pattern'],
                trigger_condition=trigger_info.get('trigger_condition'),
                action_type=trigger_info['action_type'],
                action_topic=trigger_info.get('action_topic'),
                action_payload=trigger_info.get('action_payload'),
                enabled=trigger_info.get('enabled', True),
                trigger_count=trigger_info.get('trigger_count', 0),
                last_triggered=trigger_info.get('last_triggered')
            )
            db.session.add(new_trigger)
        db.session.commit()
        logger.info(f"Message triggers for '{server_name}' saved.")
    except Exception as e:
        logger.error(f"Error saving message triggers: {e}")
        db.session.rollback()


def get_message_trigger(trigger_id):
    """Obtiene un MessageTrigger por su ID."""
    try:
        return MessageTrigger.query.get(trigger_id)
    except Exception as e:
        logger.error(f"Error getting message trigger {trigger_id}: {e}")
        return None


def create_message_trigger(server_name, data):
    """Crea un nuevo MessageTrigger."""
    try:
        new_trigger = MessageTrigger(
            id=data['id'],
            server_name=server_name,
            name=data['name'],
            topic_pattern=data['topic_pattern'],
            trigger_condition=data.get('trigger_condition'),
            action_type=data['action_type'],
            action_topic=data.get('action_topic'),
            action_payload=data.get('action_payload'),
            enabled=data.get('enabled', True),
            trigger_count=0
        )
        db.session.add(new_trigger)
        db.session.commit()
        logger.info(f"Message trigger created: {data['name']}")
        return True
    except Exception as e:
        logger.error(f"Error creating message trigger: {e}")
        db.session.rollback()
        return False


def update_message_trigger(trigger_id, data):
    """Actualiza un MessageTrigger existente."""
    try:
        trigger = MessageTrigger.query.get(trigger_id)
        if trigger:
            trigger.name = data.get('name', trigger.name)
            trigger.topic_pattern = data.get('topic_pattern', trigger.topic_pattern)
            trigger.trigger_condition = data.get('trigger_condition', trigger.trigger_condition)
            trigger.action_type = data.get('action_type', trigger.action_type)
            trigger.action_topic = data.get('action_topic', trigger.action_topic)
            trigger.action_payload = data.get('action_payload', trigger.action_payload)
            trigger.enabled = data.get('enabled', trigger.enabled)
            db.session.commit()
            logger.info(f"Message trigger updated: {trigger.name}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating message trigger: {e}")
        db.session.rollback()
        return False


def delete_message_trigger(trigger_id):
    """Elimina un MessageTrigger."""
    try:
        trigger = MessageTrigger.query.get(trigger_id)
        if trigger:
            trigger_name = trigger.name
            db.session.delete(trigger)
            db.session.commit()
            logger.info(f"Message trigger deleted: {trigger_name}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting message trigger: {e}")
        db.session.rollback()
        return False


def jsonpath_extract(data, path):
    """Extrae un valor de un dict usando notación de punto."""
    keys = path.split('.')
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return None
    return result

# --- Subscriptions ---
def load_subscriptions(server_name):
    """Carga las suscripciones para el servidor especificado."""
    try:
        subs = Subscription.query.filter_by(server_name=server_name).all()
        return [sub.topic for sub in subs]
    except Exception as e:
        logger.error(f"❌ Error al cargar suscripciones: {e}")
        return []

def save_subscriptions(server_name, subscriptions):
    """Guarda la lista completa de suscripciones para un servidor."""
    try:
        Subscription.query.filter_by(server_name=server_name).delete()
        for topic in subscriptions: db.session.add(Subscription(server_name=server_name, topic=topic))
        db.session.commit()
        logger.info(f"💾 Suscripciones para '{server_name}' guardadas.")
    except Exception as e:
        logger.error(f"❌ Error al guardar suscripciones: {e}")
        db.session.rollback()

# --- Sensor Data ---
def insert_sensor_data(device_id, location, data):
    """Inserta una nueva lectura de sensor."""
    try:
        new_data = SensorData(device_id=device_id, location=location, temp_c=data.get('temp_c'), temp_h=data.get('temp_h'), temp_st=data.get('temp_st'))
        db.session.add(new_data)
        db.session.commit()
        logger.debug(f"📊 Datos de sensor para '{device_id}' guardados.")
    except Exception as e:
        logger.error(f"❌ Error guardando datos de sensor: {e}")
        db.session.rollback()

def get_sensor_data_for_device(device_id, location, start_date=None, end_date=None):
    """Recupera datos de sensor para un dispositivo, con downsampling si es necesario."""
    try:
        logger.info(f"[SENSOR_DATA] get_device_id={device_id}, location={location}")
        logger.info(f"[SENSOR_DATA] start_date={start_date} (type: {type(start_date)}), end_date={end_date} (type: {type(end_date)})")
        
        query = SensorData.query.filter_by(device_id=device_id, location=location)

        if start_date and end_date and str(start_date).strip() and str(end_date).strip():
            try:
                start_of_day = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                end_of_day = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                logger.warning(f"[SENSOR_DATA] Formato de fecha inválido: start={start_date}, end={end_date}")
                since = datetime.now() - timedelta(hours=24)
                query = query.filter(SensorData.timestamp >= since)
            else:
                logger.info(f"[SENSOR_DATA] Filtrando entre {start_of_day} y {end_of_day}")
                query = query.filter(SensorData.timestamp.between(start_of_day, end_of_day))
        elif start_date and str(start_date).strip():
            try:
                start_of_day = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                end_of_day = start_of_day + timedelta(days=1, seconds=-1)
            except ValueError:
                logger.warning(f"[SENSOR_DATA] Formato de fecha inválido: start={start_date}")
                since = datetime.now() - timedelta(hours=24)
                query = query.filter(SensorData.timestamp >= since)
            else:
                logger.info(f"[SENSOR_DATA] Filtrando desde {start_of_day} hasta {end_of_day}")
                query = query.filter(SensorData.timestamp.between(start_of_day, end_of_day))
        elif end_date and str(end_date).strip():
            try:
                end_of_day = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                start_of_day = end_of_day - timedelta(days=1, seconds=-1)
            except ValueError:
                logger.warning(f"[SENSOR_DATA] Formato de fecha inválido: end={end_date}")
                since = datetime.now() - timedelta(hours=24)
                query = query.filter(SensorData.timestamp >= since)
            else:
                logger.info(f"[SENSOR_DATA] Filtrando desde {start_of_day} hasta {end_of_day}")
                query = query.filter(SensorData.timestamp.between(start_of_day, end_of_day))
        else:
            since = datetime.now() - timedelta(hours=24)
            logger.info(f"[SENSOR_DATA] Sin filtro de fecha, mostrando ultimas 24h desde {since}")
            query = query.filter(SensorData.timestamp >= since)

        results = query.order_by(SensorData.timestamp.asc()).all()

        MAX_POINTS = 1000
        total_points = len(results)

        if total_points > MAX_POINTS:
            data = []
            step = total_points / MAX_POINTS
            for i in range(MAX_POINTS):
                index = int(i * step)
                row = results[index]
                data.append({'id': row.id, 'device_id': row.device_id, 'location': row.location, 'timestamp': row.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'temp_c': row.temp_c, 'temp_h': row.temp_h, 'temp_st': row.temp_st})
            logger.info(f"Downsampling aplicado: {total_points} -> {len(data)} puntos.")
            return data
        else:
            return [{'id': row.id, 'device_id': row.device_id, 'location': row.location, 'timestamp': row.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'temp_c': row.temp_c, 'temp_h': row.temp_h, 'temp_st': row.temp_st} for row in results]
    except Exception as e:
        logger.error(f"Error recovering sensor data: {e}")
        return []


def get_device_logs(device_id, location, limit=100):
    """Recupera los logs de un dispositivo."""
    try:
        logs = DeviceLog.query.filter_by(device_id=device_id, location=location).order_by(DeviceLog.timestamp.desc()).limit(limit).all()
        return [{
            'id': log.id,
            'level': log.level,
            'message': log.message,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for log in logs]
    except Exception as e:
        logger.error(f"Error recovering device logs: {e}")
        return []


def add_device_log(device_id, location, level, message):
    """Añade un log de dispositivo."""
    try:
        new_log = DeviceLog(device_id=device_id, location=location, level=level, message=message)
        db.session.add(new_log)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving device log: {e}")
        db.session.rollback()
        return False


# --- Alerts ---
def get_alerts(server_name):
    """Recupera todas las alertas para un servidor específico."""
    try:
        alerts = Alert.query.filter_by(server_name=server_name).all()
        return [{c.name: getattr(a, c.name) for c in a.__table__.columns} for a in alerts]
    except Exception as e:
        logger.error(f"❌ Error recuperando alertas: {e}")
        return []

def add_alert(server_name, data):
    """Añade una nueva alerta."""
    try:
        new_alert = Alert(
            server_name=server_name,
            name=data['name'],
            device_id=data['device_id'],
            metric=data['metric'],
            operator=data['operator'],
            value=data['value'],
            message=data['message'],
            type=data.get('type', 'warning'),
            enabled=data.get('enabled', True)
        )
        db.session.add(new_alert)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error añadiendo alerta: {e}")
        db.session.rollback()
        return False

def update_alert(alert_id, data):
    """Actualiza una alerta existente."""
    try:
        alert = Alert.query.get(alert_id)
        if alert:
            alert.name = data['name']
            alert.device_id = data['device_id']
            alert.metric = data['metric']
            alert.operator = data['operator']
            alert.value = data['value']
            alert.message = data['message']
            alert.type = data.get('type', 'warning')
            alert.enabled = data.get('enabled', True)
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error actualizando alerta: {e}")
        db.session.rollback()
        return False

def delete_alert(alert_id):
    """Elimina una alerta."""
    try:
        alert = Alert.query.get(alert_id)
        if alert:
            db.session.delete(alert)
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error eliminando alerta: {e}")
        db.session.rollback()
        return False

# --- Device Management ---
def get_or_create_device(dev_id, dev_name, dev_location, server_name):
    """Busca un dispositivo por (id, location). Si no existe, lo crea. Devuelve (alias, fue_creado)."""
    try:
        device = Device.query.filter_by(dev_id=dev_id, dev_location=dev_location, dev_server=server_name).first()
        if device:
            display_name = device.dev_alias if device.dev_alias else device.dev_name
            return display_name, False
        else:
            new_device = Device(dev_id=dev_id, dev_name=dev_name, dev_location=dev_location, dev_server=server_name)
            db.session.add(new_device)
            db.session.commit()
            logger.info(f"🆕 Nuevo dispositivo registrado: {dev_id}@{dev_location}")
            return dev_name, True
    except Exception as e:
        logger.error(f"❌ Error gestionando dispositivo {dev_id}@{dev_location}: {e}")
        db.session.rollback()
        return dev_name, False

def update_device_alias(dev_id, dev_location, new_alias):
    """Actualiza el alias de un dispositivo específico por (id, location)."""
    try:
        device = Device.query.filter_by(dev_id=dev_id, dev_location=dev_location).first()
        if device:
            device.dev_alias = new_alias
            db.session.commit()
            logger.info(f"✏️ Alias actualizado para {dev_id}@{dev_location}: {new_alias}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error actualizando alias de dispositivo: {e}")
        db.session.rollback()
        return False

def get_all_known_devices(server_name):
    """Recupera todos los dispositivos registrados en la base de datos para un servidor."""
    try:
        devices = Device.query.filter_by(dev_server=server_name).all()
        return [{'id': d.dev_id, 'name': d.dev_name, 'location': d.dev_location, 'alias': d.dev_alias} for d in devices]
    except Exception as e:
        logger.error(f"❌ Error recuperando dispositivos conocidos: {e}")
        return []

def load_known_devices_to_memory(server_name):
    """Carga los dispositivos conocidos de la BD a la memoria con estado 'offline'."""
    try:
        known_devices = Device.query.filter_by(dev_server=server_name).all()
        with devices_lock:
            for d in known_devices:
                key = f"{d.dev_id}@{d.dev_location}"
                if key not in devices:
                    devices[key] = {
                        'id': d.dev_id,
                        'name': d.dev_alias or d.dev_name,
                        'location': d.dev_location,
                        'status': 'offline', # Estado inicial
                        'last_seen': 'Nunca',
                        'missed_pings': 0
                    }
        logger.info(f"📥 {len(known_devices)} dispositivos cargados desde BD a memoria.")
    except Exception as e:
        logger.error(f"❌ Error cargando dispositivos a memoria: {e}")

# --- Whitelist Management (Strict Mode) ---
def get_whitelist(server_name):
    """Recupera la whitelist con detalles del dispositivo y grupo."""
    try:
        results = db.session.query(Whitelist, Device, Group).outerjoin(
            Group, (Whitelist.group_id == Group.id)
        ).join(
            Device, (Whitelist.device_id == Device.dev_id) & (Whitelist.location == Device.dev_location)
        ).filter(Whitelist.server_name == server_name).all()
        
        whitelist_data = []
        for wl_item, device, group in results:
            whitelist_data.append({
                'id': device.dev_id,
                'name': device.dev_name,
                'location': device.dev_location,
                'alias': device.dev_alias,
                'group_name': group.name if group else None
            })
        return whitelist_data
    except Exception as e:
        logger.error(f"❌ Error recovering whitelist: {e}")
        return []

def add_to_whitelist(server_name, device_id, location, group_id=None):
    """Adds a device to the whitelist using (id, location)."""
    try:
        item = Whitelist(server_name=server_name, device_id=device_id, location=location, group_id=group_id)
        db.session.add(item)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

def remove_from_whitelist(server_name, device_id, location):
    """Elimina un dispositivo de la whitelist usando (id, location)."""
    try:
        Whitelist.query.filter_by(server_name=server_name, device_id=device_id, location=location).delete()
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

def is_device_allowed(server_name, device_id, location):
    """Verifica si un dispositivo está permitido (debe estar en la whitelist)."""
    if Whitelist.query.filter_by(server_name=server_name, device_id=device_id, location=location).first():
        return True 
    return False

# --- Cleanup & Scheduler Persistence ---

def cleanup_sensor_data(days=30):
    """Elimina registros de sensor_data más antiguos que el número de días especificado."""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = SensorData.query.filter(SensorData.timestamp < cutoff_date).delete()
        if deleted_count > 0:
            db.session.commit()
            logger.info(f"🧹 Limpieza de datos históricos: {deleted_count} registros eliminados (anteriores a {cutoff_date.strftime('%Y-%m-%d')}).")
        return deleted_count
    except Exception as e:
        logger.error(f"❌ Error en limpieza de datos históricos: {e}")
        db.session.rollback()
        return 0

def should_run_cleanup() -> bool:
    """Comprueba si debe ejecutarse la limpieza de datos."""
    try:
        last_cleanup = Setting.query.filter_by(key='last_cleanup_date').first()
        if not last_cleanup:
            return True
        last_cleanup_date = datetime.strptime(last_cleanup.value, '%Y-%m-%d %H:%M:%S')
        return (datetime.now() - last_cleanup_date) > timedelta(hours=24)
    except Exception as e:
        logger.error(f"❌ Error comprobando fecha de cleanup: {e}")
        return True

def update_cleanup_timestamp():
    """Actualiza la fecha del último cleanup."""
    try:
        setting = Setting.query.filter_by(key='last_cleanup_date').first()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if setting:
            setting.value = now_str
        else:
            db.session.add(Setting(key='last_cleanup_date', value=now_str))
        db.session.commit()
    except Exception as e:
        logger.error(f"❌ Error actualizando fecha de cleanup: {e}")
        db.session.rollback()

def save_scheduler_state():
    """Guarda el estado actual del scheduler (jobs activos) en la base de datos."""
    try:
        with app.app_context():
            jobs_data = []
            for job in scheduler.get_jobs():
                job_data = {
                    'id': job.id,
                    'name': job.name,
                    'trigger_type': str(job.trigger)[0:50],
                    'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job and job.next_run_time else 'Pausada'
                }
                jobs_data.append(job_data)
            
            jobs_json = str(jobs_data)
            setting = Setting.query.filter_by(key='scheduler_jobs').first()
            if setting:
                setting.value = jobs_json
            else:
                db.session.add(Setting(key='scheduler_jobs', value=jobs_json))
            
            # Verificar estado del scheduler de forma segura
            # Cuando scheduler.start(paused=True) se usa, el atributo 'paused' no existe después de iniciar
            try:
                is_paused = getattr(scheduler, 'paused', False) or not scheduler.running
            except:
                is_paused = False
            
            paused_state = 'true' if is_paused else 'false'
            paused_setting = Setting.query.filter_by(key='scheduler_paused').first()
            if paused_setting:
                paused_setting.value = paused_state
            else:
                db.session.add(Setting(key='scheduler_paused', value=paused_state))
            
            db.session.commit()
            logger.info(f"💾 Estado del scheduler guardado: {len(jobs_data)} job(s).")
    except Exception as e:
        logger.error(f"❌ Error guardando estado del scheduler: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass

# --- Device Events ---

def add_device_event(device_id, location, event_type, details=None):
    """Registra un evento de dispositivo."""
    try:
        with app.app_context():
            new_event = DeviceEvent(
                device_id=device_id,
                location=location,
                event_type=event_type,
                details=details
            )
            db.session.add(new_event)
            db.session.commit()
            logger.debug(f"📝 Evento registrado: {event_type} para {device_id}@{location}")
    except Exception as e:
        logger.error(f"❌ Error registrando evento de dispositivo: {e}")
        db.session.rollback()

def get_device_events(device_id, location, limit=100, event_type=None, offset=0):
    """Obtiene el historial de eventos de un dispositivo."""
    try:
        query = DeviceEvent.query.filter_by(device_id=device_id, location=location)
        if event_type:
            query = query.filter_by(event_type=event_type)
        events = query.order_by(DeviceEvent.timestamp.desc()).offset(offset).limit(limit).all()
        return [{
            'id': e.id,
            'device_id': e.device_id,
            'location': e.location,
            'event_type': e.event_type,
            'details': e.details,
            'timestamp': e.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for e in events]
    except Exception as e:
        logger.error(f"❌ Error obteniendo eventos de dispositivo: {e}")
        return []

def cleanup_old_events(days=30):
    """Elimina eventos antiguos."""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = DeviceEvent.query.filter(DeviceEvent.timestamp < cutoff_date).delete()
        if deleted_count > 0:
            db.session.commit()
            logger.info(f"🧹 Limpieza de eventos: {deleted_count} registros eliminados.")
        return deleted_count
    except Exception as e:
        logger.error(f"❌ Error en limpieza de eventos: {e}")
        db.session.rollback()
        return 0

def get_device_detail(device_id, location, server_name):
    """Obtiene toda la información de detalle de un dispositivo."""
    try:
        with app.app_context():
            detail = {
                'device_id': device_id,
                'location': location,
                'server_name': server_name,
                'info': None,
                'group': None,
                'events': [],
                'sensors': [],
                'last_seen': None,
                'status': 'unknown',
                'latency': None,
                'ip': None,
                'uptime': None,
                'alias': device_id
            }

            device = Device.query.filter_by(dev_id=device_id, dev_location=location).first()
            if device:
                detail['alias'] = device.dev_alias or device.dev_name
                detail['info'] = {
                    'id': device.dev_id,
                    'name': device.dev_name,
                    'alias': device.dev_alias,
                    'location': device.dev_location
                }

            device_key = f"{device_id}@{location}"
            with devices_lock:
                if device_key in devices:
                    dev_data = devices[device_key]
                    detail['ip'] = dev_data.get('ip')
                    detail['uptime'] = dev_data.get('uptime')
                    detail['latency'] = dev_data.get('latency')
                    detail['status'] = dev_data.get('status', 'unknown')
                    detail['last_seen'] = dev_data.get('last_seen')
                    detail['firmware'] = dev_data.get('firmware', 'Unknown')
                    detail['mac'] = dev_data.get('mac', 'N/A')
                    detail['heap'] = dev_data.get('heap', 0)
                    detail['chip_id'] = dev_data.get('chip_id', 'N/A')

                    # Sensor data (if available)
                    if dev_data.get('temp_c') is not None:
                        detail['sensor'] = {
                            'temp_c': dev_data.get('temp_c'),
                            'temp_h': dev_data.get('temp_h'),
                            'temp_st': dev_data.get('temp_st'),
                            'last_read': dev_data.get('last_read')
                        }

            whitelist = Whitelist.query.filter_by(device_id=device_id, location=location, server_name=server_name).first()
            if whitelist and whitelist.group_id:
                group = Group.query.get(whitelist.group_id)
                if group:
                    detail['group'] = {'id': group.id, 'name': group.name}

            events = DeviceEvent.query.filter_by(device_id=device_id, location=location).order_by(DeviceEvent.timestamp.desc()).limit(50).all()
            detail['events'] = [{
                'id': e.id,
                'event_type': e.event_type,
                'details': e.details,
                'timestamp': e.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            } for e in events]

            sensors = SensorData.query.filter_by(device_id=device_id, location=location).order_by(SensorData.timestamp.desc()).limit(100).all()
            detail['sensors'] = [{
                'timestamp': s.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'temp_c': s.temp_c,
                'temp_h': s.temp_h,
                'temp_st': s.temp_st
            } for s in sensors]

            return detail
    except Exception as e:
        logger.error(f"Error getting device detail: {e}")
        return None

# --- Groups Management ---

def get_groups(server_name):
    """Obtiene todos los grupos activos de un servidor."""
    try:
        groups = Group.query.filter_by(server_name=server_name, active=True).all()
        return [{'id': g.id, 'name': g.name, 'server_name': g.server_name} for g in groups]
    except Exception as e:
        logger.error(f"❌ Error getting groups: {e}")
        return []

def add_group(server_name, data):
    """Añade un nuevo grupo."""
    try:
        new_group = Group(server_name=server_name, name=data['name'], active=True)
        db.session.add(new_group)
        db.session.commit()
        logger.info(f"Grupo '{data['name']}' creado")
        return True
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        db.session.rollback()
        return False

def update_group(group_id, data):
    """Actualiza un grupo existente."""
    try:
        group = Group.query.get(group_id)
        if group:
            group.name = data['name']
            db.session.commit()
            logger.info(f"Grupo {group_id} actualizado")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating group: {e}")
        db.session.rollback()
        return False

def delete_group(group_id):
    """Elimina un grupo (soft delete)."""
    try:
        group = Group.query.get(group_id)
        if group:
            group.active = False
            db.session.commit()
            logger.info(f"Grupo {group_id} eliminado")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        db.session.rollback()
        return False

# --- Known Devices ---
