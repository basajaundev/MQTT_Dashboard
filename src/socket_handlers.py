import logging
import json
import time
import uuid
from datetime import datetime
from flask import session
from flask_socketio import emit
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

from src.globals import (
    socketio, mqtt_state, global_state, config, db,
    subscribed_topics, scheduled_tasks, message_triggers, devices, devices_lock,
    scheduler, message_history, alerts,
    DEVICE_PING_TOPIC, DEVICE_CMD_TOPIC_PREFIX, DEVICE_CMD_BROADCAST_TOPIC
)
from src.models import Setting
from src.persistence import (
    load_config, save_last_selected_server,
    add_server, update_server, delete_server,
    save_subscriptions, save_tasks, get_sensor_data_for_device,
    get_alerts, add_alert, update_alert, delete_alert,
    update_admin_password, update_device_alias,
    get_whitelist, add_to_whitelist, remove_from_whitelist,
    get_all_known_devices,
    load_known_devices_to_memory,
    get_device_events, get_device_detail,
    get_groups, add_group, update_group, delete_group,
    get_device_logs,
    load_message_triggers, save_message_triggers,
    create_message_trigger, update_message_trigger, delete_message_trigger
)
from src.mqtt_callbacks import on_connect, on_disconnect, on_message, add_message_to_history


def send_notification(title, body, notification_type='info', tag='general'):
    """Envía una notificación a todos los clientes conectados."""
    socketio.emit('new_notification', {
        'title': title,
        'body': body,
        'type': notification_type,
        'tag': tag
    })


def notify_device_connected(device_key, latency=None):
    """Notifica conexión de dispositivo."""
    title = f"Dispositivo conectado"
    body = device_key
    if latency:
        body += f" (Latencia: {latency:.0f}ms)"
    send_notification(title, body, 'connected', f'device_{device_key}')


def notify_device_disconnected(device_key):
    """Notifica desconexión de dispositivo."""
    send_notification(
        "Dispositivo desconectado",
        device_key,
        'disconnected',
        f'device_{device_key}'
    )


def notify_alert_triggered(device_id, location, alert_name, message):
    """Notifica alerta triggered."""
    send_notification(
        f"Alerta: {alert_name}",
        f"{device_id}@{location}: {message}",
        'alert',
        f'alert_{device_id}_{location}'
    )


def notify_device_reboot(device_key):
    """Notifica reinicio de dispositivo."""
    send_notification(
        "Reiniciando dispositivo",
        device_key,
        'reboot',
        f'reboot_{device_key}'
    )


def notify_mqtt_error(error_msg):
    """Notifica error de MQTT."""
    send_notification(
        "Error de conexión MQTT",
        error_msg,
        'error',
        'mqtt_error'
    )


def notify_whitelist_add(device_key):
    """Notifica nuevo dispositivo en whitelist."""
    send_notification(
        "Nuevo dispositivo en whitelist",
        device_key,
        'info',
        f'whitelist_{device_key}'
    )
from src.task_utils import _create_task_trigger, execute_scheduled_task
from src.validation import validate_topic, validate_payload, validate_device_id, validate_location

logger = logging.getLogger(__name__)

def get_current_state():
    """Devuelve un diccionario con el estado actual de la aplicación."""
    is_mqtt_connected = mqtt_state['client'] is not None and mqtt_state['client'].is_connected()
    server_name = global_state['active_server_name']
    
    current_alerts = []
    if is_mqtt_connected and server_name != "N/A":
        current_alerts = get_alerts(server_name)

    with devices_lock:
        current_devices = devices.copy()

    return {
        'mqtt_status': {'connected': is_mqtt_connected},
        'topics': subscribed_topics,
        'tasks': get_tasks_info(),
        'devices': current_devices,
        'config': config,
        'history': message_history,
        'alerts': current_alerts,
        'is_admin': session.get('is_admin', False),
        'access_lists': {
            'whitelist': get_whitelist(server_name) if server_name != "N/A" else []
        },
        'known_devices': get_all_known_devices(server_name) if server_name != "N/A" else [],
        'groups': get_groups(server_name) if server_name != "N/A" else []
    }

