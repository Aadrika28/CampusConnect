/* CampusConnect — Browser Camera QR Attendance Scanner & Manual Fallback */

let html5QrCode = null;
let isScanning = false;
let lastScannedCode = null;
let lastScanTimestamp = 0;
const SCAN_COOLDOWN_MS = 2500; // Cooldown between consecutive scans

// Web Audio API Beep synthesizer
function playBeep(success = true) {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (success) {
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note (success)
      gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.15);
    } else {
      osc.frequency.setValueAtTime(300, audioCtx.currentTime); // Low buzz (error/duplicate)
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.3);
    }
  } catch (e) {
    // Audio context not allowed or unsupported
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const startBtn = document.getElementById('startScanBtn');
  const stopBtn = document.getElementById('stopScanBtn');
  const manualForm = document.getElementById('manualCheckinForm');
  const eventSelect = document.getElementById('scannerEventSelect');

  if (startBtn) {
    startBtn.addEventListener('click', startScanner);
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', stopScanner);
  }

  if (manualForm) {
    manualForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const codeInput = document.getElementById('manualCodeInput');
      const code = codeInput ? codeInput.value.trim() : '';
      const eventId = eventSelect ? eventSelect.value : null;

      if (!code) {
        showFeedback(false, 'Please enter a valid ticket registration code.');
        return;
      }

      verifyAttendancePayload({ code: code, event_id: eventId }, 'manual');
      if (codeInput) codeInput.value = '';
    });
  }
});

function startScanner() {
  const qrReaderElement = document.getElementById('qr-reader');
  if (!qrReaderElement) return;

  if (isScanning) return;

  html5QrCode = new Html5Qrcode('qr-reader');
  const config = { fps: 10, qrbox: { width: 250, height: 250 } };

  html5QrCode.start(
    { facingMode: 'environment' },
    config,
    onScanSuccess,
    onScanError
  ).then(() => {
    isScanning = true;
    document.getElementById('startScanBtn').style.display = 'none';
    document.getElementById('stopScanBtn').style.display = 'inline-flex';
    document.getElementById('scannerStatusText').textContent = 'Camera active. Point at student QR pass.';
  }).catch((err) => {
    console.error('Error starting camera:', err);
    showFeedback(false, 'Camera access was denied or is not available. Please use the Manual Registration Code fallback below.');
  });
}

function stopScanner() {
  if (html5QrCode && isScanning) {
    html5QrCode.stop().then(() => {
      isScanning = false;
      document.getElementById('startScanBtn').style.display = 'inline-flex';
      document.getElementById('stopScanBtn').style.display = 'none';
      document.getElementById('scannerStatusText').textContent = 'Camera paused.';
    }).catch(err => console.error('Failed to stop camera:', err));
  }
}

function onScanSuccess(decodedText, decodedResult) {
  const now = Date.now();
  if (decodedText === lastScannedCode && (now - lastScanTimestamp) < SCAN_COOLDOWN_MS) {
    return; // Ignore repeated scans within cooldown
  }

  lastScannedCode = decodedText;
  lastScanTimestamp = now;

  const eventSelect = document.getElementById('scannerEventSelect');
  const eventId = eventSelect ? eventSelect.value : null;

  // The QR pass may contain either the signed token string or raw registration code
  const payload = {
    token: decodedText,
    event_id: eventId
  };

  verifyAttendancePayload(payload, 'qr_scan');
}

function onScanError(errorMessage) {
  // Silent frame parse error
}

function verifyAttendancePayload(payload, method) {
  const feedbackContainer = document.getElementById('scanFeedback');
  if (!feedbackContainer) return;

  feedbackContainer.innerHTML = '<div class="alert alert-info">Verifying attendance on server...</div>';

  fetch('/api/attendance/verify', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(payload)
  })
    .then(res => res.json().then(data => ({ status: res.status, ok: res.ok, data: data })))
    .then(result => {
      if (result.ok && result.data.success) {
        playBeep(true);
        showFeedback(true, result.data);
        addRecentVerificationItem(result.data);
      } else {
        playBeep(false);
        const msg = (result.data && result.data.message) ? result.data.message : 'Attendance verification rejected.';
        const isDuplicate = result.data && result.data.duplicate;
        showFeedback(false, msg, isDuplicate);
      }
    })
    .catch(err => {
      playBeep(false);
      showFeedback(false, 'Network or server communication error. Check your connection.');
    });
}

function showFeedback(isSuccess, payloadOrMsg, isDuplicate = false) {
  const container = document.getElementById('scanFeedback');
  if (!container) return;

  if (isSuccess) {
    container.innerHTML = `
      <div class="alert alert-success" style="display:flex; flex-direction:column; align-items:flex-start; gap:0.4rem; padding: 1.25rem;">
        <div style="font-size:1.15rem; font-weight:700;">✅ ${payloadOrMsg.message}</div>
        <div><strong>Student:</strong> ${payloadOrMsg.student_name} (${payloadOrMsg.student_id})</div>
        <div><strong>Department:</strong> ${payloadOrMsg.department}</div>
        <div><strong>Event:</strong> ${payloadOrMsg.event_title}</div>
        <div style="font-size:0.85rem; color:#065f46;"><strong>Timestamp:</strong> ${payloadOrMsg.marked_at} (via ${payloadOrMsg.verification_method})</div>
      </div>
    `;
  } else {
    const alertClass = isDuplicate ? 'alert-warning' : 'alert-danger';
    const icon = isDuplicate ? '⚠️' : '❌';
    container.innerHTML = `
      <div class="alert ${alertClass}" style="padding: 1.25rem;">
        <div style="font-weight:700; font-size:1.05rem;">${icon} Verification Failed</div>
        <div style="margin-top:0.3rem;">${payloadOrMsg}</div>
      </div>
    `;
  }
}

function addRecentVerificationItem(item) {
  const list = document.getElementById('recentScansList');
  if (!list) return;

  const row = document.createElement('tr');
  row.innerHTML = `
    <td><strong>${item.student_name}</strong></td>
    <td>${item.student_id}</td>
    <td><span class="badge badge-success">Attended</span></td>
    <td>${item.marked_at}</td>
    <td><span class="badge badge-indigo">${item.verification_method}</span></td>
  `;

  // Prepend to list
  if (list.firstChild) {
    list.insertBefore(row, list.firstChild);
  } else {
    list.appendChild(row);
  }
}
