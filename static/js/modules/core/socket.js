import { state, scheduleDevicesUpdate } from './state.js';
import { elements } from './dom.js';
import * as ui from '../ui/ui.js';
import { displayHistoryChart } from '../ui/charts.js';
import { openLoginModal } from '../modals/modals.js';
import { showToast, showToastWithAction, updateToastConfig } from '../ui/toasts.js';
import { renderDevices, renderServers } from '../device/dashboard.js';

export function initSocketListeners() {
    // --- Listener Unificado para el Estado Principal ---
    state.socket.on('state_update', (newState) => {
        console.log("Received full state update:", newState);

        // 1. Actualizar todo el estado interno
        state.isAdmin = newState.is_admin;
        state.isConnected = newState.mqtt_status?.connected || false;
        state.activeServerId = newState.active_server_id || null;
        state.config = newState.config || {};
        state.topics = newState.topics || [];
        state.tasks = newState.tasks || [];
        state.devices = newState.devices || {};
        state.alerts = newState.alerts || [];
        state.accessLists = newState.access_lists || { whitelist: [] };
        state.knownDevices = newState.known_devices || [];
        state.groups = newState.groups || [];
        state.messageTriggers = newState.message_triggers || [];

        // 2. Actualizar toda la UI (ahora que tenemos todos los datos)
        ui.updateStatus(newState.mqtt_status.connected);

        // Poblar selectores primero
        ui.populateDeviceSelects();

        // Renderizar componentes principales
        ui.renderTopics();
        ui.renderTasks();
        renderDevices();
        ui.renderAlerts();
        renderServers();
        ui.renderAccessLists();
        ui.renderGroups();
        ui.populateGroupSelect();
        ui.renderMessageTriggers();

        // Renderizar mensajes del estado completo (para persistencia entre páginas)
        if (newState.history) {
            ui.renderMessages(newState.history);
        }

        // Actualizar campos de configuración
        if (elements.serverSelector) {
            const servers = newState.config?.servers || {};
            const lastSelected = newState.config?.last_selected_server;
            elements.serverSelector.innerHTML = '';
            for (const serverName in servers) {
                const option = document.createElement('option');
                option.value = serverName;
                option.textContent = serverName;
                elements.serverSelector.appendChild(option);
            }
            if (lastSelected && servers[lastSelected]) {
                elements.serverSelector.value = lastSelected;
            }
        }
        if (elements.refreshIntervalInput) {
            const settings = newState.config?.settings || {};
            elements.refreshIntervalInput.value = settings.refresh_interval || 30;
        }
        if (elements.maxMissedPingsInput) {
            const settings = newState.config?.settings || {};
            elements.maxMissedPingsInput.value = settings.max_missed_pings || 2;
        }
        const settings = newState.config?.settings || {};
        updateToastConfig(settings);
        
        if (elements.toastSettings?.enabled) {
            elements.toastSettings.enabled.checked = settings.toast_enabled !== 'false';
            if (elements.toastSettings.duration) elements.toastSettings.duration.value = settings.toast_duration || 5;
            if (elements.toastSettings.position) elements.toastSettings.position.value = settings.toast_position || 'top-right';
            if (elements.toastSettings.animation) elements.toastSettings.animation.value = settings.toast_animation || 'fade';
            if (elements.toastSettings.types) elements.toastSettings.types.value = settings.toast_types || 'all';
        }
        if (elements.backupSection?.autoBackupEnabled) {
            elements.backupSection.autoBackupEnabled.checked = String(settings.auto_backup_enabled) === 'true';
            if (elements.backupSection.autoBackupInterval) elements.backupSection.autoBackupInterval.value = settings.auto_backup_interval || 24;
            if (elements.backupSection.autoBackupKeep) elements.backupSection.autoBackupKeep.value = settings.auto_backup_keep || 7;
        }
    });

    // --- Listeners para eventos de alta frecuencia o específicos ---
    state.socket.on('history_update', (data) => ui.renderMessages(data.history || []));
    state.socket.on('new_alert', (data) => showToast(`ALERTA: ${data.message}`, data.type || 'warning'));
    state.socket.on('device_history_response', (data) => {
        if (data.history && elements.historyChartCanvas) {
            displayHistoryChart(data.device_id, data.history);
        }
    });

    // --- Listeners para actualizaciones parciales y rápidas ---
    state.socket.on('devices_update', (data) => {
        scheduleDevicesUpdate(() => {
            state.devices = data.devices || {};
            renderDevices();
        });
    });
    state.socket.on('alerts_update', (data) => { state.alerts = data.alerts || []; ui.renderAlerts(); });
    state.socket.on('access_lists_update', (data) => {
        state.accessLists = data;
        ui.renderAccessLists();
    });
    state.socket.on('groups_update', (data) => { state.groups = data.groups || []; ui.renderGroups(); ui.populateGroupSelect(); });
    state.socket.on('known_devices_update', (data) => { state.knownDevices = data.known_devices || []; ui.populateDeviceSelects(); });
    state.socket.on('topics_update', (data) => { state.subscribedTopics = data.topics || []; ui.renderTopics(); });
    state.socket.on('task_update', (data) => { state.tasks = data.tasks || []; ui.renderTasks(); });
    state.socket.on('message_triggers_update', (data) => { state.messageTriggers = data.triggers || []; ui.renderMessageTriggers(); });
    state.socket.on('mqtt_status', (data) => {
        state.isConnected = data.connected;
        if (data.active_server_id !== undefined) {
            state.activeServerId = data.active_server_id;
        }
        ui.updateStatus(data.connected);
        renderServers();
    });
    state.socket.on('mqtt_reconnecting', (data) => ui.setReconnecting(data.reconnecting));
    
    // --- Backup Events ---
    state.socket.on('backups_list', (data) => {
        if (elements.backupSection?.backupsList) {
            renderBackupsList(data.backups || []);
        }
    });
    
    state.socket.on('backup_complete', (data) => {
        if (data.success) {
            showToast('Backup completado exitosamente', 'success');
            if (data.backups) {
                renderBackupsList(data.backups);
            }
            state.socket.emit('request_backups');
        } else {
            showToast('Error al crear backup', 'error');
        }
    });
    
    state.socket.on('backup_config_updated', (data) => {
        if (data.success) {
            showToast('Configuración de backup actualizada', 'success');
        } else {
            showToast('Error al actualizar configuración: ' + (data.error || ''), 'error');
        }
    });
    
    state.socket.on('backup_deleted', (data) => {
        if (data.success) {
            showToast('Backup eliminado', 'info');
            if (data.backups) {
                renderBackupsList(data.backups);
            }
        } else {
            showToast('Error al eliminar backup', 'error');
        }
    });
    
    state.socket.on('restore_complete', (data) => {
        if (data.success) {
            showRestartConfirmNotification();
        } else {
            showToast('Error al restaurar backup', 'error');
        }
    });
    
    state.socket.on('error', (data) => {
        showToast(data.message || 'Error desconocido', 'error');
    });

    // --- Listener de conexión inicial ---
    state.socket.on('connect', () => {
        state.socket.emit('request_initial_state');
        state.socket.emit('request_backups');
    });
}

