/* MeetAssist — Main JS */

// ── Sidebar toggle ──────────────────────────────
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
if (menuToggle && sidebar) {
  menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

// ── Flash auto-dismiss ─────────────────────────
document.querySelectorAll('.flash').forEach(el => {
  setTimeout(() => el.style.opacity = '0', 4000);
  setTimeout(() => el.remove(), 4400);
});

// ── AJAX Task status update ─────────────────────
async function updateTaskStatus(taskId, newStatus, el) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    const data = await res.json();

    if (res.status === 403) {
      showToast(data.error || 'Permission denied.', 'error');
      // Revert the select/checkbox to original value
      if (el.tagName === 'SELECT') {
        const task = data; // no task returned on error
        // reload to revert UI
        location.reload();
      } else {
        el.classList.toggle('checked'); // revert checkbox
      }
      return;
    }

    if (data.success) {
      const row = el.closest('[data-task-id]') || el.closest('tr');
      if (row) {
        const badge = row.querySelector('.badge');
        if (badge) {
          badge.className = `badge badge-${newStatus}`;
          const labels = { pending: '🔴 Pending', in_progress: '🟡 In Progress', completed: '🟢 Completed' };
          badge.innerHTML = `<span class="badge-dot"></span>${labels[newStatus] || newStatus}`;
        }
        if (newStatus === 'completed') {
          row.classList.add('completed');
        } else {
          row.classList.remove('completed');
        }
      }
      showToast(`Task marked as ${newStatus.replace('_', ' ')}`, 'success');
    }
  } catch (err) {
    showToast('Failed to update task', 'error');
  }
}

// ── Checkbox toggle ─────────────────────────────
document.querySelectorAll('.task-check').forEach(check => {
  check.addEventListener('click', function () {
    const taskId = this.dataset.taskId;
    const isChecked = this.classList.toggle('checked');
    const newStatus = isChecked ? 'completed' : 'pending';
    updateTaskStatus(taskId, newStatus, this);
  });
});

// ── Status select dropdowns ─────────────────────
document.querySelectorAll('.status-select').forEach(sel => {
  sel.addEventListener('change', function () {
    const taskId = this.dataset.taskId;
    updateTaskStatus(taskId, this.value, this);
  });
});

// ── Toast notification ─────────────────────────
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `flash flash-${type}`;
  toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;min-width:240px;animation:slideIn 0.3s ease';
  toast.innerHTML = `<span>${message}</span><button onclick="this.parentElement.remove()">×</button>`;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; }, 3000);
  setTimeout(() => toast.remove(), 3400);
}

// ── Progress bars animation ─────────────────────
function animateProgressBars() {
  document.querySelectorAll('.progress-fill[data-width]').forEach(el => {
    const w = el.dataset.width;
    setTimeout(() => el.style.width = w + '%', 100);
  });
}
animateProgressBars();

// ── Counter animation ───────────────────────────
function animateCounters() {
  document.querySelectorAll('.stat-num[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target);
    let current = 0;
    const step = Math.ceil(target / 25);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
}
animateCounters();

// ── Confirm delete dialogs ─────────────────────
document.querySelectorAll('[data-confirm]').forEach(form => {
  form.addEventListener('submit', function (e) {
    if (!confirm(this.dataset.confirm)) e.preventDefault();
  });
});

// ── Live search filter ─────────────────────────
const searchInput = document.getElementById('liveSearch');
if (searchInput) {
  searchInput.addEventListener('input', function () {
    const q = this.value.toLowerCase();
    document.querySelectorAll('[data-searchable]').forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(q) ? '' : 'none';
    });
  });
}

// ── Char counter for transcript ─────────────────
const transcriptArea = document.getElementById('transcriptInput');
const charCount = document.getElementById('charCount');
if (transcriptArea && charCount) {
  transcriptArea.addEventListener('input', function () {
    const wc = this.value.trim().split(/\s+/).filter(Boolean).length;
    charCount.textContent = `${wc} words`;
  });
}

// ── Tab switching ──────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', function () {
    const target = this.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    this.classList.add('active');
    document.getElementById(target)?.classList.add('active');
  });
});
