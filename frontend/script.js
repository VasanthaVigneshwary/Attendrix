/* ══ ATTENDRIX – Frontend JavaScript ════════════════════════════════ */
const API = '';   // same origin — FastAPI serves both

// ── Tab navigation ───────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    link.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    if (tab === 'overview') loadOverview();
    if (tab === 'students') loadStudents();
    if (tab === 'records')  loadRecords();
  });
});

// ── Toast ────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3500);
}

// ── Date display ─────────────────────────────────────────────────
document.getElementById('date-display').textContent =
  'Today: ' + new Date().toLocaleDateString('en-IN', {weekday:'long',year:'numeric',month:'long',day:'numeric'});

// ════════════════════════════════════════════════════════════════
// OVERVIEW
// ════════════════════════════════════════════════════════════════
async function loadOverview() {
  try {
    const res = await fetch(API + '/dashboard/overview');
    const data = await res.json();
    document.getElementById('ov-registered').textContent = data.total_registered ?? data.total_students ?? '–';
    document.getElementById('ov-present').textContent    = data.present ?? '–';
    document.getElementById('ov-absent').textContent     = data.absent ?? '–';
    document.getElementById('ov-pct').textContent        = (data.attendance_percentage ?? '–') + '%';
  } catch (err) {
    showToast('Could not load overview: ' + err.message, 'error');
  }
}
loadOverview();

// ════════════════════════════════════════════════════════════════
// REGISTER STUDENT
// ════════════════════════════════════════════════════════════════
const regImgInput = document.getElementById('reg-img-input');
const regPreview  = document.getElementById('reg-preview');
regImgInput.addEventListener('change', () => {
  const file = regImgInput.files[0];
  if (file) {
    regPreview.src = URL.createObjectURL(file);
    regPreview.classList.remove('hidden');
  }
});

document.getElementById('register-form').addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const fd   = new FormData(form);
  const resDiv = document.getElementById('register-result');
  resDiv.innerHTML = '<div class="spinner"></div>';

  try {
    const res  = await fetch(API + '/students/', { method: 'POST', body: fd });
    const data = await res.json();
    if (res.ok) {
      resDiv.innerHTML = `<div class="result-box success">✅ ${data.message || 'Registered!'}<br/>Name: <strong>${data.name}</strong> | ID: ${data.student_id}</div>`;
      showToast('Student registered successfully!', 'success');
      form.reset();
      regPreview.classList.add('hidden');
    } else {
      resDiv.innerHTML = `<div class="result-box error">❌ ${data.detail || 'Registration failed.'}</div>`;
      showToast(data.detail || 'Registration failed.', 'error');
    }
  } catch (err) {
    resDiv.innerHTML = `<div class="result-box error">❌ Network error: ${err.message}</div>`;
    showToast('Network error', 'error');
  }
});

// ════════════════════════════════════════════════════════════════
// STUDENTS LIST
// ════════════════════════════════════════════════════════════════
let allStudents = [];
async function loadStudents() {
  try {
    const res = await fetch(API + '/students/');
    allStudents = await res.json();
    renderStudentsTable(allStudents);
  } catch (err) {
    showToast('Could not load students: ' + err.message, 'error');
  }
}

