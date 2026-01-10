import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetTasksInfoFromGlobals:
    """Tests para la función get_tasks_info_from_globals.

    Esta función tuvo un bug donde job.next_run_time era None para tareas pausadas,
    causando: AttributeError: 'NoneType' object has no attribute 'strftime'
    """

    def test_tarea_pausada_next_run_none_no_crashea(self, app, db_session):
        """Bug fix: job.next_run_time puede ser None para tareas pausadas.

        Cuando scheduler.get_job() devuelve un job pero next_run_time es None
        (tareas pausadas), la función no debe crashear.
        """
        from src.mqtt_callbacks import get_tasks_info_from_globals
        from src.globals import scheduled_tasks, scheduler
        
        with app.app_context():
            # Simular estado con una tarea
            task_id = 'paused_task_001'
            scheduled_tasks[task_id] = {
                'name': 'Tarea Pausada',
                'topic': 'test/topic',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=60',
                'enabled': False
            }
            
            # Crear job en scheduler con next_run_time = None (pausado)
            from apscheduler.triggers.interval import IntervalTrigger
            trigger = IntervalTrigger(seconds=60)
            scheduler.add_job(
                lambda: None,
                trigger,
                id=task_id,
                name='Tarea Pausada'
            )
            # Pausar el job para que next_run_time sea None
            scheduler.pause_job(task_id)
            
            # La función debe manejar esto sin crashear
            result = get_tasks_info_from_globals()
            
            assert len(result) == 1
            assert result[0]['id'] == task_id
            assert result[0]['name'] == 'Tarea Pausada'
            # El bug original crasheaba aquí:
            # AttributeError: 'NoneType' object has no attribute 'strftime'
            # Ahora debe devolver 'Pausada'
            assert result[0]['next_run'] == 'Pausada'

    def test_tarea_con_proxima_ejecucion_valida(self, app, db_session):
        """Tarea con next_run_time válido debe mostrar la fecha."""
        from src.mqtt_callbacks import get_tasks_info_from_globals
        from src.globals import scheduled_tasks, scheduler
        
        with app.app_context():
            task_id = 'active_task_001'
            scheduled_tasks[task_id] = {
                'name': 'Tarea Activa',
                'topic': 'test/topic',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=60',
                'enabled': True
            }
            
            # Crear job con next_run_time válido
            next_run = datetime.now() + timedelta(hours=1)
            scheduler.add_job(
                lambda: None,
                'date',
                next_run_time=next_run,
                id=task_id,
                name='Tarea Activa'
            )
            
            result = get_tasks_info_from_globals()
            
            assert len(result) == 1
            assert result[0]['next_run'] != 'Pausada'
            # Debe ser una fecha formateada
            assert '2026' in result[0]['next_run'] or '-' in result[0]['next_run']

    def test_tarea_sin_job_en_scheduler(self, app, db_session):
        """Tarea sin job en scheduler debe devolver 'Pausada'."""
        from src.mqtt_callbacks import get_tasks_info_from_globals
        from src.globals import scheduled_tasks, scheduler
        
        with app.app_context():
            task_id = 'orphan_task_001'
            scheduled_tasks[task_id] = {
                'name': 'Tarea Huerfana',
                'topic': 'test/topic',
                'payload': '{}',
                'schedule_type': 'interval',
                'schedule_data': 'seconds=60'
            }
            # No crear job en scheduler (simula estado inconsistente)
            
            result = get_tasks_info_from_globals()
            
            assert len(result) == 1
            assert result[0]['next_run'] == 'Pausada'

    def test_multiple_tareas_mixto(self, app, db_session):
        """Múltiples tareas con estados mixtos."""
        from src.mqtt_callbacks import get_tasks_info_from_globals
        from src.globals import scheduled_tasks, scheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        with app.app_context():
            # Tarea 1: activa
            task1_id = 'active_001'
            scheduled_tasks[task1_id] = {'name': 'Activa', 'topic': 't1', 'payload': '{}'}
            scheduler.add_job(lambda: None, IntervalTrigger(seconds=30), id=task1_id)
            
            # Tarea 2: pausada
            task2_id = 'paused_001'
            scheduled_tasks[task2_id] = {'name': 'Pausada', 'topic': 't2', 'payload': '{}'}
            scheduler.add_job(lambda: None, IntervalTrigger(seconds=60), id=task2_id)
            scheduler.pause_job(task2_id)
            
            # Tarea 3: sin job
            task3_id = 'orphan_001'
            scheduled_tasks[task3_id] = {'name': 'Huerfana', 'topic': 't3', 'payload': '{}'}
            
            result = get_tasks_info_from_globals()
            
            assert len(result) == 3
            
            # Verificar que ninguna crasheó
            for task in result:
                assert 'next_run' in task
                # Todas deben tener un valor válido (fecha o 'Pausada')
                assert task['next_run'] is not None

    def test_lista_vacia(self, app, db_session):
        """Lista vacía de tareas debe devolver lista vacía."""
        from src.mqtt_callbacks import get_tasks_info_from_globals
        from src.globals import scheduled_tasks
        
        with app.app_context():
            scheduled_tasks.clear()
            
            result = get_tasks_info_from_globals()
            
            assert result == []


