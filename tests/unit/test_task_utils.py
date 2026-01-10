"""Unit tests for task_utils module."""
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCreateTaskTrigger:
    """Tests para la función _create_task_trigger."""

    def test_interval_seconds(self, app, db_session):
        """Crear trigger de intervalo en segundos."""
        from src.task_utils import _create_task_trigger
        
        trigger, info = _create_task_trigger('interval', 'seconds=30')
        
        assert trigger is not None
        assert '30' in info

    def test_interval_minutes(self, app, db_session):
        """Crear trigger de intervalo en minutos."""
        from src.task_utils import _create_task_trigger
        
        trigger, info = _create_task_trigger('interval', 'minutes=5')
        
        assert trigger is not None
        assert '5' in info

    def test_interval_hours(self, app, db_session):
        """Crear trigger de intervalo en horas."""
        from src.task_utils import _create_task_trigger
        
        trigger, info = _create_task_trigger('interval', 'hours=2')
        
        assert trigger is not None
        assert '2' in info

    def test_cron_basico(self, app, db_session):
        """Crear trigger cron básico."""
        from src.task_utils import _create_task_trigger
        
        trigger, info = _create_task_trigger('cron', 'hour=8,minute=0')
        
        assert trigger is not None

    def test_date_especifico(self, app, db_session):
        """Crear trigger de fecha específica."""
        from src.task_utils import _create_task_trigger
        
        trigger, info = _create_task_trigger('date', '2026-12-31 23:59:00')
        
        assert trigger is not None

    def test_tipo_invalido(self, app, db_session):
        """Tipo de trigger inválido debe devolver None."""
        from src.task_utils import _create_task_trigger
        
        trigger, info = _create_task_trigger('invalid_type', 'data')
        
        assert trigger is None
        assert info == 'invalid'


class TestExecuteScheduledTask:
    """Tests para la función execute_scheduled_task."""

    def test_ejecutar_tarea_publica_mqtt(self, app, db_session):
        """Ejecutar tarea debe publicar en MQTT."""
        from src.task_utils import execute_scheduled_task
        from src.globals import mqtt_state
        
        with app.app_context():
            # Mock del cliente MQTT
            mock_client = MagicMock()
            mqtt_state['client'] = mock_client
            
            execute_scheduled_task('task-001', 'test/topic', '{"cmd": "test"}')
            
            # Verificar que se publicó
            mock_client.publish.assert_called_once()
            call_args = mock_client.publish.call_args
            assert call_args[0][0] == 'test/topic'

    def test_ejecutar_tarea_sin_cliente_mqtt(self, app, db_session):
        """Ejecutar tarea sin cliente MQTT no debe crashear."""
        from src.task_utils import execute_scheduled_task
        from src.globals import mqtt_state
        
        with app.app_context():
            mqtt_state['client'] = None
            
            # No debe crashear
            execute_scheduled_task('task-001', 'test/topic', '{}')

    def test_ejecutar_tarea_incrementa_contador(self, app, db_session):
        """Ejecutar tarea debe incrementar contador."""
        from src.task_utils import execute_scheduled_task
        from src.globals import mqtt_state, scheduled_tasks
        
        with app.app_context():
            mock_client = MagicMock()
            mqtt_state['client'] = mock_client
            
            scheduled_tasks['test_count'] = {
                'name': 'Test',
                'executions': 5
            }
            
            execute_scheduled_task('test_count', 'test/topic', '{}')
            
            assert scheduled_tasks['test_count']['executions'] == 6

    def test_ejecutar_tarea_actualiza_last_run(self, app, db_session):
        """Ejecutar tarea debe actualizar last_run."""
        from src.task_utils import execute_scheduled_task
        from src.globals import mqtt_state, scheduled_tasks
        
        with app.app_context():
            mock_client = MagicMock()
            mqtt_state['client'] = mock_client
            
            scheduled_tasks['test_last'] = {
                'name': 'Test',
                'last_run': 'Nunca'
            }
            
            execute_scheduled_task('test_last', 'test/topic', '{}')
            
            assert scheduled_tasks['test_last']['last_run'] != 'Nunca'
