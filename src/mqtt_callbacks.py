import logging
import json
import re
import time
from datetime import datetime

from src.globals import (
    app,
    mqtt_state,
    subscribed_topics, devices, devices_lock, scheduled_tasks, alerts,
    socketio, scheduler, message_history, MAX_MESSAGES,
    global_state,
    DEVICE_STATUS_TOPIC, DEVICE_PONG_TOPIC, DEVICE_PING_TOPIC, DEVICE_CMD_BROADCAST_TOPIC, DEVICE_CONFIG_TOPIC
)
from src.persistence import load_subscriptions, load_tasks, load_message_triggers, insert_sensor_data, get_alerts, get_or_create_device, is_device_allowed, get_all_known_devices, add_device_event

logger = logging.getLogger(__name__)

def topic_matches(topic, subscription):
    """Comprueba si un topic coincide con una suscripción MQTT (soporta + y #)."""
    if subscription == "#":
        return True
    
    topic_parts = topic.split('/')
    sub_parts = subscription.split('/')
    
    i = 0
    while i < len(sub_parts):
        if sub_parts[i] == '#':
            return True
        if i >= len(topic_parts):
            return False
        if sub_parts[i] != '+' and sub_parts[i] != topic_parts[i]:
            return False
        i += 1
    
    return i == len(topic_parts)

def check_alerts(device_id, location, device_data, server_name):
    """Comprueba si los datos de un dispositivo disparan alguna alerta."""
    with app.app_context():
        try:
            active_alerts = get_alerts(server_name)
            for alert in active_alerts:
                device_matches = (alert['device_id'] == '*') or \
                                 (alert['device_id'] == f"{device_id}@{location}") or \
                                 (alert['device_id'] == device_id)
                
                if not alert['enabled'] or not device_matches:
                    continue

                if alert['metric'] in device_data:
                    actual_value, threshold_value = device_data[alert['metric']], alert['value']
                    operator = alert['operator']
                    try:
                        actual_value_f, threshold_value_f = float(actual_value), float(threshold_value)
                        if (operator == '>' and actual_value_f > threshold_value_f) or \
                           (operator == '<' and actual_value_f < threshold_value_f) or \
                           (operator == '==' and actual_value_f == threshold_value_f):
                            message = alert['message'].format(device_name=device_data.get('name', device_id), value=actual_value)
                            logger.warning(f"🚨 ALERTA DISPARADA: {message}")
                            socketio.emit('new_alert', {'message': message, 'type': alert.get('type', 'warning')})
                    except (ValueError, TypeError):
                        if operator == '==' and str(actual_value) == str(threshold_value):
                            message = alert['message'].format(device_name=device_data.get('name', device_id), value=actual_value)
                            logger.warning(f"🚨 ALERTA DISPARADA: {message}")
                            socketio.emit('new_alert', {'message': message, 'type': alert.get('type', 'warning')})
        except Exception as e:
            logger.error(f"❌ Error al comprobar alertas para {device_id}@{location}: {e}")

def add_message_to_history(topic, payload, force=False, direction='in'):
    """
    Añade un mensaje al historial.
    force: Si es True, ignora el filtro de suscripciones.
    direction: 'in' (recibido) o 'out' (enviado).
    """
    
    is_system_msg = topic in ['SISTEMA', 'ERROR'] or not topic_matches(topic, '#/#')
    is_subscribed = False
    
    if not is_system_msg and not force:
        for sub in subscribed_topics:
            if topic_matches(topic, sub):
                is_subscribed = True
                break
    
    if is_system_msg or is_subscribed or force:
        timestamp = datetime.now().strftime('%H:%M:%S')
        message_data = {
            'topic': topic, 
            'payload': payload, 
            'timestamp': timestamp,
            'direction': direction
        }
        
        message_history.insert(0, message_data)
        
        while len(message_history) > MAX_MESSAGES:
            message_history.pop()
        
        socketio.emit('history_update', {'history': message_history})

