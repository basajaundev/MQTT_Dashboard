import pytest
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCheckAdminPassword:
    """Tests para funciones de autenticación de admin."""

    def test_password_correcto(self, app, db_session):
        """Verificar contraseña correcta."""
        from src.persistence import check_admin_password, update_admin_password
        
        with app.app_context():
            update_admin_password('testpassword')
            assert check_admin_password('testpassword') is True

    def test_password_incorrecto(self, app, db_session):
        """Verificar contraseña incorrecta."""
        from src.persistence import check_admin_password, update_admin_password
        
        with app.app_context():
            update_admin_password('testpassword')
            assert check_admin_password('wrongpassword') is False

    def test_password_sin_configurar(self, app, db_session):
        """Verificar cuando no hay contraseña configurada."""
        from src.persistence import check_admin_password
        
        with app.app_context():
            assert check_admin_password('anything') is False

    def test_update_password(self, app, db_session):
        """Actualizar contraseña."""
        from src.persistence import check_admin_password, update_admin_password
        
        with app.app_context():
            update_admin_password('newpassword')
            assert check_admin_password('newpassword') is True
            assert check_admin_password('oldpassword') is False


class TestServerConfiguration:
    """Tests para gestión de servidores."""

    def test_add_server(self, app, db_session):
        """Añadir un servidor."""
        from src.persistence import add_server
        from src.models import Server
        
        with app.app_context():
            result = add_server({
                'name': 'RPI3',
                'broker': '192.168.0.5',
                'port': 1883,
                'username': '',
                'password': ''
            })
            assert result is True
            
            server = Server.query.filter_by(name='RPI3').first()
            assert server is not None
            assert server.broker == '192.168.0.5'
            assert server.port == 1883

    def test_add_server_con_credenciales(self, app, db_session):
        """Añadir servidor con credenciales."""
        from src.persistence import add_server
        from src.models import Server
        
        with app.app_context():
            result = add_server({
                'name': 'SecureServer',
                'broker': 'broker.example.com',
                'port': 8883,
                'username': 'admin',
                'password': 'secret123'
            })
            assert result is True
            
            server = Server.query.filter_by(name='SecureServer').first()
            assert server.username == 'admin'
            assert server.password == 'secret123'

    def test_add_server_duplicado(self, app, db_session):
        """Añadir servidor duplicado debe fallar."""
        from src.persistence import add_server
        from sqlalchemy.exc import IntegrityError
        
        with app.app_context():
            add_server({
                'name': 'DuplicateServer',
                'broker': 'localhost',
                'port': 1883
            })
            
            result = add_server({
                'name': 'DuplicateServer',
                'broker': 'other.com',
                'port': 1883
            })
            assert result is False

    def test_update_server(self, app, db_session):
        """Actualizar un servidor."""
        from src.persistence import add_server, update_server
        from src.models import Server
        
        with app.app_context():
            add_server({
                'name': 'UpdateServer',
                'broker': 'old.local',
                'port': 1883
            })
            
            server = Server.query.filter_by(name='UpdateServer').first()
            result = update_server(server.id, {
                'name': 'UpdatedServer',
                'broker': 'new.local',
                'port': 8883
            })
            assert result is True
            
            updated = Server.query.get(server.id)
            assert updated.broker == 'new.local'
            assert updated.port == 8883

    def test_delete_server(self, app, db_session):
        """Eliminar un servidor."""
        from src.persistence import add_server, delete_server
        from src.models import Server
        
        with app.app_context():
            add_server({
                'name': 'DeleteServer',
                'broker': 'localhost',
                'port': 1883
            })
            
            server = Server.query.filter_by(name='DeleteServer').first()
            result = delete_server(server.id)
            assert result is True
            
            assert Server.query.filter_by(name='DeleteServer').first() is None

    def test_delete_server_cascade(self, app, db_session):
        """Eliminar servidor elimina tareas relacionadas."""
        from src.persistence import add_server, add_task, delete_server
        from src.models import Server, Task
        
        with app.app_context():
            add_server({
                'name': 'CascadeServer',
                'broker': 'localhost',
                'port': 1883
            })
            
            add_task('CascadeServer', {
                'id': 'cascade-task',
                'name': 'Cascade Task',
                'topic': 'test/topic',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=60'
            })
            
            server = Server.query.filter_by(name='CascadeServer').first()
            delete_server(server.id)
            
            assert Task.query.filter_by(id='cascade-task').first() is None


