import logging
import json
import time
import re
from datetime import datetime
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.globals import mqtt_state, socketio, app, config

logger = logging.getLogger(__name__)


def _create_task_trigger(schedule_type, schedule_data):
    """Crea un trigger de APScheduler basado en la configuración."""
    try:
        if schedule_type == 'interval':
            minutes = int(schedule_data.get('minutes', 5))
            return IntervalTrigger(minutes=minutes), f"Cada {minutes} min"

        elif schedule_type == 'daily':
            hour = int(schedule_data.get('hour', 12))
            minute = int(schedule_data.get('minute', 0))
            return CronTrigger(hour=hour, minute=minute), f"Diario a las {hour:02d}:{minute:02d}"

        elif schedule_type == 'cron':
            cron_expr = schedule_data.get('cron', '* * * * *')
            return CronTrigger.from_crontab(cron_expr), f"Cron: {cron_expr}"

    except Exception as e:
        logger.error(f"Error creating trigger: {e}")
        return None, "Error"
    return None, "Desconocido"


def process_placeholders(payload, task_id=None):
    """Reemplaza placeholders en el payload con valores dinámicos."""
    if not payload:
        return payload

    now = datetime.now()
    timestamp = int(time.time())
    timestamp_ms = int(time.time() * 1000)
    datetime_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')

    replacements = {
        '{{timestamp}}': str(timestamp),
        '{{timestamp_ms}}': str(timestamp_ms),
        '{{datetime}}': datetime_iso,
        '{{date}}': date_str,
        '{{time}}': time_str,
    }

    result = payload
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


def evaluate_condition(condition, response_data):
    """Evalúa una condición contra los datos de respuesta.

    Soporta tres formatos:
    - Simple: "temp_c > 30"
    - Expresión: "temp_c > 25 and humidity < 60"
    - JSONPath: "$.status == 'ok'"
    """
    if not condition:
        return True

    response_str = str(response_data)

    # Try JSONPath format: "$.field == value" or "$.field == 'value'"
    if condition.startswith('$.'):
        try:
            from src.persistence import jsonpath_extract
            # Parse JSONPath expression like "$.status == 'ok'"
            match = re.match(r'\$\.(\w+)\s*(==|!=|<|>|<=|>=)\s*(.+)', condition)
            if match:
                field, op, value = match.groups()
                field_value = jsonpath_extract(response_data, field)

                # Parse the comparison value
                if value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        value = value

                # Evaluate comparison
                if op == '==':
                    return field_value == value
                elif op == '!=':
                    return field_value != value
                elif op == '>':
                    return field_value > value
                elif op == '<':
                    return field_value < value
                elif op == '>=':
                    return field_value >= value
                elif op == '<=':
                    return field_value <= value
        except Exception as e:
            logger.debug(f"JSONPath evaluation failed: {e}")

    # Try simple comparison or expression
    try:
        # Add response_data as local variables
        local_vars = {}
        if isinstance(response_data, dict):
            local_vars.update(response_data)
        elif isinstance(response_data, str):
            try:
                local_vars.update(json.loads(response_data))
            except:
                pass

        # Evaluate expression safely
        result = eval(condition, {"__builtins__": {}}, local_vars)
        return bool(result)
    except Exception as e:
        logger.debug(f"Condition evaluation failed: {condition} -> {e}")
        return False

    return True


def handle_response_action(response_action, response_data, task_name):
    """Maneja la acción a tomar después de evaluar la respuesta."""
    from src.mqtt_callbacks import add_message_to_history

    if response_action == 'notify':
        add_message_to_history(
            f"Respuesta OK: {task_name}",
            str(response_data)[:200],
            force=True,
            direction='in'
        )
        socketio.emit('new_notification', {
            'title': f"Respuesta: {task_name}",
            'body': str(response_data)[:200],
            'type': 'success',
            'tag': f'task_response_{task_name}'
        })
    elif response_action == 'error':
        add_message_to_history(
            f"Error en respuesta: {task_name}",
            str(response_data)[:200],
            force=True,
            direction='in'
        )
        socketio.emit('new_notification', {
            'title': f"Error: {task_name}",
            'body': str(response_data)[:200],
            'type': 'error',
            'tag': f'task_error_{task_name}'
        })
    # 'log' is the default - just add to history


