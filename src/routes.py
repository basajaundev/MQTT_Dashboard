from flask import render_template, request, session, redirect, url_for, flash, jsonify
from functools import wraps
from src.globals import app
from src.persistence import check_admin_password
import time

# Rate limiting: {ip: [timestamp1, timestamp2, ...]}
login_attempts = {}
RATE_LIMIT = 5
RATE_WINDOW = 60  # segundos

def check_rate_limit(ip: str) -> tuple[bool, int]:
    """Comprueba si una IP ha excedido el límite de intentos.

    Args:
        ip: Dirección IP del cliente

    Returns:
        Tupla (permitido, intentos_restantes)
    """
    now = time.time()
    window_start = now - RATE_WINDOW
    
    if ip not in login_attempts:
        login_attempts[ip] = []
    
    login_attempts[ip] = [t for t in login_attempts[ip] if t > window_start]
    
    if len(login_attempts[ip]) >= RATE_LIMIT:
        return False, 0
    
    login_attempts[ip].append(now)
    return True, RATE_LIMIT - len(login_attempts[ip])

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('dashboard')) # Redirigir al dashboard para mostrar el modal
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def dashboard():
    """Renderiza la página principal del dashboard (Pública)."""
    return render_template('dashboard.html')

@app.route('/login', methods=['POST'])
def login():
    """Procesa el intento de inicio de sesión desde el modal."""
    client_ip = request.remote_addr
    allowed, remaining = check_rate_limit(client_ip)
    
    if not allowed:
        flash('Demasiados intentos. Intenta de nuevo en un minuto.', 'error')
        return redirect(url_for('dashboard'))
    
    password = request.form.get('password')
    if check_admin_password(password):
        session['is_admin'] = True
        return redirect(url_for('dashboard'))
    else:
        flash('Contraseña incorrecta.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """Cierra la sesión del administrador."""
    session.pop('is_admin', None)
    return redirect(url_for('dashboard'))

@app.route('/tasks')
@login_required
def tasks():
    """Renderiza la página de gestión de tareas (Solo Admin)."""
    return render_template('tasks.html')

@app.route('/alerts')
@login_required
def alerts():
    """Renderiza la página de gestión de alertas (Solo Admin)."""
    return render_template('alerts.html')

@app.route('/config')
@login_required
def config():
    """Renderiza la página de configuración (Solo Admin)."""
    return render_template('config.html')

@app.route('/testing')
@login_required
def testing():
    """Renderiza la página de pruebas (Solo Admin)."""
    return render_template('testing.html')

@app.route('/device/<device_id>/<location>')
@login_required
def device_detail(device_id, location):
    """Renderiza la página de detalle de un dispositivo (Solo Admin)."""
    return render_template('device.html', device_id=device_id, location=location)
