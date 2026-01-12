import { state } from '../core/state.js';

export function renderDeviceChart(sensors) {
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
            label: 'S. Termica (°C)',
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
                    time: { zone: 'local', displayFormats: { hour: 'dd/MM HH:mm', minute: 'HH:mm', day: 'dd/MM' } },
                    title: { display: true, text: 'Fecha y Hora' }
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
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: (context) => {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
                        }
                    }
                }
            }
        }
    });
}

export function renderCurrentSensors(data) {
    const section = document.getElementById('currentSensorsSection');
    if (!section) return;

    const tempCard = document.getElementById('tempCurrentCard');
    const humCard = document.getElementById('humCurrentCard');
    const stCard = document.getElementById('stCurrentCard');

    const tempValue = document.getElementById('tempCurrentValue');
    const humValue = document.getElementById('humCurrentValue');
    const stValue = document.getElementById('stCurrentValue');

    let hasSensors = false;

    let sensorData = null;

    if (data.sensor && typeof data.sensor === 'object') {
        sensorData = data.sensor;
    } else if (data.sensors && Array.isArray(data.sensors) && data.sensors.length > 0) {
        sensorData = data.sensors[0];
    } else if (data.temp_c !== undefined || data.temp_h !== undefined || data.temp_st !== undefined) {
        sensorData = {
            temp_c: data.temp_c,
            temp_h: data.temp_h,
            temp_st: data.temp_st
        };
    }

    if (sensorData) {
        if (sensorData.temp_c !== null && sensorData.temp_c !== undefined) {
            tempCard.style.display = 'flex';
            tempValue.textContent = sensorData.temp_c.toFixed(1) + ' °C';
            hasSensors = true;
        } else {
            tempCard.style.display = 'none';
        }

        if (sensorData.temp_h !== null && sensorData.temp_h !== undefined) {
            humCard.style.display = 'flex';
            humValue.textContent = sensorData.temp_h.toFixed(1) + ' %';
            hasSensors = true;
        } else {
            humCard.style.display = 'none';
        }

        if (sensorData.temp_st !== null && sensorData.temp_st !== undefined) {
            stCard.style.display = 'flex';
            stValue.textContent = sensorData.temp_st.toFixed(1) + ' °C';
            hasSensors = true;
        } else {
            stCard.style.display = 'none';
        }
    } else {
        tempCard.style.display = 'none';
        humCard.style.display = 'none';
        stCard.style.display = 'none';
    }

    section.style.display = hasSensors ? 'block' : 'none';
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

export function renderDeviceStats(sensors) {
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
            <td>🔥 S. Termica</td>
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
