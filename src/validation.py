import re
import logging

logger = logging.getLogger(__name__)

PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 64
TOPIC_MAX_LEN = 200
PAYLOAD_MAX_BYTES = 10 * 1024

TOPIC_PATTERN = re.compile(r'^[a-zA-Z0-9/_+\-.*#]+$')

def validate_password(password: str) -> tuple[bool, str]:
    """Valida la contraseña.

    Args:
        password: Contraseña a validar

    Returns:
        Tupla (es_valida, mensaje_error)
    """
    if not password:
        return False, 'La contraseña no puede estar vacía'
    
    if len(password) < PASSWORD_MIN_LEN:
        return False, f'La contraseña debe tener al menos {PASSWORD_MIN_LEN} caracteres'
    
    if len(password) > PASSWORD_MAX_LEN:
        return False, f'La contraseña no puede exceder {PASSWORD_MAX_LEN} caracteres'
    
    if ' ' in password:
        return False, 'La contraseña no puede contener espacios'
    
    return True, ''

def validate_topic(topic: str) -> tuple[bool, str]:
    """Valida un topic MQTT.

    Args:
        topic: Topic MQTT a validar

    Returns:
        Tupla (es_valido, mensaje_error)
    """
    if not topic:
        return False, 'El topic no puede estar vacío'
    
    if len(topic) > TOPIC_MAX_LEN:
        return False, f'El topic no puede exceder {TOPIC_MAX_LEN} caracteres'
    
    if '..' in topic or topic.startswith('/..') or '/..' in topic:
        return False, 'El topic contiene secuencias de path inválidas'
    
    if not TOPIC_PATTERN.match(topic):
        return False, 'El topic contiene caracteres inválidos'
    
    return True, ''

def validate_payload(payload: str) -> tuple[bool, str]:
    """Valida un payload MQTT.

    Args:
        payload: Payload a validar

    Returns:
        Tupla (es_válido, mensaje_error)
    """
    if payload is None:
        return True, ''
    
    payload_bytes = payload.encode('utf-8') if isinstance(payload, str) else payload
    
    if len(payload_bytes) > PAYLOAD_MAX_BYTES:
        return False, f'El payload excede el límite de {PAYLOAD_MAX_BYTES // 1024}KB'
    
    return True, ''

def validate_device_id(device_id: str) -> tuple[bool, str]:
    """Valida un ID de dispositivo.

    Args:
        device_id: ID del dispositivo a validar

    Returns:
        Tupla (es_válido, mensaje_error)
    """
    if not device_id:
        return False, 'El ID de dispositivo no puede estar vacío'
    
    if len(device_id) > 100:
        return False, 'El ID de dispositivo es demasiado largo'
    
    if not re.match(r'^[a-zA-Z0-9_\-@]+$', device_id):
        return False, 'El ID de dispositivo contiene caracteres inválidos'
    
    return True, ''

def validate_location(location: str) -> tuple[bool, str]:
    """Valida una ubicación de dispositivo.

    Args:
        location: Ubicación a validar

    Returns:
        Tupla (es_válida, mensaje_error)
    """
    if not location:
        return False, 'La ubicación no puede estar vacía'
    
    if len(location) > 100:
        return False, 'La ubicación es demasiado larga'
    
    if not re.match(r'^[a-zA-Z0-9_\-]+$', location):
        return False, 'La ubicación contiene caracteres inválidos'
    
    return True, ''
