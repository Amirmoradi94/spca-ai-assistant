// Dashboard JavaScript for SPCA Conversation Analytics

const API_BASE = window.location.origin;
let charts = {};

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', () => {
    refreshDashboard();
    // Auto-refresh every 30 seconds
    setInterval(refreshDashboard, 30000);
});

async function refreshDashboard() {
    const days = parseInt(document.getElementById('dateRange').value);
    clearError();
    
    try {
        // Load all data in parallel
        const [overview, topics, animals, timeline, engagement, questions, performance] = await Promise.all([
            fetch(`${API_BASE}/api/v1/analytics/overview?days=${days}`).then(r => r.json()),
            fetch(`${API_BASE}/api/v1/analytics/topics?days=${days}`).then(r => r.json()),
            fetch(`${API_BASE}/api/v1/analytics/animals?days=${days}`).then(r => r.json()),
            fetch(`${API_BASE}/api/v1/analytics/timeline?days=${days}`).then(r => r.json()),
            fetch(`${API_BASE}/api/v1/analytics/engagement?days=${days}`).then(r => r.json()),
            fetch(`${API_BASE}/api/v1/analytics/questions?days=${days}`).then(r => r.json()),
            fetch(`${API_BASE}/api/v1/analytics/performance?days=${days}`).then(r => r.json()),
        ]);
        
        updateMetrics(overview, engagement, performance);
        updateCharts(overview, topics, animals, timeline, engagement, questions, performance);
        updateTables(animals, questions);
        
    } catch (error) {
        showError(`Failed to load dashboard data: ${error.message}`);
        console.error('Dashboard error:', error);
    }
}

function updateMetrics(overview, engagement, performance) {
    document.getElementById('totalConversations').textContent = 
        formatNumber(overview.total_conversations);
    document.getElementById('activeConversations').textContent = 
        formatNumber(overview.active_conversations);
    document.getElementById('avgMessages').textContent = 
        formatNumber(overview.avg_messages_per_conversation, 1);
    document.getElementById('avgDuration').textContent = 
        formatDuration(overview.avg_duration_seconds);
    
    document.getElementById('completionRate').textContent = 
        formatNumber(engagement.completion_rate, 1) + '%';
    document.getElementById('bounceRate').textContent = 
        formatNumber(engagement.bounce_rate, 1) + '%';
    document.getElementById('deepEngagement').textContent = 
        formatNumber(engagement.deep_engagement_rate, 1) + '%';
    
    document.getElementById('avgResponseTime').textContent = 
        formatNumber(performance.avg_response_time_ms, 0) + 'ms';
    document.getElementById('errorRate').textContent = 
        formatNumber(performance.error_rate, 2) + '%';
    document.getElementById('avgSources').textContent = 
        formatNumber(performance.avg_sources_per_response, 1);
}