def broadcast_full_update():
    """Recarga la configuración y la envía a todos los clientes."""
    load_config()
    state = get_current_state()
    # En lugar de emitir eventos individuales, podríamos emitir un solo 'state_update'
    socketio.emit('state_update', state)
    logger.info("📢 Configuración actualizada y enviada a todos los clientes.")

@socketio.on('connect')
def handle_connect(auth=None):
    """Manejador para cuando un cliente WebSocket se conecta."""
    logger.info('🔌 Cliente WebSocket conectado')
    
    if not config.get('servers'):
        logger.info("Configuración vacía, recargando desde la base de datos...")
        load_config()
        if not devices and global_state['active_server_name'] != "N/A":
            load_known_devices_to_memory(global_state['active_server_name'])

    # CORRECCIÓN: Enviar un único evento con todo el estado
    state = get_current_state()
    emit('state_update', state)

@socketio.on('request_initial_state')
def handle_request_initial_state():
    """Maneja la solicitud explícita de estado desde el frontend."""
    
    if not config.get('servers'):
        logger.info("Configuración vacía, recargando desde la base de datos...")
        load_config()
        if not devices and global_state['active_server_name'] != "N/A":
            load_known_devices_to_memory(global_state['active_server_name'])

    # CORRECCIÓN: Enviar un único evento con todo el estado
    state = get_current_state()
    emit('state_update', state)

@socketio.on('clear_message_history')
def handle_clear_message_history():
    if not session.get('is_admin'): return
    message_history.clear()
    logger.info("🗑️ Historial de mensajes limpiado.")
    emit('history_update', {'history': []}, broadcast=True)

@socketio.on('ping_all_devices')
def handle_ping_all_devices():
    client = mqtt_state.get('client')
    if not (client and client.is_connected()): return

    logger.info("📢 Iniciando actualización de dispositivos...")
    with devices_lock:
        for device_key in devices:
            devices[device_key]['status'] = 'offline'
        socketio.emit('devices_update', {'devices': devices})
    
    ping_command = json.dumps({"cmd": "PING", "time": int(time.time())})
    client.publish(DEVICE_PING_TOPIC, ping_command)
    status_command = json.dumps({"cmd": "STATUS"})
    client.publish(DEVICE_CMD_BROADCAST_TOPIC, status_command)
    
    add_message_to_history('SISTEMA', '📢 Actualización completa solicitada...', direction='out')

    def final_check():
        socketio.sleep(3)
        with devices_lock:
            socketio.emit('devices_update', {'devices': devices})
    socketio.start_background_task(final_check)

@socketio.on('request_single_device_status')
def handle_request_single_device_status(data):
    if not session.get('is_admin'): return
    client = mqtt_state.get('client')
    if client and client.is_connected():
        device_id, location = data.get('device_id'), data.get('location')
        valid_id, id_error = validate_device_id(device_id)
        valid_loc, loc_error = validate_location(location)
        if not valid_id or not valid_loc:
            logger.warning(f"Intento de solicitar estado con datos inválidos: {device_id}@{location}")
            return
        if device_id and location:
            topic = f"{DEVICE_CMD_TOPIC_PREFIX}/{device_id}/{location}"
            command = json.dumps({"cmd": "STATUS"})
            client.publish(topic, command)
            logger.info(f"📢 Solicitando estado al dispositivo: {topic}")
            add_message_to_history('SISTEMA', f'📢 Solicitando estado a <code>{topic}</code>', direction='out')

@socketio.on('request_device_config')
def handle_request_device_config(data):
    """Solicitar configuración a un dispositivo específico."""
    if not session.get('is_admin'): return
    client = mqtt_state.get('client')
    if client and client.is_connected():
        device_id, location = data.get('device_id'), data.get('location')
        valid_id, id_error = validate_device_id(device_id)
        valid_loc, loc_error = validate_location(location)
        if not valid_id or not valid_loc:
            logger.warning(f"Intento de solicitar config con datos inválidos: {device_id}@{location}")
            return
        if device_id and location:
            topic = f"{DEVICE_CMD_TOPIC_PREFIX}/{device_id}/{location}"
            command = json.dumps({"cmd": "GET_CONFIG"})
            client.publish(topic, command)
            logger.info(f"⚙️ Solicitando configuración al dispositivo: {topic}")
            add_message_to_history('SISTEMA', f'⚙️ Solicitando configuración a <code>{topic}</code>', direction='out')

