import { initElements, elements } from './modules/core/dom.js';
import { initSocketListeners, setupNotificationListener } from './modules/socket_client.js';
import { initEventListeners } from './modules/events/events.js';
import { applyTheme } from './modules/ui/ui.js';
import { showToast } from './modules/ui/toasts.js';
import { initNotifications } from './modules/events/notifications.js';
import { state } from './modules/core/state.js';

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