function renderStudentsTable(students) {
  const tbody = document.querySelector('#students-table tbody');
  if (!students.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:24px">No students registered yet.</td></tr>';
    return;
  }
  tbody.innerHTML = students.map((s, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><strong>${s.student_id}</strong></td>
      <td>${s.name}</td>
      <td>${s.department || '–'}</td>
      <td>${s.year || '–'}</td>
      <td>${s.section || '–'}</td>
      <td><button class="btn btn-danger" onclick="deleteStudent(${s.id}, '${s.name}')">🗑 Delete</button></td>
    </tr>`).join('');
}

function filterStudentsTable() {
  const q = document.getElementById('student-search').value.toLowerCase();
  renderStudentsTable(allStudents.filter(s =>
    s.name.toLowerCase().includes(q) || s.student_id.toLowerCase().includes(q)
  ));
}

async function deleteStudent(id, name) {
  if (!confirm(`Delete student "${name}"? This cannot be undone.`)) return;
  try {
    const res  = await fetch(API + '/students/' + id, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) { showToast(data.detail, 'success'); loadStudents(); }
    else         showToast(data.detail || 'Delete failed.', 'error');
  } catch (err) {
    showToast('Network error: ' + err.message, 'error');
  }
}

// ════════════════════════════════════════════════════════════════
// TAKE ATTENDANCE (Upload & Live Webcam)
// ════════════════════════════════════════════════════════════════
let webcamStream = null;

function setAttendanceMode(mode) {
  const btnUpload = document.getElementById('btn-mode-upload');
  const btnWebcam = document.getElementById('btn-mode-webcam');
  const cardUpload = document.getElementById('card-att-upload');
  const cardWebcam = document.getElementById('card-att-webcam');

  if (mode === 'upload') {
    btnUpload.className = 'btn btn-primary';
    btnWebcam.className = 'btn btn-secondary';
    cardUpload.classList.remove('hidden');
    cardWebcam.classList.add('hidden');
    stopWebcam();
  } else {
    btnUpload.className = 'btn btn-secondary';
    btnWebcam.className = 'btn btn-primary';
    cardUpload.classList.add('hidden');
    cardWebcam.classList.remove('hidden');
  }
}

async function startWebcam() {
  const video = document.getElementById('webcam-video');
  const status = document.getElementById('webcam-status');
  const btnCapture = document.getElementById('btn-capture-webcam');
  const btnStop = document.getElementById('btn-stop-webcam');

  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
    video.srcObject = webcamStream;
    video.style.display = 'block';
    status.textContent = 'Camera active. Point towards students and click "Capture & Mark".';
    status.style.color = '#15803d';
    btnCapture.disabled = false;
    btnStop.disabled = false;
  } catch (err) {
    status.textContent = 'Webcam unavailable or permission denied: ' + err.message;
    status.style.color = '#dc2626';
    showToast('Cannot access webcam: ' + err.message, 'error');
  }
}

function stopWebcam() {
  const video = document.getElementById('webcam-video');
  const status = document.getElementById('webcam-status');
  const btnCapture = document.getElementById('btn-capture-webcam');
  const btnStop = document.getElementById('btn-stop-webcam');

  if (webcamStream) {
    webcamStream.getTracks().forEach(t => t.stop());
    webcamStream = null;
  }
  if (video) {
    video.srcObject = null;
    video.style.display = 'none';
  }
  if (status) {
    status.textContent = 'Camera stopped.';
    status.style.color = '#64748b';
  }
  if (btnCapture) btnCapture.disabled = true;
  if (btnStop) btnStop.disabled = true;
}

function captureWebcam() {
  const video = document.getElementById('webcam-video');
  const canvas = document.getElementById('webcam-canvas');
  if (!video || !webcamStream) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(blob => {
    if (!blob) {
      showToast('Frame capture failed', 'error');
      return;
    }
    const file = new File([blob], 'webcam_capture.jpg', { type: 'image/jpeg' });
    processAttendanceImage(file);
  }, 'image/jpeg', 0.95);
}

const attImgInput = document.getElementById('att-img-input');
const attPreview  = document.getElementById('att-preview');
if (attImgInput) {
  attImgInput.addEventListener('change', () => {
    const file = attImgInput.files[0];
    if (file) { attPreview.src = URL.createObjectURL(file); attPreview.classList.remove('hidden'); }
  });
}

async function takeAttendance() {
  const file = attImgInput ? attImgInput.files[0] : null;
  if (!file) { showToast('Please select a classroom image first.', 'error'); return; }
  processAttendanceImage(file);
}

async function processAttendanceImage(file) {
  const spinner   = document.getElementById('att-spinner');
  const resultDiv = document.getElementById('att-result');
  spinner.classList.remove('hidden');
  resultDiv.innerHTML = '';

  const fd = new FormData();
  fd.append('image', file);

  try {
    const res  = await fetch(API + '/attendance/recognize', { method: 'POST', body: fd });
    const data = await res.json();
    spinner.classList.add('hidden');

    if (!res.ok) {
      resultDiv.innerHTML = `<div class="result-box error">❌ ${data.detail || 'Recognition failed.'}</div>`;
      return;
    }

    const rec = data.recognition;
    const att = data.attendance;

    let html = `<div class="result-box success">
      <strong>🔍 Detected ${rec.total_faces_detected} face(s)</strong><br/>
      Recognized Students: ${rec.recognized.length} | Unknown Faces: ${rec.unknown.length}
    </div>`;

    if (rec.recognized.length) {
      html += '<div style="margin-top:14px"><strong>✅ Recognized Students:</strong><div class="recognized-list">';
      rec.recognized.forEach(r => {
        const attStatus = att.find(a => a.student_id === r.student_id);
        const statusBadge = attStatus
          ? (attStatus.status === 'marked' ? '🟢 Present (Marked)' : '🟡 Already Marked')
          : '';
        html += `<div class="recognized-badge">👤 ${r.name} (${r.student_id}) — dist: ${r.distance} | conf: ${Math.round(r.confidence * 100)}% ${statusBadge}</div>`;
      });
      html += '</div></div>';
    }

    if (rec.unknown.length) {
      html += `<div style="margin-top:14px"><strong>❓ Unknown Faces (${rec.unknown.length}):</strong>
        <div class="unknown-list">${rec.unknown.map((u, i) => `<span class="unknown-badge">👤 Unknown Face #${i+1}</span>`).join('')}</div>
        <small style="color:#64748b;display:block;margin-top:4px;">* Unknown faces are never marked as present.</small>
      </div>`;
    }

    if (rec.error) html += `<div class="result-box error">⚠️ ${rec.error}</div>`;

    resultDiv.innerHTML = html;
    showToast(`Processed: ${rec.recognized.length} recognized, ${rec.unknown.length} unknown.`, 'success');
    loadOverview();
  } catch (err) {
    spinner.classList.add('hidden');
    resultDiv.innerHTML = `<div class="result-box error">❌ ${err.message}</div>`;
    showToast('Network error', 'error');
  }
}

// ════════════════════════════════════════════════════════════════
// RECORDS
// ════════════════════════════════════════════════════════════════
async function loadRecords() {
  const date   = document.getElementById('rec-date').value;
  const search = document.getElementById('rec-search').value;
  const params = new URLSearchParams();
  if (date)   params.set('date', date);
  if (search) params.set('search', search);

  try {
    const [recRes, sumRes] = await Promise.all([
      fetch(API + '/attendance/records?' + params),
      fetch(API + '/attendance/summary' + (date ? '?date=' + date : '')),
    ]);
    const records = await recRes.json();
    const summary = await sumRes.json();

    // Summary bar
    document.getElementById('rec-summary').innerHTML =
      `<span>📅 Date: ${summary.date}</span>
       <span>Total Students: ${summary.total_students}</span>
       <span>Present: ${summary.present}</span>
       <span>Absent: ${summary.absent}</span>
       <span>Attendance: ${summary.attendance_percentage}%</span>`;

    // Table
    const tbody = document.querySelector('#records-table tbody');
    if (!records.length) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#94a3b8;padding:24px">No attendance records found.</td></tr>';
      return;
    }
    tbody.innerHTML = records.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><strong>${r.student_id}</strong></td>
        <td>${r.name}</td>
        <td>${r.department || '–'}</td>
        <td>${r.year || '–'}</td>
        <td>${r.section || '–'}</td>
        <td>${r.date}</td>
        <td>${r.time}</td>
      </tr>`).join('');
  } catch (err) {
    showToast('Could not load records: ' + err.message, 'error');
  }
}

