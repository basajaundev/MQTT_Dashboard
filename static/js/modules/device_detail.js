import { elements } from './core/dom.js';
import { showToast } from './ui/toasts.js';
import { state } from './core/state.js';

// Modal state management

let deviceDetailData = {
    deviceId: '',
    location: ''
};

let socketListenersInitialized = false;

export function initDeviceDetail(deviceId, location) {
    deviceDetailData = { deviceId, location };
    state.deviceDetailData = deviceDetailData;
    state.currentDevicePage = 1;
    state.currentDeviceEvents = [];
    state.currentDeviceEventFilter = '';

    setupEventListeners();

    // Solo registrar socket listeners una vez
    if (!socketListenersInitialized) {
        socketListenersInitialized = true;

        state.socket.on('device_detail_response', (data) => {
            handleDeviceDetailResponse(data);
        });

        state.socket.on('device_history_response', (data) => {
            handleDeviceHistoryResponse(data);
        });

        state.socket.on('device_logs_response', (data) => {
            handleDeviceLogsResponse(data);
        });

        state.socket.on('device_config_update', (data) => {
            handleDeviceConfigUpdate(data);
        });

        state.socket.on('device_status_response', (data) => {
            handleDeviceDetailResponse(data);
        });

        state.socket.on('devices_update', (data) => {
            if (data.devices && deviceDetailData) {
                const key = `${deviceDetailData.deviceId}@${deviceDetailData.location}`;
                const deviceData = data.devices[key];
                if (deviceData) {
                    handleDeviceDetailResponse({
                        device_id: deviceDetailData.deviceId,
                        location: deviceDetailData.location,
                        status: deviceData.status,
                        latency: deviceData.latency,
                        last_seen: deviceData.last_seen,
                        ip: deviceData.ip,
                        firmware: deviceData.firmware,
                        mac: deviceData.mac,
                        heap: deviceData.heap,
                        uptime: deviceData.uptime,
                        alias: deviceData.name,
                        sensor: {
                            temp_c: deviceData.temp_c,
                            temp_h: deviceData.temp_h,
                            temp_st: deviceData.temp_st
                        }
                    });
                }
            }
        });

        state.socket.on('device_events_response', (data) => {
            if (data.device_id !== deviceDetailData.deviceId || data.location !== deviceDetailData.location) return;
            renderDeviceEvents(data.events || []);

            const prevBtn = document.getElementById('prevPage');
            const nextBtn = document.getElementById('nextPage');
            if (prevBtn) prevBtn.disabled = state.currentDevicePage === 1;
            if (nextBtn) nextBtn.disabled = data.events.length < 50;
        });
    }

    if (state.socket.connected) {
        requestDeviceDetail();
        requestDeviceLogs();
        setTimeout(() => requestDeviceConfig(), 1000);
        loadDeviceEvents();
    } else {
        state.socket.once('connect', () => {
            requestDeviceDetail();
            requestDeviceLogs();
            setTimeout(() => requestDeviceConfig(), 1000);
            loadDeviceEvents();
        });
    }
}

function setupEventListeners() {
    const refreshBtn = document.getElementById('deviceChartRefresh');
    const dateStartInput = document.getElementById('deviceChartDateStart');
    const dateEndInput = document.getElementById('deviceChartDateEnd');
    const presetSelect = document.getElementById('chartDatePreset');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    const eventFilter = document.getElementById('eventFilter');

    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshDeviceHistory);
    }

    if (dateStartInput) {
        dateStartInput.addEventListener('change', refreshDeviceHistory);
    }

    if (dateEndInput) {
        dateEndInput.addEventListener('change', refreshDeviceHistory);
    }

    if (presetSelect) {
        presetSelect.addEventListener('change', refreshDeviceHistory);
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (state.currentDevicePage > 1) {
                state.currentDevicePage--;
                loadDeviceEvents();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            state.currentDevicePage++;
            loadDeviceEvents();
        });
    }

    if (eventFilter) {
        eventFilter.addEventListener('change', () => {
            state.currentDeviceEventFilter = eventFilter.value;
            state.currentDevicePage = 1;
            loadDeviceEvents();
        });
    }

    refreshDeviceHistory();
}