@socketio.on('reboot_device')
def handle_reboot_device(data):
    if not session.get('is_admin'): return
    client = mqtt_state.get('client')
    if client and client.is_connected():
        device_id, location = data.get('device_id'), data.get('location')
        valid_id, id_error = validate_device_id(device_id)
        valid_loc, loc_error = validate_location(location)
        if not valid_id or not valid_loc:
            logger.warning(f"Intento de reiniciar con datos inválidos: {device_id}@{location}")
            return
        if device_id and location:
            topic = f"{DEVICE_CMD_TOPIC_PREFIX}/{device_id}/{location}"
            command = json.dumps({"cmd": "REBOOT"})
            logger.info(f"🔥 Enviando comando REBOOT a: {topic}")
            client.publish(topic, command)
            add_message_to_history('SISTEMA', f'🔥 Comando REBOOT enviado a <code>{topic}</code>', direction='out')

@socketio.on('get_device_history')
def handle_get_device_history(data):
    device_id = data.get('device_id')
    location = data.get('location')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    logger.info(f"[HISTORY] Solicitud: device={device_id}@{location}, start={start_date}, end={end_date}")
    
    if device_id and location:
        history_data = get_sensor_data_for_device(device_id, location, start_date, end_date)
        logger.info(f"[HISTORY] Respuesta: {len(history_data)} registros")
        emit('device_history_response', {'device_id': device_id, 'history': history_data})


@socketio.on('get_device_logs')
def handle_get_device_logs(data):
    if not session.get('is_admin'): return
    device_id, location = data.get('device_id'), data.get('location')
    limit = data.get('limit', 100)
    if device_id and location:
        logs = get_device_logs(device_id, location, limit)
        emit('device_logs_response', {'device_id': device_id, 'logs': logs})


@socketio.on('update_device_alias')
def handle_update_device_alias(data):
    if not session.get('is_admin'): return
    device_id, location, new_alias = data.get('device_id'), data.get('location'), data.get('new_alias')
    
    if device_id and location and new_alias:
        if update_device_alias(device_id, location, new_alias):
            device_key = f"{device_id}@{location}"
            with devices_lock:
                if device_key in devices:
                    devices[device_key]['name'] = new_alias
                    emit('devices_update', {'devices': devices}, broadcast=True)
            add_message_to_history('SISTEMA', f"✏️ Alias actualizado para {device_key}: {new_alias}")
        else:
            logger.error(f"❌ Error al actualizar alias para {device_id}@{location}")

# --- Access Control Handlers ---
@socketio.on('add_to_whitelist')
def handle_add_to_whitelist(data):
    if not session.get('is_admin'): return
    device_id, location = data.get('device_id'), data.get('location')
    group_id = data.get('group_id')
    if device_id and location and add_to_whitelist(global_state['active_server_name'], device_id, location, group_id):
        broadcast_full_update()

@socketio.on('remove_from_whitelist')
def handle_remove_from_whitelist(data):
    if not session.get('is_admin'): return
    device_id, location = data.get('device_id'), data.get('location')
    if device_id and location and remove_from_whitelist(global_state['active_server_name'], device_id, location):
        device_key = f"{device_id}@{location}"
        with devices_lock:
            if device_key in devices:
                del devices[device_key]
        broadcast_full_update()

@socketio.on('mqtt_connect')
def handle_mqtt_connect(data):
    if not session.get('is_admin'): return
    _internal_mqtt_connect(data)

