import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestServerModel:
    """Tests para el modelo Server."""

    def test_crear_server(self, app, db_session):
        """Crear un servidor básico."""
        from src.models import Server
        
        with app.app_context():
            server = Server(
                name='TestServer',
                broker='localhost',
                port=1883,
                username='',
                password=''
            )
            db_session.add(server)
            db_session.commit()
            
            assert server.id is not None
            assert server.name == 'TestServer'
            assert server.broker == 'localhost'
            assert server.port == 1883

    def test_server_con_credenciales(self, app, db_session):
        """Crear un servidor con credenciales."""
        from src.models import Server
        
        with app.app_context():
            server = Server(
                name='SecureServer',
                broker='broker.example.com',
                port=8883,
                username='user',
                password='pass123'
            )
            db_session.add(server)
            db_session.commit()
            
            assert server.username == 'user'
            assert server.password == 'pass123'

    def test_server_unique_name(self, app, db_session):
        """El nombre del servidor debe ser único."""
        from src.models import Server
        from sqlalchemy.exc import IntegrityError
        
        with app.app_context():
            server1 = Server(name='UniqueServer', broker='localhost', port=1883)
            db_session.add(server1)
            db_session.commit()
            
            server2 = Server(name='UniqueServer', broker='other.com', port=1883)
            db_session.add(server2)
            
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()

    def test_server_relacion_tasks(self, app, db_session, sample_server):
        """Verificar relación con tareas."""
        from src.models import Task
        
        with app.app_context():
            task = Task(
                id='task-001',
                server_name=sample_server.name,
                name='Test Task',
                topic='test/topic',
                payload='{}',
                schedule_type='interval',
                schedule_data='seconds=60'
            )
            db_session.add(task)
            db_session.commit()
            
            # Relación inversa
            assert task in sample_server.tasks

    def test_server_cascade_delete(self, app, db_session):
        """Al eliminar un servidor, se eliminan sus tareas relacionadas."""
        from src.models import Server, Task
        
        with app.app_context():
            server = Server(name='CascadeServer', broker='localhost', port=1883)
            db_session.add(server)
            db_session.commit()
            
            task = Task(
                id='cascade-task-001',
                server_name=server.name,
                name='Cascade Task',
                topic='test/topic',
                payload='{}',
                schedule_type='interval',
                schedule_data='seconds=60'
            )
            db_session.add(task)
            db_session.commit()
            
            # Eliminar servidor
            db_session.delete(server)
            db_session.commit()
            
            # Verificar que la tarea también fue eliminada
            assert Task.query.filter_by(id='cascade-task-001').first() is None


class TestDeviceModel:
    """Tests para el modelo Device."""

    def test_crear_device(self, app, db_session, sample_server):
        """Crear un dispositivo básico."""
        from src.models import Device
        
        with app.app_context():
            device = Device(
                dev_id='ESP32_001',
                dev_name='Sensor Temperatura',
                dev_location='Dormitorio',
                dev_server=sample_server.name
            )
            db_session.add(device)
            db_session.commit()
            
            assert device.id is not None
            assert device.dev_id == 'ESP32_001'
            assert device.dev_name == 'Sensor Temperatura'
            assert device.dev_location == 'Dormitorio'

    def test_device_con_alias(self, app, db_session, sample_server):
        """Crear un dispositivo con alias."""
        from src.models import Device
        
        with app.app_context():
            device = Device(
                dev_id='ESP32_002',
                dev_name='Sensor',
                dev_location='Salon',
                dev_alias='Mi Sensor Principal',
                dev_server=sample_server.name
            )
            db_session.add(device)
            db_session.commit()
            
            assert device.dev_alias == 'Mi Sensor Principal'

    def test_device_relacion_server(self, app, db_session, sample_server):
        """Verificar relación con servidor."""
        from src.models import Device
        
        with app.app_context():
            device = Device(
                dev_id='ESP32_003',
                dev_name='Test',
                dev_location='Test',
                dev_server=sample_server.name
            )
            db_session.add(device)
            db_session.commit()
            
            assert device.server == sample_server


class TestTaskModel:
    """Tests para el modelo Task."""

    def test_crear_task(self, app, db_session, sample_server):
        """Crear una tarea básica."""
        from src.models import Task
        
        with app.app_context():
            task = Task(
                id='task-001',
                server_name=sample_server.name,
                name='Enviar Temperatura',
                topic='home/livingroom/temp',
                payload='{"cmd": "get_temp"}',
                schedule_type='interval',
                schedule_data='seconds=30'
            )
            db_session.add(task)
            db_session.commit()
            
            assert task.id == 'task-001'
            assert task.enabled is True
            assert task.executions == 0
            assert task.last_run == 'Nunca'

    def test_task_disabled(self, app, db_session, sample_server):
        """Crear una tarea deshabilitada."""
        from src.models import Task
        
        with app.app_context():
            task = Task(
                id='task-002',
                server_name=sample_server.name,
                name='Disabled Task',
                topic='test/topic',
                payload='{}',
                schedule_type='interval',
                schedule_data='minutes=5',
                enabled=False
            )
            db_session.add(task)
            db_session.commit()
            
            assert task.enabled is False


