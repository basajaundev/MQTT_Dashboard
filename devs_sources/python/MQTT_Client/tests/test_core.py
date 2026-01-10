import json
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, 'D:\\Programacion\\Python\\Proyectos\\MQTT_Client')

from src.config import Config, setup_logging
from src.system import SystemController


class TestConfig(unittest.TestCase):
    """Tests para la clase Config."""
    
    def test_config_missing_file(self):
        """Test que verifica error con archivo inexistente."""
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(FileNotFoundError):
                Config("nonexistent.json")
    
    def test_config_valid_json_with_values(self):
        """Test que verifica carga de configuración con mocks."""
        mock_config_data = {
            'mqtt': {
                'broker': '192.168.1.100',
                'port': 1883,
                'device_id': 'test-device',
                'location': 'test-location',
                'username': 'user',
                'password': 'pass'
            },
            'logging': {
                'log_dir': 'logs'
            },
            'gpio': {
                'led_pin': 2
            },
            'settings': {
                'reconnect_delay': 5
            }
        }
        
        with patch('os.path.exists', return_value=True):
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.read = MagicMock(return_value=json.dumps(mock_config_data))
            
            with patch('builtins.open', return_value=mock_file):
                config = Config("dummy.json")
                
                self.assertEqual(config.BROKER, '192.168.1.100')
                self.assertEqual(config.BROKER_PORT, 1883)
                self.assertEqual(config.DEVICE, 'test-device')
                self.assertEqual(config.LOCATION, 'test-location')
                self.assertEqual(config.USERNAME, 'user')
                self.assertEqual(config.PASSWORD, 'pass')
                self.assertEqual(config.LED_GPIO_PIN, 2)
                self.assertEqual(config.RECONNECT_DELAY, 5)
    
    def test_config_default_values(self):
        """Test que verifica valores por defecto."""
        mock_config_data = {
            'mqtt': {},
            'logging': {},
            'gpio': {},
            'settings': {}
        }
        
        with patch('os.path.exists', return_value=True):
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.read = MagicMock(return_value=json.dumps(mock_config_data))
            
            with patch('builtins.open', return_value=mock_file):
                config = Config("dummy.json")
                
                self.assertEqual(config.BROKER, '127.0.0.1')
                self.assertEqual(config.BROKER_PORT, 1883)
                self.assertEqual(config.DEVICE, 'generic-device')
                self.assertEqual(config.LOCATION, 'default-location')
                self.assertEqual(config.LED_GPIO_PIN, None)
                self.assertEqual(config.RECONNECT_DELAY, 5)
    
    def test_config_invalid_json(self):
        """Test que verifica error con JSON inválido."""
        with patch('os.path.exists', return_value=True):
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.read = MagicMock(side_effect=json.JSONDecodeError("Expecting value", "", 0))
            
            with patch('builtins.open', return_value=mock_file):
                with self.assertRaises(ValueError):
                    Config("invalid.json")
    
    def test_topics_generated_correctly(self):
        """Test que verifica generación de tópicos."""
        mock_config_data = {
            'mqtt': {
                'device_id': 'test-device',
                'location': 'kitchen'
            },
            'logging': {},
            'gpio': {},
            'settings': {}
        }
        
        with patch('os.path.exists', return_value=True):
            mock_file = MagicMock()
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            mock_file.read = MagicMock(return_value=json.dumps(mock_config_data))
            
            with patch('builtins.open', return_value=mock_file):
                config = Config("dummy.json")
                
                self.assertEqual(config.PING_TOPIC, "iot/ping/all")
                self.assertEqual(config.PONG_TOPIC, "iot/pong/test-device/kitchen")
                self.assertEqual(config.CMD_TOPIC, "iot/cmd/test-device/kitchen")
                self.assertEqual(config.STATUS_TOPIC, "iot/status/test-device/kitchen")