def _internal_mqtt_connect(data):
    """Lógica interna de conexión MQTT (sin chequeo de sesión para uso interno)."""
    if mqtt_state.get('client'):
        mqtt_state['client'].loop_stop()
        mqtt_state['client'].disconnect()
        socketio.sleep(0.1)

    with devices_lock:
        devices.clear()
    
    server_name = data.get('server_name')
    if server_name and server_name in config.get('servers', {}):
        global_state['active_server_name'] = server_name
        global_state['active_server_config'] = config['servers'][server_name]
    else:
        return

    try:
        client_userdata = {'server_name': global_state['active_server_name']}
        client_id = f"flask-mqtt-dashboard-{uuid.uuid4()}"
        new_client = mqtt.Client(client_id=client_id, callback_api_version=CallbackAPIVersion.VERSION2, userdata=client_userdata)
        new_client.on_connect = on_connect
        new_client.on_disconnect = on_disconnect
        new_client.on_message = on_message
        
        if global_state['active_server_config'].get('username'):
            new_client.username_pw_set(global_state['active_server_config']['username'], global_state['active_server_config'].get('password'))
        
        new_client.connect(global_state['active_server_config']['broker'], global_state['active_server_config']['port'], 60)
        new_client.loop_start()
        
        new_client.reconnect_delay_set(min_delay=10, max_delay=60)
        
        mqtt_state['client'] = new_client
        mqtt_state['auto_reconnect'] = True
        save_last_selected_server()
        logger.info(f"🔄 Conectado a {global_state['active_server_config']['broker']}:{global_state['active_server_config']['port']} (Servidor: {global_state['active_server_name']})")
    except Exception as e:
        logger.error(f"❌ Error al conectar: {e}")
        emit('mqtt_status', {'connected': False, 'message': f'❌ Error: {str(e)}', 'timestamp': datetime.now().strftime('%H:%M:%S')})

@socketio.on('mqtt_disconnect')
def handle_mqtt_disconnect():
    if not session.get('is_admin'): return
    client = mqtt_state.get('client')
    if client:
        mqtt_state['user_disconnected'] = True
        mqtt_state['auto_reconnect'] = False
        client.loop_stop()
        client.disconnect()
        socketio.emit('mqtt_status', {'connected': False})

# --- Server Management Handlers ---
@socketio.on('add_server')
def handle_add_server(data):
    if not session.get('is_admin'): return
    if add_server(data):
        broadcast_full_update()

@socketio.on('update_server')
def handle_update_server(data):
    if not session.get('is_admin'): return
    if update_server(data['id'], data):
        broadcast_full_update()

@socketio.on('delete_server')
def handle_delete_server(data):
    if not session.get('is_admin'): return
    if delete_server(data['id']):
        broadcast_full_update()

# --- Settings Handler ---
@socketio.on('save_settings')
def handle_save_settings(data):
    if not session.get('is_admin'): return
    logger.info(f"💾 Recibida petición para guardar ajustes: {data}")
    try:
        for key, value in data.items():
            if key == 'whitelist_mode': continue

            if isinstance(value, bool):
                str_value = 'true' if value else 'false'
            else:
                str_value = str(value)
                
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                logger.info(f"   Actualizando {key}: {setting.value} -> {str_value}")
                setting.value = str_value
            else:
                logger.info(f"   Creando nuevo ajuste {key}: {str_value}")
                db.session.add(Setting(key=key, value=str_value))
        
        db.session.commit()
        logger.info(f"⚙️ Ajustes guardados exitosamente en BD.")
        broadcast_full_update()
    except Exception as e:
        logger.error(f"❌ Error guardando ajustes: {e}", exc_info=True)
        db.session.rollback()

@socketio.on('change_password')
def handle_change_password(data):
    if not session.get('is_admin'): return
    new_password = data.get('new_password')
    if new_password:
        if update_admin_password(new_password):
            emit('password_changed', {'success': True})
        else:
            emit('password_changed', {'success': False, 'message': 'Error al actualizar en BD'})

# --- Alert Handlers ---
@socketio.on('add_alert')
def handle_add_alert(data):
    if not session.get('is_admin'): return
    if add_alert(global_state['active_server_name'], data):
        broadcast_full_update()

@socketio.on('update_alert')
def handle_update_alert(data):
    if not session.get('is_admin'): return
    if update_alert(data['id'], data):
        broadcast_full_update()

