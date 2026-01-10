from src.globals import db
from sqlalchemy.orm import relationship

class Server(db.Model):
    __tablename__ = 'servers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    broker = db.Column(db.String(200), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))

    tasks = relationship("Task", back_populates="server", cascade="all, delete-orphan")
    message_triggers = relationship("MessageTrigger", back_populates="server", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="server", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="server", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="server", cascade="all, delete-orphan")
    whitelist_devices = relationship("Whitelist", back_populates="server", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="server", cascade="all, delete-orphan")

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    server_name = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    server = relationship("Server", back_populates="groups")
    __table_args__ = (db.UniqueConstraint('server_name', 'name', name='_group_server_name_uc'),)

# Toast settings constants
TOAST_DURATION = 'toast_duration'
TOAST_POSITION = 'toast_position'
TOAST_SOUND = 'toast_sound'
TOAST_ANIMATION = 'toast_animation'
TOAST_TYPES = 'toast_types'

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    dev_id = db.Column(db.String(100), nullable=False)
    dev_name = db.Column(db.String(100), nullable=False)
    dev_location = db.Column(db.String(100), nullable=False)
    dev_alias = db.Column(db.String(100))
    dev_server = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    
    server = relationship("Server", back_populates="devices")
    __table_args__ = (db.UniqueConstraint('dev_id', 'dev_location', 'dev_server', name='_device_location_server_uc'),)

class Whitelist(db.Model):
    __tablename__ = 'whitelist'
    id = db.Column(db.Integer, primary_key=True)
    server_name = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    
    server = relationship("Server", back_populates="whitelist_devices")
    __table_args__ = (db.UniqueConstraint('server_name', 'device_id', 'location', name='_wl_server_device_loc_uc'),)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.String(36), primary_key=True)
    server_name = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    payload = db.Column(db.String(500), nullable=False)
    schedule_type = db.Column(db.String(50), nullable=False)
    schedule_data = db.Column(db.String(200), nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    executions = db.Column(db.Integer, default=0, nullable=False)
    last_run = db.Column(db.String(50), default='Nunca')

    # Placeholders support
    use_placeholders = db.Column(db.Boolean, default=True, nullable=False)

    # Response analysis
    response_enabled = db.Column(db.Boolean, default=False, nullable=False)
    response_topic = db.Column(db.String(200))
    response_timeout = db.Column(db.Integer, default=10)
    response_condition = db.Column(db.String(500))
    response_action = db.Column(db.String(50))  # log, notify, error

    server = relationship("Server", back_populates="tasks")


class MessageTrigger(db.Model):
    __tablename__ = 'message_triggers'
    id = db.Column(db.String(36), primary_key=True)
    server_name = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    topic_pattern = db.Column(db.String(200), nullable=False)
    trigger_condition = db.Column(db.String(500))
    action_type = db.Column(db.String(50), nullable=False)
    action_topic = db.Column(db.String(200))
    action_payload = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    trigger_count = db.Column(db.Integer, default=0)
    last_triggered = db.Column(db.String(50))

    server = relationship("Server", back_populates="message_triggers")
    __table_args__ = (db.UniqueConstraint('server_name', 'name', name='_trigger_server_name_uc'),)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    server_name = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    
    server = relationship("Server", back_populates="subscriptions")
    __table_args__ = (db.UniqueConstraint('server_name', 'topic', name='_server_topic_uc'),)

class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)

class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=db.func.now(), index=True)
    temp_c = db.Column(db.Float)
    temp_h = db.Column(db.Float)
    temp_st = db.Column(db.Float)

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    server_name = db.Column(db.String(100), db.ForeignKey('servers.name', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    device_id = db.Column(db.String(100), nullable=False)
    metric = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(5), nullable=False)
    value = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(200))
    type = db.Column(db.String(20), default='warning', nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    server = relationship("Server", back_populates="alerts")

class DeviceEvent(db.Model):
    __tablename__ = 'device_events'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=db.func.now(), index=True)
    __table_args__ = (db.Index('idx_device_location', 'device_id', 'location'),)


class DeviceLog(db.Model):
    __tablename__ = 'device_logs'
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    level = db.Column(db.String(10), nullable=False, default='INFO')
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now(), index=True)
    __table_args__ = (db.Index('idx_log_device_location', 'device_id', 'location'),)