class TestTasksManagement:
    """Tests para gestión de tareas."""

    def test_add_task(self, app, db_session, sample_server):
        """Añadir una tarea."""
        from src.persistence import add_task
        from src.models import Task
        
        with app.app_context():
            result = add_task(sample_server.name, {
                'id': 'task-001',
                'name': 'Enviar Temperatura',
                'topic': 'home/livingroom/temp',
                'payload': '{"cmd": "get_temp"}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=30',
                'enabled': True,
                'executions': 0,
                'last_run': 'Nunca'
            })
            assert result is True
            
            task = Task.query.filter_by(id='task-001').first()
            assert task is not None
            assert task.name == 'Enviar Temperatura'

    def test_get_tasks(self, app, db_session, sample_server):
        """Obtener tareas de un servidor."""
        from src.persistence import add_task, get_tasks
        from src.models import Task
        
        with app.app_context():
            add_task(sample_server.name, {
                'id': 'get-task-1',
                'name': 'Task 1',
                'topic': 'test1',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=60'
            })
            add_task(sample_server.name, {
                'id': 'get-task-2',
                'name': 'Task 2',
                'topic': 'test2',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=120'
            })
            
            tasks = get_tasks(sample_server.name)
            assert len(tasks) == 2

    def test_delete_task(self, app, db_session, sample_server):
        """Eliminar una tarea."""
        from src.persistence import add_task, delete_task
        from src.models import Task
        
        with app.app_context():
            add_task(sample_server.name, {
                'id': 'delete-task',
                'name': 'Delete Me',
                'topic': 'test',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=60'
            })
            
            result = delete_task(sample_server.name, 'delete-task')
            assert result is True
            assert Task.query.filter_by(id='delete-task').first() is None


class TestWhitelistManagement:
    """Tests para gestión de whitelist."""

    def test_add_to_whitelist(self, app, db_session, sample_server):
        """Añadir a whitelist."""
        from src.persistence import add_to_whitelist
        from src.models import Whitelist
        
        with app.app_context():
            result = add_to_whitelist(
                sample_server.name,
                'ESP32_001',
                'Dormitorio'
            )
            assert result is True
            
            wl = Whitelist.query.filter_by(
                server_name=sample_server.name,
                device_id='ESP32_001'
            ).first()
            assert wl is not None

    def test_add_to_whitelist_con_grupo(self, app, db_session, sample_server):
        """Añadir a whitelist con grupo."""
        from src.persistence import add_to_whitelist, add_group
        from src.models import Whitelist
        
        with app.app_context():
            add_group(sample_server.name, {'name': 'Dormitorios'})
            group_id = sample_server.groups[0].id if sample_server.groups else None
            
            if group_id:
                result = add_to_whitelist(
                    sample_server.name,
                    'ESP32_001',
                    'Dormitorio',
                    group_id
                )
                assert result is True
                
                wl = Whitelist.query.filter_by(device_id='ESP32_001').first()
                assert wl.group_id == group_id

    def test_remove_from_whitelist(self, app, db_session, sample_server):
        """Eliminar de whitelist."""
        from src.persistence import add_to_whitelist, remove_from_whitelist
        from src.models import Whitelist
        
        with app.app_context():
            add_to_whitelist(sample_server.name, 'ESP32_001', 'Dormitorio')
            
            result = remove_from_whitelist(sample_server.name, 'ESP32_001', 'Dormitorio')
            assert result is True
            
            assert Whitelist.query.filter_by(device_id='ESP32_001').first() is None

    def test_get_whitelist(self, app, db_session, sample_server):
        """Obtener whitelist."""
        from src.persistence import add_to_whitelist, get_whitelist
        
        with app.app_context():
            add_to_whitelist(sample_server.name, 'ESP32_001', 'Dormitorio')
            add_to_whitelist(sample_server.name, 'ESP32_002', 'Salon')
            
            wl = get_whitelist(sample_server.name)
            assert len(wl) == 2


class TestGroupManagement:
    """Tests para gestión de grupos."""

    def test_add_group(self, app, db_session, sample_server):
        """Añadir grupo."""
        from src.persistence import add_group
        from src.models import Group
        
        with app.app_context():
            result = add_group(sample_server.name, {'name': 'Dormitorios'})
            assert result is True
            
            group = Group.query.filter_by(
                server_name=sample_server.name,
                name='Dormitorios'
            ).first()
            assert group is not None
            assert group.active is True

    def test_update_group(self, app, db_session, sample_server):
        """Actualizar grupo."""
        from src.persistence import add_group, update_group
        from src.models import Group
        
        with app.app_context():
            add_group(sample_server.name, {'name': 'OldName'})
            group = Group.query.filter_by(name='OldName').first()
            
            result = update_group(group.id, {'name': 'NewName', 'active': False})
            assert result is True
            
            updated = Group.query.get(group.id)
            assert updated.name == 'NewName'
            assert updated.active is False

    def test_delete_group(self, app, db_session, sample_server):
        """Eliminar grupo."""
        from src.persistence import add_group, delete_group
        from src.models import Group
        
        with app.app_context():
            add_group(sample_server.name, {'name': 'ToDelete'})
            group = Group.query.filter_by(name='ToDelete').first()
            
            result = delete_group(group.id)
            assert result is True
            
            assert Group.query.filter_by(name='ToDelete').first() is None

    def test_get_groups(self, app, db_session, sample_server):
        """Obtener grupos."""
        from src.persistence import add_group, get_groups
        
        with app.app_context():
            add_group(sample_server.name, {'name': 'Group1'})
            add_group(sample_server.name, {'name': 'Group2'})
            
            groups = get_groups(sample_server.name)
            assert len(groups) == 2


