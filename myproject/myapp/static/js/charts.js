/**
 * Chart.js Initialization and Configuration
 * Provides reusable chart creation functions
 */

// Global chart configuration
Chart.defaults.font.family = "'Open Sans', sans-serif";
Chart.defaults.color = '#666';
Chart.defaults.plugins.legend.display = true;
Chart.defaults.plugins.legend.position = 'bottom';

/**
 * Create a line chart
 */
function createLineChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom'
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                cornerRadius: 4
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: mergedOptions
    });
}

/**
 * Create a bar chart
 */
function createBarChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom'
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                cornerRadius: 4
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: mergedOptions
    });
}

/**
 * Create a doughnut chart
 */
function createDoughnutChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom'
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                cornerRadius: 4,
                callbacks: {
                    label: function(context) {
                        const label = context.label || '';
                        const value = context.parsed || 0;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${label}: ${value} (${percentage}%)`;
                    }
                }
            }
        },
        cutout: '60%'
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: mergedOptions
    });
}

/**
 * Create a pie chart
 */
function createPieChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom'
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                cornerRadius: 4,
                callbacks: {
                    label: function(context) {
                        const label = context.label || '';
                        const value = context.parsed || 0;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${label}: ${value} (${percentage}%)`;
                    }
                }
            }
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: 'pie',
        data: data,
        options: mergedOptions
    });
}

/**
 * Create a horizontal bar chart
 */
function createHorizontalBarChart(canvasId, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                cornerRadius: 4
            }
        },
        scales: {
            x: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: mergedOptions
    });
}

/**
 * Update chart data dynamically
 */
function updateChartData(chart, newData) {
    if (!chart) return;
    
    chart.data.labels = newData.labels;
    chart.data.datasets = newData.datasets;
    chart.update();
}

/**
 * Destroy chart instance
 */
function destroyChart(chart) {
    if (chart) {
        chart.destroy();
    }
}

/**
 * Create empty state message for charts with no data
 */
function showEmptyChartState(canvasId, message = 'No data available') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const container = canvas.parentElement;
    container.style.position = 'relative';
    
    const emptyState = document.createElement('div');
    emptyState.className = 'chart-empty-state';
    emptyState.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        color: #999;
        font-size: 14px;
    `;
    emptyState.innerHTML = `
        <i class="bi bi-bar-chart" style="font-size: 48px; opacity: 0.3;"></i>
        <p style="margin-top: 10px;">${message}</p>
    `;
    
    container.appendChild(emptyState);
    canvas.style.opacity = '0.2';
}

/**
 * Fetch chart data from API endpoint
 */
async function fetchChartData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Failed to fetch chart data');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching chart data:', error);
        return null;
    }
}

/**
 * Initialize all charts on page load
 */
function initializeCharts() {
    // This function can be called from individual pages
    // to initialize their specific charts
    console.log('Charts initialized');
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCharts);
} else {
    initializeCharts();
}

// Export functions for use in other scripts
window.ChartUtils = {
    createLineChart,
    createBarChart,
    createDoughnutChart,
    createPieChart,
    createHorizontalBarChart,
    updateChartData,
    destroyChart,
    showEmptyChartState,
    fetchChartData
};