def auto_refresh_loop():
    """Bucle que envía pings periódicamente y gestiona la tolerancia a fallos."""
    from src.globals import config, devices, app
    logger.info("🔄 Bucle de auto-refresco iniciado.")
    
    socketio.sleep(5)

    while mqtt_state['connected']:
        try:
            interval_str = config.get('settings', {}).get('refresh_interval', '30')
            interval = int(interval_str)
            
            max_missed_pings_str = config.get('settings', {}).get('max_missed_pings', '2')
            max_missed_pings = int(max_missed_pings_str)

        except (ValueError, TypeError):
            interval = 30
            max_missed_pings = 2
        
        client = mqtt_state.get('client')
        if client and client.is_connected():
            logger.info(f"🔄 Auto-refresco: Verificando dispositivos y enviando PING. Próximo ciclo en {interval}s.")
            
            if devices:
                for device_key in list(devices.keys()):
                    if device_key not in devices:
                        continue
                    missed = devices[device_key].get('missed_pings', 0) + 1
                    devices[device_key]['missed_pings'] = missed
                    
                    if missed > max_missed_pings:
                        if devices[device_key].get('status') != 'offline':
                            logger.info(f"🔌 Dispositivo '{device_key}' marcado como offline (sin respuesta).")
                            devices[device_key]['status'] = 'offline'
                            device_id, location = device_key.split('@')
                            # AGREGAR: Contexto de aplicación para operaciones DB
                            with app.app_context():
                                try:
                                    add_device_event(device_id, location, 'disconnected', f'Sin respuesta tras {max_missed_pings} intentos')
                                except Exception as e:
                                    logger.error(f'❌ Error registrando evento de dispositivo: {e}')

                socketio.emit('devices_update', {'devices': devices})
            
            ping_command = json.dumps({"cmd": "PING", "time": int(time.time())})
            client.publish(DEVICE_PING_TOPIC, ping_command)
            
            socketio.sleep(interval)
        else:
            logger.warning("🔄 Auto-refresco: Cliente no conectado. Deteniendo bucle.")
            break
    
    mqtt_state['background_task_started'] = False
    logger.info("🔄 Bucle de auto-refresco detenido.")

