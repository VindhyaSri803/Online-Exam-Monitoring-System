/**
 * ExamGuard Chart.js Analytics Suite
 */

const ChartTheme = {
  textColor: '#9ca3af',
  borderColor: '#374151',
  fontFamily: "'Inter', sans-serif",
  colors: {
    primary: '#3b82f6',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#06b6d4',
    purple: '#8b5cf6'
  }
};

// Set global defaults if Chart.js is loaded
if (typeof Chart !== 'undefined') {
  Chart.defaults.color = ChartTheme.textColor;
  Chart.defaults.borderColor = ChartTheme.borderColor;
  Chart.defaults.font.family = ChartTheme.fontFamily;
}

function initDashboardCharts(data) {
  if (!data || typeof Chart === 'undefined') return;

  // Chart 1: Integrity Score Distribution
  const ctx1 = document.getElementById('chart-score-dist');
  if (ctx1 && data.chart1_score_dist) {
    new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: data.chart1_score_dist.labels,
        datasets: [{
          label: 'Number of Sessions',
          data: data.chart1_score_dist.data,
          backgroundColor: [
            'rgba(239, 68, 68, 0.75)',
            'rgba(249, 115, 22, 0.75)',
            'rgba(245, 158, 11, 0.75)',
            'rgba(59, 130, 246, 0.75)',
            'rgba(16, 185, 129, 0.75)'
          ],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: 'rgba(55, 65, 81, 0.4)' } } }
      }
    });
  }

  // Chart 2: Risk Level Distribution
  const ctx2 = document.getElementById('chart-risk-dist');
  if (ctx2 && data.chart2_risk_dist) {
    new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: data.chart2_risk_dist.labels,
        datasets: [{
          data: data.chart2_risk_dist.data,
          backgroundColor: [
            ChartTheme.colors.success,
            ChartTheme.colors.warning,
            ChartTheme.colors.danger
          ],
          borderWidth: 2,
          borderColor: '#111827'
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' }
        },
        cutout: '70%'
      }
    });
  }

  // Chart 3: Event Frequency
  const ctx3 = document.getElementById('chart-event-freq');
  if (ctx3 && data.chart3_event_freq) {
    new Chart(ctx3, {
      type: 'bar',
      data: {
        labels: data.chart3_event_freq.labels,
        datasets: [{
          label: 'Total Occurrences',
          data: data.chart3_event_freq.data,
          backgroundColor: 'rgba(59, 130, 246, 0.7)',
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, grid: { color: 'rgba(55, 65, 81, 0.4)' } } }
      }
    });
  }

  // Chart 4: Face Presence Ratio Distribution
  const ctx4 = document.getElementById('chart-face-presence');
  if (ctx4 && data.chart4_face_presence) {
    new Chart(ctx4, {
      type: 'bar',
      data: {
        labels: data.chart4_face_presence.labels,
        datasets: [{
          label: 'Sessions in Range',
          data: data.chart4_face_presence.data,
          backgroundColor: 'rgba(16, 185, 129, 0.7)',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: 'rgba(55, 65, 81, 0.4)' } } }
      }
    });
  }

  // Chart 5: Suspicious Rule Frequency
  const ctx5 = document.getElementById('chart-suspicious-heatmap');
  if (ctx5 && data.chart5_suspicious_heatmap) {
    new Chart(ctx5, {
      type: 'bar',
      data: {
        labels: data.chart5_suspicious_heatmap.rules,
        datasets: [{
          label: 'Times Triggered',
          data: data.chart5_suspicious_heatmap.counts,
          backgroundColor: 'rgba(245, 158, 11, 0.75)',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, grid: { color: 'rgba(55, 65, 81, 0.4)' } } }
      }
    });
  }

  // Chart 6: Integrity Score vs Suspicious Events Scatter
  const ctx6 = document.getElementById('chart-scatter');
  if (ctx6 && data.chart6_scatter) {
    new Chart(ctx6, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Sessions',
          data: data.chart6_scatter.map(p => ({ x: p.x, y: p.y, meta: p })),
          backgroundColor: data.chart6_scatter.map(p => {
            if (p.risk === 'LOW') return 'rgba(16, 185, 129, 0.8)';
            if (p.risk === 'MEDIUM') return 'rgba(245, 158, 11, 0.8)';
            return 'rgba(239, 68, 68, 0.8)';
          }),
          pointRadius: 6,
          pointHoverRadius: 8
        }]
      },
      options: {
        responsive: true,
        plugins: {
          tooltip: {
            callbacks: {
              label: function(ctx) {
                const item = ctx.raw.meta;
                return `${item.candidate} (Score: ${item.y}, Suspicious: ${item.x}, Risk: ${item.risk})`;
              }
            }
          }
        },
        scales: {
          x: { title: { display: true, text: 'Suspicious Event Count' }, grid: { color: 'rgba(55, 65, 81, 0.4)' } },
          y: { title: { display: true, text: 'Integrity Score (0-100)' }, min: 0, max: 100, grid: { color: 'rgba(55, 65, 81, 0.4)' } }
        }
      }
    });
  }
}

// Chart 7: K-Means Clustering PCA Scatter Visualization
function initClusteringChart(clusteringData) {
  const ctx7 = document.getElementById('chart-kmeans-pca');
  if (!ctx7 || !clusteringData || !clusteringData.points) return;

  const clusterDatasets = [
    { label: 'Normal Behaviour', data: [], backgroundColor: '#10b981', pointRadius: 6 },
    { label: 'Moderate Suspicion', data: [], backgroundColor: '#f59e0b', pointRadius: 6 },
    { label: 'High Suspicion', data: [], backgroundColor: '#ef4444', pointRadius: 6 }
  ];

  clusteringData.points.forEach(pt => {
    const ds = clusterDatasets.find(d => d.label === pt.cluster_label) || clusterDatasets[0];
    ds.data.push({ x: pt.x, y: pt.y, meta: pt });
  });

  new Chart(ctx7, {
    type: 'scatter',
    data: { datasets: clusterDatasets },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const item = ctx.raw.meta;
              return `${item.candidate_name} [${item.exam_title}] - Score: ${item.integrity_score} (${item.cluster_label})`;
            }
          }
        }
      },
      scales: {
        x: { title: { display: true, text: 'Principal Component 1 (PCA-1)' }, grid: { color: 'rgba(55, 65, 81, 0.4)' } },
        y: { title: { display: true, text: 'Principal Component 2 (PCA-2)' }, grid: { color: 'rgba(55, 65, 81, 0.4)' } }
      }
    }
  });
}

window.initDashboardCharts = initDashboardCharts;
window.initClusteringChart = initClusteringChart;
