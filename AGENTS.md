# AGENTS.md - MQTT Dashboard Development Guide

## Build & Run Commands

```bash
# Setup
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt

# Run server
python app.py                                    # Flask-SocketIO at http://localhost:5000

# Update dependencies
pip freeze > requirements.txt

# Linting & Type Checking
pip install ruff pyright
python -m ruff check src/ --fix                 # Lint + auto-fix
python -m pyright src/                          # Type check

# Testing
pip install pytest pytest-cov
pytest                                          # All tests
pytest tests/unit/                              # Unit tests only
pytest tests/integration/                       # Integration tests only
pytest tests/test_file.py::TestClass::test_method  # Single test
pytest -k "test_name"                           # Tests matching pattern
pytest --tb=short -x                            # Short traceback, stop on first failure

# Database
del dashboard.db && python app.py                # Reset DB (Windows)
rm -f dashboard.db && python app.py              # Reset DB (Linux/Mac)

# Backup System (uses backup_db.py)
python backup_db.py                              # Create backup
python backup_db.py --restore                    # Restore last backup
python backup_db.py --list                       # List available backups
python backup_db.py --delete-old 30              # Delete backups older than 30 days

# Quick validation
python -c "from src.models import *; print('Models OK')"
```

## Project Structure

```
MQTT_Dashboard/
├── app.py                  # Entry point (monkey.patch_all() BEFORE imports)
├── requirements.txt        # Python dependencies
├── AGENTS.md              # This file
├── backup_db.py           # Backup manager (BackupManager class, CLI + scheduler integration)
├── src/
│   ├── database.py        # DB initialization
│   ├── models.py          # SQLAlchemy models (12 models: Server, Device, Task, Alert, etc.)
│   ├── persistence.py     # DB operations (queries, CRUD)
│   ├── routes.py          # Flask HTTP routes
│   ├── socket_handlers.py # Socket.IO event handlers (900+ lines)
│   ├── mqtt_callbacks.py  # MQTT message handlers (on_connect, on_message, on_disconnect)
│   ├── globals.py         # App init (app, db, scheduler, mqtt_state)
│   ├── validation.py      # Input validation functions
│   └── task_utils.py      # APScheduler triggers + task execution
├── static/js/
│   ├── main.js            # Entry point
│   └── modules/
│       ├── core/          # state.js, dom.js, socket.js
│       ├── ui/            # ui.js, toasts.js, charts.js
│       ├── events/        # events.js
│       ├── device/        # dashboard.js, chart.js, detail.js, response.js
│       └── modals/        # modals.js
└── tests/
    ├── conftest.py        # Pytest fixtures
    ├── unit/              # Unit tests
    └── integration/       # Integration tests
```

## Python Conventions

**Threading:** `monkey.patch_all()` MUST be called BEFORE any imports in `app.py`.

**Imports:** Standard lib → third-party → local.
```python
import logging
import os
from datetime import datetime

from flask import Flask
from gevent import monkey
monkey.patch_all()

from src.globals import app, db
```

**Naming:** `snake_case` vars/functions/methods, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.

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

**SQLAlchemy:** Explicit `__tablename__`, use `db.Column`, always `db.session.commit()`.

**App Context:** Always use `with app.app_context():` for DB operations outside request handlers.

## Backup System Architecture

**BackupManager Class** (`backup_db.py`): Central class for all backup operations.
- `create_backup()`: Creates timestamped backup with compression
- `restore_backup()`: Restores from backup file
- `rotate_backups()`: Keeps only N most recent backups
- `delete_backup()`: Removes specific backup file
- `get_backups_for_ui()`: Returns formatted list for frontend

**Integration** (`socket_handlers.py`): Backend handlers import and use BackupManager:
- `handle_request_backups()`: List available backups
- `handle_trigger_backup()`: Manual backup trigger
- `handle_update_backup_config()`: Configure auto-backup scheduler
- `handle_restore_backup()`: Restore from backup
- `handle_delete_backup()`: Delete backup file

**Settings** (stored in `settings` table):
- `auto_backup_enabled`: Enable automatic backups
- `auto_backup_interval`: Hours between backups (default: 24)
- `auto_backup_keep`: Number of backups to retain (default: 7)

**Backup Location:** `/backups/dashboard_backup_YYYYMMDD_HHMMSS.db.gz`

## JavaScript Conventions

**ES6 Modules:** Use relative imports, organize by feature (core, ui, events, device, modals).
```javascript
import { state } from './modules/core/state.js';
import { elements } from './modules/core/dom.js';
import { showToast } from './modules/ui/toasts.js';
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

**Socket.IO:** Use `state.socket` exclusively. Use flags to prevent duplicate listeners.

## Communication Conventions

**Socket.IO Events:**
- Client → Server: `camelCase` (e.g., `add_to_whitelist`)
- Server → Client: `snake_case` (e.g., `state_update`, `new_notification`)

**MQTT:** Topics `location/device/sensor`, QoS 0/1, retain only for persistent state.

## General Guidelines

- **Comments:** Spanish (project convention)
- **Security:** Never commit `.env` files
- **Database:** SQLite + SQLAlchemy, explicit `db.session.commit()`
- **Files to never commit:** `venv/`, `.env`, `dashboard.db`, `__pycache__/`, `node_modules/`
