document.addEventListener('DOMContentLoaded', function () {
    const forecastData = JSON.parse(document.getElementById('forecast-data').textContent);
    const labels = ['Current', 'Forecast'];

    const ctx = document.getElementById('forecastChart').getContext('2d');
    const forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Forecast',
                data: forecastData.day,
                borderColor: 'blue',
                backgroundColor: 'rgba(0,0,255,0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    window.updateForecastChart = function (period) {
        forecastChart.data.datasets[0].data = forecastData[period];
        forecastChart.update();
    };
});
