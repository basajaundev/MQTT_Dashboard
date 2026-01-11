import { elements } from '../core/dom.js';
import * as modals from '../modals/modals.js';
import * as ui from '../ui/ui.js';
import { showToast } from '../ui/toasts.js';
import { state } from '../core/state.js';

export async function initEventListeners() {
    console.log('[DEBUG] initEventListeners called');
    console.log('[DEBUG] elements.loginModal:', elements.loginModal);
    console.log('[DEBUG] modals.openLoginModal:', typeof modals.openLoginModal);

    // Event listener específico para el botón de login
    const loginBtn = document.querySelector('[data-action="open-login-modal"]');
    if (loginBtn) {
        loginBtn.addEventListener('click', (e) => {
            console.log('[DEBUG] Login button clicked');
            modals.openLoginModal();
        });
        console.log('[DEBUG] Login button event listener attached');
    } else {
        console.log('[DEBUG] Login button not found');
    }

    document.body.addEventListener('click', async (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        console.log('[DEBUG] Click action:', action);

        let deviceId = target.dataset.deviceId;
        let location = target.dataset.location;

        if (!deviceId && !location && state.deviceDetailData) {
            deviceId = state.deviceDetailData.deviceId;
            location = state.deviceDetailData.location;
        }

        const topic = target.dataset.topic;
        const taskId = target.dataset.taskId;
        const serverId = target.dataset.serverId;
        const alertId = target.dataset.alertId;
        const groupId = target.dataset.groupId;
        const triggerId = target.dataset.triggerId;

        switch(action) {
            case 'reboot-device': {
                const confirmed = await ui.showConfirmDialog({
                    title: 'Reiniciar dispositivo',
                    message: `¿Reiniciar "${deviceId}@${location}"?`,
                    details: 'El dispositivo se reiniciará y volverá a conectarse.',
                    type: 'warning',
                    confirmText: 'Reiniciar'
                });
                if (confirmed) state.socket.emit('reboot_device', { device_id: deviceId, location: location });
                break;
            }
            case 'delete-task': {
                const confirmed = await ui.showConfirmDialog({
                    title: 'Eliminar tarea',
                    message: '¿Eliminar esta tarea programada?',
                    type: 'danger',
                    confirmText: 'Eliminar'
                });
                if (confirmed) state.socket.emit('task_delete', { task_id: taskId });
                break;
            }
            case 'delete-server': {
                const confirmed = await ui.showConfirmDialog({
                    title: 'Eliminar servidor',
                    message: '¿Eliminar este servidor MQTT?',
                    type: 'danger',
                    confirmText: 'Eliminar'
                });
                if (confirmed) state.socket.emit('delete_server', { id: serverId });
                break;
            }
            case 'delete-alert': {
                const confirmed = await ui.showConfirmDialog({
                    title: 'Eliminar alerta',
                    message: '¿Eliminar esta alerta?',
                    type: 'danger',
                    confirmText: 'Eliminar'
                });
                if (confirmed) state.socket.emit('delete_alert', { id: alertId });
                break;
            }
            case 'save-alert': modals.saveAlert(); break;
            case 'close-alert-modal': modals.closeAlertModal(); break;
            case 'cancel-alert-modal': modals.closeAlertModal(); break;
            case 'add-task-modal': modals.openTaskModal(); break;
            case 'save-task': modals.saveTask(); break;
            case 'close-task-modal': modals.closeTaskModal(); break;
            case 'cancel-task-modal': modals.closeTaskModal(); break;
            case 'save-settings': {
                const newInterval = parseInt(elements.refreshIntervalInput.value, 10);
                const newMaxMissedPings = parseInt(elements.maxMissedPingsInput.value, 10);

                if (newInterval >= 5 && newMaxMissedPings >= 1) {
                    const settings = {
                        'refresh_interval': newInterval,
                        'max_missed_pings': newMaxMissedPings
                    };

                    state.socket.emit('save_settings', settings);

                    showToast('Ajustes guardados. Los cambios se aplicarán en la próxima conexión/ciclo.', 'success');
                } else {
                    showToast('Valores inválidos. El intervalo debe ser >= 5 y la tolerancia >= 1.', 'error');
                }
                break;
            }
            case 'manual-backup': {
                showToast('Creando backup...', 'info');
                state.socket.emit('trigger_backup');
                break;
            }
            case 'restore-backup-item': {
                const filename = target?.dataset?.filename;
                if (filename) {
                    state.socket.emit('restore_backup', { filename });
                }
                break;
            }
            case 'delete-backup-item': {
                const filename = target?.dataset?.filename;
                if (filename) {
                    showToast('Eliminando backup...', 'info');
                    state.socket.emit('delete_backup', { filename });
                }
                break;
            }
            case 'close-history-modal':
                elements.historyModal.style.display = 'none';
                break;
            case 'show-history':
                if (deviceId && location) {
                    state.currentHistoryDevice = { deviceId, location };
                    if (elements.historyDatePreset) elements.historyDatePreset.value = 'week';
                    if (elements.historyDateStart) elements.historyDateStart.value = '';
                    if (elements.historyDateEnd) elements.historyDateEnd.value = '';
                    refreshHistoryChart();
                }
                break;
            case 'refresh-history':
                refreshHistoryChart();
                break;
            case 'toggle-stats':
                const statsSection = elements.historyStatsSection;
                if (statsSection) {
                    const table = statsSection.querySelector('.stats-table');
                    const toggle = statsSection.querySelector('.stats-toggle');
                    if (table) table.style.display = table.style.display === 'none' ? 'table' : 'none';
                    if (toggle) toggle.textContent = table.style.display === 'none' ? '▶' : '▼';
                }
                break;
            case 'show-timeline':
                ui.openTimelineModal(deviceId, location);
                break;
            case 'close-timeline-modal':
                if (elements.timelineModal) elements.timelineModal.style.display = 'none';
                break;
            case 'request-status':
            case 'request-device-status': {
                state.socket.emit('request_single_device_status', { device_id: deviceId, location: location });
                showToast('Solicitando status...', 'info');
                state.socket.emit('get_device_detail', { device_id: deviceId, location: location });
                break;
            }
            case 'request-device-config': {
                state.socket.emit('request_device_config', { device_id: deviceId, location: location });
                showToast('Solicitando configuracion...', 'info');
                break;
            }
            case 'unsubscribe': state.socket.emit('mqtt_unsubscribe', { topic: topic }); break;
            case 'edit-task': modals.openTaskModal(taskId); break;
            case 'toggle-task': state.socket.emit('task_toggle', { task_id: taskId }); break;
            case 'add-server-modal': modals.openServerModal(); break;
            case 'edit-server': modals.openServerModal(serverId); break;
            case 'save-server': modals.saveServer(); break;
            case 'close-server-modal': elements.serverModal.style.display = 'none'; break;
            case 'add-alert-modal': modals.openAlertModal(); break;
            case 'edit-alert': modals.openAlertModal(alertId); break;
            case 'cancel-alert-modal': modals.closeAlertModal(); break;
            case 'add-task-modal': modals.openTaskModal(); break;
            case 'add-group-modal': modals.openGroupModal(); break;
            case 'edit-group': modals.openGroupModal(groupId); break;
            case 'save-group': modals.saveGroup(); break;
            case 'close-group-modal': modals.closeGroupModal(); break;
            case 'cancel-group-modal': modals.closeGroupModal(); break;
            case 'save-task': modals.saveTask(); break;
            case 'close-task-modal': elements.taskModal.style.display = 'none'; break;
            case 'change-password': {
                const p1 = elements.newPasswordInput.value;
                const p2 = elements.confirmPasswordInput.value;
                if (p1 && p1 === p2) {
                    state.socket.emit('change_password', { 'new_password': p1 });
                } else {
                    showToast('Las contraseñas no coinciden o están vacías.', 'error');
                }
                break;
            }
            case 'open-login-modal':
                modals.openLoginModal();
                break;
            case 'close-login-modal':
                elements.loginModal.style.display = 'none';
                break;
            case 'add-to-whitelist': {
                const selectedDevice = elements.whitelistInput?.value;
                const selectedGroupId = elements.whitelistGroupInput?.value;
                if (selectedDevice) {
                    const [devId, devLocation] = selectedDevice.split('@');
                    state.socket.emit('add_to_whitelist', {
                        device_id: devId,
                        location: devLocation,
                        group_id: selectedGroupId || null
                    });
                } else {
                    showToast('Selecciona un dispositivo', 'warning');
                }
                break;
            }
            case 'remove-from-whitelist': {
                const confirmed = await ui.showConfirmDialog({
                    title: 'Eliminar de whitelist',
                    message: `¿Eliminar "${deviceId}@${location}" de la whitelist?`,
                    details: 'El dispositivo dejará de aparecer en el dashboard.',
                    type: 'danger',
                    confirmText: 'Eliminar'
                });
                if (confirmed) {
                    state.socket.emit('remove_from_whitelist', {
                        device_id: deviceId,
                        location: location
                    });
                }
                break;
            }
            case 'edit-device-alias': {
                const modal = document.getElementById('deviceAliasModal');
                if (modal) modal.style.display = 'block';
                break;
            }
            case 'remove-device-whitelist': {
                const modal = document.getElementById('deviceRemoveModal');
                if (modal) modal.style.display = 'block';
                break;
            }
            case 'confirm-device-remove': {
                const confirmed = await ui.showConfirmDialog({
                    title: 'Eliminar dispositivo',
                    message: `¿Eliminar "${deviceId}@${location}" de la whitelist?`,
                    details: 'El dispositivo no podrá conectarse al sistema.',
                    type: 'danger',
                    confirmText: 'Eliminar'
                });
                if (confirmed) {
                    state.socket.emit('remove_from_whitelist', {
                        device_id: deviceId,
                        location: location
                    });
                }
                const modal = document.getElementById('deviceRemoveModal');
                if (modal) modal.style.display = 'none';
                break;
            }
            case 'close-device-reboot-modal':
            case 'cancel-device-reboot': {
                const modal = document.getElementById('deviceRebootModal');
                if (modal) modal.style.display = 'none';
                break;
            }
            case 'confirm-device-reboot': {
                state.socket.emit('reboot_device', { device_id: deviceId, location: location });
                const modal = document.getElementById('deviceRebootModal');
                if (modal) modal.style.display = 'none';
                break;
            }
            case 'close-device-alias-modal':
            case 'cancel-device-alias': {
                const modal = document.getElementById('deviceAliasModal');
                if (modal) modal.style.display = 'none';
                break;
            }
            case 'confirm-device-alias': {
                const aliasInput = document.getElementById('deviceAliasInput');
                const alias = aliasInput ? aliasInput.value.trim() : '';
                if (alias) {
                    state.socket.emit('update_device_alias', {
                        device_id: deviceId,
                        location: location,
                        alias: alias
                    });
                }
                const modal = document.getElementById('deviceAliasModal');
                if (modal) modal.style.display = 'none';
                break;
            }
            case 'close-device-remove-modal':
            case 'cancel-device-remove': {
                const modal = document.getElementById('deviceRemoveModal');
                if (modal) modal.style.display = 'none';
                break;
            }
            case 'add-trigger-modal': modals.openTriggerModal(); break;
            case 'save-task': modals.saveTask(); break;
            case 'close-task-modal': modals.closeTaskModal(); break;
            case 'cancel-task-modal': modals.closeTaskModal(); break;
            case 'save-trigger': modals.saveTrigger(); break;
            case 'close-trigger-modal': modals.closeTriggerModal(); break;
            case 'cancel-trigger-modal': modals.closeTriggerModal(); break;
            case 'close-trigger-modal':
                if (elements.triggerModal) elements.triggerModal.style.display = 'none';
                break;
        }
    });

    if (elements.backupSection?.autoBackupEnabled) {
        elements.backupSection.autoBackupEnabled.addEventListener('change', () => {
            console.log('[BACKUP] Auto-guardando configuración de backup...');
            state.socket.emit('update_backup_config', {
                'auto_backup_enabled': elements.backupSection.autoBackupEnabled.checked,
                'auto_backup_interval': parseInt(elements.backupSection?.autoBackupInterval?.value || 24, 10),
                'auto_backup_keep': parseInt(elements.backupSection?.autoBackupKeep?.value || 7, 10)
            });
        });
    }

    if (elements.backupSection?.autoBackupInterval) {
        elements.backupSection.autoBackupInterval.addEventListener('blur', () => {
            console.log('[BACKUP] Intervalo cambiado, guardando...');
            state.socket.emit('update_backup_config', {
                'auto_backup_enabled': elements.backupSection?.autoBackupEnabled?.checked || false,
                'auto_backup_interval': parseInt(elements.backupSection.autoBackupInterval.value, 10),
                'auto_backup_keep': parseInt(elements.backupSection?.autoBackupKeep?.value || 7, 10)
            });
        });
    }

    if (elements.backupSection?.autoBackupKeep) {
        elements.backupSection.autoBackupKeep.addEventListener('blur', () => {
            console.log('[BACKUP] Keep cambiado, guardando...');
            state.socket.emit('update_backup_config', {
                'auto_backup_enabled': elements.backupSection?.autoBackupEnabled?.checked || false,
                'auto_backup_interval': parseInt(elements.backupSection?.autoBackupInterval?.value || 24, 10),
                'auto_backup_keep': parseInt(elements.backupSection.autoBackupKeep.value, 10)
            });
        });
    }

    function refreshHistoryChart() {
        if (!state.currentHistoryDevice) return;
        const preset = elements.historyDatePreset?.value || '';
        const dateStartInput = elements.historyDateStart;
        const dateEndInput = elements.historyDateEnd;
        let startDate = null;
        let endDate = null;
        const now = new Date();
        if (preset) {
            if (preset === 'today') {
                startDate = now.toLocaleDateString('en-CA');
                endDate = startDate;
            } else if (preset === 'yesterday') {
                const yesterday = new Date(now);
                yesterday.setDate(yesterday.getDate() - 1);
                startDate = yesterday.toLocaleDateString('en-CA');
                endDate = startDate;
            } else if (preset === 'week') {
                endDate = now.toLocaleDateString('en-CA');
                const weekAgo = new Date(now);
                weekAgo.setDate(weekAgo.getDate() - 7);
                startDate = weekAgo.toLocaleDateString('en-CA');
            } else if (preset === 'month') {
                endDate = now.toLocaleDateString('en-CA');
                const monthAgo = new Date(now);
                monthAgo.setDate(monthAgo.getDate() - 30);
                startDate = monthAgo.toLocaleDateString('en-CA');
            } else if (preset === 'all') {
                startDate = null;
                endDate = null;
            }
        } else {
            startDate = dateStartInput?.value || null;
            endDate = dateEndInput?.value || null;
        }
        if (dateStartInput) dateStartInput.value = startDate || '';
        if (dateEndInput) dateEndInput.value = endDate || '';
        state.socket.emit('get_device_history', {
            device_id: state.currentHistoryDevice.deviceId,
            location: state.currentHistoryDevice.location,
            start_date: startDate,
            end_date: endDate
        });
    }

    if (elements.historyDatepicker) {
        elements.historyDatepicker.addEventListener('change', () => {
            if (state.currentHistoryDevice) {
                const date = elements.historyDatepicker.value;
                if (date) {
                    state.socket.emit('get_device_history', {
                        device_id: state.currentHistoryDevice.deviceId,
                        location: state.currentHistoryDevice.location,
                        start_date: date,
                        end_date: date
                    });
                }
            }
        });
    }

    if (elements.historyDatePreset) {
        elements.historyDatePreset.addEventListener('change', () => {
            if (elements.historyDateStart) elements.historyDateStart.value = '';
            if (elements.historyDateEnd) elements.historyDateEnd.value = '';
            refreshHistoryChart();
        });
    }

    if (elements.historyDateStart) {
        elements.historyDateStart.addEventListener('change', () => {
            if (elements.historyDatePreset) elements.historyDatePreset.value = '';
            refreshHistoryChart();
        });
    }

    if (elements.historyDateEnd) {
        elements.historyDateEnd.addEventListener('change', () => {
            if (elements.historyDatePreset) elements.historyDatePreset.value = '';
            refreshHistoryChart();
        });
    }

    if (elements.historyChartRefresh) {
        elements.historyChartRefresh.addEventListener('click', () => {
            refreshHistoryChart();
        });
    }

    if(elements.themeSwitch) {
        elements.themeSwitch.addEventListener('change', () => {
            const theme = elements.themeSwitch.checked ? 'dark' : 'light';
            localStorage.setItem('theme', theme);
            ui.applyTheme(theme);
        });
    }

    if(elements.connectBtn) elements.connectBtn.addEventListener('click', () => {
        state.socket.emit('mqtt_connect', { server_name: elements.serverSelector.value });
    });
    if(elements.disconnectBtn) elements.disconnectBtn.addEventListener('click', () => state.socket.emit('mqtt_disconnect'));
    if (elements.clearBtn) elements.clearBtn.addEventListener('click', () => state.socket.emit('clear_message_history'));
    if (elements.subscribeBtn) elements.subscribeBtn.addEventListener('click', () => { const topic = elements.topicInput.value.trim(); if (topic) state.socket.emit('mqtt_subscribe', { topic }); });
    if (elements.publishBtn) elements.publishBtn.addEventListener('click', () => { const topic = elements.publishTopic.value.trim(); const payload = elements.publishPayload.value; if (topic) state.socket.emit('mqtt_publish', { topic, payload }); });
    if (elements.configTabs) {
        elements.configTabs.addEventListener('click', (e) => {
            const target = e.target.closest('a.tab-link, button.tab-link');
            if (target && target.dataset.tab) {
                e.preventDefault();
                const tab = target.dataset.tab;
                state.currentTab = tab;
                document.querySelectorAll('.tab-content').forEach(s => {
                    if (s) s.style.display = 'none';
                });
                document.querySelectorAll('.tab-link').forEach(t => {
                    t.classList.remove('active');
                });
                const section = document.getElementById(tab);
                if (section) {
                    section.style.display = 'block';
                    target.classList.add('active');
                }
            }
        });
    }

    if (elements.messagesFooterHeader) {
        elements.messagesFooterHeader.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="clear-messages"]')) return;

            if (elements.messagesFooter) {
                const isExpanded = elements.messagesFooter.classList.toggle('expanded');
                elements.messagesFooter.classList.toggle('collapsed', !isExpanded);
                localStorage.setItem('messagesFooterExpanded', String(isExpanded));
                ui.setMessagesFooterExpanded(isExpanded);
            }
        });
    }

    document.body.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action="clear-messages"]');
        if (target) {
            state.socket.emit('clear_message_history');
        }
    });

    if (elements.messagesFooter) {
        if (state.messagesFooterExpanded) {
            elements.messagesFooter.classList.add('expanded');
            elements.messagesFooter.classList.remove('collapsed');
        } else {
            elements.messagesFooter.classList.add('collapsed');
            elements.messagesFooter.classList.remove('expanded');
        }
    }

    if (elements.timelineFilter) {
        elements.timelineFilter.addEventListener('change', (e) => {
            ui.setTimelineFilter(e.target.value);
        });
    }

    if (elements.toastSettings?.enabled) {
        elements.toastSettings.enabled.addEventListener('change', () => {
            console.log('[TOAST] Habilitación cambiada, guardando...');
            state.socket.emit('save_settings', {
                'toast_enabled': elements.toastSettings.enabled.checked
            });
        });
    }

    if (elements.toastSettings?.duration) {
        elements.toastSettings.duration.addEventListener('change', () => {
            console.log('[TOAST] Guardando configuración...');
            state.socket.emit('save_settings', {
                'toast_duration': parseInt(elements.toastSettings.duration.value, 10)
            });
        });
    }

    if (elements.toastSettings?.position) {
        elements.toastSettings.position.addEventListener('change', () => {
            console.log('[TOAST] Posición cambiada, guardando...');
            state.socket.emit('save_settings', {
                'toast_position': elements.toastSettings.position.value
            });
        });
    }

    if (elements.toastSettings?.animation) {
        elements.toastSettings.animation.addEventListener('change', () => {
            console.log('[TOAST] Animación cambiada, guardando...');
            state.socket.emit('save_settings', {
                'toast_animation': elements.toastSettings.animation.value
            });
        });
    }

    if (elements.toastSettings?.types) {
        elements.toastSettings.types.addEventListener('change', () => {
            console.log('[TOAST] Tipos visibles cambiados, guardando...');
            state.socket.emit('save_settings', {
                'toast_types': elements.toastSettings.types.value
            });
        });
    }

    window.onclick = (event) => {
        if (event.target === elements.taskModal && elements.taskModal) elements.taskModal.style.display = 'none';
        if (event.target === elements.historyModal) elements.historyModal.style.display = 'none';
        if (event.target === elements.timelineModal) elements.timelineModal.style.display = 'none';
        if (event.target === elements.loginModal && elements.loginModal) elements.loginModal.style.display = 'none';
        if (event.target === elements.serverModal) elements.serverModal.style.display = 'none';
        if (event.target === elements.alertModal) elements.alertModal.style.display = 'none';
        if (event.target === elements.groupModal) elements.groupModal.style.display = 'none';
        if (event.target === elements.triggerModal) elements.triggerModal.style.display = 'none';
        if (event.target === elements.deviceModals?.rebootModal) elements.deviceModals.rebootModal.style.display = 'none';
        if (event.target === elements.deviceModals?.aliasModal) elements.deviceModals.aliasModal.style.display = 'none';
        if (event.target === elements.deviceModals?.removeModal) elements.deviceModals.removeModal.style.display = 'none';
        if (event.target === elements.restoreBackupModal) elements.restoreBackupModal.style.display = 'none';
    };
}
