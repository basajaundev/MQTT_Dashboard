import { state } from '../core/state.js';
import { elements } from '../core/dom.js';

let toastConfig = {
    enabled: true,
    duration: 5000,
    position: 'top-right',
    sound: true,
    animation: 'fade',
    types: 'all'
};

export function updateToastConfig(config) {
    if (config) {
        toastConfig.enabled = config.toast_enabled !== 'false';
        toastConfig.duration = (config.toast_duration || 5) * 1000;
        toastConfig.position = config.toast_position || 'top-right';
        toastConfig.sound = config.toast_sound !== 'false';
        toastConfig.animation = config.toast_animation || 'fade';
        toastConfig.types = config.toast_types || 'all';
        
        updateToastContainerPosition();
    }
}

function updateToastContainerPosition() {
    const container = document.getElementById('toast-container');
    if (container) {
        container.className = 'toast-container toast-position-' + toastConfig.position;
    }
}

function playToastSound() {
    if (!toastConfig.sound) return;
    
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        
        const audioContext = new AudioContext();
        
        if (audioContext.state === 'suspended') {
            audioContext.resume().catch(() => {});
            return;
        }
        
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.3);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
    } catch (e) {
        console.log('[TOAST] Could not play sound:', e);
    }
}

export function showToast(message, type = 'info', duration = 0) {
    if (!toastConfig.enabled) return;
    if (toastConfig.types === 'none') return;
    if (toastConfig.types === 'info+warning' && !['info', 'warning'].includes(type)) return;
    
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} toast-anim-${toastConfig.animation}`;

    let icon = '';
    switch(type) {
        case 'success': icon = '✅'; break;
        case 'error': icon = '❌'; break;
        case 'warning': icon = '⚠️'; break;
        default: icon = 'ℹ️';
    }

    toast.innerHTML = `
        <span class="toast-message">${icon} ${message}</span>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    const removeToast = () => {
        if (!toast.classList.contains('toast-hiding')) {
            toast.classList.add('toast-hiding');
            toast.style.animation = 'none';
            toast.offsetHeight;
            toast.style.animation = null;
        }
        const handleAnimationEnd = () => {
            if (toast.classList.contains('toast-hiding') && toast.parentElement) {
                toast.remove();
            }
            toast.removeEventListener('animationend', handleAnimationEnd);
        };
        toast.addEventListener('animationend', handleAnimationEnd);
    };

    const toastDuration = duration > 0 ? duration : toastConfig.duration;
    if (toastDuration > 0) {
        setTimeout(removeToast, toastDuration);
    }

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', removeToast);

    if (type !== 'success' && type !== 'info') {
        playToastSound();
    }
}

export function showToastWithAction(message, type, actionId, actionText, actionCallback) {
    if (!toastConfig.enabled) return;
    if (toastConfig.types === 'none') return;
    if (toastConfig.types === 'info+warning' && !['info', 'warning'].includes(type)) return;
    
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} toast-anim-${toastConfig.animation} toast-with-action`;

    toast.innerHTML = `
        <span class="toast-message">${message}</span>
        <button class="toast-action-btn" data-action="${actionId}">${actionText}</button>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    const removeToast = () => {
        if (!toast.classList.contains('toast-hiding')) {
            toast.classList.add('toast-hiding');
            toast.style.animation = 'none';
            toast.offsetHeight;
            toast.style.animation = null;
        }
        const handleAnimationEnd = () => {
            if (toast.classList.contains('toast-hiding') && toast.parentElement) {
                toast.remove();
            }
            toast.removeEventListener('animationend', handleAnimationEnd);
        };
        toast.addEventListener('animationend', handleAnimationEnd);
    };

    setTimeout(removeToast, toastConfig.duration);

    const actionBtn = toast.querySelector(`[data-action="${actionId}"]`);
    if (actionBtn) {
        actionBtn.addEventListener('click', () => {
            if (actionCallback) actionCallback();
            removeToast();
        });
    }

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', removeToast);
}

export function initToastFromState() {
    if (state.config?.settings) {
        updateToastConfig(state.config.settings);
    }
}