@socketio.on('delete_alert')
def handle_delete_alert(data):
    if not session.get('is_admin'): return
    if delete_alert(data['id']):
        broadcast_full_update()

# --- Group Handlers ---
@socketio.on('add_group')
def handle_add_group(data):
    if not session.get('is_admin'): return
    if add_group(global_state['active_server_name'], data):
        broadcast_full_update()

@socketio.on('update_group')
def handle_update_group(data):
    if not session.get('is_admin'): return
    if update_group(data['id'], data):
        broadcast_full_update()

@socketio.on('delete_group')
def handle_delete_group(data):
    if not session.get('is_admin'): return
    if delete_group(data['id']):
        broadcast_full_update()

# --- Subscription Handlers ---
@socketio.on('mqtt_subscribe')
def handle_mqtt_subscribe(data):
    if not session.get('is_admin'): return
    topic = data.get('topic')
    valid, error = validate_topic(topic)
    if not valid:
        logger.warning(f"Intento de suscripción con topic inválido: {topic} - {error}")
        emit('error', {'message': f'Topic inválido: {error}'})
        return
    client = mqtt_state.get('client')
    if client and client.is_connected() and topic and topic not in subscribed_topics:
        client.subscribe(topic)
        subscribed_topics.append(topic)
        save_subscriptions(global_state['active_server_name'], subscribed_topics)
        add_message_to_history('SISTEMA', f'✅ Suscrito a {topic}')
        emit('topics_update', {'topics': subscribed_topics}, broadcast=True)

@socketio.on('mqtt_unsubscribe')
def handle_mqtt_unsubscribe(data):
    if not session.get('is_admin'): return
    topic = data.get('topic')
    valid, error = validate_topic(topic)
    if not valid:
        logger.warning(f"Intento de desuscripción con topic inválido: {topic} - {error}")
        return
    client = mqtt_state.get('client')
    if client and topic and topic in subscribed_topics:
        client.unsubscribe(topic)
        subscribed_topics.remove(topic)
        save_subscriptions(global_state['active_server_name'], subscribed_topics)
        add_message_to_history('SISTEMA', f'⚠️ Desuscrito de {topic}')
        emit('topics_update', {'topics': subscribed_topics}, broadcast=True)


# --- Device Events Handler ---
@socketio.on('get_device_events')
def handle_get_device_events(data):
    if not session.get('is_admin'): return
    device_id = data.get('device_id')
    location = data.get('location')
    limit = data.get('limit', 100)
    page = data.get('page', 1)
    event_type = data.get('event_type')
    offset = (page - 1) * limit
    
    if not device_id or not location:
        emit('error', {'message': 'device_id y location son requeridos'})
        return
    
    events = get_device_events(device_id, location, limit, event_type, offset)
    emit('device_events_response', {
        'device_id': device_id,
        'location': location,
        'events': events
    })

# --- Publish Handler ---
@socketio.on('mqtt_publish')
def handle_mqtt_publish(data):
    if not session.get('is_admin'): return
    topic = data.get('topic')
    payload = data.get('payload', '')
    valid_topic, topic_error = validate_topic(topic)
    valid_payload, payload_error = validate_payload(payload)
    if not valid_topic:
        logger.warning(f"Intento de publicación con topic inválido: {topic}")
        emit('error', {'message': f'Topic inválido: {topic_error}'})
        return
    if not valid_payload:
        logger.warning(f"Intento de publicación con payload demasiado grande: {len(str(payload))} bytes")
        emit('error', {'message': f'Payload inválido: {payload_error}'})
        return
    client = mqtt_state.get('client')
    if client and client.is_connected() and topic:
        client.publish(topic, payload)
        add_message_to_history('SISTEMA', f'📤Publicado en {topic}: {payload}', force=True, direction='out')
        add_message_to_history('SISTEMA', f'📤Publicado en {topic}: {payload}', force=True, direction='out')

# --- Task Handlers ---
def get_tasks_info():
    tasks_info = []
    for task_id, task_data in scheduled_tasks.items():
        job = scheduler.get_job(task_id)
        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job and job.next_run_time else 'Pausada'
        task_info_copy = task_data.copy()
        task_info_copy['id'] = task_id
        task_info_copy['next_run'] = next_run
        tasks_info.append(task_info_copy)
    return tasks_info

