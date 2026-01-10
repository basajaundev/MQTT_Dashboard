import { elements } from '../core/dom.js';
import { state } from '../core/state.js';

export function displayHistoryChart(deviceId, history) {
    if (!elements.historyChartCanvas) return;

    const deviceName = state.devices[deviceId]?.name || deviceId;
    elements.historyModalTitle.textContent = `📈 Historial de ${deviceName}`;

    const dateValue = elements.historyDatepicker.value;
    let minTime, maxTime;

    if (dateValue) {
        const parts = dateValue.split('-');
        minTime = new Date(parts[0], parts[1]-1, parts[2], 0, 0, 0);
        maxTime = new Date(parts[0], parts[1]-1, parts[2], 23, 59, 59);
    } else {
        maxTime = new Date();
        minTime = new Date(maxTime.getTime() - (24 * 60 * 60 * 1000));
    }

    const datasets = [];
    if (history.some(d => d.temp_c !== null)) datasets.push({ label: 'Temperatura (°C)', data: history.map(d => ({ x: new Date(d.timestamp + 'Z'), y: d.temp_c })), borderColor: 'rgba(255, 99, 132, 1)', backgroundColor: 'rgba(255, 99, 132, 0.2)', yAxisID: 'y_temp' });
    if (history.some(d => d.temp_st !== null)) datasets.push({ label: 'S. Térmica (°C)', data: history.map(d => ({ x: new Date(d.timestamp + 'Z'), y: d.temp_st })), borderColor: 'rgba(255, 159, 64, 1)', backgroundColor: 'rgba(255, 159, 64, 0.2)', yAxisID: 'y_temp' });
    if (history.some(d => d.temp_h !== null)) datasets.push({ label: 'Humedad (%)', data: history.map(d => ({ x: new Date(d.timestamp + 'Z'), y: d.temp_h })), borderColor: 'rgba(54, 162, 235, 1)', backgroundColor: 'rgba(54, 162, 235, 0.2)', yAxisID: 'y_hum' });

    if (state.historyChart) state.historyChart.destroy();

    state.historyChart = new Chart(elements.historyChartCanvas, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'hour' },
                    title: { display: true, text: 'Hora' },
                    min: minTime,
                    max: maxTime
                },
                y_temp: { type: 'linear', position: 'left', title: { display: true, text: 'Temperatura (°C)' } },
                y_hum: { type: 'linear', position: 'right', title: { display: true, text: 'Humedad (%)' }, grid: { drawOnChartArea: false } }
            }
        }
    });
    elements.historyModal.style.display = 'block';
}