def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback para cuando el cliente se conecta al broker MQTT."""
    server_name = userdata.get('server_name', 'N/A')

    if reason_code.value == 0:
        mqtt_state['connected'] = True
        mqtt_state['auto_reconnect'] = True
        mqtt_state['user_disconnected'] = False
        socketio.emit('mqtt_reconnecting', {'reconnecting': False})
        socketio.emit('mqtt_status', {'connected': True})
        logger.info(f"✅ Conectado al broker MQTT: {server_name}")
        add_message_to_history('SISTEMA', f'✅ Conectado a {server_name}')
        
        client.subscribe(DEVICE_STATUS_TOPIC)
        client.subscribe(DEVICE_PONG_TOPIC)
        client.subscribe(DEVICE_CONFIG_TOPIC)
        
        with app.app_context():
            subscribed_topics.clear()
            subscribed_topics.extend(load_subscriptions(server_name))
            for topic in subscribed_topics:
                client.subscribe(topic)
            socketio.emit('topics_update', {'topics': subscribed_topics})
            
            load_tasks(server_name)
            socketio.emit('task_update', {'tasks': get_tasks_info_from_globals()})

            load_message_triggers(server_name)
            from src.globals import message_triggers
            socketio.emit('message_triggers_update', {'triggers': list(message_triggers.values())})

            alerts.clear()
            alerts.extend(get_alerts(server_name))
            socketio.emit('alerts_update', {'alerts': alerts})

        logger.info("📢 Solicitando estado inicial de dispositivos...")
        client.publish(DEVICE_PING_TOPIC, json.dumps({"cmd": "PING", "time": int(time.time())}))
        client.publish(DEVICE_CMD_BROADCAST_TOPIC, json.dumps({"cmd": "STATUS"}))
        client.publish(DEVICE_CMD_BROADCAST_TOPIC, json.dumps({"cmd": "GET_CONFIG"}))

        if not mqtt_state.get('background_task_started'):
            mqtt_state['background_task_started'] = True
            socketio.start_background_task(target=auto_refresh_loop)

        scheduler.resume()
        logger.info("⏰ Scheduler reanudado.")
    else:
        mqtt_state['connected'] = False
        logger.error(f"❌ Error de conexión MQTT en '{server_name}': {reason_code.getName()}")
        add_message_to_history('ERROR', f'❌ Error de conexión en {server_name}: {reason_code.getName()}')
        socketio.emit('mqtt_status', {'connected': False})

def on_disconnect(client, userdata, flags, reason_code, properties=None):
    """Callback para cuando el cliente se desconecta del broker MQTT."""
    server_name = userdata.get('server_name', 'N/A')
    
    mqtt_state['connected'] = False
    
    is_auto_reconnect = mqtt_state.get('auto_reconnect', False)
    is_manual_disconnect = mqtt_state.get('user_disconnected', False)
    
    if is_auto_reconnect and not is_manual_disconnect:
        socketio.emit('mqtt_reconnecting', {'reconnecting': True})
        logger.info(f"🔄 Reconectando al broker MQTT: {server_name}...")
        add_message_to_history('SISTEMA', f'🔄 Reconectando a {server_name}...')
    else:
        mqtt_state['auto_reconnect'] = False
        logger.info(f"⚠️ Desconectado del broker MQTT: {server_name}")
        add_message_to_history('SISTEMA', f'⚠️ Desconectado de {server_name}')
        socketio.emit('mqtt_status', {'connected': False})
    
    scheduler.pause()
    logger.info("⏰ Scheduler pausado.")
    scheduler.remove_all_jobs()
    
    scheduled_tasks.clear()
    subscribed_topics.clear()
    alerts.clear()
    
    with devices_lock:
        for device_key in list(devices.keys()):
            if device_key in devices:
                devices[device_key]['status'] = 'offline'
                devices[device_key]['missed_pings'] = 0
    
    socketio.emit('task_update', {'tasks': []})
    socketio.emit('topics_update', {'topics': []})
    socketio.emit('devices_update', {'devices': devices})
    socketio.emit('alerts_update', {'alerts': []})

def on_message(client, userdata, msg):
    """Callback para cuando se recibe un mensaje MQTT."""
    global devices
    payload_str = msg.payload.decode('utf-8')
    timestamp = datetime.now().strftime('%H:%M:%S')
    server_name = userdata.get('server_name', 'N/A')
    
    try:
        topic_parts = msg.topic.split('/')

        # Determinar si es un mensaje de dispositivo y extraer device_id/location
        device_id, location = None, None
        message_type = None

        if topic_parts[0:2] == ['iot', 'pong'] and len(topic_parts) >= 4:
            device_id, location = topic_parts[2], topic_parts[3]
            message_type = 'pong'
        elif topic_parts[0:2] == ['iot', 'status'] and len(topic_parts) >= 4:
            device_id, location = topic_parts[2], topic_parts[3]
            message_type = 'status'
        elif topic_parts[0:2] == ['iot', 'config'] and len(topic_parts) >= 4:
            device_id, location = topic_parts[2], topic_parts[3]
            message_type = 'config'

        # Si no es un mensaje de dispositivo conocido, procesar como mensaje genérico
        if device_id is None or location is None:
            add_message_to_history(msg.topic, payload_str, direction='in')
            check_message_triggers(msg.topic, payload_str)
            return


        # CORRECCIÓN: Registrar el dispositivo ANTES de comprobar la whitelist
        with app.app_context():
            _, created = get_or_create_device(device_id, device_id, location, server_name)
            if created:
                # Si es nuevo, notificar al frontend para que actualice los comboboxes
                socketio.emit('known_devices_update', {'known_devices': get_all_known_devices(server_name)})

            # Ahora, comprobar si está permitido para continuar
            if not is_device_allowed(server_name, device_id, location):
                logger.debug(f"🚫 Dispositivo '{device_id}@{location}' bloqueado por whitelist. Registrado pero no mostrado.")
                return

        device_key = f"{device_id}@{location}"

        is_subscribed = any(topic_matches(msg.topic, sub) for sub in subscribed_topics)
        if is_subscribed:
            history_title = device_key
            history_payload = f"Topic: {msg.topic}\n{payload_str}"
            add_message_to_history(history_title, history_payload, force=True, direction='in')

        # Procesar según el tipo de mensaje
        if message_type == 'pong':
            data = json.loads(payload_str)

            if data.get("cmd") == "PONG":
                ping_time = data.get("time", 0)
                latency = (time.time() - ping_time) * 1000 if ping_time > 0 else -1
                
                was_offline = False
                if device_key in devices and devices[device_key].get('status') == 'offline':
                    was_offline = True
                
                update_data = {'status': 'online', 'latency': f"{latency:.2f}", 'last_seen': timestamp, 'location': location, 'missed_pings': 0}
                
                with app.app_context():
                    display_name, was_created = get_or_create_device(device_id, device_id, location, server_name)
                    if was_created:
                        known_devices = get_all_known_devices(server_name)
                        socketio.emit('known_devices_update', {'known_devices': known_devices})
                
                if device_key not in devices:
                    update_data['id'] = device_id
                    update_data['name'] = device_id
                elif devices[device_key].get('name') != display_name:
                    update_data['name'] = display_name
                
                devices.setdefault(device_key, {}).update(update_data)
                socketio.emit('devices_update', {'devices': devices})
                
                if was_offline:
                    add_device_event(device_id, location, 'connected', f'Latencia: {latency:.2f}ms')
        
        elif topic_parts[0:2] == ['iot', 'config']:
            try:
                data = json.loads(payload_str)

                with app.app_context():
                    device_key = f"{data.get('device_id', device_id)}@{data.get('location', location)}"

                    # Crear o actualizar el dispositivo si no existe
                    if device_key not in devices:
                        display_name, was_created = get_or_create_device(
                            data.get('device_id', device_id),
                            data.get('device', device_id),
                            data.get('location', location),
                            server_name
                        )

                    # Actualizar información de configuración siempre
                    if 'firmware' in data:
                        devices[device_key]['firmware'] = data.get('firmware', 'Unknown')
                    if 'mac' in data:
                        devices[device_key]['mac'] = data.get('mac', 'N/A')
                    if 'heap' in data:
                        devices[device_key]['heap'] = data.get('heap', 0)
                    if 'chip_id' in data:
                        devices[device_key]['chip_id'] = data.get('chip_id', 'N/A')
                    if 'ip' in data:
                        devices[device_key]['ip'] = data.get('ip', 'N/A')
                    if 'uptime' in data:
                        devices[device_key]['uptime'] = data.get('uptime', 0)

                    # Actualizar datos de sensores desde config
                    sensor_data = data.get('sensor', {})
                    if isinstance(sensor_data, dict):
                        if 'temp_c' in sensor_data:
                            devices[device_key]['temp_c'] = sensor_data.get('temp_c')
                        if 'temp_h' in sensor_data:
                            devices[device_key]['temp_h'] = sensor_data.get('temp_h')
                        if 'temp_st' in sensor_data:
                            devices[device_key]['temp_st'] = sensor_data.get('temp_st')

                    logger.info(f"Config actualizada para {device_key}: firmware={data.get('firmware')}, mac={data.get('mac')}, heap={data.get('heap')}")

                    socketio.emit('devices_update', {'devices': devices})
                    socketio.emit('device_config_update', {
                        'device_id': data.get('device_id', device_id),
                        'location': data.get('location', location),
                        'config': {
                            'firmware': data.get('firmware', 'Unknown'),
                            'mac': data.get('mac', 'N/A'),
                            'heap': data.get('heap', 0),
                            'chip_id': data.get('chip_id', 'N/A'),
                            'sensor': data.get('sensor', {}),
                            'ip': data.get('ip', 'N/A'),
                            'uptime': data.get('uptime', 0)
                        }
                    })
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parsing config payload: {e}")
                add_message_to_history('ERROR', f'Error parseando config de {msg.topic}: {e}', direction='in')
        elif message_type == 'status':
            data = json.loads(payload_str)

            if data.get('status') == 'offline':
                logger.info(f"🔌 Dispositivo '{device_key}' reportó offline.")
                devices.setdefault(device_key, {'id': device_id, 'name': device_id, 'location': location}).update({'status': 'offline', 'last_seen': timestamp, 'missed_pings': 0})
                socketio.emit('devices_update', {'devices': devices})
                add_device_event(device_id, location, 'offline', 'Reporte de estado offline')
                check_alerts(device_id, location, {'status': 'offline'}, server_name)
                return

            with app.app_context():
                display_name, was_created = get_or_create_device(device_id, data.get('device', device_id), location, server_name)
                if was_created:
                    known_devices = get_all_known_devices(server_name)
                    socketio.emit('known_devices_update', {'known_devices': known_devices})

            device_info = {
                'id': device_id,
                'name': display_name,
                'location': data.get('location', location),
                'ip': data.get('ip', 'N/A'),
                'uptime': data.get('uptime', 0),
                'status': 'online',
                'last_seen': timestamp,
                'missed_pings': 0,
                'firmware': data.get('firmware', 'Unknown'),
                'mac': data.get('mac', 'N/A'),
                'heap': data.get('heap', 0)
            }
            
            has_sensor_data = False
            if 'temp_c' in data: device_info['temp_c'], has_sensor_data = data['temp_c'], True
            if 'temp_h' in data: device_info['temp_h'], has_sensor_data = data['temp_h'], True
            if 'temp_st' in data: device_info['temp_st'], has_sensor_data = data['temp_st'], True

            devices.setdefault(device_key, {}).update(device_info)
            socketio.emit('devices_update', {'devices': devices})

            if has_sensor_data:
                with app.app_context():
                    insert_sensor_data(device_id, location, data)
            
            check_alerts(device_id, location, device_info, server_name)

        elif message_type == 'config':
            try:
                data = json.loads(payload_str)

                # Actualizar devices dict con info de configuración
                with devices_lock:
                    if device_key in devices:
                        devices[device_key]['firmware'] = data.get('firmware', 'Unknown')
                        devices[device_key]['mac'] = data.get('mac', 'N/A')
                        devices[device_key]['heap'] = data.get('heap', 0)
                        devices[device_key]['chip_id'] = data.get('chip_id', 'N/A')

                        # Sensor data (if available)
                        if data.get('sensor'):
                            sensor_data = data['sensor']
                            if isinstance(sensor_data, dict):
                                # Si es un objeto con datos de temperatura
                                devices[device_key]['temp_c'] = sensor_data.get('temp_c')
                                devices[device_key]['temp_h'] = sensor_data.get('temp_h')
                                devices[device_key]['temp_st'] = sensor_data.get('temp_st')
                            else:
                                # Si es un string (tipo de sensor), convertir a objeto
                                devices[device_key]['sensor_type'] = str(sensor_data)

                logger.debug(f"✅ Config recibida para {device_key}: firmware={data.get('firmware')}, mac={data.get('mac')}, heap={data.get('heap')}")

                # Notificar al frontend (si el dispositivo ya está en pantalla)
                sensor_info = data.get('sensor', {})
                if not isinstance(sensor_info, dict):
                    # Si es un string (tipo de sensor), convertir a objeto
                    sensor_info = {'type': str(sensor_info)}

                socketio.emit('device_config_update', {
                    'device_id': device_id,
                    'location': location,
                    'config': {
                        'firmware': data.get('firmware', 'Unknown'),
                        'mac': data.get('mac', 'N/A'),
                        'heap': data.get('heap', 0),
                        'chip_id': data.get('chip_id', 'N/A'),
                        'sensor': sensor_info
                    }
                })

            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parsing config de {device_id}@{location}: {e}")

    except (json.JSONDecodeError, IndexError) as e:
        logger.warning(f"Could not process message payload: {msg.topic} | {payload_str} | Error: {e}")


def check_message_triggers(topic, payload_str):
    """Check if a message matches any message triggers and execute actions."""
    from src.globals import message_triggers, mqtt_state, devices_lock

    if not message_triggers:
        return

    try:
        # Try to parse payload as JSON
        try:
            payload_data = json.loads(payload_str)
        except:
            payload_data = payload_str

        for trigger_id, trigger in message_triggers.items():
            if not trigger.get('enabled', True):
                continue

            # Check if topic matches pattern
            if not _topic_matches(topic, trigger['topic_pattern']):
                continue

            # Evaluate condition if exists
            condition = trigger.get('trigger_condition')
            if condition:
                if not _evaluate_trigger_condition(condition, payload_data):
                    continue

            # Condition met - execute action
            logger.info(f"Message trigger activated: {trigger['name']} (topic: {topic})")

            # Update trigger count
            from datetime import datetime
            trigger['trigger_count'] = trigger.get('trigger_count', 0) + 1
            trigger['last_triggered'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute action
            action_type = trigger.get('action_type')
            if action_type == 'publish':
                action_topic = trigger.get('action_topic')
                action_payload = trigger.get('action_payload', '{}')
                if action_topic and action_payload:
                    from src.task_utils import process_placeholders
                    processed_payload = process_placeholders(action_payload)
                    client = mqtt_state.get('client')
                    if client and client.is_connected():
                        client.publish(action_topic, processed_payload)
                        add_message_to_history(
                            f"Trigger: {trigger['name']}",
                            f"Published to {action_topic}: {processed_payload}",
                            force=True,
                            direction='out'
                        )
            elif action_type == 'notify':
                socketio.emit('new_notification', {
                    'title': f"Trigger: {trigger['name']}",
                    'body': f"Topic: {topic}\nPayload: {payload_str[:200]}",
                    'type': 'info',
                    'tag': f'trigger_{trigger_id}'
                })
                add_message_to_history(
                    f"Trigger: {trigger['name']}",
                    f"Topic: {topic}",
                    force=True,
                    direction='in'
                )

    except Exception as e:
        logger.error(f"Error checking message triggers: {e}")


def _topic_matches(topic, pattern):
    """Check if a topic matches a pattern (supports + and # wildcards)."""
    topic_parts = topic.split('/')
    pattern_parts = pattern.split('/')

    if len(topic_parts) != len(pattern_parts):
        return False

    for t, p in zip(topic_parts, pattern_parts):
        if p == '#':
            return True
        if p == '+':
            continue
        if t != p:
            return False

    return True


def _evaluate_trigger_condition(condition, payload_data):
    """Evaluate a trigger condition against payload data."""
    if not condition:
        return True

    # Simple comparison: "field > value"
    match = re.match(r'(\w+)\s*(==|!=|<|>|<=|>=)\s*(.+)', condition)
    if match:
        field, op, value = match.groups()

        # Get field value from payload
        field_value = payload_data
        for key in field.split('.'):
            if isinstance(field_value, dict):
                field_value = field_value.get(key)
            else:
                return False

        # Parse comparison value
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        else:
            try:
                value = float(value)
            except ValueError:
                pass

        # Evaluate
        try:
            if op == '==':
                return field_value == value
            elif op == '!=':
                return field_value != value
            elif op == '>':
                return float(field_value) > float(value)
            elif op == '<':
                return float(field_value) < float(value)
            elif op == '>=':
                return float(field_value) >= float(value)
            elif op == '<=':
                return float(field_value) <= float(value)
        except (ValueError, TypeError):
            return False

    # Try simple eval as fallback
    try:
        local_vars = {}
        if isinstance(payload_data, dict):
            local_vars.update(payload_data)
        result = eval(condition, {"__builtins__": {}}, local_vars)
        return bool(result)
    except:
        return False


def get_tasks_info_from_globals():
    """Función auxiliar para evitar importación circular en on_connect."""
    result = []
    for task_id, task_data in scheduled_tasks.items():
        job = scheduler.get_job(task_id)
        if job and job.next_run_time:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            next_run = 'Pausada'
        result.append({'id': task_id, **task_data, 'next_run': next_run})
    return result
