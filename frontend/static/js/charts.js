let charts = {};

function renderGraphicalCharts() {
  if (charts.radar) charts.radar.destroy();
  if (charts.bar) charts.bar.destroy();

  const ctxRadar = document.getElementById('radarChartCanvas').getContext('2d');
  charts.radar = new Chart(ctxRadar, {
    type: 'radar',
    data: {
      labels: ['Tech Accuracy', 'Problem Solving', 'Coding', 'Communication', 'STAR Behavioral', 'Confidence', 'Leadership', 'System Design'],
      datasets: [{
        label: 'Candidate Competency Score',
        data: [88, 85, 92, 86, 84, 90, 85, 88],
        backgroundColor: 'rgba(99, 102, 241, 0.25)',
        borderColor: '#6366f1',
        pointBackgroundColor: '#06b6d4',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: 'rgba(255,255,255,0.1)' },
          grid: { color: 'rgba(255,255,255,0.1)' },
          pointLabels: { color: '#cbd5e1', font: { size: 10 } },
          ticks: { backdropColor: 'transparent', color: '#94a3b8' },
          min: 40, max: 100
        }
      },
      plugins: { legend: { display: false } }
    }
  });

  const ctxBar = document.getElementById('barChartCanvas').getContext('2d');
  charts.bar = new Chart(ctxBar, {
    type: 'bar',
    data: {
      labels: ['Intro', 'Motivation', 'Project', 'Tech', 'Coding', 'Design'],
      datasets: [{
        label: 'Quality Score (%)',
        data: [92, 86, 84, 88, 94, 86],
        backgroundColor: ['#06b6d4', '#6366f1', '#a855f7', '#ec4899', '#10b981', '#f59e0b'],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
        y: { grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { color: '#94a3b8' }, min: 40, max: 100 }
      },
      plugins: { legend: { display: false } }
    }
  });
}
