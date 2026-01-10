import { elements } from './core/dom.js';
import { state } from './core/state.js';
import { showNotification } from './ui/ui.js';

export function openServerModal(serverId) {
    elements.serverModal.style.display = 'block';
    if (serverId) {
        var server = state.config.servers[Object.keys(state.config.servers).find(function(k) { return state.config.servers[k].id == serverId; })];
        if (server) {
            document.getElementById('serverModalTitle').textContent = 'Edit Server';
            document.getElementById('serverId').value = server.id;
            document.getElementById('serverName').value = server.name;
            document.getElementById('serverBroker').value = server.broker;
            document.getElementById('serverPort').value = server.port;
            document.getElementById('serverUsername').value = server.username || '';
            document.getElementById('serverPassword').value = server.password || '';
        }
    } else {
        document.getElementById('serverModalTitle').textContent = 'Add New Server';
        document.getElementById('serverId').value = '';
        document.getElementById('serverName').value = '';
        document.getElementById('serverBroker').value = '';
        document.getElementById('serverPort').value = '1883';
        document.getElementById('serverUsername').value = '';
        document.getElementById('serverPassword').value = '';
    }
}

export function saveServer() {
    var id = document.getElementById('serverId').value;
    var data = {
        id: id ? parseInt(id) : null,
        name: document.getElementById('serverName').value,
        broker: document.getElementById('serverBroker').value,
        port: parseInt(document.getElementById('serverPort').value),
        username: document.getElementById('serverUsername').value,
        password: document.getElementById('serverPassword').value
    };

    if (data.name && data.broker && data.port) {
        if (id) {
            state.socket.emit('update_server', data);
        } else {
            state.socket.emit('add_server', data);
        }
        elements.serverModal.style.display = 'none';
    } else {
        showNotification('Please complete all required fields.', 'error');
    }
}

export function openAlertModal(alertId) {
    if (!elements.alertModal) return;
    elements.alertModal.style.display = 'block';

    if (alertId && state.alerts) {
        var alert = state.alerts.find(function(a) { return a.id == alertId; });
        if (alert) {
            elements.alertId.value = alert.id;
            elements.alertName.value = alert.name;
            elements.alertDevice.value = alert.device_id;
            elements.alertMetric.value = alert.metric;
            elements.alertOperator.value = alert.operator;
            elements.alertValue.value = alert.value;
            elements.alertType.value = alert.type;
            elements.alertMessage.value = alert.message;
            if (elements.alertModalTitle) {
                elements.alertModalTitle.textContent = 'Edit Alert';
            }
        }
    } else {
        elements.alertId.value = '';
        elements.alertName.value = '';
        elements.alertDevice.value = '*';
        elements.alertMetric.value = 'temp_c';
        elements.alertOperator.value = '>';
        elements.alertValue.value = '';
        elements.alertType.value = 'warning';
        elements.alertMessage.value = '';
        if (elements.alertModalTitle) {
            elements.alertModalTitle.textContent = 'New Alert';
        }
    }

    setTimeout(function() {
        if (elements.alertName) {
            elements.alertName.focus();
        }
    }, 100);
}

export function saveAlert() {
    var id = elements.alertId.value;
    var name = elements.alertName.value.trim();
    var deviceId = elements.alertDevice.value;
    var metric = elements.alertMetric.value;
    var operator = elements.alertOperator.value;
    var value = elements.alertValue.value.trim();
    var type = elements.alertType.value;
    var message = elements.alertMessage.value.trim();

    if (!name || !value || !message) {
        showNotification('Please complete all required fields.', 'error');
        return;
    }

    var data = {
        id: id ? parseInt(id) : null,
        name: name,
        device_id: deviceId,
        metric: metric,
        operator: operator,
        value: value,
        type: type,
        message: message
    };

    if (id) {
        state.socket.emit('update_alert', data);
    } else {
        state.socket.emit('add_alert', data);
    }

    elements.alertModal.style.display = 'none';
}

export function closeAlertModal() {
    if (elements.alertModal) {
        elements.alertModal.style.display = 'none';
    }
}

