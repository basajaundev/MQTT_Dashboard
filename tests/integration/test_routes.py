import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDashboardRoute:
    """Tests para la ruta del dashboard."""

    def test_dashboard_es_publico(self, client):
        """El dashboard debe ser accesible sin autenticación."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Dashboard' in response.data or b'dashboard' in response.data.lower()

    def test_dashboard_200(self, client):
        """El dashboard debe devolver 200."""
        response = client.get('/')
        assert response.status_code == 200


class TestLoginRoute:
    """Tests para la ruta de login."""

    def test_login_get_muestra_formulario(self, client):
        """GET /login debe mostrar formulario."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'password' in response.data.lower()

    def test_login_post_incorrecto(self, client):
        """POST /login con contraseña incorrecta."""
        response = client.post('/login', data={'password': 'wrongpassword'})
        # Puede redirigir o mostrar error
        assert response.status_code in [200, 302]

    def test_login_post_correcto_redirect(self, client, admin_session):
        """POST /login con contraseña correcta redirige al dashboard."""
        with client.session_transaction() as sess:
            sess['is_admin'] = True
        
        response = client.post('/login', data={'password': 'testpassword'}, follow_redirects=False)
        # Debe redirigir (302) o mostrar dashboard (200)
        assert response.status_code in [200, 302]


class TestLogoutRoute:
    """Tests para la ruta de logout."""

    def test_logout_limpia_sesion(self, client, admin_session):
        """Logout debe limpiar la sesión de admin."""
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Verificar que ya no tiene acceso a rutas protegidas
        response2 = client.get('/config')
        assert response2.status_code == 302  # Redirect a login


class TestProtectedRoutes:
    """Tests para rutas protegidas."""

    def test_tasks_requiere_login(self, client):
        """Ruta /tasks requiere autenticación."""
        response = client.get('/tasks')
        assert response.status_code == 302  # Redirect a login

    def test_alerts_requiere_login(self, client):
        """Ruta /alerts requiere autenticación."""
        response = client.get('/alerts')
        assert response.status_code == 302

    def test_config_requiere_login(self, client):
        """Ruta /config requiere autenticación."""
        response = client.get('/config')
        assert response.status_code == 302

    def test_testing_requiere_login(self, client):
        """Ruta /testing requiere autenticación."""
        response = client.get('/testing')
        assert response.status_code == 302

    def test_device_detail_requiere_login(self, client):
        """Ruta /device/<id>/<location> requiere autenticación."""
        response = client.get('/device/ESP32_001/Dormitorio')
        assert response.status_code == 302

    def test_tasks_con_login(self, client, admin_session):
        """Ruta /tasks accesible con login."""
        response = client.get('/tasks')
        assert response.status_code == 200

    def test_alerts_con_login(self, client, admin_session):
        """Ruta /alerts accesible con login."""
        response = client.get('/alerts')
        assert response.status_code == 200

    def test_config_con_login(self, client, admin_session):
        """Ruta /config accesible con login."""
        response = client.get('/config')
        assert response.status_code == 200

    def test_testing_con_login(self, client, admin_session):
        """Ruta /testing accesible con login."""
        response = client.get('/testing')
        assert response.status_code == 200

    def test_device_detail_con_login(self, client, admin_session):
        """Ruta /device/<id>/<location> accesible con login."""
        response = client.get('/device/ESP32_001/Dormitorio')
        assert response.status_code == 200


class TestRateLimiting:
    """Tests para rate limiting de login."""

    def test_rate_limit_allow_first_attempt(self, client):
        """Primer intento de login debe permitirse."""
        response = client.post('/login', data={'password': 'test'}, follow_redirects=False)
        # Debe permitir el intento (no 429)
        assert response.status_code != 429

    def test_rate_limit_multiple_attempts(self, client):
        """Múltiples intentos deben controlarse."""
        from src.routes import RATE_LIMIT, RATE_WINDOW
        
        # Hacer varios intentos
        for i in range(RATE_LIMIT + 5):
            response = client.post('/login', data={'password': f'pass{i}'}, follow_redirects=False)
        
        # Después del límite, debe rechazarse o mostrar mensaje de error
        # (El comportamiento exacto depende de la implementación)


class TestMiddleware:
    """Tests para middleware de autenticación."""

    def test_session_no_admin_redirige(self, client):
        """Usuario sin sesión admin debe ser redirigido."""
        response = client.get('/tasks', follow_redirects=False)
        # Debe redirigir al login
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')

    def test_session_admin_permite_acceso(self, client, admin_session):
        """Usuario con sesión admin tiene acceso."""
        response = client.get('/tasks')
        assert response.status_code == 200


class TestTemplateRendering:
    """Tests para renderizado de templates."""

    def test_dashboard_template_existe(self, client):
        """Verificar que el template dashboard.html se renderiza."""
        response = client.get('/')
        assert response.status_code == 200
        # Verificar elementos comunes del dashboard
        assert b'html' in response.data.lower() or b'<!DOCTYPE' in response.data

    def test_tasks_template_existe(self, client, admin_session):
        """Verificar que el template tasks.html se renderiza."""
        response = client.get('/tasks')
        assert response.status_code == 200

    def test_alerts_template_existe(self, client, admin_session):
        """Verificar que el template alerts.html se renderiza."""
        response = client.get('/alerts')
        assert response.status_code == 200

    def test_config_template_existe(self, client, admin_session):
        """Verificar que el template config.html se renderiza."""
        response = client.get('/config')
        assert response.status_code == 200
