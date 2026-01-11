import { state } from '../core/state.js';
import { elements } from '../core/dom.js';

let currentMessageCount = 0;

export function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('dark-mode');
        if(elements.themeSwitch) elements.themeSwitch.checked = true;
    } else {
        document.body.classList.remove('dark-mode');
        if(elements.themeSwitch) elements.themeSwitch.checked = false;
    }
}

export function setReconnecting(reconnecting) {
    const icon = document.getElementById('reconnecting-icon');
    if (icon) {
        icon.style.display = reconnecting ? 'inline-block' : 'none';
    }
}

function formatUptime(seconds) {
    if (!seconds || isNaN(seconds)) return 'N/A';
    const d = Math.floor(seconds / (3600*24));
    const h = Math.floor(seconds % (3600*24) / 3600);
    const m = Math.floor(seconds % 3600 / 60);
    const s = Math.floor(seconds % 60);
    
    let result = [];
    if (d > 0) result.push(d + 'd');
    if (h > 0) result.push(h + 'h');
    if (m > 0) result.push(m + 'm');
    if (s > 0 || result.length === 0) result.push(s + 's');
    
    return result.join(' ');
}

export { formatUptime };

export function updateStatus(connected) {
    state.isConnected = connected;
    const enableControls = !connected && state.isAdmin;

    if(elements.serverSelector) elements.serverSelector.disabled = !enableControls;

    if (elements.status) {
        if (connected) {
            elements.status.className = 'status status-connected';
            elements.status.innerHTML = '<div class="status-dot"></div>Conectado';
        } else {
            elements.status.className = 'status status-disconnected';
            elements.status.innerHTML = '<div class="status-dot"></div>Desconectado';
        }
    }

    if (elements.connectBtn) {
        elements.connectBtn.style.display = connected ? 'none' : (state.isAdmin ? 'inline-block' : 'none');
    }
    if (elements.disconnectBtn) {
        elements.disconnectBtn.style.display = connected && state.isAdmin ? 'inline-block' : 'none';
    }

    if (elements.subscribeBtn) elements.subscribeBtn.disabled = !connected || !state.isAdmin;
    if (elements.publishBtn) elements.publishBtn.disabled = !connected || !state.isAdmin;
    if (elements.newTaskBtn) elements.newTaskBtn.disabled = !connected || !state.isAdmin;
    if (elements.newTriggerBtn) elements.newTriggerBtn.disabled = !connected || !state.isAdmin;
    if (elements.addAlertBtn) elements.addAlertBtn.disabled = !connected || !state.isAdmin;
}

export function renderMessages(messageHistory) {
    if (!elements.messagesList) return;
    
    currentMessageCount = messageHistory.length || 0;
    updateUnreadBadge(messageHistory);
    
    if (!messageHistory || messageHistory.length === 0) {
        elements.messagesList.innerHTML = '<div class="empty-state">📭<br>No hay mensajes aún</div>';
        return;
    }
    elements.messagesList.innerHTML = messageHistory.map(msg => {
        const directionClass = msg.direction === 'out' ? 'msg-out' : 'msg-in';
        const icon = msg.direction === 'out' ? '📤' : '📥';
        
        return `
        <div class="message-item ${directionClass}">
            <div class="message-header">
                <span class="message-topic">${icon} ${msg.topic}</span>
                <span class="message-time">${msg.timestamp}</span>
            </div>
            <div class="message-payload">${msg.payload}</div>
        </div>`;
    }).join('');
}

export function renderTopics() {
    if (!elements.topicsList) return;
    if (state.subscribedTopics.length === 0) {
        elements.topicsList.innerHTML = '<div class="empty-state">📋<br>No hay suscripciones activas</div>';
        return;
    }
    elements.topicsList.innerHTML = state.subscribedTopics.map(topic => `
        <div class="topic-item">
            <span class="topic-name">${topic}</span>
            <button class="btn-small btn-danger-text" data-action="unsubscribe" data-topic="${topic}">Cancelar</button>
        </div>`).join('');
}

