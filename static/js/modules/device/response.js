import { state } from '../core/state.js';
import { showToast } from '../ui/toasts.js';
import { getDeviceDetailData } from './detail.js';
import { renderDeviceChart, renderDeviceStats, renderCurrentSensors } from './chart.js';

export function renderDeviceEvents(events) {
    const container = document.getElementById('deviceEvents');
    const pageInfo = document.getElementById('pageInfo');
    const prevBtn = document.getElementById('prevPage');

    if (pageInfo) pageInfo.textContent = state.currentDevicePage;
    if (prevBtn) prevBtn.disabled = state.currentDevicePage === 1;

    if (!container) return;

    if (events.length === 0) {
        container.innerHTML = '<div class="empty-state">Sin eventos</div>';
        return;
    }

    const icons = {
        'connected': { icon: '🟢', label: 'Conectado' },
        'disconnected': { icon: '🔴', label: 'Desconectado' },
        'alert': { icon: '⚠️', label: 'Alerta' },
        'status': { icon: '📊', label: 'Status' },
        'reboot': { icon: '🔄', label: 'Reinicio' }
    };

    container.innerHTML = events.map(e => {
        const iconInfo = icons[e.event_type] || { icon: '📌', label: e.event_type };
        return `
            <div class="timeline-item" data-event-type="${e.event_type}">
                <div class="timeline-icon">${iconInfo.icon}</div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-type">${iconInfo.label}</span>
                        <span class="timeline-time">${e.timestamp}</span>
                    </div>
                    ${e.details ? `<div class="timeline-details">${e.details}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

export function handleDeviceDetailResponse(data) {
    const deviceDetailData = getDeviceDetailData();
    if (data.device_id !== deviceDetailData.deviceId) return;

    const title = document.getElementById('deviceTitle');
    const infoId = document.getElementById('infoId');
    const infoName = document.getElementById('infoName');
    const infoGroup = document.getElementById('infoGroup');
    const infoStatus = document.getElementById('infoStatus');
    const infoIp = document.getElementById('infoIp');
    const infoUptime = document.getElementById('infoUptime');
    const infoLatency = document.getElementById('infoLatency');
    const infoLastSeen = document.getElementById('infoLastSeen');

    if (title) title.textContent = data.alias || data.device_id;
    if (infoId) infoId.textContent = data.device_id;
    if (infoName) infoName.textContent = data.alias || data.device_id;
    if (infoGroup) infoGroup.textContent = data.group ? data.group.name : 'Sin Grupo';

    if (infoStatus) {
        const status = data.status || 'unknown';
        infoStatus.textContent = status === 'online' ? 'Online' : status === 'offline' ? 'Offline' : 'Desconocido';
        infoStatus.className = 'status-badge ' + status;
    }

    const infoLatencyBadge = document.getElementById('infoLatencyBadge');
    if (infoLatencyBadge && data.latency) {
        infoLatencyBadge.textContent = data.latency + ' ms';
        infoLatencyBadge.style.display = 'inline';
    } else if (infoLatencyBadge) {
        infoLatencyBadge.style.display = 'none';
    }

    if (infoIp) infoIp.textContent = data.ip || 'N/A';
    if (infoUptime) infoUptime.textContent = formatUptime(data.uptime);
    if (infoLastSeen) infoLastSeen.textContent = data.last_seen || 'Nunca';

    const infoFirmware = document.getElementById('infoFirmware');
    const infoMac = document.getElementById('infoMac');
    const infoHeap = document.getElementById('infoHeap');
    if (infoFirmware) infoFirmware.textContent = data.firmware || 'N/A';
    if (infoMac) infoMac.textContent = data.mac || 'N/A';
    if (infoHeap) infoHeap.textContent = formatBytes(data.heap);

    renderCurrentSensors(data);

    if (data.sensors && data.sensors.length > 0) {
        renderDeviceChart(data.sensors);
        renderDeviceStats(data.sensors);
    } else {
        const chartContainer = document.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = '<div class="empty-state">Sin datos</div>';
        }
        const statsSection = document.getElementById('deviceStatsSection');
        if (statsSection) statsSection.style.display = 'none';
    }

    state.currentDeviceEvents = data.events || [];
    renderDeviceEvents(data.events || []);

    const dateStartInput = document.getElementById('deviceChartDateStart');
    const dateEndInput = document.getElementById('deviceChartDateEnd');
    if (dateStartInput && !dateStartInput.value && dateEndInput && !dateEndInput.value) {
        const now = new Date();
        const weekAgo = new Date(now);
        weekAgo.setDate(weekAgo.getDate() - 7);
        dateStartInput.value = weekAgo.toLocaleDateString('en-CA');
        dateEndInput.value = now.toLocaleDateString('en-CA');
    }

    const nextBtn = document.getElementById('nextPage');
    if (nextBtn) {
        nextBtn.disabled = state.currentDeviceEvents.length < 50;
    }
}

export function handleDeviceHistoryResponse(data) {
    const deviceDetailData = getDeviceDetailData();
    if (data.device_id === deviceDetailData.deviceId) {
        renderDeviceChart(data.history);
    }
}

export function handleDeviceLogsResponse(data) {
    const deviceDetailData = getDeviceDetailData();
    if (data.device_id !== deviceDetailData.deviceId) return;

    const section = document.getElementById('deviceLogsSection');
    const container = document.getElementById('deviceLogs');
    if (!section || !container) return;

    const logs = data.logs || [];

    if (logs.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    container.innerHTML = logs.map(log => `
        <div class="log-entry">
            <span class="log-timestamp">${log.timestamp}</span>
            <span class="log-level ${log.level}">${log.level}</span>
            <span class="log-message">${escapeHtml(log.message)}</span>
        </div>
    `).join('');
}

export function handleDeviceConfigUpdate(data) {
    const deviceDetailData = getDeviceDetailData();
    console.log('[CONFIG] handleDeviceConfigUpdate called:', data);

    if (data.device_id !== deviceDetailData.deviceId ||
        data.location !== deviceDetailData.location) {
        return;
    }

    const infoFirmware = document.getElementById('infoFirmware');
    const infoMac = document.getElementById('infoMac');
    const infoHeap = document.getElementById('infoHeap');

    if (data.config.firmware && infoFirmware) {
        infoFirmware.textContent = data.config.firmware;
    }

    if (data.config.mac && infoMac) {
        infoMac.textContent = data.config.mac;
    }

    if (data.config.heap !== undefined && infoHeap) {
        infoHeap.textContent = formatBytes(data.config.heap);
    }

    if (data.config.sensor && typeof data.config.sensor === 'object' && !data.config.sensor.type) {
        renderCurrentSensors({ sensor: data.config.sensor });
    }

    showToast('Configuracion actualizada', 'success');
}

function formatUptime(seconds) {
    if (!seconds || isNaN(seconds)) return 'N/A';
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor(seconds % (3600 * 24) / 3600);
    const m = Math.floor(seconds % 3600 / 60);
    const s = Math.floor(seconds % 60);

    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    if (s > 0 || parts.length === 0) parts.push(`${s}s`);

    return parts.join(' ');
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
