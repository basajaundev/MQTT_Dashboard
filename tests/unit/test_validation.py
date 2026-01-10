import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.validation import (
    validate_password,
    validate_topic,
    validate_payload,
    validate_device_id,
    validate_location,
    PASSWORD_MIN_LEN,
    PASSWORD_MAX_LEN,
    TOPIC_MAX_LEN
)


class TestValidatePassword:
    """Tests para la función validate_password."""

    def test_password_valido_longitud_minima(self):
        """Password con exactamente la longitud mínima."""
        password = 'a' * PASSWORD_MIN_LEN
        result, error = validate_password(password)
        assert result is True
        assert error == ''

    def test_password_valido_longitud_media(self):
        """Password con longitud media válida."""
        password = 'securePassword123'
        result, error = validate_password(password)
        assert result is True
        assert error == ''

    def test_password_valido_longitud_maxima(self):
        """Password con exactamente la longitud máxima."""
        password = 'a' * PASSWORD_MAX_LEN
        result, error = validate_password(password)
        assert result is True
        assert error == ''

    def test_password_muy_corto(self):
        """Password muy corto debe fallar."""
        result, error = validate_password('123')
        assert result is False
        assert 'al menos' in error.lower()

    def test_password_vacio(self):
        """Password vacío debe fallar."""
        result, error = validate_password('')
        assert result is False
        assert 'vacía' in error.lower() or 'vacío' in error.lower()

    def test_password_none(self):
        """Password None debe fallar."""
        result, error = validate_password(None)
        assert result is False

    def test_password_con_espacio(self):
        """Password con espacio debe fallar."""
        result, error = validate_password('pass word')
        assert result is False
        assert 'espacio' in error.lower()

    def test_password_con_espacios_multiples(self):
        """Password con múltiples espacios debe fallar."""
        result, error = validate_password('pass  word')
        assert result is False
        assert 'espacio' in error.lower()

    def test_password_excede_maximo(self):
        """Password que excede el máximo debe fallar."""
        password = 'a' * (PASSWORD_MAX_LEN + 1)
        result, error = validate_password(password)
        assert result is False
        assert 'exceder' in error.lower() or 'máximo' in error.lower()

    def test_password_solo_numeros(self):
        """Password con solo números es válido."""
        result, error = validate_password('12345678')
        assert result is True

    def test_password_solo_letras(self):
        """Password con solo letras es válido."""
        result, error = validate_password('abcdefgh')
        assert result is True

    def test_password_alphanumerico(self):
        """Password alfanumérico es válido."""
        result, error = validate_password('abc123def')
        assert result is True

    def test_password_caracteres_especiales(self):
        """Password con caracteres especiales es válido."""
        result, error = validate_password('pass@#$%^&*')
        assert result is True


class TestValidateTopic:
    """Tests para la función validate_topic."""

    def test_topic_simple_valido(self):
        """Topic simple válido."""
        result, error = validate_topic('casa/salon/temperatura')
        assert result is True
        assert error == ''

    def test_topic_con_nivel_unico(self):
        """Topic con un solo nivel."""
        result, error = validate_topic('temperatura')
        assert result is True

    def test_topic_con_wildcard_single(self):
        """Topic con wildcard + (nivel único)."""
        result, error = validate_topic('casa/+/temperatura')
        assert result is True
        assert error == ''

    def test_topic_con_wildcard_multiples(self):
        """Topic con múltiples wildcards +."""
        result, error = validate_topic('casa/+/+/sensor')
        assert result is True

    def test_topic_con_wildcard_all(self):
        """Topic con wildcard # (todos los niveles)."""
        result, error = validate_topic('casa/#')
        assert result is True
        assert error == ''

    def test_topic_vacio(self):
        """Topic vacío debe fallar."""
        result, error = validate_topic('')
        assert result is False
        assert 'vacío' in error.lower()

    def test_topic_none(self):
        """Topic None debe fallar."""
        result, error = validate_topic(None)
        assert result is False

    def test_topic_caracter_invalido(self):
        """Topic con carácter inválido debe fallar."""
        result, error = validate_topic('casa@salon/temp')
        assert result is False
        assert 'inválido' in error.lower()

    def test_topic_con_espacio(self):
        """Topic con espacio debe fallar."""
        result, error = validate_topic('casa salon/temp')
        assert result is False

    def test_topic_excede_maximo(self):
        """Topic que excede el máximo debe fallar."""
        topic = 'a' * (TOPIC_MAX_LEN + 1)
        result, error = validate_topic(topic)
        assert result is False
        assert 'exceder' in error.lower()

    def test_topic_con_secuencia_punto_punto(self):
        """Topic con '..' debe fallar."""
        result, error = validate_topic('casa/../salon')
        assert result is False
        assert 'secuencia' in error.lower() or 'path' in error.lower()

    def test_topic_inicia_con_punto_punto(self):
        """Topic que inicia con '/..' debe fallar."""
        result, error = validate_topic('/../salon')
        assert result is False

    def test_topic_contiene_punto_punto(self):
        """Topic que contiene '/..' debe fallar."""
        result, error = validate_topic('casa/../salon')
        assert result is False

    def test_topic_con_guion_bajo(self):
        """Topic con guion bajo es válido."""
        result, error = validate_topic('casa/salon_sensor/temp')
        assert result is True

    def test_topic_con_guion(self):
        """Topic con guion es válido."""
        result, error = validate_topic('casa/salon-sensor/temp')
        assert result is True

    def test_topic_con_numeros(self):
        """Topic con números es válido."""
        result, error = validate_topic('casa/room123/temp')
        assert result is True

    def test_topic_con_mas(self):
        """Topic con + (single level wildcard) es válido."""
        result, error = validate_topic('+/temp')
        assert result is True

    def test_topic_con_numeral(self):
        """Topic con # (multi level wildcard) es válido."""
        result, error = validate_topic('#')
        assert result is True

    def test_topic_con_signo_mas_y_numeral(self):
        """Topic con + y # es válido."""
        result, error = validate_topic('casa/+/sensor/#')
        assert result is True

    def test_topic_con_asterisco(self):
        """Topic con asterisco es válido (caracter válido)."""
        result, error = validate_topic('casa/*/temp')
        assert result is True