function loadDeviceEvents() {
    state.socket.emit('get_device_events', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location,
        limit: 50,
        event_type: state.currentDeviceEventFilter || null
    });
}

function refreshDeviceHistory() {
    const dateStartInput = document.getElementById('deviceChartDateStart');
    const dateEndInput = document.getElementById('deviceChartDateEnd');
    const presetSelect = document.getElementById('chartDatePreset');
    const preset = presetSelect ? presetSelect.value : '';
    let startDate = null;
    let endDate = null;

    if (preset) {
        const now = new Date();
        
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
        startDate = dateStartInput ? dateStartInput.value : null;
        endDate = dateEndInput ? dateEndInput.value : null;
    }

    if (dateStartInput) dateStartInput.value = startDate || '';
    if (dateEndInput) dateEndInput.value = endDate || '';

    console.log('[HISTORY] Enviando peticion:', { device_id: deviceDetailData.deviceId, location: deviceDetailData.location, start_date: startDate, end_date: endDate });

    state.socket.emit('request_device_history', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location,
        start_date: startDate,
        end_date: endDate
    });
}

function requestDeviceDetail() {
    state.socket.emit('get_device_detail', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location
    });
}

function requestDeviceStatus() {
    state.socket.emit('request_single_device_status', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location
    });
    showToast('Solicitando status...', 'info');
    setTimeout(requestDeviceDetail, 1000);
}

function requestDeviceConfig() {
    state.socket.emit('request_device_config', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location
    });
}

export function handleDeviceDetailResponse(data) {
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
        const chartContainer = document.querySelector('.chart-container-compact');
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
    if (data.device_id === deviceDetailData.deviceId) {
        renderDeviceChart(data.history);
    }
}

function renderDeviceEvents(events) {
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

function renderDeviceChart(sensors) {
    const canvas = document.getElementById('deviceChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    if (state.deviceChart) {
        state.deviceChart.destroy();
    }

    if (!sensors || sensors.length === 0) {
        const chartContainer = document.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = '<div class="empty-state">Sin datos de sensores</div>';
        }
        return;
    }

    var datasets = [];

    var tempSensors = sensors.filter(function(s) { return s.temp_c !== null; });
    if (tempSensors.length > 0) {
        datasets.push({
            label: 'Temperatura (°C)',
            data: tempSensors.map(s => ({ x: new Date(s.timestamp), y: s.temp_c })),
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            yAxisID: 'y_temp'
        });
    }

    var humSensors = sensors.filter(function(s) { return s.temp_h !== null; });
    if (humSensors.length > 0) {
        datasets.push({
            label: 'Humedad (%)',
            data: humSensors.map(s => ({ x: new Date(s.timestamp), y: s.temp_h })),
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            yAxisID: 'y_hum'
        });
    }

    var stSensors = sensors.filter(function(s) { return s.temp_st !== null; });
    if (stSensors.length > 0) {
        datasets.push({
            label: 'S. Térmica (°C)',
            data: stSensors.map(s => ({ x: new Date(s.timestamp), y: s.temp_st })),
            borderColor: 'rgba(255, 159, 64, 1)',
            backgroundColor: 'rgba(255, 159, 64, 0.2)',
            yAxisID: 'y_temp'
        });
    }

    state.deviceChart = new Chart(ctx, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'hour' },
                    title: { display: true, text: 'Hora' }
                },
                y_temp: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: 'Temperatura (°C)' }
                },
                y_hum: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: 'Humedad (%)' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

