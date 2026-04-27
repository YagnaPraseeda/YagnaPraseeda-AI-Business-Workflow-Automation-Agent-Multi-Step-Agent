/* ── State ── */
let uploadedFilePath = null;
let lastResult = '';

/* ── Server health indicator ── */
async function checkHealth() {
  const dot = document.getElementById('status-dot');
  try {
    const res = await fetch('/api/v1/health');
    dot.classList.toggle('ok',  res.ok);
    dot.classList.toggle('err', !res.ok);
    dot.title = res.ok ? 'Server online' : 'Server error';
  } catch {
    dot.className = 'status-dot err';
    dot.title = 'Cannot reach server';
  }
}
checkHealth();

/* ── File selection ── */
document.getElementById('file-input').addEventListener('change', (e) => {
  const file = e.target.files[0];
  document.getElementById('file-name').textContent = file ? file.name : 'No file selected';
  document.getElementById('clear-file-btn').classList.toggle('hidden', !file);
  uploadedFilePath = null;
});

function clearFile() {
  const input = document.getElementById('file-input');
  input.value = '';
  document.getElementById('file-name').textContent = 'No file selected';
  document.getElementById('clear-file-btn').classList.add('hidden');
  uploadedFilePath = null;
}

/* ── Main workflow runner ── */
async function runWorkflow() {
  const instruction = document.getElementById('instruction').value.trim();
  if (!instruction) {
    showError('Please enter an instruction before running.');
    return;
  }

  setLoading(true);
  hideError();
  clearPanels();

  try {
    /* Step 1 — upload file if one is selected and not yet uploaded */
    const fileInput = document.getElementById('file-input');
    if (fileInput.files[0] && !uploadedFilePath) {
      const form = new FormData();
      form.append('file', fileInput.files[0]);

      const upRes = await fetch('/api/v1/upload', { method: 'POST', body: form });
      if (!upRes.ok) {
        const err = await upRes.json().catch(() => ({}));
        throw new Error(err.detail || 'File upload failed');
      }
      uploadedFilePath = (await upRes.json()).file_path;
    }

    /* Step 2 — run the workflow */
    const payload = { instruction };
    if (uploadedFilePath) payload.file_path = uploadedFilePath;

    const res = await fetch('/api/v1/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }

    const data = await res.json();
    renderLog(data.execution_log, data.total_duration_ms);
    renderResult(data.result);

  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

/* ── Render execution log ── */
function renderLog(steps, totalMs) {
  const panel = document.getElementById('log-panel');
  const container = document.getElementById('log-steps');
  panel.classList.remove('hidden');
  container.innerHTML = '';

  steps.forEach((step, i) => {
    setTimeout(() => {
      const el = document.createElement('div');
      el.className = 'step';

      const statusClass = step.status === 'error' ? 'error' : 'completed';
      const statusLabel = step.status === 'error' ? '✗ Error' : '✓ Done';
      const reasonHtml  = step.reasoning
        ? `<div class="step-reason">💭 ${esc(step.reasoning)}</div>`
        : '';

      el.innerHTML = `
        <div class="step-num">${step.step_number}</div>
        <div class="step-body">
          <div class="step-head">
            <span class="step-tool">${esc(step.tool_name)}</span>
            <span class="step-status ${statusClass}">${statusLabel}</span>
            <span class="step-ms">${step.duration_ms} ms</span>
          </div>
          ${reasonHtml}
          <div class="step-out">${esc(step.output)}</div>
        </div>`;
      container.appendChild(el);
    }, i * 150);
  });

  setTimeout(() => {
    document.getElementById('total-time').textContent =
      `Completed ${steps.length} step${steps.length !== 1 ? 's' : ''} in ${(totalMs / 1000).toFixed(2)}s`;
  }, steps.length * 150 + 50);
}

/* ── Render final result as Markdown ── */
function renderResult(text) {
  lastResult = text;
  const panel = document.getElementById('result-panel');
  const content = document.getElementById('result-content');
  panel.classList.remove('hidden');
  content.innerHTML = marked.parse(text);
}

/* ── Copy result to clipboard ── */
function copyResult() {
  if (!lastResult) return;
  navigator.clipboard.writeText(lastResult).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => (btn.textContent = 'Copy'), 1800);
  });
}

/* ── Download result as .md file ── */
function downloadReport() {
  if (!lastResult) return;
  const blob = new Blob([lastResult], { type: 'text/markdown' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `report_${new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/* ── UI helpers ── */
function setLoading(on) {
  const btn  = document.getElementById('run-btn');
  const text = document.getElementById('btn-text');
  const spin = document.getElementById('btn-spinner');
  btn.disabled = on;
  text.textContent = on ? 'Running…' : '▶ Run Workflow';
  spin.classList.toggle('hidden', !on);
}

function clearPanels() {
  document.getElementById('log-panel').classList.add('hidden');
  document.getElementById('result-panel').classList.add('hidden');
  document.getElementById('log-steps').innerHTML = '';
  document.getElementById('total-time').textContent = '';
  document.getElementById('result-content').innerHTML = '';
  lastResult = '';
}

function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = `Error: ${msg}`;
  el.classList.remove('hidden');
}

function hideError() {
  document.getElementById('error-msg').classList.add('hidden');
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