function renderBackupsList(backups) {
    if (!elements.backupSection?.backupsList) return;
    
    const container = elements.backupSection.backupsList;
    const countEl = elements.backupSection.backupsCount;
    const selectEl = elements.backupSection?.restoreBackupSelect;
    
    if (countEl) {
        countEl.textContent = backups.length;
    }
    
    if (backups.length === 0) {
        container.innerHTML = '<div class="empty-state">No hay backups disponibles</div>';
        if (selectEl) {
            selectEl.innerHTML = '<option value="">-- No hay backups --</option>';
        }
        return;
    }
    
    container.innerHTML = backups.map(backup => `
        <div class="backup-item" data-filename="${backup.filename}">
            <div class="backup-item-info">
                <div class="backup-item-filename">${backup.filename}</div>
                <div class="backup-item-meta">${backup.display} - ${backup.size_mb} MB</div>
            </div>
            <div class="backup-item-actions">
                <button class="btn-icon" data-action="restore-backup-item" data-filename="${backup.filename}" title="Restaurar">♻️</button>
                <button class="btn-icon btn-danger" data-action="delete-backup-item" data-filename="${backup.filename}" title="Eliminar">🗑️</button>
            </div>
        </div>
    `).join('');
    
    if (selectEl) {
        selectEl.innerHTML = '<option value="">-- Seleccionar backup --</option>' +
            backups.map(backup => `<option value="${backup.filename}">${backup.display} (${backup.size_mb} MB)</option>`).join('');
    }
}

function showRestartConfirmNotification() {
    showToastWithAction(
        'Restauración completa',
        'La base de datos ha sido restaurada. ¿Reiniciar servidor ahora?',
        'warning',
        'restart_confirm',
        'Reiniciar',
        () => {
            state.socket.emit('restart_server');
        }
    );
}
