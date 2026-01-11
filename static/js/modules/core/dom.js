export let elements = {};

export function initElements() {
    elements = {
        themeSwitch: document.getElementById('theme-checkbox'),
        connectBtn: document.getElementById('connectBtn'),
        disconnectBtn: document.getElementById('disconnectBtn'),
        status: document.getElementById('status'),
        serverSelector: document.getElementById('serverSelector'),
        
        messagesList: document.getElementById('messagesList'),
        messagesFooter: document.getElementById('messagesFooter'),
        messagesFooterHeader: document.querySelector('.messages-footer-header'),
        subscribeBtn: document.getElementById('subscribeBtn'),
        publishBtn: document.getElementById('publishBtn'),
        topicInput: document.getElementById('topicInput'),
        topicsList: document.getElementById('topicsList'),
        publishTopic: document.getElementById('publishTopic'),
        publishPayload: document.getElementById('publishPayload'),

        taskModal: document.getElementById('taskModal'),
        tasksList: document.getElementById('tasksList'),
        newTaskBtn: document.getElementById('newTaskBtn'),

        deviceGrid: document.getElementById('deviceGrid'),
        historyModal: document.getElementById('historyModal'),
        historyModalTitle: document.getElementById('historyModalTitle'),
        historyChartCanvas: document.getElementById('historyChart'),
        historyDatepicker: document.getElementById('historyDatepicker'),
        historyDatePreset: document.getElementById('historyDatePreset'),
        historyDateStart: document.getElementById('historyDateStart'),
        historyDateEnd: document.getElementById('historyDateEnd'),
        historyChartRefresh: document.getElementById('historyChartRefresh'),
        historyStatsSection: document.getElementById('historyStatsSection'),
        historyStatsTableBody: document.getElementById('historyStatsTableBody'),
        
        timelineModal: document.getElementById('timelineModal'),
        timelineDeviceInfo: document.getElementById('timelineDeviceInfo'),
        timelineContainer: document.getElementById('timelineContainer'),
        timelineFilter: document.getElementById('timelineFilter'),
        
        serversListGrid: document.getElementById('serversListGrid'),
        serverModal: document.getElementById('serverModal'),
        addServerBtn: document.getElementById('addServerBtn'),
        
        alertsList: document.getElementById('alertsList'),
        alertModal: document.getElementById('alertModal'),
        addAlertBtn: document.getElementById('addAlertBtn'),
        
        alertId: document.getElementById('alertId'),
        alertName: document.getElementById('alertName'),
        alertDevice: document.getElementById('alertDevice'),
        alertMetric: document.getElementById('alertMetric'),
        alertOperator: document.getElementById('alertOperator'),
        alertValue: document.getElementById('alertValue'),
        alertType: document.getElementById('alertType'),
        alertMessage: document.getElementById('alertMessage'),
        alertModalTitle: document.getElementById('alertModalTitle'),

        configTabs: document.querySelector('.config-tabs'),
        refreshIntervalInput: document.getElementById('refreshInterval'),
        maxMissedPingsInput: document.getElementById('maxMissedPings'),
        saveSettingsBtn: document.getElementById('saveSettingsBtn'),
        
        toastSettings: {
            enabled: document.getElementById('toastEnabled'),
            duration: document.getElementById('toastDuration'),
            durationValue: document.getElementById('toastDurationValue'),
            position: document.getElementById('toastPosition'),
            sound: document.getElementById('toastSound'),
            animation: document.getElementById('toastAnimation'),
            types: document.getElementById('toastTypes')
        },
        
        newPasswordInput: document.getElementById('newPassword'),
        confirmPasswordInput: document.getElementById('confirmPassword'),

        loginModal: document.getElementById('loginModal'),
        loginError: document.getElementById('loginError'),
        flashMessages: document.getElementById('flashMessages'),
        
        groupsList: document.getElementById('groupsList'),
        groupModal: document.getElementById('groupModal'),
        groupModalTitle: document.getElementById('groupModalTitle'),
        groupIdInput: document.getElementById('groupId'),
        groupNameInput: document.getElementById('groupName'),
        groupDescriptionInput: document.getElementById('groupDescription'),
        whitelistGroupInput: document.getElementById('whitelist-group-id'),
        whitelistInput: document.getElementById('whitelist-device-id'),
        whitelistContainer: document.getElementById('whitelistContainer'),

        triggersList: document.getElementById('triggersList'),
        triggerModal: document.getElementById('triggerModal'),
        newTriggerBtn: document.getElementById('newTriggerBtn'),
        
        backupSection: {
            autoBackupEnabled: document.getElementById('autoBackupEnabled'),
            autoBackupInterval: document.getElementById('autoBackupInterval'),
            autoBackupKeep: document.getElementById('autoBackupKeep'),
            manualBackupBtn: document.querySelector('[data-action="manual-backup"]'),
            backupsList: document.getElementById('backupsList'),
            backupsCount: document.getElementById('backupsCount')
        },

        deviceModals: {
            rebootModal: document.getElementById('deviceRebootModal'),
            aliasModal: document.getElementById('deviceAliasModal'),
            removeModal: document.getElementById('deviceRemoveModal'),
            aliasInput: document.getElementById('deviceAliasInput')
        }
    };
}