def execute_scheduled_task(task_id, topic, payload, task_data=None):
    """Ejecuta una tarea programada: publica MQTT y actualiza BD."""
    with app.app_context():
        from src.persistence import update_task_execution
        from src.globals import scheduled_tasks
        from src.mqtt_callbacks import add_message_to_history

        # Get task data if not provided
        if task_data is None and task_id in scheduled_tasks:
            task_data = scheduled_tasks[task_id]

        try:
            client = mqtt_state.get('client')
            if client and client.is_connected():
                processed_payload = process_placeholders(payload, task_id)
                mqtt_qos = int(config['settings'].get('mqtt_default_qos', 1))
                client.publish(topic, processed_payload, qos=mqtt_qos)
                logger.info(f"Task executed: {topic} -> {processed_payload}")

                task_name = task_data.get('name', 'Scheduled Task') if task_data else 'Scheduled Task'

                display_payload = f"Published to {topic}: {processed_payload}"
                add_message_to_history(task_name, display_payload, force=True, direction='out')

                if task_id in scheduled_tasks:
                    scheduled_tasks[task_id]['executions'] += 1
                    scheduled_tasks[task_id]['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    update_task_execution(
                        task_id,
                        scheduled_tasks[task_id]['last_run'],
                        scheduled_tasks[task_id]['executions']
                    )

                # Handle response analysis if enabled
                if task_data and task_data.get('response_enabled'):
                    _handle_response_analysis(task_id, topic, task_data)

            else:
                logger.warning(f"Task skipped (MQTT disconnected): {topic}")

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")


def _handle_response_analysis(task_id, topic, task_data):
    """Handle response analysis after publishing a task."""
    from src.globals import subscribed_topics, devices_lock, devices

    response_topic = task_data.get('response_topic')
    if not response_topic:
        return

    response_timeout = task_data.get('response_timeout', 10)
    response_condition = task_data.get('response_condition')
    response_action = task_data.get('response_action', 'log')

    # Subscribe to response topic if not already subscribed
    with devices_lock:
        if response_topic not in subscribed_topics:
            client = mqtt_state.get('client')
            if client and client.is_connected():
                client.subscribe(response_topic)
                subscribed_topics.append(response_topic)
                socketio.emit('topics_update', {'topics': subscribed_topics})
                logger.debug(f"Subscribed to response topic: {response_topic}")

    # Store pending response check
    from src.globals import global_state
    if 'pending_responses' not in global_state:
        global_state['pending_responses'] = {}

    global_state['pending_responses'][response_topic] = {
        'task_id': task_id,
        'task_name': task_data.get('name', 'Scheduled Task'),
        'condition': response_condition,
        'action': response_action,
        'expires': time.time() + response_timeout
    }


def check_pending_response(topic, payload):
    """Check if a received message matches a pending response."""
    from src.globals import global_state, devices
    from src.persistence import update_task_execution
    from datetime import datetime
    from src.mqtt_callbacks import add_message_to_history

    if 'pending_responses' not in global_state:
        return

    pending = global_state['pending_responses']

    if topic not in pending:
        return

    response_info = pending[topic]
    task_id = response_info['task_id']
    task_name = response_info['task_name']
    condition = response_info['condition']
    response_action = response_info['action']

    # Check expiration
    if time.time() > response_info['expires']:
        del pending[topic]
        logger.debug(f"Response timeout for task {task_id}")
        return

    # Parse payload
    try:
        if isinstance(payload, str):
            response_data = json.loads(payload)
        else:
            response_data = payload
    except:
        response_data = payload

    # Evaluate condition
    if evaluate_condition(condition, response_data):
        # Condition met - execute action
        handle_response_action(response_action, response_data, task_name)

        # Update task execution count
        if task_id in global_state.get('scheduled_tasks', {}):
            global_state['scheduled_tasks'][task_id]['executions'] += 1
            global_state['scheduled_tasks'][task_id]['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                update_task_execution(
                    task_id,
                    global_state['scheduled_tasks'][task_id]['last_run'],
                    global_state['scheduled_tasks'][task_id]['executions']
                )
            except:
                pass

        logger.info(f"Response condition met for task {task_id}")
    else:
        logger.debug(f"Response condition not met for task {task_id}")

    # Remove pending response check
    del pending[topic]