export function renderTasks() {
    if (!elements.tasksList) return;
    if (state.tasks.length === 0) {
        elements.tasksList.innerHTML = '<div class="empty-state">⏰<br>No hay tareas programadas</div>';
        return;
    }
    elements.tasksList.innerHTML = state.tasks.map(task => `
        <div class="task-item ${task.enabled ? '' : 'disabled'}">
            <div class="task-header">
                <span class="task-name">${task.name}</span>
                <span class="task-badge ${task.enabled ? 'badge-enabled' : 'badge-disabled'}">${task.enabled ? 'Activa' : 'Pausada'}</span>
            </div>
            <div class="task-body">
                <div class="task-details">
                    <strong>Topic:</strong> ${task.topic}<br>
                    <strong>Payload:</strong> ${task.payload}
                </div>
                <div class="task-schedule">
                    <span class="task-stat">📅 ${task.schedule_info}</span>
                    <span class="task-stat">⏭️ ${task.next_run}</span>
                    <span class="task-stat">▶️ ${task.executions}</span>
                    <span class="task-stat">🕐 ${task.last_run}</span>
                </div>
            </div>
            <div class="task-footer">
                <button class="btn-small" data-action="edit-task" data-task-id="${task.id}">Editar</button>
                <button class="btn-small" data-action="toggle-task" data-task-id="${task.id}">${task.enabled ? 'Pausar' : 'Activar'}</button>
                <button class="btn-small btn-danger-text" data-action="delete-task" data-task-id="${task.id}">Eliminar</button>
            </div>
        </div>`).join('');
}

export function renderMessageTriggers() {
    if (!elements.triggersList) return;
    if (!state.messageTriggers || state.messageTriggers.length === 0) {
        elements.triggersList.innerHTML = '<div class="empty-state">⚡<br>No hay disparadores configurados</div>';
        return;
    }
    elements.triggersList.innerHTML = state.messageTriggers.map(trigger => `
        <div class="trigger-card ${trigger.enabled ? '' : 'disabled'}">
            <div class="trigger-info">
                <div class="trigger-name">${trigger.name}</div>
                <div class="trigger-details">
                    <span>📡 ${trigger.topic_pattern}</span>
                    ${trigger.trigger_condition ? `<span>🔍 ${trigger.trigger_condition}</span>` : ''}
                    <span class="trigger-badge ${trigger.action_type}">${trigger.action_type === 'publish' ? 'MQTT' : 'Notif'}</span>
                </div>
            </div>
            <div class="trigger-stats">
                <div class="count">${trigger.trigger_count || 0}</div>
                <div>disparos</div>
            </div>
            <div class="trigger-actions">
                <button class="btn-icon" data-action="edit-trigger" data-trigger-id="${trigger.id}" title="Editar">✏️</button>
                <button class="btn-icon" data-action="toggle-trigger" data-trigger-id="${trigger.id}" title="${trigger.enabled ? 'Desactivar' : 'Activar'}">${trigger.enabled ? '⏸️' : '▶️'}</button>
                <button class="btn-icon" data-action="delete-trigger" data-trigger-id="${trigger.id}" title="Eliminar">🗑️</button>
            </div>
        </div>`).join('');
}

function updateUnreadBadge(messageHistory) {
    const badge = document.getElementById('unreadBadge');
    if (!badge) return;
    
    const isExpanded = elements.messagesFooter?.classList.contains('expanded');
    
    if (!isExpanded && messageHistory && messageHistory.length > state.lastSeenMessageCount) {
        const unreadCount = messageHistory.length - state.lastSeenMessageCount;
        badge.textContent = unreadCount;
        badge.style.display = 'inline-flex';
    } else {
        badge.style.display = 'none';
        state.lastSeenMessageCount = messageHistory ? messageHistory.length : 0;
    }
}

export function setMessagesFooterExpanded(expanded) {
    const badge = document.getElementById('unreadBadge');
    if (expanded && badge) {
        state.lastSeenMessageCount = currentMessageCount;
        badge.style.display = 'none';
    }
    state.messagesFooterExpanded = expanded;
}

// --- Timeline Functions ---
let currentTimelineFilter = '';

export function openTimelineModal(deviceId, location) {
    if (!elements.timelineModal || !state.isAdmin) return;
    
    const deviceKey = `${deviceId}@${location}`;
    const device = state.devices[deviceKey];
    const displayName = device?.name || deviceId;
    
    if (elements.timelineDeviceInfo) {
        elements.timelineDeviceInfo.innerHTML = `<span>${displayName}</span><span class="device-location">${deviceKey}</span>`;
    }
    
    if (elements.timelineContainer) {
        elements.timelineContainer.innerHTML = '<div class="timeline-empty">Cargando eventos...</div>';
    }
    
    const timelineHandler = (data) => {
        if (data.device_id === deviceId && data.location === location) {
            setCurrentTimelineData(data);
            state.socket.off('device_events_response', timelineHandler);
        }
    };
    state.socket.on('device_events_response', timelineHandler);
    
    state.socket.emit('get_device_events', { device_id: deviceId, location: location, limit: 100 });
    
    elements.timelineModal.style.display = 'flex';
}

