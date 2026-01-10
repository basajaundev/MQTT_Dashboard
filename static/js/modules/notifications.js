import { elements } from './core/dom.js';
import { state } from './core/state.js';

export function initNotifications() {
    state.notificationsEnabled = localStorage.getItem('notificationsEnabled') === 'true';
    state.notificationsSound = localStorage.getItem('notificationsSound') !== 'false';

    const notificationsToggle = document.getElementById('notificationsEnabled');
    const notificationsSoundToggle = document.getElementById('notificationsSound');

    if (notificationsToggle) {
        notificationsToggle.checked = state.notificationsEnabled;
        notificationsToggle.addEventListener('change', (e) => {
            toggleNotifications(e.target.checked);
        });
    }

    if (notificationsSoundToggle) {
        notificationsSoundToggle.checked = state.notificationsSound;
        notificationsSoundToggle.addEventListener('change', (e) => {
            toggleSound(e.target.checked);
        });
    }

    if (state.notificationsEnabled) {
        requestNotificationPermission();
    }
}

export function requestNotificationPermission() {
    if (!("Notification" in window)) {
        console.log("Este navegador no soporta notificaciones");
        return;
    }

    if (Notification.permission === "granted") {
        state.notificationsEnabled = true;
        localStorage.setItem('notificationsEnabled', 'true');
        const notificationsToggle = document.getElementById('notificationsEnabled');
        if (notificationsToggle) notificationsToggle.checked = true;
        return true;
    }

    if (Notification.permission !== "denied") {
        Notification.requestPermission().then((permission) => {
            if (permission === "granted") {
                state.notificationsEnabled = true;
                localStorage.setItem('notificationsEnabled', 'true');
                const notificationsToggle = document.getElementById('notificationsEnabled');
                if (notificationsToggle) notificationsToggle.checked = true;
                showNotification("Notificaciones habilitadas", "Recibirás alertas en tiempo real", "info");
            }
        });
    }
}

export function toggleNotifications(enabled) {
    if (enabled) {
        requestNotificationPermission();
    } else {
        state.notificationsEnabled = false;
        localStorage.setItem('notificationsEnabled', 'false');
    }
}

export function toggleSound(enabled) {
    state.notificationsSound = enabled;
    localStorage.setItem('notificationsSound', String(enabled));
}

export function showNotification(title, body, type = 'info', tag = 'general') {
    if (!state.notificationsEnabled || !("Notification" in window)) return;

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
        connected: '🟢',
        disconnected: '🔴',
        alert: '🚨',
        reboot: '🔄'
    };

    const icon = icons[type] || 'ℹ️';
    const fullTitle = `${icon} ${title}`;

    if (Notification.permission === "granted") {
        const notification = new Notification(fullTitle, {
            body: body,
            icon: '/static/favicon.ico',
            tag: tag,
            requireInteraction: ['alert', 'disconnected', 'error'].includes(type)
        });

        notification.onclick = () => {
            window.focus();
            notification.close();
        };

        setTimeout(() => notification.close(), 5000);
    }

    if (state.notificationsSound) {
        playNotificationSound(type);
    }
}

function playNotificationSound(type = 'info') {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        const frequencies = {
            success: 800,
            error: 300,
            warning: 600,
            info: 500,
            connected: 1000,
            disconnected: 200,
            alert: 1200,
            reboot: 700
        };

        const freq = frequencies[type] || 500;

        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(freq, audioContext.currentTime);

        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.5);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        console.log("No se pudo reproducir el sonido");
    }
}

export function handleNotificationEvent(data) {
    showNotification(data.title, data.body, data.type, data.tag);
    
    if (data.action === 'restart') {
        showRestartConfirmDialog();
    }
}

function showRestartConfirmDialog() {
    const confirmed = confirm('La base de datos ha sido restaurada. ¿Reiniciar servidor ahora?');
    if (confirmed) {
        import('./socket_client.js').then(module => {
            module.state.socket.emit('restart_server');
        });
    }
}
