import { state } from '../core/state.js';
import { elements } from '../core/dom.js';

let toastConfig = {
    enabled: true,
    duration: 5000,
    position: 'top-right',
    animation: 'fade',
    types: 'all'
};

export function updateToastConfig(config) {
    if (config) {
        toastConfig.enabled = config.toast_enabled !== 'false';
        toastConfig.duration = (config.toast_duration || 5) * 1000;
        toastConfig.position = config.toast_position || 'top-right';
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
        if (toast.classList.contains('toast-hiding')) return;
        
        toast.classList.add('toast-hiding');
        
        if (toastConfig.animation === 'fade') {
            toast.style.transition = 'opacity 0.3s ease-out';
            toast.style.opacity = '0';
        } else if (toastConfig.animation === 'zoom') {
            toast.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';
            toast.style.transform = 'scale(0.8)';
            toast.style.opacity = '0';
        }
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);
    };

    const toastDuration = duration > 0 ? duration : toastConfig.duration;
    if (toastDuration > 0) {
        setTimeout(removeToast, toastDuration);
    }

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', removeToast);
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
        if (toast.classList.contains('toast-hiding')) return;
        
        toast.classList.add('toast-hiding');
        
        if (toastConfig.animation === 'fade') {
            toast.style.transition = 'opacity 0.3s ease-out';
            toast.style.opacity = '0';
        } else if (toastConfig.animation === 'zoom') {
            toast.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out';
            toast.style.transform = 'scale(0.8)';
            toast.style.opacity = '0';
        }
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);
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