export function openTaskModal(taskId) {
    elements.taskModal.style.display = 'block';

    var modalTitle = elements.taskModal.querySelector('h3');
    var nameInput = elements.taskModal.querySelector('#taskName');
    var topicInput = elements.taskModal.querySelector('#taskTopic');
    var payloadInput = elements.taskModal.querySelector('#taskPayload');

    if (taskId && state.tasks) {
        var task = state.tasks.find(function(t) { return t.id == taskId; });
        if (task) {
            document.getElementById('editTaskId').value = task.id;
            nameInput.value = task.name;
            topicInput.value = task.topic;
            payloadInput.value = task.payload;

            var scheduleType = elements.taskModal.querySelector('#scheduleType');
            scheduleType.value = task.schedule_type || 'interval';
            elements.taskModal.querySelectorAll('.schedule-option').forEach(function(o) { o.style.display = 'none'; });
            elements.taskModal.querySelector('#' + scheduleType.value + 'Options').style.display = 'block';

            if (scheduleType.value === 'interval') {
                elements.taskModal.querySelector('#intervalMinutes').value = task.schedule_data.minutes || 5;
            } else if (scheduleType.value === 'daily') {
                elements.taskModal.querySelector('#dailyHour').value = task.schedule_data.hour || 12;
                elements.taskModal.querySelector('#dailyMinute').value = task.schedule_data.minute || 0;
            } else if (scheduleType.value === 'cron') {
                elements.taskModal.querySelector('#cronExpression').value = task.schedule_data.cron || '0 12 * * *';
            }

            var responseEnabled = elements.taskModal.querySelector('#responseEnabled');
            var responseOptions = elements.taskModal.querySelector('#responseOptions');
            if (responseEnabled && responseOptions) {
                responseEnabled.checked = task.response_enabled || false;
                responseOptions.style.display = responseEnabled.checked ? 'block' : 'none';
            }

            var responseTopic = elements.taskModal.querySelector('#responseTopic');
            var responseTimeout = elements.taskModal.querySelector('#responseTimeout');
            var responseCondition = elements.taskModal.querySelector('#responseCondition');
            var responseAction = elements.taskModal.querySelector('#responseAction');

            if (responseTopic) responseTopic.value = task.response_topic || '';
            if (responseTimeout) responseTimeout.value = task.response_timeout || 10;
            if (responseCondition) responseCondition.value = task.response_condition || '';
            if (responseAction) responseAction.value = task.response_action || 'log';

            if (modalTitle) modalTitle.textContent = 'Edit Task';
        }
    } else {
        document.getElementById('editTaskId').value = '';
        nameInput.value = '';
        topicInput.value = '';
        payloadInput.value = '';
        elements.taskModal.querySelector('#scheduleType').value = 'interval';
        elements.taskModal.querySelector('#intervalOptions').style.display = 'block';
        elements.taskModal.querySelector('#intervalMinutes').value = '5';
    }
}

export function saveTask() {
    var id = elements.taskModal.querySelector('#editTaskId').value;
    var name = elements.taskModal.querySelector('#taskName').value.trim();
    var topic = elements.taskModal.querySelector('#taskTopic').value.trim();
    var payload = elements.taskModal.querySelector('#taskPayload').value.trim();
    var type = elements.taskModal.querySelector('#scheduleType').value;

    if (!name || !topic || !payload) {
        showNotification('Please complete all required fields.', 'error');
        return;
    }

    var scheduleData = {};
    if (type === 'interval') {
        scheduleData = { minutes: parseInt(elements.taskModal.querySelector('#intervalMinutes').value) };
    } else if (type === 'daily') {
        scheduleData = { 
            hour: parseInt(elements.taskModal.querySelector('#dailyHour').value),
            minute: parseInt(elements.taskModal.querySelector('#dailyMinute').value)
        };
    } else if (type === 'cron') {
        scheduleData = { cron: elements.taskModal.querySelector('#cronExpression').value };
    }

    var data = {
        task_id: id || null,
        name: name,
        topic: topic,
        payload: payload,
        schedule_type: type,
        schedule_data: scheduleData,
        response_enabled: elements.taskModal.querySelector('#responseEnabled') ? elements.taskModal.querySelector('#responseEnabled').checked : false,
        response_topic: elements.taskModal.querySelector('#responseTopic') ? elements.taskModal.querySelector('#responseTopic').value : null,
        response_timeout: elements.taskModal.querySelector('#responseTimeout') ? parseInt(elements.taskModal.querySelector('#responseTimeout').value) : null,
        response_condition: elements.taskModal.querySelector('#responseCondition') ? elements.taskModal.querySelector('#responseCondition').value : null,
        response_action: elements.taskModal.querySelector('#responseAction') ? elements.taskModal.querySelector('#responseAction').value : 'log'
    };

    if (id) {
        state.socket.emit('task_edit', data);
    } else {
        state.socket.emit('task_create', data);
    }

    elements.taskModal.style.display = 'none';
}

export function closeTaskModal() {
    if (elements.taskModal) {
        elements.taskModal.style.display = 'none';
    }
}

export function openLoginModal() {
    if (!elements.loginModal) return;
    elements.loginModal.style.display = 'block';
    if (elements.loginError) elements.loginError.style.display = 'none';
    const passwordInput = document.getElementById('loginPassword');
    if (passwordInput) passwordInput.value = '';
}