class TestWhitelistModel:
    """Tests para el modelo Whitelist."""

    def test_crear_whitelist_entry(self, app, db_session, sample_server):
        """Crear entrada en whitelist."""
        from src.models import Whitelist
        
        with app.app_context():
            wl = Whitelist(
                server_name=sample_server.name,
                device_id='ESP32_001',
                location='Dormitorio'
            )
            db_session.add(wl)
            db_session.commit()
            
            assert wl.id is not None
            assert wl.device_id == 'ESP32_001'

    def test_whitelist_con_grupo(self, app, db_session, sample_server):
        """Crear entrada en whitelist con grupo."""
        from src.models import Whitelist, Group
        
        with app.app_context():
            group = Group(
                server_name=sample_server.name,
                name='Dormitorios'
            )
            db_session.add(group)
            db_session.commit()
            
            wl = Whitelist(
                server_name=sample_server.name,
                device_id='ESP32_001',
                location='Dormitorio',
                group_id=group.id
            )
            db_session.add(wl)
            db_session.commit()
            
            assert wl.group_id == group.id


class TestGroupModel:
    """Tests para el modelo Group."""

    def test_crear_grupo(self, app, db_session, sample_server):
        """Crear un grupo."""
        from src.models import Group
        
        with app.app_context():
            group = Group(
                server_name=sample_server.name,
                name='Dormitorios'
            )
            db_session.add(group)
            db_session.commit()
            
            assert group.id is not None
            assert group.active is True


class TestAlertModel:
    """Tests para el modelo Alert."""

    def test_crear_alerta(self, app, db_session, sample_server):
        """Crear una alerta."""
        from src.models import Alert
        
        with app.app_context():
            alert = Alert(
                server_name=sample_server.name,
                name='Temperatura Alta',
                device_id='ESP32_001',
                metric='temp_c',
                operator='>',
                value='30',
                message='Temperatura excesiva'
            )
            db_session.add(alert)
            db_session.commit()
            
            assert alert.id is not None
            assert alert.type == 'warning'
            assert alert.enabled is True

    def test_alerta_tipos(self, app, db_session, sample_server):
        """Crear alertas de diferentes tipos."""
        from src.models import Alert
        
        with app.app_context():
            alert_info = Alert(
                server_name=sample_server.name,
                name='Info Alert',
                device_id='ESP32_001',
                metric='status',
                operator='==',
                value='online',
                type='info'
            )
            alert_error = Alert(
                server_name=sample_server.name,
                name='Error Alert',
                device_id='ESP32_001',
                metric='status',
                operator='==',
                value='offline',
                type='error'
            )
            db_session.add_all([alert_info, alert_error])
            db_session.commit()
            
            assert alert_info.type == 'info'
            assert alert_error.type == 'error'


class TestSubscriptionModel:
    """Tests para el modelo Subscription."""

    def test_crear_subscription(self, app, db_session, sample_server):
        """Crear una suscripción MQTT."""
        from src.models import Subscription
        
        with app.app_context():
            sub = Subscription(
                server_name=sample_server.name,
                topic='home/+/temperatura'
            )
            db_session.add(sub)
            db_session.commit()
            
            assert sub.id is not None
            assert sub.topic == 'home/+/temperatura'


class TestSensorDataModel:
    """Tests para el modelo SensorData."""

    def test_crear_sensor_data(self, app, db_session):
        """Crear datos de sensor."""
        from src.models import SensorData
        
        with app.app_context():
            data = SensorData(
                device_id='ESP32_001',
                location='Dormitorio',
                temp_c=22.5,
                temp_h=45.0,
                temp_st=23.0
            )
            db_session.add(data)
            db_session.commit()
            
            assert data.id is not None
            assert data.temp_c == 22.5


class TestDeviceEventModel:
    """Tests para el modelo DeviceEvent."""

    def test_crear_device_event(self, app, db_session):
        """Crear evento de dispositivo."""
        from src.models import DeviceEvent
        
        with app.app_context():
            event = DeviceEvent(
                device_id='ESP32_001',
                location='Dormitorio',
                event_type='connected',
                details='Conexión establecida'
            )
            db_session.add(event)
            db_session.commit()
            
            assert event.id is not None
            assert event.timestamp is not None


class TestDeviceLogModel:
    """Tests para el modelo DeviceLog."""

    def test_crear_device_log(self, app, db_session):
        """Crear log de dispositivo."""
        from src.models import DeviceLog
        
        with app.app_context():
            log = DeviceLog(
                device_id='ESP32_001',
                location='Dormitorio',
                level='INFO',
                message='Device started successfully'
            )
            db_session.add(log)
            db_session.commit()
            
            assert log.id is not None
            assert log.level == 'INFO'

    def test_device_log_niveles(self, app, db_session):
        """Crear logs con diferentes niveles."""
        from src.models import DeviceLog
        
        with app.app_context():
            log_debug = DeviceLog(
                device_id='ESP32_001',
                location='Test',
                level='DEBUG',
                message='Debug message'
            )
            log_error = DeviceLog(
                device_id='ESP32_001',
                location='Test',
                level='ERROR',
                message='Error message'
            )
            db_session.add_all([log_debug, log_error])
            db_session.commit()
            
            assert log_debug.level == 'DEBUG'
            assert log_error.level == 'ERROR'


class TestSettingModel:
    """Tests para el modelo Setting."""

    def test_crear_setting(self, app, db_session):
        """Crear un ajuste."""
        from src.models import Setting
        
        with app.app_context():
            setting = Setting(key='theme', value='dark')
            db_session.add(setting)
            db_session.commit()
            
            assert setting.key == 'theme'
            assert setting.value == 'dark'

    def test_setting_update(self, app, db_session):
        """Actualizar un ajuste."""
        from src.models import Setting
        
        with app.app_context():
            setting = Setting(key='theme', value='light')
            db_session.add(setting)
            db_session.commit()
            
            setting.value = 'dark'
            db_session.commit()
            
            updated = Setting.query.filter_by(key='theme').first()
            assert updated.value == 'dark'