export function renderTimeline(data) {
    if (!elements.timelineContainer) return;
    
    const events = data.events || [];
    
    if (events.length === 0) {
        elements.timelineContainer.innerHTML = '<div class="timeline-empty">📭 No hay eventos registrados</div>';
        return;
    }
    
    const filter = currentTimelineFilter;
    const filteredEvents = filter ? events.filter(e => e.event_type === filter) : events;
    
    if (filteredEvents.length === 0) {
        elements.timelineContainer.innerHTML = '<div class="timeline-empty">📭 No hay eventos para este filtro</div>';
        return;
    }
    
    elements.timelineContainer.innerHTML = filteredEvents.map(event => {
        const iconInfo = getTimelineIcon(event.event_type);
        
        return `
            <div class="timeline-item" data-event-type="${event.event_type}">
                <div class="timeline-icon ${iconInfo.class}">${iconInfo.icon}</div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-type">${iconInfo.label}</span>
                        <span class="timeline-time">${event.timestamp}</span>
                    </div>
                    ${event.details ? `<div class="timeline-details">${event.details}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function getTimelineIcon(eventType) {
    const icons = {
        'connected': { icon: '🟢', class: 'connected', label: 'Conectado' },
        'disconnected': { icon: '🔴', class: 'disconnected', label: 'Desconectado' },
        'offline': { icon: '⚠️', class: 'offline', label: 'Offline' }
    };
    return icons[eventType] || { icon: '📌', class: '', label: eventType };
}

export function setTimelineFilter(filter) {
    currentTimelineFilter = filter;
    
    if (state.currentTimelineData) {
        renderTimeline(state.currentTimelineData);
    }
}

export function setCurrentTimelineData(data) {
    state.currentTimelineData = data;
    renderTimeline(data);
}

export function renderAlerts() {
    if (!elements.alertsList) return;

    const alerts = state.alerts || [];

    if (alerts.length === 0) {
        elements.alertsList.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🔔</span>
                <span class="empty-title">Sin alertas configuradas</span>
                <span class="empty-action">Crea una alerta para recibir notificaciones</span>
            </div>`;
        return;
    }

    elements.alertsList.innerHTML = alerts.map(alert => {
        let icon = '⚠️';
        let typeClass = 'alert-warning';

        if (alert.type === 'error') { icon = '🚨'; typeClass = 'alert-error'; }
        else if (alert.type === 'success') { icon = '✅'; typeClass = 'alert-success'; }
        else if (alert.type === 'info') { icon = 'ℹ️'; typeClass = 'alert-info'; }

        return `
        <div class="alert-item ${typeClass}">
            <div class="alert-header">
                <span class="alert-name">${icon} ${alert.name}</span>
            </div>
            <div class="alert-body">
                <div class="alert-condition">
                    SI <strong>${alert.device_id === '*' ? 'Cualquier Dispositivo' : alert.device_id}</strong> >
                    <strong>${alert.metric}</strong> ${alert.operator} <strong>${alert.value}</strong>
                </div>
                <div class="alert-message">"${alert.message}"</div>
            </div>
            <div class="alert-footer">
                <button class="btn-small" data-action="edit-alert" data-alert-id="${alert.id}">Editar</button>
                <button class="btn-small btn-danger-text" data-action="delete-alert" data-alert-id="${alert.id}">Eliminar</button>
            </div>
        </div>`;
    }).join('');
}

export function populateDeviceSelects() {
    const knownDevices = state.knownDevices || [];

    if (elements.alertDevice) {
        elements.alertDevice.innerHTML = '<option value="*">Cualquier Dispositivo (*)</option>';
        knownDevices.forEach(d => {
            const option = document.createElement('option');
            const value = `${d.id}@${d.location}`;
            option.value = value;
            option.textContent = `${d.name} (${value})`;
            elements.alertDevice.appendChild(option);
        });
    }

    if (elements.whitelistInput) {
        elements.whitelistInput.innerHTML = '<option value="">Dispositivo...</option>';
        knownDevices.forEach(d => {
            const option = document.createElement('option');
            const value = `${d.id}@${d.location}`;
            option.value = value;
            option.textContent = `${d.name} (${value})`;
            elements.whitelistInput.appendChild(option);
        });
    }
}

export function renderAccessLists() {
    if (!elements.whitelistContainer) return;

    const whitelist = state.accessLists?.whitelist || [];

    elements.whitelistContainer.innerHTML = whitelist.length ? whitelist.map(device => {
        const label = device.group_name
            ? `${device.name}@${device.location} [${device.group_name}]`
            : `${device.name}@${device.location}`;
        return `
            <div class="list-item">
                <span>${label}</span>
                <div class="list-item-actions">
                    <button class="btn-small btn-danger-text" data-action="remove-from-whitelist"
                        data-device-id="${device.id}" data-location="${device.location}"
                        ${!state.isAdmin ? 'disabled' : ''}>Eliminar</button>
                </div>
            </div>`;
    }).join('') : `
        <div class="empty-state">
            <span class="empty-icon">📭</span>
            <span class="empty-title">Whitelist vacía</span>
            <span class="empty-action">Selecciona un dispositivo y añádelo desde Configuración</span>
        </div>
    `;
}

export function renderGroups() {
    if (!elements.groupsList) return;

    const groups = state.groups || [];

    if (groups.length === 0) {
        elements.groupsList.innerHTML = `
            <div class="empty-state">
                <span class="empty-title">Sin grupos</span>
                <span class="empty-action">Crea un grupo para organizar tus dispositivos</span>
            </div>
        `;
        return;
    }

    elements.groupsList.innerHTML = groups.map(g => `
        <div class="list-item">
            <span>${g.name}</span>
            <div class="list-item-actions">
                <button class="btn-small" data-action="edit-group" data-group-id="${g.id}">Editar</button>
                <button class="btn-small btn-danger-text" data-action="delete-group" data-group-id="${g.id}">Eliminar</button>
            </div>
        </div>
    `).join('');
}

export function showConfirmDialog(options) {
    const {
        title = 'Confirmar',
        message = '¿Estás seguro?',
        details = '',
        confirmText = 'Confirmar',
        cancelText = 'Cancelar',
        type = 'info'
    } = options;

    const iconEmoji = type === 'danger' ? '⚠️' : type === 'warning' ? '⚡' : 'ℹ️';

    return new Promise((resolve) => {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.innerHTML = `
            <div class="confirm-content">
                <div class="confirm-header">
                    <span class="confirm-icon ${type}">${iconEmoji}</span>
                    <span class="confirm-title">${title}</span>
                </div>
                <div class="confirm-message">${message}</div>
                ${details ? `<div class="confirm-details">${details}</div>` : ''}
                <div class="confirm-actions">
                    <button class="btn-secondary" id="confirm-cancel">${cancelText}</button>
                    <button class="btn-${type === 'danger' ? 'danger' : 'primary'}" id="confirm-ok">${confirmText}</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);

        dialog.querySelector('#confirm-cancel').onclick = () => {
            dialog.remove();
            resolve(false);
        };

        dialog.querySelector('#confirm-ok').onclick = () => {
            dialog.remove();
            resolve(true);
        };
    });
}

export function populateGroupSelect() {
    if (!elements.whitelistGroupInput) return;

    const groups = state.groups || [];
    elements.whitelistGroupInput.innerHTML = '<option value="">Grupo...</option>' +
        groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
}

export function showNotification(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${getNotificationIcon(type)}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" data-action="close-toast">&times;</button>
    `;

    container.appendChild(toast);

    toast.querySelector('[data-action="close-toast"]').onclick = () => {
        toast.remove();
    };

    setTimeout(() => {
        if (toast.parentNode) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

function getNotificationIcon(type) {
    const icons = {
        'error': '🚨',
        'warning': '⚠️',
        'success': '✅',
        'info': 'ℹ️'
    };
    return icons[type] || icons.info;
}

export function showFieldError(inputId, message) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.classList.add('input-error');
    input.setAttribute('title', message);

    input.onblur = function() {
        this.classList.remove('input-error');
        this.removeAttribute('title');
    };
}
