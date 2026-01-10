import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope='function')
def app():
    """Create application for the tests with temporary file-based database."""
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    
    db = SQLAlchemy(test_app)
    
    with test_app.app_context():
        from src.models import Server, Task, Subscription, Setting, SensorData, Alert, Device, Whitelist, DeviceEvent, Group, DeviceLog, MessageTrigger
        db.create_all()
    
    test_app.db = db
    test_app.db_path = db_path
    
    yield test_app
    
    db.session.remove()
    db.engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture(scope='function')
def db(app):
    """Get database from app fixture."""
    return app.db

@pytest.fixture(scope='function')
def db_session(app, db):
    """Get database session for tests that need direct db access."""
    with app.app_context():
        yield db
        db.session.rollback()

@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    with app.test_client() as test_client:
        yield test_client

@pytest.fixture(scope='function')
def admin_session(client):
    """Create an admin session for testing protected routes."""
    flask_app = client.application
    
    with flask_app.app_context():
        from src.persistence import update_admin_password
        update_admin_password('testpassword')
    
    with client.session_transaction() as sess:
        sess['is_admin'] = True
    
    yield client

@pytest.fixture
def sample_server(app):
    """Create a sample server for testing."""
    with app.app_context():
        from src.models import Server
        db = app.db
        
        server = Server(
            name='TestServer',
            broker='localhost',
            port=1883,
            username='',
            password=''
        )
        db.session.add(server)
        db.session.commit()
        server_id = server.id
        yield server
        try:
            db.session.execute(db.select(Server).filter_by(id=server_id))
            db.session.commit()
        except:
            pass

@pytest.fixture
def sample_device(app, sample_server):
    """Create a sample device for testing."""
    with app.app_context():
        from src.models import Device
        db = app.db
        
        device = Device(
            dev_id='ESP32_001',
            dev_name='Test Device',
            dev_location='Dormitorio',
            dev_alias='Mi Sensor',
            dev_server=sample_server.name
        )
        db.session.add(device)
        db.session.commit()
        device_id = device.id
        yield device
        try:
            db.session.execute(db.select(Device).filter_by(id=device_id))
            db.session.commit()
        except:
            pass

@pytest.fixture
def sample_task(app, sample_server):
    """Create a sample task for testing."""
    with app.app_context():
        from src.models import Task
        db = app.db
        
        task = Task(
            id='test-task-001',
            server_name=sample_server.name,
            name='Test Task',
            topic='test/topic',
            payload='{"cmd": "test"}',
            schedule_type='interval',
            schedule_data='seconds=60'
        )
        db.session.add(task)
        db.session.commit()
        yield task

@pytest.fixture
def mock_scheduler():
    """Create a mock scheduler."""
    from unittest.mock import MagicMock
    scheduler = MagicMock()
    scheduler.get_job.return_value = None
    return scheduler

@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    from unittest.mock import MagicMock
    client = MagicMock()
    client.is_connected.return_value = True
    client.publish.return_value = MagicMock()
    return client
