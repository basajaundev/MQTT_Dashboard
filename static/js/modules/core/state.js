// Estado global de la aplicacion
export const state = {
    socket: io(), // Instancia única de Socket.IO
    isConnected: false,
    isAdmin: false,
    activeServerId: null,
    config: {},
    devices: {},
    knownDevices: [],
    tasks: [],
    alerts: [],
    subscribedTopics: [],
    historyChart: null,
    deviceChart: null,
    currentHistoryDevice: null,
    _pendingDevicesUpdate: null,
    _devicesUpdateTimer: null,
    messagesFooterExpanded: localStorage.getItem('messagesFooterExpanded') !== 'false',
    lastSeenMessageCount: 0,
    selectedDevices: [],
    currentDevicePage: 1,
    currentDeviceEvents: [],
    currentDeviceEventFilter: '',
    messageTriggers: [],
    deviceDetailData: null
};

// Throttle para actualizaciones de dispositivos (evita renders excesivos)
export function scheduleDevicesUpdate(updateFn) {
    state._pendingDevicesUpdate = updateFn;
    
    if (state._devicesUpdateTimer) {
        return; // Ya hay un timer pendiente
    }
    
    state._devicesUpdateTimer = setTimeout(() => {
        if (state._pendingDevicesUpdate) {
            state._pendingDevicesUpdate();
        }
        state._pendingDevicesUpdate = null;
        state._devicesUpdateTimer = null;
    }, 100); // 100ms throttle
}
