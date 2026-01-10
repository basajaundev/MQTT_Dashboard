import { state } from '../core/state.js';
import { showToast } from '../ui/toasts.js';
import { handleDeviceDetailResponse, handleDeviceHistoryResponse, handleDeviceLogsResponse, handleDeviceConfigUpdate, renderDeviceEvents } from './response.js';

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

    state.socket.emit('get_device_history', {
        device_id: deviceDetailData.deviceId,
        location: deviceDetailData.location,
        start_date: startDate,
        end_date: endDate
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