export function openGroupModal(groupId) {
    if (!elements.groupModal) return;
    elements.groupModal.style.display = 'block';

    if (groupId && state.groups) {
        var group = state.groups.find(function(g) { return g.id == groupId; });
        if (group) {
            elements.groupIdInput.value = group.id;
            elements.groupNameInput.value = group.name;
            if (elements.groupDescriptionInput) {
                elements.groupDescriptionInput.value = group.description || '';
            }
            if (elements.groupModalTitle) {
                elements.groupModalTitle.textContent = 'Edit Group';
            }
        }
    } else {
        elements.groupIdInput.value = '';
        elements.groupNameInput.value = '';
        if (elements.groupDescriptionInput) {
            elements.groupDescriptionInput.value = '';
        }
        if (elements.groupModalTitle) {
            elements.groupModalTitle.textContent = 'New Group';
        }
    }

    setTimeout(function() {
        if (elements.groupNameInput) {
            elements.groupNameInput.focus();
        }
    }, 100);
}

export function saveGroup() {
    var id = elements.groupIdInput.value;
    var name = elements.groupNameInput.value.trim();

    if (!name) {
        showNotification('Group name is required', 'error');
        return;
    }

    if (id) {
        state.socket.emit('update_group', { id: parseInt(id), name: name });
    } else {
        state.socket.emit('add_group', { name: name });
    }

    elements.groupModal.style.display = 'none';
}

export function closeGroupModal() {
    if (elements.groupModal) {
        elements.groupModal.style.display = 'none';
    }
}

export function openTriggerModal(triggerId) {
    if (!elements.triggerModal) return;
    elements.triggerModal.style.display = 'block';

    if (triggerId && state.messageTriggers) {
        var trigger = state.messageTriggers.find(function(t) { return t.id == triggerId; });
        if (trigger) {
            document.getElementById('editTriggerId').value = trigger.id;
            document.getElementById('triggerName').value = trigger.name;
            document.getElementById('triggerTopicPattern').value = trigger.topic_pattern;
            document.getElementById('triggerCondition').value = trigger.trigger_condition || '';
            document.getElementById('triggerActionType').value = trigger.action_type || 'notify';
            document.getElementById('triggerActionTopic').value = trigger.action_topic || '';
            document.getElementById('triggerActionPayload').value = trigger.action_payload || '';
            if (document.getElementById('triggerModalTitle')) {
                document.getElementById('triggerModalTitle').textContent = 'Edit Trigger';
            }
            var publishOptions = document.getElementById('triggerPublishOptions');
            if (publishOptions) {
                publishOptions.style.display = trigger.action_type === 'publish' ? 'block' : 'none';
            }
        }
    } else {
        document.getElementById('editTriggerId').value = '';
        document.getElementById('triggerName').value = '';
        document.getElementById('triggerTopicPattern').value = '';
        document.getElementById('triggerCondition').value = '';
        document.getElementById('triggerActionType').value = 'notify';
        document.getElementById('triggerActionTopic').value = '';
        document.getElementById('triggerActionPayload').value = '';
        if (document.getElementById('triggerModalTitle')) {
            document.getElementById('triggerModalTitle').textContent = 'New Trigger';
        }
        var publishOptions = document.getElementById('triggerPublishOptions');
        if (publishOptions) {
            publishOptions.style.display = 'none';
        }
    }
}

export function saveTrigger() {
    var id = document.getElementById('editTriggerId').value;
    var name = document.getElementById('triggerName').value.trim();
    var topicPattern = document.getElementById('triggerTopicPattern').value.trim();
    var triggerCondition = document.getElementById('triggerCondition').value.trim();
    var actionType = document.getElementById('triggerActionType').value;
    var actionTopic = document.getElementById('triggerActionTopic').value.trim();
    var actionPayload = document.getElementById('triggerActionPayload').value.trim();

    if (!name || !topicPattern || !actionType) {
        showNotification('Please complete all required fields.', 'error');
        return;
    }

    if (actionType === 'publish' && (!actionTopic || !actionPayload)) {
        showNotification('For publish action, you need to specify topic and payload.', 'error');
        return;
    }

    var data = {
        trigger_id: id || null,
        name: name,
        topic_pattern: topicPattern,
        trigger_condition: triggerCondition || null,
        action_type: actionType,
        action_topic: actionType === 'publish' ? actionTopic : null,
        action_payload: actionType === 'publish' ? actionPayload : null
    };

    if (id) {
        state.socket.emit('message_trigger_edit', data);
    } else {
        state.socket.emit('message_trigger_create', data);
    }

    elements.triggerModal.style.display = 'none';
}

export function closeTriggerModal() {
    if (elements.triggerModal) {
        elements.triggerModal.style.display = 'none';
    }
}

export function deleteTrigger(triggerId) {
    if (!confirm('Delete this trigger?')) return;
    state.socket.emit('message_trigger_delete', { trigger_id: triggerId });
}

export function toggleTrigger(triggerId) {
    state.socket.emit('message_trigger_toggle', { trigger_id: triggerId });
}