@socketio.on('task_create')
def handle_task_create(data):
    if not session.get('is_admin'): return
    try:
        task_id = str(uuid.uuid4())
        trigger, schedule_info = _create_task_trigger(data['schedule_type'], data['schedule_data'])
        if not trigger: raise ValueError("Tipo de schedule inválido")
        scheduler.add_job(execute_scheduled_task, trigger, args=[task_id, data['topic'], data['payload']], id=task_id, name=data['name'])
        scheduled_tasks[task_id] = {**data, 'schedule_info': schedule_info, 'enabled': True, 'executions': 0, 'last_run': 'Nunca'}
        save_tasks(global_state['active_server_name'])
        add_message_to_history('SISTEMA', f"✅ Tarea creada: {data['name']}")
        emit('task_update', {'tasks': get_tasks_info()}, broadcast=True)
    except Exception as e:
        logger.error(f"❌ Error al crear tarea: {e}")
        add_message_to_history('ERROR', f"❌ Error al crear tarea: {e}")

@socketio.on('task_delete')
def handle_task_delete(data):
    if not session.get('is_admin'): return
    task_id = data.get('task_id')
    if task_id in scheduled_tasks:
        task_name = scheduled_tasks.pop(task_id)['name']
        if scheduler.get_job(task_id):
            scheduler.remove_job(task_id)
        save_tasks(global_state['active_server_name'])
        add_message_to_history('SISTEMA', f"🗑️ Tarea eliminada: {task_name}")
        emit('task_update', {'tasks': get_tasks_info()}, broadcast=True)

@socketio.on('task_toggle')
def handle_task_toggle(data):
    if not session.get('is_admin'): return
    task_id = data.get('task_id')
    if task_id in scheduled_tasks and scheduler.get_job(task_id):
        task = scheduled_tasks[task_id]
        task['enabled'] = not task.get('enabled', True)
        status = 'activada' if task['enabled'] else 'pausada'
        if task['enabled']:
            scheduler.resume_job(task_id)
        else:
            scheduler.pause_job(task_id)
        save_tasks(global_state['active_server_name'])
        add_message_to_history('SISTEMA', f"⏯️ Tarea {status}: {task['name']}")
        emit('task_update', {'tasks': get_tasks_info()}, broadcast=True)

@socketio.on('task_edit')
def handle_task_edit(data):
    if not session.get('is_admin'): return
    try:
        task_id = data.get('task_id')
        if task_id not in scheduled_tasks: raise ValueError("Tarea no encontrada")
        if scheduler.get_job(task_id):
            scheduler.remove_job(task_id)
        trigger, schedule_info = _create_task_trigger(data['schedule_type'], data['schedule_data'])
        if not trigger: raise ValueError("Tipo de schedule inválido")
        scheduler.add_job(execute_scheduled_task, trigger, args=[task_id, data['topic'], data['payload']], id=task_id, name=data['name'])
        scheduled_tasks[task_id].update({**data, 'schedule_info': schedule_info, 'enabled': True})
        save_tasks(global_state['active_server_name'])
        add_message_to_history('SISTEMA', f"✏️ Tarea editada: {data['name']}")
        emit('task_update', {'tasks': get_tasks_info()}, broadcast=True)
    except Exception as e:
        logger.error(f"❌ Error al editar tarea: {e}")
        add_message_to_history('ERROR', f"Error editing task: {e}")


@socketio.on('message_trigger_create')
def handle_message_trigger_create(data):
    if not session.get('is_admin'): return
    try:
        trigger_id = str(uuid.uuid4())
        if create_message_trigger(global_state['active_server_name'], {**data, 'id': trigger_id}):
            load_message_triggers(global_state['active_server_name'])
            add_message_to_history('SYSTEM', f"Message trigger created: {data['name']}")
            emit('message_triggers_update', {'triggers': list(message_triggers.values())}, broadcast=True)
    except Exception as e:
        logger.error(f"Error creating message trigger: {e}")
        add_message_to_history('ERROR', f"Error creating message trigger: {e}")