class TestAlertManagement:
    """Tests para gestión de alertas."""

    def test_add_alert(self, app, db_session, sample_server):
        """Añadir alerta."""
        from src.persistence import add_alert
        from src.models import Alert
        
        with app.app_context():
            result = add_alert(sample_server.name, {
                'name': 'Temp Alta',
                'device_id': 'ESP32_001',
                'metric': 'temp_c',
                'operator': '>',
                'value': '30',
                'message': 'Temperatura excesiva'
            })
            assert result is True
            
            alert = Alert.query.filter_by(name='Temp Alta').first()
            assert alert is not None

    def test_get_alerts(self, app, db_session, sample_server):
        """Obtener alertas."""
        from src.persistence import add_alert, get_alerts
        
        with app.app_context():
            add_alert(sample_server.name, {'name': 'Alert1', 'device_id': 'D1', 'metric': 'temp', 'operator': '>', 'value': '25'})
            add_alert(sample_server.name, {'name': 'Alert2', 'device_id': 'D2', 'metric': 'temp', 'operator': '<', 'value': '10'})
            
            alerts = get_alerts(sample_server.name)
            assert len(alerts) == 2


class TestKnownDevices:
    """Tests para dispositivos conocidos."""

    def test_load_known_devices_to_memory(self, app, db_session, sample_server):
        """Cargar dispositivos conocidos a memoria."""
        from src.persistence import add_to_whitelist, load_known_devices_to_memory
        from src.globals import devices, devices_lock
        
        with app.app_context():
            add_to_whitelist(sample_server.name, 'ESP32_001', 'Dormitorio')
            add_to_whitelist(sample_server.name, 'ESP32_002', 'Salon')
            
            load_known_devices_to_memory(sample_server.name)
            
            with devices_lock:
                assert 'ESP32_001@Dormitorio' in devices
                assert 'ESP32_002@Salon' in devices

    def test_get_all_known_devices(self, app, db_session, sample_server):
        """Obtener todos los dispositivos conocidos."""
        from src.persistence import add_to_whitelist, get_all_known_devices
        
        with app.app_context():
            add_to_whitelist(sample_server.name, 'ESP32_001', 'Dormitorio')
            add_to_whitelist(sample_server.name, 'ESP32_002', 'Salon')
            
            devices = get_all_known_devices(sample_server.name)
            assert len(devices) == 2


class TestSubscriptions:
    """Tests para gestión de suscripciones MQTT."""

    def test_save_and_load_subscriptions(self, app, db_session, sample_server):
        """Guardar y cargar suscripciones."""
        from src.persistence import save_subscriptions, load_subscriptions
        from src.models import Subscription
        
        with app.app_context():
            topics = ['home/+/temperatura', 'home/+/humedad']
            save_subscriptions(sample_server.name, topics)
            
            loaded = load_subscriptions(sample_server.name)
            assert loaded == topics
            
            subs = Subscription.query.filter_by(server_name=sample_server.name).all()
            assert len(subs) == 2


class TestMessageHistory:
    """Tests para historial de mensajes."""

    def test_add_message_to_history(self, app, db_session):
        """Añadir mensaje al historial."""
        from src.mqtt_callbacks import add_message_to_history
        from src.globals import message_history
        
        with app.app_context():
            add_message_to_history('TOPIC', 'Payload', direction='in')
            
            assert len(message_history) == 1
            msg = message_history[0]
            assert msg['topic'] == 'TOPIC'
            assert msg['direction'] == 'in'

    def test_message_history_limit(self, app, db_session):
        """Verificar límite del historial."""
        from src.mqtt_callbacks import add_message_to_history
        from src.globals import message_history, MAX_MESSAGES
        
        with app.app_context():
            for i in range(MAX_MESSAGES + 10):
                add_message_to_history(f'Topic{i}', f'Payload{i}')
            
            assert len(message_history) <= MAX_MESSAGES


class TestDeviceLogs:
    """Tests para logs de dispositivos."""

    def test_get_device_logs(self, app, db_session):
        """Obtener logs de dispositivo."""
        from src.persistence import add_device_log, get_device_logs
        from src.models import DeviceLog
        
        with app.app_context():
            add_device_log('ESP32_001', 'Dormitorio', 'INFO', 'Test log 1')
            add_device_log('ESP32_001', 'Dormitorio', 'ERROR', 'Test log 2')
            
            logs = get_device_logs('ESP32_001', 'Dormitorio', 100)
            assert len(logs) == 2

    def test_get_device_logs_empty(self, app, db_session):
        """Obtener logs de dispositivo sin logs."""
        from src.persistence import get_device_logs
        
        with app.app_context():
            logs = get_device_logs('ESP32_999', 'Unknown', 100)
            assert len(logs) == 0