class TestSystemController(unittest.TestCase):
    """Tests para la clase SystemController."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.controller = SystemController(led_gpio_pin=None)
    
    def test_get_uptime_returns_integer(self):
        """Test que verifica que uptime retorna un entero."""
        uptime = self.controller.get_uptime()
        self.assertIsInstance(uptime, int)
        self.assertGreaterEqual(uptime, 0)
    
    def test_get_ip_address_returns_string(self):
        """Test que verifica que IP es un string."""
        ip = self.controller.get_ip_address()
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) > 0)
    
    def test_led_state_initially_false(self):
        """Test que verifica estado inicial del LED."""
        self.assertFalse(self.controller.led_state)
    
    def test_led_on_without_gpio(self):
        """Test que LED on no falla sin GPIO configurado."""
        controller = SystemController(led_gpio_pin=None)
        controller.led_on()
        self.assertFalse(controller.led_available)
    
    def test_led_off_without_gpio(self):
        """Test que LED off no falla sin GPIO configurado."""
        controller = SystemController(led_gpio_pin=None)
        controller.led_off()
        self.assertFalse(controller.led_available)
    
    def test_toggle_led_without_gpio(self):
        """Test que toggle LED no falla sin GPIO configurado."""
        controller = SystemController(led_gpio_pin=None)
        controller.toggle_led()
        self.assertFalse(controller.led_available)
    
    def test_cleanup_without_gpio(self):
        """Test que cleanup no falla sin GPIO."""
        controller = SystemController(led_gpio_pin=None)
        controller.cleanup()
    
    def test_periphery_available_flag(self):
        """Test que verifica bandera de disponibilidad de periphery."""
        from src.system import PERIPHERY_AVAILABLE
        self.assertIsInstance(PERIPHERY_AVAILABLE, bool)
    
    def test_uptime_increases(self):
        """Test que verifica que el uptime aumenta con el tiempo."""
        controller = SystemController(led_gpio_pin=None)
        uptime1 = controller.get_uptime()
        import time
        time.sleep(0.1)
        uptime2 = controller.get_uptime()
        self.assertGreaterEqual(uptime2, uptime1)


class TestMQTTDeviceClient(unittest.TestCase):
    """Tests básicos para MQTTDeviceClient."""
    
    @patch('src.client.mqtt.Client')
    def test_client_initialization(self, mock_mqtt_client):
        """Test que verifica inicialización del cliente."""
        mock_config = MagicMock()
        mock_config.DEVICE = 'test-device'
        mock_config.USERNAME = None
        mock_config.PASSWORD = None
        mock_config.LED_GPIO_PIN = None
        mock_config.BROKER = 'localhost'
        mock_config.BROKER_PORT = 1883
        mock_config.PING_TOPIC = 'test/ping'
        mock_config.CMD_TOPIC = 'test/cmd'
        mock_config.PONG_TOPIC = 'test/pong'
        mock_config.STATUS_TOPIC = 'test/status'
        
        from src.client import MQTTDeviceClient
        client = MQTTDeviceClient(mock_config)
        
        self.assertEqual(client.config, mock_config)
        self.assertTrue(client.running)
        self.assertFalse(client.is_connected)
        self.assertIn('PING', client.command_handlers)
        self.assertIn('STATUS', client.command_handlers)
        self.assertIn('REBOOT', client.command_handlers)
        self.assertIn('LED_ON', client.command_handlers)
        self.assertIn('LED_OFF', client.command_handlers)
        self.assertIn('LED_TOGGLE', client.command_handlers)
    
    @patch('src.client.mqtt.Client')
    def test_publish_json_checks_connection(self, mock_mqtt_client):
        """Test que verifica que no se publica si no hay conexión."""
        mock_config = MagicMock()
        mock_config.DEVICE = 'test-device'
        mock_config.USERNAME = None
        mock_config.PASSWORD = None
        mock_config.LED_GPIO_PIN = None
        mock_config.STATUS_TOPIC = 'test/status'
        
        from src.client import MQTTDeviceClient
        client = MQTTDeviceClient(mock_config)
        
        client._publish_json('test/topic', {'data': 'test'})
        mock_client_instance = mock_mqtt_client.return_value
        mock_client_instance.publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
