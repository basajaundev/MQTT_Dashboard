import { initElements, elements } from './modules/dom.js';
import { initSocketListeners, setupNotificationListener } from './modules/socket_client.js';
import { initEventListeners } from './modules/events.js';
import { applyTheme } from './modules/ui.js';
import { showToast } from './modules/toasts.js';
import { initNotifications } from './modules/notifications.js';
import { state } from './modules/state.js';

document.addEventListener('DOMContentLoaded', () => {
    initElements();
    initSocketListeners();
    initEventListeners();

    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    initNotifications();
    setupNotificationListener();

    state.socket.on('state_update', (newState) => {
        if (elements && elements.notificationsControls) {
            elements.notificationsControls.style.display = newState.is_admin ? 'flex' : 'none';
        }
    });
});
