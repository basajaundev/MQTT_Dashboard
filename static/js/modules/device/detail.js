import { state } from '../core/state.js';
import { showToast } from '../ui/toasts.js';

// Device detail page state
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

    if (!socketListenersInitialized) {
        socketListenersInitialized = true;
        setupSocketListeners();
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

function setupSocketListeners() {
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

export function getDeviceDetailData() {
    return deviceDetailData;
}

export function requestDeviceDetail() {
    state.socket.emit('get_device_detail', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location
    });
}

export function requestDeviceStatus() {
    state.socket.emit('request_single_device_status', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location
    });
    showToast('Solicitando status...', 'info');
    setTimeout(requestDeviceDetail, 1000);
}

export function requestDeviceConfig() {
    state.socket.emit('request_device_config', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location
    });
}

export function requestDeviceLogs() {
    state.socket.emit('get_device_logs', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location,
        limit: 100
    });
}