function updateCharts(overview, topics, animals, timeline, engagement, questions, performance) {
    // Conversations over time
    updateLineChart('conversationsChart', {
        labels: timeline.timeline.map(t => t.date),
        datasets: [{
            label: 'Conversations',
            data: timeline.timeline.map(t => t.conversations),
            borderColor: 'rgb(102, 126, 234)',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            tension: 0.4
        }, {
            label: 'Messages',
            data: timeline.timeline.map(t => t.messages),
            borderColor: 'rgb(118, 75, 162)',
            backgroundColor: 'rgba(118, 75, 162, 0.1)',
            tension: 0.4
        }]
    });
    
    // Language distribution
    updatePieChart('languageChart', {
        labels: ['English', 'French'],
        data: [overview.language_distribution.en, overview.language_distribution.fr],
        colors: ['#667eea', '#764ba2']
    });
    
    // Peak hours
    updateBarChart('peakHoursChart', {
        labels: overview.peak_hours.map(h => `${h.hour}:00`),
        data: overview.peak_hours.map(h => h.count),
        label: 'Conversations',
        color: '#667eea'
    });
    
    // Topic distribution
    updatePieChart('topicsChart', {
        labels: ['Adoption', 'Animals', 'Services', 'Hours/Location', 'Fees', 'General'],
        data: [
            topics.distribution.adoption,
            topics.distribution.animals,
            topics.distribution.services,
            topics.distribution.hours_location,
            topics.distribution.fees,
            topics.distribution.general
        ],
        colors: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a']
    });
    
    // Topic trends
    if (topics.trends && topics.trends.length > 0) {
        updateLineChart('topicsTrendChart', {
            labels: topics.trends.map(t => t.date),
            datasets: [
                { label: 'Adoption', data: topics.trends.map(t => t.adoption), borderColor: '#667eea' },
                { label: 'Animals', data: topics.trends.map(t => t.animals), borderColor: '#764ba2' },
                { label: 'Services', data: topics.trends.map(t => t.services), borderColor: '#f093fb' },
                { label: 'Hours/Location', data: topics.trends.map(t => t.hours_location), borderColor: '#4facfe' },
                { label: 'Fees', data: topics.trends.map(t => t.fees), borderColor: '#43e97b' },
                { label: 'General', data: topics.trends.map(t => t.general), borderColor: '#fa709a' }
            ]
        });
    }
    
    // Species popularity
    updateBarChart('speciesChart', {
        labels: Object.keys(animals.species_popularity),
        data: Object.values(animals.species_popularity),
        label: 'Queries',
        color: '#667eea'
    });
    
    // Message distribution
    updateBarChart('messageDistributionChart', {
        labels: ['1', '2-4', '5-9', '10+'],
        data: [
            engagement.message_count_distribution['1'],
            engagement.message_count_distribution['2-4'],
            engagement.message_count_distribution['5-9'],
            engagement.message_count_distribution['10+']
        ],
        label: 'Conversations',
        color: '#667eea'
    });
}

function updateTables(animals, questions) {
    // Top animals table
    const topAnimalsHtml = `
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Reference Number</th>
                    <th>Query Count</th>
                </tr>
            </thead>
            <tbody>
                ${animals.top_animals.map((animal, idx) => `
                    <tr>
                        <td>${idx + 1}</td>
                        <td>${animal.reference_number}</td>
                        <td>${animal.query_count}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('topAnimalsTable').innerHTML = topAnimalsHtml;
    
    // Questions table
    const questionsHtml = `
        <h3>Top First Questions</h3>
        <table>
            <thead>
                <tr>
                    <th>Question</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                ${questions.top_first_questions.map(q => `
                    <tr>
                        <td>${q.question}</td>
                        <td>${q.count}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('questionsTable').innerHTML = questionsHtml;
}

function updateLineChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }
    charts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: config,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function updateBarChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }
    charts[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: config.labels,
            datasets: [{
                label: config.label,
                data: config.data,
                backgroundColor: config.color,
                borderColor: config.color,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function updatePieChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }
    charts[canvasId] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: config.labels,
            datasets: [{
                data: config.data,
                backgroundColor: config.colors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'right' }
            }
        }
    });
}

function formatNumber(num, decimals = 0) {
    if (num === null || num === undefined) return '-';
    return Number(num).toLocaleString('en-US', { 
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatDuration(seconds) {
    if (!seconds) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
}

function showError(message) {
    const container = document.getElementById('errorContainer');
    container.innerHTML = `<div class="error">${message}</div>`;
}

function clearError() {
    document.getElementById('errorContainer').innerHTML = '';
}

async function exportData() {
    const days = parseInt(document.getElementById('dateRange').value);
    try {
        const overview = await fetch(`${API_BASE}/api/v1/analytics/overview?days=${days}`).then(r => r.json());
        const dataStr = JSON.stringify(overview, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `spca-analytics-${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        showError(`Failed to export data: ${error.message}`);
    }
}
