export function showToast(message, type = 'info', duration = 0) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

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
        toast.style.animation = 'fadeOut 0.3s ease-out forwards';
        toast.addEventListener('animationend', () => {
            if (toast.parentElement) {
                toast.remove();
            }
        });
    };

    if (duration > 0) {
        setTimeout(removeToast, duration);
    }

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', removeToast);
}
