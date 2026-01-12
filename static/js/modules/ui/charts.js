import { elements } from '../core/dom.js';
import { state } from '../core/state.js';

function calculateStats(values) {
    if (!values || values.length === 0) return { min: null, avg: null, max: null };
    const validValues = values.filter(v => v !== null && v !== undefined);
    if (validValues.length === 0) return { min: null, avg: null, max: null };
    const min = Math.min(...validValues);
    const max = Math.max(...validValues);
    const sum = validValues.reduce((a, b) => a + b, 0);
    const avg = sum / validValues.length;
    return { min, avg, max };
}

export function renderHistoryStats(sensors) {
    const section = elements.historyStatsSection;
    if (!section) return;
    const tbody = elements.historyStatsTableBody;
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
        html += `<tr class="stats-temp"><td>🌡️ Temperatura</td>
            <td>${tempStats.min.toFixed(1)} °C</td><td>${tempStats.avg.toFixed(1)} °C</td>
            <td>${tempStats.max.toFixed(1)} °C</td></tr>`;
    }
    if (hums.length > 0) {
        html += `<tr class="stats-hum"><td>💧 Humedad</td>
            <td>${humStats.min.toFixed(1)} %</td><td>${humStats.avg.toFixed(1)} %</td>
            <td>${humStats.max.toFixed(1)} %</td></tr>`;
    }
    if (sts.length > 0) {
        html += `<tr class="stats-st"><td>🔥 S. Termica</td>
            <td>${stStats.min.toFixed(1)} °C</td><td>${stStats.avg.toFixed(1)} °C</td>
            <td>${stStats.max.toFixed(1)} °C</td></tr>`;
    }
    if (html === '') section.style.display = 'none';
    else { tbody.innerHTML = html; section.style.display = 'block'; }
}

export function displayHistoryChart(deviceId, history) {
    if (!elements.historyChartCanvas) return;
    const deviceName = state.devices[deviceId]?.name || deviceId;
    elements.historyModalTitle.textContent = `📈 Historial de ${deviceName}`;
    const preset = elements.historyDatePreset?.value || '';
    const dateStartInput = elements.historyDateStart;
    const dateEndInput = elements.historyDateEnd;
    let minTime, maxTime;
    const now = new Date();
    if (preset) {
        if (preset === 'today') {
            minTime = new Date(now.toDateString());
            maxTime = new Date(now.getTime() + 24 * 60 * 60 * 1000 - 1);
        } else if (preset === 'yesterday') {
            const yesterday = new Date(now);
            yesterday.setDate(yesterday.getDate() - 1);
            minTime = new Date(yesterday.toDateString());
            maxTime = new Date(yesterday.getTime() + 24 * 60 * 60 * 1000 - 1);
        } else if (preset === 'week') {
            const weekAgo = new Date(now);
            weekAgo.setDate(weekAgo.getDate() - 7);
            minTime = weekAgo;
            maxTime = now;
        } else if (preset === 'month') {
            const monthAgo = new Date(now);
            monthAgo.setDate(monthAgo.getDate() - 30);
            minTime = monthAgo;
            maxTime = now;
        } else if (preset === 'all') {
            minTime = null;
            maxTime = null;
        }
    } else {
        const startVal = dateStartInput?.value;
        const endVal = dateEndInput?.value;
        if (startVal) {
            minTime = new Date(startVal);
            if (endVal) maxTime = new Date(endVal);
            else maxTime = new Date(minTime.getTime() + 24 * 60 * 60 * 1000 - 1);
        } else {
            maxTime = now;
            const weekAgo = new Date(now);
            weekAgo.setDate(weekAgo.getDate() - 7);
            minTime = weekAgo;
        }
    }

    if (history && history.length > 0) {
        const dataMinTime = new Date(history[0].timestamp);
        const dataMaxTime = new Date(history[history.length - 1].timestamp);
        if (preset === 'all') {
            minTime = dataMinTime;
            maxTime = dataMaxTime;
        } else if (minTime && maxTime && (dataMinTime > minTime || dataMaxTime < maxTime)) {
            minTime = dataMinTime;
            maxTime = dataMaxTime;
        }
    }
    const datasets = [];
    if (history.some(d => d.temp_c !== null)) {
        datasets.push({ label: 'Temperatura (°C)', data: history.map(d => ({ x: new Date(d.timestamp), y: d.temp_c })), borderColor: 'rgba(255, 99, 132, 1)', backgroundColor: 'rgba(255, 99, 132, 0.2)', yAxisID: 'y_temp' });
    }
    if (history.some(d => d.temp_st !== null)) {
        datasets.push({ label: 'S. Termica (°C)', data: history.map(d => ({ x: new Date(d.timestamp), y: d.temp_st })), borderColor: 'rgba(255, 159, 64, 1)', backgroundColor: 'rgba(255, 159, 64, 0.2)', yAxisID: 'y_temp' });
    }
    if (history.some(d => d.temp_h !== null)) {
        datasets.push({ label: 'Humedad (%)', data: history.map(d => ({ x: new Date(d.timestamp), y: d.temp_h })), borderColor: 'rgba(54, 162, 235, 1)', backgroundColor: 'rgba(54, 162, 235, 0.2)', yAxisID: 'y_hum' });
    }
    if (state.historyChart) state.historyChart.destroy();
    state.historyChart = new Chart(elements.historyChartCanvas, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { type: 'time', time: { unit: 'hour', timezone: 'local', displayFormats: { hour: 'HH:mm' } }, title: { display: true, text: 'Hora' }, min: minTime, max: maxTime },
                y_temp: { type: 'linear', position: 'left', title: { display: true, text: 'Temperatura (°C)' } },
                y_hum: { type: 'linear', position: 'right', title: { display: true, text: 'Humedad (%)' }, grid: { drawOnChartArea: false } }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false });
                        }
                    }
                }
            }
        }
    });
    renderHistoryStats(history);
    elements.historyModal.style.display = 'block';
}
