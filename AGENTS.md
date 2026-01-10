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
python -m pyright src/                           # Type check

# Testing
pip install pytest
pytest                                           # All tests
pytest -v                                        # Verbose
pytest tests/test_file.py::TestClass::test_method  # Single test

# Database
del dashboard.db && python app.py                # Reset DB
```

## Project Structure

```
MQTT_Dashboard/
├── src/                      # Python modules
│   ├── models.py            # SQLAlchemy models
│   ├── persistence.py       # DB operations
│   ├── routes.py            # Flask routes
│   ├── socket_handlers.py   # Socket.IO handlers
│   ├── mqtt_callbacks.py    # MQTT handlers
│   ├── globals.py           # App init (app, db, scheduler)
│   └── database.py          # DB setup
├── static/
│   ├── js/modules/          # ES6 modules (state.js, dom.js, ui.js, etc.)
│   └── css/modules/         # Modular CSS
├── templates/               # Jinja2 templates
├── static/sw.js            # Service Worker
└── app.py                  # Entry point
```

## Python Conventions

**Threading:** `monkey.patch_all()` BEFORE any imports in `app.py`.

**Imports:** Standard lib first, then third-party, then local.
```python
import logging
import os
from datetime import datetime

from flask import Flask
from src.globals import app, db
```

**Naming:**
- `snake_case` for variables/functions
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants

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

**SQLAlchemy:** Explicit `__tablename__`, `back_populates`, use `db.Column`.
```python
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
```

**Logging:** `logger = logging.getLogger(__name__)`. **Strings:** Single quotes, f-strings. **App Context:** Always use `with app.app_context():` for DB ops outside request handlers.

## JavaScript Conventions

**ES6 Modules:**
```javascript
import { state } from './state.js';
import { elements } from './dom.js';
```

**Indentation:** 4 spaces. **Naming:** `camelCase` for vars/functions, `PascalCase` for components.

**State:** Use `state` object from `state.js` exclusively.

**DOM:** Cache elements in `elements`, use `data-action` for clicks.
```javascript
document.body.addEventListener('click', (e) => {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action;
});
```

**Socket.IO:** Use `state.socket` exclusively. Full state sync via `request_initial_state`.

## CSS Conventions

- Modular files in `static/css/modules/`, import in `style.css`
- BEM naming: `block__element--modifier`
- CSS custom properties from `variables.css`
- Grid/flexbox for layout

## Communication Conventions

**Socket.IO Events:**
- Client → Server: `camelCase` (e.g., `add_to_whitelist`)
- Server → Client: `snake_case` (e.g., `state_update`, `new_notification`)

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
