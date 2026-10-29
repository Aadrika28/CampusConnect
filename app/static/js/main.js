/* CampusConnect Main JavaScript Utilities */

document.addEventListener('DOMContentLoaded', function () {
  // 1. User Profile Menu Dropdown
  const userBtn = document.getElementById('userMenuBtn');
  const userDropdown = document.getElementById('userDropdown');

  if (userBtn && userDropdown) {
    userBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      userDropdown.classList.toggle('show');
      const notifDropdown = document.getElementById('notifDropdown');
      if (notifDropdown) notifDropdown.classList.remove('show');
    });
  }

  // 2. Notification Bell Dropdown
  const notifBtn = document.getElementById('notifBellBtn');
  const notifDropdown = document.getElementById('notifDropdown');

  if (notifBtn && notifDropdown) {
    notifBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      notifDropdown.classList.toggle('show');
      if (userDropdown) userDropdown.classList.remove('show');
    });
  }

  // Close dropdowns when clicking outside
  document.addEventListener('click', function () {
    if (userDropdown) userDropdown.classList.remove('show');
    if (notifDropdown) notifDropdown.classList.remove('show');
  });

  // 3. Dismiss Flash Alerts
  const alertCloses = document.querySelectorAll('.alert-close');
  alertCloses.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const alert = this.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 250);
      }
    });
  });
});

// Helper: Get CSRF token from meta tag
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}