function renderCurrentSensors(data) {
    const section = document.getElementById('currentSensorsSection');
    if (!section) return;

    const tempCard = document.getElementById('tempCurrentCard');
    const humCard = document.getElementById('humCurrentCard');
    const stCard = document.getElementById('stCurrentCard');

    const tempValue = document.getElementById('tempCurrentValue');
    const humValue = document.getElementById('humCurrentValue');
    const stValue = document.getElementById('stCurrentValue');

    let hasSensors = false;

    // Usar data.sensor (valores actuales del dispositivo) en lugar de data.sensors (historial)
    if (data.sensor) {
        const latest = data.sensor;

        if (latest.temp_c !== null && latest.temp_c !== undefined) {
            tempCard.style.display = 'flex';
            tempValue.textContent = latest.temp_c.toFixed(1) + ' °C';
            hasSensors = true;
        } else {
            tempCard.style.display = 'none';
        }

        if (latest.temp_h !== null && latest.temp_h !== undefined) {
            humCard.style.display = 'flex';
            humValue.textContent = latest.temp_h.toFixed(1) + ' %';
            hasSensors = true;
        } else {
            humCard.style.display = 'none';
        }

        if (latest.temp_st !== null && latest.temp_st !== undefined) {
            stCard.style.display = 'flex';
            stValue.textContent = latest.temp_st.toFixed(1) + ' °C';
            hasSensors = true;
        } else {
            stCard.style.display = 'none';
        }
    } else {
        tempCard.style.display = 'none';
        humCard.style.display = 'none';
        stCard.style.display = 'none';
    }

    section.style.display = hasSensors ? 'flex' : 'none';
}

    function calculateStats(values) {
        if (!values || values.length === 0) return { min: null, avg: null, max: null };
        
        var validValues = values.filter(function(v) { return v !== null && v !== undefined; });
        if (validValues.length === 0) return { min: null, avg: null, max: null };

    const min = Math.min(...validValues);
    const max = Math.max(...validValues);
    const sum = validValues.reduce((a, b) => a + b, 0);
    const avg = sum / validValues.length;

    return { min, avg, max };
}

function renderDeviceStats(sensors) {
    const section = document.getElementById('deviceStatsSection');
    if (!section) return;

    const tbody = document.getElementById('statsTableBody');
    if (!tbody) return;

    if (!sensors || sensors.length === 0) {
        section.style.display = 'none';
        return;
    }

    const temps = sensors.map(s => s.temp_c).filter(v => v !== null && v !== undefined);
    const hums = sensors.map(s => s.temp_h).filter(v => v !== null && v !== undefined);
    const sts = sensors.map(s => s.temp_st).filter(v => v !== null && v !== undefined);

    const tempStats = calculateStats(temps);
    const humStats = calculateStats(hums);
    const stStats = calculateStats(sts);

    let html = '';

    if (temps.length > 0) {
        html += `<tr class="stats-temp">
            <td>🌡️ Temperatura</td>
            <td>${tempStats.min.toFixed(1)} °C</td>
            <td>${tempStats.avg.toFixed(1)} °C</td>
            <td>${tempStats.max.toFixed(1)} °C</td>
        </tr>`;
    }

    if (hums.length > 0) {
        html += `<tr class="stats-hum">
            <td>💧 Humedad</td>
            <td>${humStats.min.toFixed(1)} %</td>
            <td>${humStats.avg.toFixed(1)} %</td>
            <td>${humStats.max.toFixed(1)} %</td>
        </tr>`;
    }

    if (sts.length > 0) {
        html += `<tr class="stats-st">
            <td>🔥 S. Térmica</td>
            <td>${stStats.min.toFixed(1)} °C</td>
            <td>${stStats.avg.toFixed(1)} °C</td>
            <td>${stStats.max.toFixed(1)} °C</td>
        </tr>`;
    }

    if (html === '') {
        section.style.display = 'none';
    } else {
        tbody.innerHTML = html;
        section.style.display = 'block';
    }
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

export function requestDeviceLogs() {
    state.socket.emit('get_device_logs', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location,
        limit: 100
    });
}

