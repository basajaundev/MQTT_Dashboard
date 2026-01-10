# AGENTS.md - MQTT Dashboard Development Guide

## Project Overview

IoT Dashboard built with Flask, Flask-SocketIO for real-time MQTT communication. Python backend, modular JavaScript frontend with CSS. Target: Raspberry Pi 3 with Armbian, dev on Windows.

## Build & Run Commands

```bash
# Setup
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt

# Run server
python app.py                                    # Flask-SocketIO at http://localhost:5000

# Dependencies
pip freeze > requirements.txt                    # Update dependencies

# Linting & Type Checking
pip install ruff pyright
python -m ruff check src/                        # Lint Python
python -m ruff check src/ --fix                  # Lint and auto-fix
python -m pyright src/                           # Type check
python -m pyright src/ --level basic             # Basic type checking

# Testing
pip install pytest pytest-cov
pytest                                           # All tests
pytest -v                                        # Verbose output
pytest tests/                                    # Run from tests directory
pytest tests/unit/                               # Unit tests only
pytest tests/integration/                        # Integration tests only
pytest tests/test_file.py                        # Specific test file
pytest tests/test_file.py::TestClass             # Specific test class
pytest tests/test_file.py::TestClass::test_method  # Single test method
pytest -k "test_name"                            # Run tests matching pattern
pytest --co -q                                   # List all test cases
pytest --tb=short                                # Short traceback on errors
pytest -x                                        # Stop on first failure

# Database
del dashboard.db && python app.py                # Reset DB (Windows)
rm -f dashboard.db && python app.py              # Reset DB (Linux/Mac)

# Development
python -c "from src.models import *; print('Models OK')"  # Quick import test
```

## Project Structure

```
MQTT_Dashboard/
├── app.py                  # Entry point (monkey.patch_all() BEFORE imports)
├── requirements.txt        # Python dependencies
├── backup_db.py            # Database backup utility
├── AGENTS.md              # This file
├── src/
│   ├── database.py        # DB initialization
│   ├── models.py          # SQLAlchemy models
│   ├── persistence.py     # DB operations (queries, CRUD)
│   ├── routes.py          # Flask HTTP routes
│   ├── socket_handlers.py # Socket.IO event handlers
│   ├── mqtt_callbacks.py  # MQTT message handlers
│   ├── globals.py         # App init (app, db, scheduler, mqtt_state)
│   ├── task_utils.py      # Scheduled task utilities
│   ├── validation.py      # Input validation functions
│   └── database_backup.py # Database backup functions
├── static/
│   ├── js/
│   │   ├── main.js        # Entry point, imports all modules
│   │   └── modules/
│   │       ├── state.js   # Global state (socket, devices, config)
│   │       ├── dom.js     # DOM element caching
│   │       ├── ui.js      # UI rendering functions
│   │       ├── events.js  # Click event handlers
│   │       ├── socket_client.js # Socket.IO setup
│   │       ├── modals.js  # Modal management
│   │       ├── toasts.js  # Toast notifications
│   │       ├── charts.js  # Chart.js integration
│   │       ├── device_detail.js # Device detail page
│   │       └── notifications.js # Browser notifications
│   ├── css/
│   │   ├── style.css      # Main CSS (imports modules/)
│   │   └── modules/
│   │       ├── variables.css  # CSS custom properties
│   │       ├── base.css       # Base styles
│   │       ├── layout.css     # Layout styles
│   │       ├── components.css # Component styles
│   │       ├── modals.css     # Modal styles
│   │       ├── toasts.css     # Toast styles
│   │       └── responsive.css # Media queries
│   └── sw.js              # Service Worker
├── templates/
│   ├── layout.html        # Base template
│   ├── dashboard.html     # Main dashboard
│   ├── device.html        # Device detail page
│   ├── config.html        # Configuration page
│   ├── alerts.html        # Alerts page
│   ├── tasks.html         # Tasks page
│   ├── testing.html       # Testing page
│   └── login.html         # Login page
├── tests/
│   ├── conftest.py        # Pytest fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_validation.py
│   │   └── test_task_utils.py
│   └── integration/
│       ├── test_routes.py
│       ├── test_persistence.py
│       └── test_mqtt_callbacks.py
└── backups/               # Database backups
```

## Python Conventions

**Threading:** `monkey.patch_all()` MUST be called BEFORE any imports in `app.py`.

**Imports:** Standard lib first, then third-party, then local.
```python
import logging
import os
from datetime import datetime

from flask import Flask
from gevent import monkey
monkey.patch_all()

from src.globals import app, db
```

**Naming:**
- `snake_case` for variables/functions/methods
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- `_private` prefix for internal functions

**Typing:** Explicit type hints in public APIs.
```python
def connect_to_broker(broker: str, port: int) -> bool:
    """Connect to MQTT broker."""
```

**Error Handling:** Specific try/except, `logger.error()`, never expose raw exceptions.
```python
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Error: {e}")
    db.session.rollback()
```

**SQLAlchemy:** Explicit `__tablename__`, use `db.Column`.
```python
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
```

**Logging:** Use module-level logger. Single quotes for strings. Use f-strings.
```python
logger = logging.getLogger(__name__)
logger.info(f"Device connected: {device_id}")
```

**App Context:** Always use `with app.app_context():` for DB operations outside request handlers.

## JavaScript Conventions

**ES6 Modules:**
```javascript
import { state } from './state.js';
import { elements } from './dom.js';
import { showToast } from './toasts.js';
```

**Indentation:** 4 spaces. **Naming:** `camelCase` for vars/functions, `PascalCase` for components.

**State:** Use `state` object from `state.js` exclusively. Never create global variables.

**DOM:** Cache elements in `elements` object, use `data-action` for click handlers.
```javascript
document.body.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action;
});
```

**Socket.IO:** Use `state.socket` exclusively. Full state sync via `request_initial_state`.

**Avoid Duplicate Listeners:** Use flags to prevent registering socket listeners multiple times.
```javascript
let socketListenersInitialized = false;

if (!socketListenersInitialized) {
    socketListenersInitialized = true;
    state.socket.on('event', handler);
}
```

## CSS Conventions

- Modular files in `static/css/modules/`, import in `style.css`
- BEM naming: `block__element--modifier`
- CSS custom properties from `variables.css`
- Grid/flexbox for layout
- 4-space indentation

## Communication Conventions

**Socket.IO Events:**
- Client → Server: `camelCase` (e.g., `add_to_whitelist`, `request_device_config`)
- Server → Client: `snake_case` (e.g., `state_update`, `new_notification`, `device_config_update`)

**MQTT:**
- Topics: `location/device/sensor` format
- QoS: 0 (at most once), 1 (at least once)
- Retain: only for persistent state
- PING/PONG for device liveness

## General Guidelines

- **Comments:** Spanish (project convention)
- **Security:** Never commit `.env` files
- **Database:** SQLite + SQLAlchemy, explicit `db.session.commit()`
- **Service Worker:** Cache name `static-v1`, handles offline/push
- **Testing:** Write tests in `tests/unit/` and `tests/integration/`
- **Files to never commit:** `venv/`, `.env`, `dashboard.db`, `__pycache__/`, `node_modules/`