class TestValidatePayload:
    """Tests para la función validate_payload."""

    def test_payload_none(self):
        """Payload None es válido."""
        result, error = validate_payload(None)
        assert result is True
        assert error == ''

    def test_payload_vacio(self):
        """Payload vacío es válido."""
        result, error = validate_payload('')
        assert result is True

    def test_payload_string_pequeno(self):
        """Payload string pequeño es válido."""
        result, error = validate_payload('{"cmd": "test"}')
        assert result is True

    def test_payload_json_grande(self):
        """Payload JSON grande es válido."""
        payload = '{"data": "' + 'x' * 5000 + '"}'
        result, error = validate_payload(payload)
        assert result is True

    def test_payload_bytes_pequeno(self):
        """Payload bytes pequeño es válido."""
        result, error = validate_payload(b'{"cmd": "test"}')
        assert result is True

    def test_payload_bytes_vacio(self):
        """Payload bytes vacío es válido."""
        result, error = validate_payload(b'')
        assert result is True


class TestValidateDeviceId:
    """Tests para la función validate_device_id."""

    def test_device_id_valido_alfanumerico(self):
        """Device ID alfanumérico válido."""
        result, error = validate_device_id('ESP32_001')
        assert result is True
        assert error == ''

    def test_device_id_valido_con_guion(self):
        """Device ID con guion es válido."""
        result, error = validate_device_id('device-001')
        assert result is True

    def test_device_id_valido_con_guion_bajo(self):
        """Device ID con guion bajo es válido."""
        result, error = validate_device_id('device_001')
        assert result is True

    def test_device_id_valido_con_arrob(self):
        """Device ID con @ es válido."""
        result, error = validate_device_id('device@001')
        assert result is True

    def test_device_id_valido_solo_numeros(self):
        """Device ID con solo números es válido."""
        result, error = validate_device_id('123456')
        assert result is True

    def test_device_id_vacio(self):
        """Device ID vacío debe fallar."""
        result, error = validate_device_id('')
        assert result is False
        assert 'vacío' in error.lower()

    def test_device_id_none(self):
        """Device ID None debe fallar."""
        result, error = validate_device_id(None)
        assert result is False

    def test_device_id_muy_largo(self):
        """Device ID muy largo debe fallar."""
        result, error = validate_device_id('a' * 101)
        assert result is False
        assert 'largo' in error.lower()

    def test_device_id_con_espacio(self):
        """Device ID con espacio debe fallar."""
        result, error = validate_device_id('device 001')
        assert result is False

    def test_device_id_con_punto(self):
        """Device ID con punto debe fallar."""
        result, error = validate_device_id('device.001')
        assert result is False

    def test_device_id_con_barra(self):
        """Device ID con barra debe fallar."""
        result, error = validate_device_id('device/001')
        assert result is False

    def test_device_id_con_signo_mas(self):
        """Device ID con + debe fallar."""
        result, error = validate_device_id('device+001')
        assert result is False

    def test_device_id_con_hash(self):
        """Device ID con # debe fallar."""
        result, error = validate_device_id('device#001')
        assert result is False


class TestValidateLocation:
    """Tests para la función validate_location."""

    def test_location_valida_alfanumerica(self):
        """Location alfanumérica válida."""
        result, error = validate_location('Dormitorio')
        assert result is True
        assert error == ''

    def test_location_valida_con_guion(self):
        """Location con guion es válida."""
        result, error = validate_location('Sala-de-Estar')
        assert result is True

    def test_location_valida_con_guion_bajo(self):
        """Location con guion bajo es válida."""
        result, error = validate_location('Sala_de_Estar')
        assert result is True

    def test_location_valida_solo_numeros(self):
        """Location con solo números es válida."""
        result, error = validate_location('Habitacion101')
        assert result is True

    def test_location_vacia(self):
        """Location vacía debe fallar."""
        result, error = validate_location('')
        assert result is False
        assert 'vacía' in error.lower()

    def test_location_none(self):
        """Location None debe fallar."""
        result, error = validate_location(None)
        assert result is False

    def test_location_muy_larga(self):
        """Location muy larga debe fallar."""
        result, error = validate_location('a' * 101)
        assert result is False
        assert result is False
        assert len(error) > 0  # Debe tener mensaje de error

    def test_location_con_espacio(self):
        """Location con espacio debe fallar."""
        result, error = validate_location('Sala de Estar')
        assert result is False

    def test_location_con_punto(self):
        """Location con punto debe fallar."""
        result, error = validate_location('Sala.Estar')
        assert result is False

    def test_location_con_barra(self):
        """Location con barra debe fallar."""
        result, error = validate_location('Sala/Estar')
        assert result is False

    def test_location_con_arroba(self):
        """Location con @ debe fallar."""
        result, error = validate_location('Sala@Estar')
        assert result is False

    def test_location_con_signo_mas(self):
        """Location con + debe fallar."""
        result, error = validate_location('Sala+Estar')
        assert result is False

    def test_location_con_hash(self):
        """Location con # debe fallar."""
        result, error = validate_location('Sala#Estar')
        assert result is False

    def test_location_con_parentesis(self):
        """Location con paréntesis debe fallar."""
        result, error = validate_location('Sala(Estar)')
        assert result is False