@socketio.on('message_trigger_edit')
def handle_message_trigger_edit(data):
    if not session.get('is_admin'): return
    try:
        trigger_id = data.get('trigger_id')
        if update_message_trigger(trigger_id, data):
            if trigger_id in message_triggers:
                message_triggers[trigger_id].update(data)
            save_message_triggers(global_state['active_server_name'])
            add_message_to_history('SYSTEM', f"Message trigger edited: {data['name']}")
            emit('message_triggers_update', {'triggers': list(message_triggers.values())}, broadcast=True)
    except Exception as e:
        logger.error(f"Error editing message trigger: {e}")
        add_message_to_history('ERROR', f"Error editing message trigger: {e}")


@socketio.on('message_trigger_delete')
def handle_message_trigger_delete(data):
    if not session.get('is_admin'): return
    try:
        trigger_id = data.get('trigger_id')
        if trigger_id in message_triggers:
            trigger_name = message_triggers[trigger_id]['name']
            del message_triggers[trigger_id]
        if delete_message_trigger(trigger_id):
            save_message_triggers(global_state['active_server_name'])
            add_message_to_history('SYSTEM', f"Message trigger deleted: {trigger_name}")
            emit('message_triggers_update', {'triggers': list(message_triggers.values())}, broadcast=True)
    except Exception as e:
        logger.error(f"Error deleting message trigger: {e}")
        add_message_to_history('ERROR', f"Error deleting message trigger: {e}")


@socketio.on('message_trigger_toggle')
def handle_message_trigger_toggle(data):
    if not session.get('is_admin'): return
    try:
        trigger_id = data.get('trigger_id')
        if trigger_id in message_triggers:
            trigger = message_triggers[trigger_id]
            trigger['enabled'] = not trigger.get('enabled', True)
            status = 'enabled' if trigger['enabled'] else 'disabled'
            update_message_trigger(trigger_id, {'enabled': trigger['enabled']})
            save_message_triggers(global_state['active_server_name'])
            add_message_to_history('SYSTEM', f"Message trigger {status}: {trigger['name']}")
            emit('message_triggers_update', {'triggers': list(message_triggers.values())}, broadcast=True)
    except Exception as e:
        logger.error(f"Error toggling message trigger: {e}")


@socketio.on('get_device_detail')
def handle_get_device_detail(data):
    if not session.get('is_admin'): return
    device_id = data.get('device_id')
    location = data.get('location')
    if not device_id or not location:
        emit('error', {'message': 'device_id y location son requeridos'})
        return
    detail = get_device_detail(device_id, location, global_state['active_server_name'])
    if detail:
        emit('device_detail_response', detail)
    else:
        emit('error', {'message': 'No se pudo obtener el detalle del dispositivo'})


# --- Backup Handlers ---
@socketio.on('request_backups')
def handle_request_backups():
    """Solicitar lista de backups disponibles."""
    if not session.get('is_admin'): return
    
    try:
        from backup_db import BackupManager
        manager = BackupManager()
        backups = manager.get_backups_for_ui()
        
        emit('backups_list', {'backups': backups})
        logger.info(f"📁 Enviando lista de {len(backups)} backups")
    except Exception as e:
        logger.error(f"❌ Error obteniendo lista de backups: {e}")
        emit('backups_list', {'backups': []})


@socketio.on('trigger_backup')
def handle_trigger_backup():
    """Trigger backup manual."""
    if not session.get('is_admin'): return
    
    try:
        from backup_db import BackupManager
        manager = BackupManager()
        result = manager.create_backup()
        
        if result:
            backups = manager.get_backups_for_ui()
            emit('backup_complete', {'success': True, 'backups': backups})
            add_message_to_history('SISTEMA', '✅ Backup manual completado')
            logger.info("✅ Backup manual completado")
        else:
            emit('backup_complete', {'success': False})
    except Exception as e:
        logger.error(f"❌ Error en backup manual: {e}")
        emit('backup_complete', {'success': False})


