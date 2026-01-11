import { state } from '../core/state.js';
import { elements } from '../core/dom.js';

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

export function renderDevices() {
    if (!elements.deviceGrid) return;

    const whitelist = state.accessLists?.whitelist || [];

    const allowedKeys = new Set();
    const deviceToGroup = {};
    whitelist.forEach(w => {
        const key = `${w.id}@${w.location}`;
        allowedKeys.add(key);
        deviceToGroup[key] = w.group_name || 'Sin Grupo';
    });

    const deviceKeys = Object.keys(state.devices).filter(key => allowedKeys.has(key));

    if (deviceKeys.length === 0) {
        elements.deviceGrid.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📡</span>
                <span class="empty-title">Esperando dispositivos...</span>
                <span class="empty-action">${state.isConnected ? 'Añade dispositivos a la whitelist desde Configuración' : 'Conecta a un servidor MQTT para ver los dispositivos'}</span>
            </div>
        `;
        return;
    }

    const groups = {};
    deviceKeys.forEach(key => {
        const groupName = deviceToGroup[key];
        if (!groups[groupName]) groups[groupName] = [];
        groups[groupName].push(key);
    });

    const sortedGroupNames = Object.keys(groups).sort((a, b) => {
        if (a === 'Sin Grupo') return 1;
        if (b === 'Sin Grupo') return -1;
        return a.localeCompare(b);
    });

    const renderDeviceCard = (device, key) => {
        const statusClass = device.status === 'online' ? 'status-online' : 'status-offline';

        let sensorHtml = '';
        if (device.temp_c !== undefined) sensorHtml += `<div class="device-info"><span class="info-label">🌡️ Temp:</span><span class="info-value">${device.temp_c.toFixed(1)} °C</span></div>`;
        if (device.temp_h !== undefined) sensorHtml += `<div class="device-info"><span class="info-label">💧 Humedad:</span><span class="info-value">${device.temp_h.toFixed(1)} %</span></div>`;
        if (device.temp_st !== undefined) sensorHtml += `<div class="device-info"><span class="info-label">🔥 S. Térmica:</span><span class="info-value">${device.temp_st.toFixed(1)} °C</span></div>`;

        const hasSensorData = device.temp_c !== undefined || device.temp_h !== undefined || device.temp_st !== undefined;
        const graphButtonHtml = hasSensorData ? `<button class="btn-icon" data-action="show-history" data-device-id="${device.id}" data-location="${device.location}" title="Gráfico">📈</button>` : '';
        const adminControls = state.isAdmin ?
            `<button class="btn-icon" data-action="request-status" data-device-id="${device.id}" data-location="${device.location}" title="Status">📊</button>
             <button class="btn-icon" data-action="reboot-device" data-device-id="${device.id}" data-location="${device.location}" title="Reboot">🔄</button>` :
            '';

        return `
            <div class="device-card ${statusClass}" id="device-${key}">
                <a href="/device/${device.id}/${device.location}" class="device-card-link">
                    <div class="device-header">
                        <span class="device-name">${device.name}</span>
                        <span class="device-id">${device.id}@${device.location}</span>
                        <span class="device-last-seen">Ultima vez visto: ${device.last_seen || 'Nunca'}</span>
                    </div>
                </a>
                <div class="device-body">
                    <div class="device-info"><span class="info-label">Latencia:</span><span class="info-value">${device.latency ? device.latency + ' ms' : 'N/A'}</span></div>
                    <div class="device-info"><span class="info-label">IP:</span><span class="info-value">${device.ip || 'N/A'}</span></div>
                    <div class="device-info"><span class="info-label">Uptime:</span><span class="info-value">${formatUptime(device.uptime)}</span></div>
                    ${sensorHtml}
                </div>
                <div class="device-footer">
                    <div class="device-actions">
                        ${graphButtonHtml}
                        ${adminControls}
                    </div>
                </div>
            </div>`;
    };

    elements.deviceGrid.innerHTML = sortedGroupNames.map(groupName => `
        <div class="device-group">
            <h3 class="device-group-title">${groupName}</h3>
            <div class="device-group-grid">
                ${groups[groupName].map(key => renderDeviceCard(state.devices[key], key)).join('')}
            </div>
        </div>
    `).join('');
}

export function renderServers() {
    if (!elements.serversListGrid) return;
    const serverNames = Object.keys(state.config.servers || {});
    if (serverNames.length === 0) {
        elements.serversListGrid.innerHTML = '<div class="empty-state"><p>No hay servidores configurados.</p></div>';
        return;
    }

    const currentServerId = state.activeServerId;
    const devices = state.devices || {};
    const tasks = state.tasks || {};

    elements.serversListGrid.innerHTML = serverNames.map(name => {
        const server = state.config.servers[name];
        const isActive = server.id === currentServerId;
        const isConnected = state.isConnected && isActive;

        const serverDevices = Object.values(devices).filter(d => d.server_id === server.id).length;
        const serverTasks = Object.values(tasks).filter(t => t.server_name === server.name).length;

        const statusClass = isConnected ? 'server-status-connected' : 'server-status-disconnected';
        const statusText = isConnected ? 'Conectado' : 'Desconectado';
        const statusIcon = isConnected ? '🟢' : '🔴';

        const activeBadge = isActive ? '<span class="server-active-badge">Activo</span>' : '';

        return `
            <div class="server-card ${statusClass}" data-server-id="${server.id}">
                <div class="server-card-header">
                    <span class="server-name">${server.name}</span>
                    ${activeBadge}
                </div>
                <div class="server-status">
                    <span class="status-indicator ${statusClass}">${statusIcon} ${statusText}</span>
                </div>
                <div class="server-card-body">
                    <div class="server-info-row">
                        <span class="info-label">Broker:</span>
                        <span class="info-value">${server.broker}:${server.port}</span>
                    </div>
                    <div class="server-info-row">
                        <span class="info-label">Usuario:</span>
                        <span class="info-value">${server.username || 'Ninguno'}</span>
                    </div>
                    <div class="server-stats">
                        <span class="server-stat" title="Dispositivos">📱 ${serverDevices}</span>
                        <span class="server-stat" title="Tareas">⚙️ ${serverTasks}</span>
                    </div>
                </div>
                <div class="server-card-footer">
                    <button class="btn-icon" data-action="edit-server" data-server-id="${server.id}" title="Editar">✏️</button>
                    <button class="btn-icon" data-action="delete-server" data-server-id="${server.id}" title="Eliminar">🗑️</button>
                </div>
            </div>`;
    }).join('');
}