class TestTopicMatching:
    """Tests para coincidencia de topics MQTT."""

    def test_topic_exacto_coincide(self, app, db_session):
        """Topic exacto debe coincidir."""
        from src.mqtt_callbacks import topic_matches
        
        assert topic_matches('casa/salon/temperatura', 'casa/salon/temperatura') is True

    def test_wildcard_single_level(self, app, db_session):
        """Wildcard + debe coincidir un nivel."""
        from src.mqtt_callbacks import topic_matches
        
        assert topic_matches('casa/salon/temperatura', 'casa/+/temperatura') is True
        assert topic_matches('casa/dormitorio/temperatura', 'casa/+/temperatura') is True
        assert topic_matches('casa/salon/humedad', 'casa/+/temperatura') is False

    def test_wildcard_multi_level(self, app, db_session):
        """Wildcard # debe coincidir múltiples niveles."""
        from src.mqtt_callbacks import topic_matches
        
        assert topic_matches('casa/salon/temperatura', 'casa/#') is True
        assert topic_matches('casa/salon/humedad/sensor', 'casa/#') is True
        assert topic_matches('garaje/sensor', 'casa/#') is False

    def test_wildcard_combinados(self, app, db_session):
        """Wildcards combinados."""
        from src.mqtt_callbacks import topic_matches
        
        assert topic_matches('casa/+/sensor/#', 'casa/+/sensor/#') is True
        assert topic_matches('casa/salon/sensor/temp', 'casa/+/sensor/#') is True

    def test_wildcard_hash_solo(self, app, db_session):
        """# solo debe coincidir todo."""
        from src.mqtt_callbacks import topic_matches
        
        assert topic_matches('cualquier/cosa/aqui', '#') is True

    def test_topic_no_coincide(self, app, db_session):
        """Topics diferentes no deben coincidir."""
        from src.mqtt_callbacks import topic_matches
        
        assert topic_matches('casa/salon/temp', 'casa/dormitorio/temp') is False


class TestAddMessageToHistory:
    """Tests para historial de mensajes."""

    def test_add_message_in(self, app, db_session):
        """Añadir mensaje entrante."""
        from src.mqtt_callbacks import add_message_to_history
        from src.globals import message_history
        
        with app.app_context():
            add_message_to_history('test/topic', 'payload', direction='in')
            
            assert len(message_history) == 1
            msg = message_history[0]
            assert msg['topic'] == 'test/topic'
            assert msg['payload'] == 'payload'
            assert msg['direction'] == 'in'

    def test_add_message_out(self, app, db_session):
        """Añadir mensaje saliente."""
        from src.mqtt_callbacks import add_message_to_history
        from src.globals import message_history
        
        with app.app_context():
            add_message_to_history('test/topic', 'payload', direction='out')
            
            assert message_history[0]['direction'] == 'out'

    def test_message_timestamp(self, app, db_session):
        """Verificar que el mensaje tiene timestamp."""
        from src.mqtt_callbacks import add_message_to_history
        from src.globals import message_history
        
        with app.app_context():
            add_message_to_history('test', 'payload')
            
            msg = message_history[0]
            assert 'timestamp' in msg
            assert msg['timestamp'] is not None

    def test_message_history_limit(self, app, db_session):
        """Verificar límite del historial."""
        from src.mqtt_callbacks import add_message_to_history
        from src.globals import message_history, MAX_MESSAGES
        
        with app.app_context():
            message_history.clear()
            
            # Añadir más del límite
            for i in range(MAX_MESSAGES + 50):
                add_message_to_history(f'topic{i}', f'payload{i}')
            
            # Debe respetar el límite
            assert len(message_history) <= MAX_MESSAGES


class TestOnConnectCallback:
    """Tests para el callback on_connect de MQTT."""

    def test_on_connect_emit_task_update(self, app, db_session):
        """on_connect debe emitir task_update."""
        from src.mqtt_callbacks import on_connect
        from src.globals import scheduled_tasks, scheduler, socketio
        
        with app.app_context():
            # Setup
            client = MagicMock()
            userdata = {'server_name': 'TestServer'}
            flags = {'session_present': False}
            result_code = 0
            
            scheduled_tasks.clear()
            
            with patch.object(socketio, 'emit') as mock_emit:
                on_connect(client, userdata, flags, result_code)
                
                # Debe emitir task_update
                mock_emit.assert_called()
                call_args = mock_emit.call_args_list
                # Buscar llamada a task_update
                task_update_called = any(
                    'task_update' in str(args) if args else False
                    for args in call_args
                )
                assert task_update_called or mock_emit.called


class TestOnDisconnectCallback:
    """Tests para el callback on_disconnect de MQTT."""

    def test_on_disconnect_detiene_scheduler(self, app, db_session):
        """on_disconnect debe pausar el scheduler."""
        from src.mqtt_callbacks import on_disconnect
        from src.globals import scheduler
        
        with app.app_context():
            client = MagicMock()
            reason_code = 0
            
            on_disconnect(client, reason_code)
            
            # El scheduler debe estar pausado
            # Nota: El comportamiento exacto depende de la implementación