@socketio.on('update_backup_config')
def handle_update_backup_config(data):
    """Actualizar configuración de backup y reconfigurar scheduler."""
    if not session.get('is_admin'): return
    
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
    
    try:
        from src.globals import scheduler, app
        from src.models import Setting
        
        enabled = data.get('auto_backup_enabled', False)
        interval = data.get('auto_backup_interval', 24)
        
        with app.app_context():
            enabled_setting = Setting.query.filter_by(key='auto_backup_enabled').first()
            interval_setting = Setting.query.filter_by(key='auto_backup_interval').first()
            keep_setting = Setting.query.filter_by(key='auto_backup_keep').first()
            
            if enabled_setting:
                enabled_setting.value = 'true' if enabled else 'false'
            if interval_setting:
                interval_setting.value = str(interval)
            if keep_setting:
                keep_setting.value = str(data.get('auto_backup_keep', 7))
            
            db.session.commit()
            
            if scheduler.get_job('auto_backup'):
                scheduler.remove_job('auto_backup')
            
            if enabled:
                scheduler.add_job(
                    scheduled_backup_job,
                    'interval',
                    hours=interval,
                    id='auto_backup',
                    replace_existing=True,
                    name='Backup automático de base de datos'
                )
                logger.info(f"Job backup configurado cada {interval} horas")
            else:
                logger.info("Job backup deshabilitado")
        
        emit('backup_config_updated', {'success': True})
    except Exception as e:
        logger.error(f"Error actualizando config de backup: {e}")
        emit('backup_config_updated', {'success': False, 'error': str(e)})


@socketio.on('restore_backup')
def handle_restore_backup(data):
    """Restaurar base de datos desde backup."""
    if not session.get('is_admin'): return
    
    filename = data.get('filename')
    if not filename:
        emit('error', {'message': 'Selecciona un backup'})
        return
    
    try:
        from backup_db import BackupManager
        manager = BackupManager()
        backup_path = manager.backup_path / filename
        
        if not backup_path.exists():
            emit('error', {'message': 'Archivo de backup no encontrado'})
            return
        
        result = manager.restore_backup(backup_path)
        
        if result:
            emit('restore_complete', {'success': True})
            add_message_to_history('SISTEMA', f'♻️ Restaurado desde: {filename}')
            logger.info(f"✅ Restaurado backup: {filename}")
        else:
            emit('restore_complete', {'success': False})
            add_message_to_history('ERROR', f'❌ Error restaurando: {filename}')
    except Exception as e:
        logger.error(f"❌ Error restaurando backup: {e}")
        emit('restore_complete', {'success': False})


@socketio.on('delete_backup')
def handle_delete_backup(data):
    """Eliminar archivo de backup."""
    if not session.get('is_admin'): return
    
    filename = data.get('filename')
    if not filename:
        return
    
    try:
        from backup_db import BackupManager
        manager = BackupManager()
        result = manager.delete_backup(filename)
        
        if result:
            backups = manager.get_backups_for_ui()
            emit('backup_deleted', {'success': True, 'filename': filename, 'backups': backups})
            add_message_to_history('SISTEMA', f'🗑️ Eliminado: {filename}')
            logger.info(f"🗑️ Eliminado backup: {filename}")
        else:
            emit('backup_deleted', {'success': False, 'filename': filename})
    except Exception as e:
        logger.error(f"❌ Error eliminando backup: {e}")
        emit('backup_deleted', {'success': False, 'filename': filename})


@socketio.on('restart_server')
def handle_restart_server():
    """Reiniciar el servidor."""
    if not session.get('is_admin'): return
    
    logger.info("🔄 Reiniciando servidor por peticion del usuario...")
    
    try:
        import sys
        import os
        
        # Emitir notificacion antes de reiniciar
        emit('notification', {
            'title': 'Reiniciando',
            'body': 'El servidor se esta reiniciando...',
            'type': 'info',
            'tag': 'server_restart'
        })
        
        # Programar reinicio con delay pequeno
        import threading
        def restart():
            socketio.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        socketio.start_background_task(restart)
        
    except Exception as e:
        logger.error(f"❌ Error reiniciando servidor: {e}")
        emit('error', {'message': f'No se pudo reiniciar: {str(e)}'})
