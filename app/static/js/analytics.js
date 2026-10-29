/* CampusConnect — Interactive Analytics Dashboard with Chart.js */

document.addEventListener('DOMContentLoaded', function () {
  const chartCategoryCanvas = document.getElementById('chartCategories');
  if (!chartCategoryCanvas) return;

  fetch('/analytics/data')
    .then(res => res.json())
    .then(data => {
      initCategoryChart(data.categories);
      initTopEventsChart(data.top_events);
      initClubMembersChart(data.club_members);
      initPerformanceChart(data.performance);
    })
    .catch(err => console.error('Failed to load analytics data:', err));
});

function initCategoryChart(catData) {
  const ctx = document.getElementById('chartCategories').getContext('2d');
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: catData.labels,
      datasets: [{
        data: catData.counts,
        backgroundColor: [
          '#4f46e5', // Indigo
          '#2563eb', // Blue
          '#10b981', // Emerald
          '#f59e0b', // Amber
          '#ec4899', // Pink
          '#8b5cf6'  // Purple
        ],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });
}

function initTopEventsChart(eventsData) {
  const ctx = document.getElementById('chartTopEvents').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: eventsData.labels,
      datasets: [{
        label: 'Confirmed Registrations',
        data: eventsData.counts,
        backgroundColor: 'rgba(79, 70, 229, 0.85)',
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        y: { grid: { display: false } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function initClubMembersChart(clubData) {
  const ctx = document.getElementById('chartClubMembers').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: clubData.labels,
      datasets: [{
        label: 'Active Members',
        data: clubData.counts,
        backgroundColor: 'rgba(37, 99, 235, 0.85)',
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function initPerformanceChart(perfData) {
  const ctx = document.getElementById('chartPerformance').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: perfData.labels,
      datasets: [
        {
          label: 'Registrations',
          data: perfData.registrations,
          backgroundColor: '#94a3b8',
          borderRadius: 6
        },
        {
          label: 'Attended (Verified)',
          data: perfData.attendance,
          backgroundColor: '#10b981',
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } }
      },
      plugins: {
        legend: { position: 'top' }
      }
    }
  });
}
