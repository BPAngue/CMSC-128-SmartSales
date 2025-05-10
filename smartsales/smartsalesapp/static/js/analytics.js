document.addEventListener('DOMContentLoaded', function () {
    function getJSONData(id) {
        const scriptTag = document.getElementById(id);
        return scriptTag ? JSON.parse(scriptTag.textContent) : [];
    }

    const trendData = {
        daily: { 
            labels: getJSONData('daily_labels'), 
            data: getJSONData('daily_data') 
        },
        weekly: { 
            labels: getJSONData('weekly_labels'), 
            data: getJSONData('weekly_data') 
        },
        monthly: { 
            labels: getJSONData('monthly_labels'), 
            data: getJSONData('monthly_data') 
        },
    };

    const ctx = document.getElementById('revenueChart').getContext('2d');
    const revenueChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.daily.labels,
            datasets: [{
                label: 'Revenue',
                data: trendData.daily.data,
                borderColor: 'black',
                backgroundColor: 'rgba(0,0,0,0.1)',
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

    window.updateChart = function (period) {
        revenueChart.data.labels = trendData[period].labels;
        revenueChart.data.datasets[0].data = trendData[period].data;
        revenueChart.update();
    };
});