export function handleDeviceLogsResponse(data) {
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
    console.log('[CONFIG] handleDeviceConfigUpdate called:', data);
    console.log('[CONFIG] Current device data:', deviceDetailData);

    // Solo actualizar si es el dispositivo actual
    if (data.device_id !== deviceDetailData.deviceId ||
        data.location !== deviceDetailData.location) {
        console.log('[CONFIG] Device/location mismatch - expected:', deviceDetailData.deviceId, deviceDetailData.location, '- got:', data.device_id, data.location);
        return;
    }

    console.log('[CONFIG] Processing config update for device:', data.device_id, data.location);

    // Verificar que los elementos DOM existan antes de intentar actualizarlos
    const infoFirmware = document.getElementById('infoFirmware');
    const infoMac = document.getElementById('infoMac');
    const infoHeap = document.getElementById('infoHeap');

    console.log('[CONFIG] DOM elements check:', {
        infoFirmware: !!infoFirmware,
        infoMac: !!infoMac,
        infoHeap: !!infoHeap
    });

    // Actualizar campos de información
    if (data.config.firmware && infoFirmware) {
        console.log('[CONFIG] Updating firmware:', data.config.firmware);
        infoFirmware.textContent = data.config.firmware;
    } else if (data.config.firmware) {
        console.log('[CONFIG] Firmware element not found');
    }

    if (data.config.mac && infoMac) {
        console.log('[CONFIG] Updating MAC:', data.config.mac);
        infoMac.textContent = data.config.mac;
    } else if (data.config.mac) {
        console.log('[CONFIG] MAC element not found');
    }

    if (data.config.heap !== undefined && infoHeap) {
        console.log('[CONFIG] Updating heap:', data.config.heap);
        infoHeap.textContent = formatBytes(data.config.heap);
    } else if (data.config.heap !== undefined) {
        console.log('[CONFIG] Heap element not found');
    }

    // Si hay datos de sensor, actualizar también
    if (data.config.sensor) {
        // Si es un objeto con datos de temperatura
        if (typeof data.config.sensor === 'object' && !data.config.sensor.type) {
            const tempC = data.config.sensor.temp_c;
            const tempH = data.config.sensor.temp_h;
            const tempSt = data.config.sensor.temp_st;

            // Obtener elementos de las tarjetas
            const tempCard = document.getElementById('tempCurrentCard');
            const humCard = document.getElementById('humCurrentCard');
            const stCard = document.getElementById('stCurrentCard');

            // Actualizar valores actuales y mostrar/ocultar tarjetas
            if (tempC !== null && tempC !== undefined) {
                const tempCElement = document.getElementById('tempCurrentValue');
                if (tempCElement) tempCElement.textContent = tempC.toFixed(1) + ' °C';
                if (tempCard) tempCard.style.display = 'flex';
            } else {
                if (tempCard) tempCard.style.display = 'none';
            }

            if (tempH !== null && tempH !== undefined) {
                const tempHElement = document.getElementById('humCurrentValue');
                if (tempHElement) tempHElement.textContent = tempH.toFixed(1) + ' %';
                if (humCard) humCard.style.display = 'flex';
            } else {
                if (humCard) humCard.style.display = 'none';
            }

            if (tempSt !== null && tempSt !== undefined) {
                const tempStElement = document.getElementById('stCurrentValue');
                if (tempStElement) tempStElement.textContent = tempSt.toFixed(1) + ' °C';
                if (stCard) stCard.style.display = 'flex';
            } else {
                if (stCard) stCard.style.display = 'none';
            }

            // Mostrar sección de sensores si hay al menos un dato
            const hasSensors = (tempC !== null && tempC !== undefined) || (tempH !== null && tempH !== undefined) || (tempSt !== null && tempSt !== undefined);
            const sensorsSection = document.getElementById('currentSensorsSection');
            if (sensorsSection) {
                sensorsSection.style.display = hasSensors ? 'block' : 'none';
            }
        }
        // Si es solo el tipo de sensor (sin valores)
        if (data.config.sensor.type) {
            console.log('Sensor type detected:', data.config.sensor.type);
        }
    }

    showToast('Configuracion actualizada', 'success');
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

// Modal management functions
function setupModalEventListeners() {
    // Reboot modal
    document.addEventListener('click', (e) => {
        const action = e.target.getAttribute('data-action');
        if (!action) return;

        switch (action) {
            case 'close-device-reboot-modal':
                closeDeviceRebootModal();
                break;
            case 'cancel-device-reboot':
                closeDeviceRebootModal();
                break;
            case 'confirm-device-reboot':
                handleDeviceRebootConfirm();
                break;
            case 'close-device-alias-modal':
                closeDeviceAliasModal();
                break;
            case 'cancel-device-alias':
                closeDeviceAliasModal();
                break;
            case 'confirm-device-alias':
                handleDeviceAliasConfirm();
                break;
            case 'close-device-remove-modal':
                closeDeviceRemoveModal();
                break;
            case 'cancel-device-remove':
                closeDeviceRemoveModal();
                break;
            case 'confirm-device-remove':
                handleDeviceRemoveConfirm();
                break;
        }
    });
}