function exportCSV() {
  const date   = document.getElementById('rec-date').value;
  const search = document.getElementById('rec-search').value;
  const params = new URLSearchParams();
  if (date)   params.set('date', date);
  if (search) params.set('search', search);
  window.location.href = API + '/attendance/export?' + params;
}

// ════════════════════════════════════════════════════════════════
// EVALUATION
// ════════════════════════════════════════════════════════════════
async function loadEvalResults() {
  const loading = document.getElementById('eval-loading');
  const display = document.getElementById('eval-display');
  loading.classList.remove('hidden');

  try {
    const res = await fetch(API + '/evaluation/metrics');
    const data = await res.json();
    loading.classList.add('hidden');

    if (!data.metrics) {
      showToast('No saved evaluation results found. Click "Run Live Evaluation".', 'info');
      return;
    }

    display.classList.remove('hidden');
    const m = data.metrics;
    document.getElementById('em-acc').textContent  = (m.accuracy * 100).toFixed(1) + '%';
    document.getElementById('em-prec').textContent = (m.precision * 100).toFixed(1) + '%';
    document.getElementById('em-rec').textContent  = (m.recall * 100).toFixed(1) + '%';
    document.getElementById('em-f1').textContent   = (m.f1_score * 100).toFixed(1) + '%';

    // Confusion matrix image cache-buster
    const cmImg = document.getElementById('cm-image');
    cmImg.src = '/evaluation/confusion-matrix?t=' + Date.now();

    // Predictions table
    const tbody = document.querySelector('#eval-pred-table tbody');
    if (data.predictions && data.predictions.length) {
      tbody.innerHTML = data.predictions.map(p => {
        const isCorrect = String(p.correct).toLowerCase() === 'true';
        const badge = isCorrect
          ? '<span style="color:#16a34a;font-weight:600;">Match</span>'
          : '<span style="color:#dc2626;font-weight:600;">Mismatch</span>';
        return `<tr>
          <td>${p.image}</td>
          <td><strong>${p.actual}</strong></td>
          <td>${p.predicted}</td>
          <td>${badge}</td>
        </tr>`;
      }).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;">No predictions logged.</td></tr>';
    }

    showToast('Evaluation metrics loaded successfully.', 'success');
  } catch (err) {
    loading.classList.add('hidden');
    showToast('Failed to load metrics: ' + err.message, 'error');
  }
}

async function runLiveEvaluation() {
  const loading = document.getElementById('eval-loading');
  loading.classList.remove('hidden');
  showToast('Running evaluation script on test dataset...', 'info');

  try {
    const res = await fetch(API + '/evaluation/run', { method: 'POST' });
    const data = await res.json();
    loading.classList.add('hidden');
    if (data.success) {
      showToast('Evaluation completed successfully!', 'success');
      loadEvalResults();
    } else {
      showToast('Evaluation error: ' + (data.stderr || 'Script exited with error'), 'error');
    }
  } catch (err) {
    loading.classList.add('hidden');
    showToast('Evaluation execution failed: ' + err.message, 'error');
  }
}

