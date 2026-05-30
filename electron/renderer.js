// Brain4me Desktop — Renderer Process

(function () {
  'use strict';

  // ── DOM refs ──────────────────────────────────────────────────────────────

  const dbPathInput = document.getElementById('db-path-input');
  const saveConfigBtn = document.getElementById('save-config-btn');
  const configStatus = document.getElementById('config-status');

  const addFilesBtn = document.getElementById('add-files-btn');
  const ingestAllBtn = document.getElementById('ingest-all-btn');
  const clearFilesBtn = document.getElementById('clear-files-btn');
  const dropZone = document.getElementById('drop-zone');
  const fileList = document.getElementById('file-list');
  const progressContainer = document.getElementById('progress-container');
  const progressFill = document.getElementById('progress-fill');
  const progressLabel = document.getElementById('progress-label');
  const logContainer = document.getElementById('log-container');
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const summaryCounts = document.getElementById('summary-counts');
  const filesCount = document.getElementById('files-count');

  // ── State ─────────────────────────────────────────────────────────────────

  let selectedFiles = [];
  let isIngesting = false;

  // ── Helpers ───────────────────────────────────────────────────────────────

  function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
      case 'pdf':
        return '\u{1F4C4}'; // 📄
      case 'docx':
      case 'doc':
        return '\u{1F4DD}'; // 📝
      case 'txt':
        return '\u{1F4C3}'; // 📃
      case 'md':
      case 'markdown':
        return '\u{1F4D7}'; // 📗
      default:
        return '\u{1F4C1}'; // 📁
    }
  }

  function getFileName(path) {
    return path.split(/[/\\]/).pop();
  }

  function getTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour12: false });
  }

  function addLog(message, className) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML =
      '<span class="log-time">[' + getTimestamp() + ']</span>' +
      '<span class="log-msg' + (className ? ' ' + className : '') + '">' +
      escapeHtml(message) +
      '</span>';
    logContainer.insertBefore(entry, logContainer.firstChild);

    // Keep max 100 log entries
    while (logContainer.children.length > 100) {
      logContainer.removeChild(logContainer.lastChild);
    }
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function setIngesting(ingesting) {
    isIngesting = ingesting;
    addFilesBtn.disabled = ingesting;
    ingestAllBtn.disabled = ingesting || selectedFiles.length === 0;
    clearFilesBtn.disabled = ingesting;
    statusDot.className = 'status-dot ' + (ingesting ? 'offline' : 'ready');
    statusText.textContent = ingesting ? 'Ingesting...' : 'Ready';
  }

  function updateFileList() {
    fileList.innerHTML = '';
    selectedFiles.forEach(function (file, index) {
      var li = document.createElement('li');
      var name = getFileName(file);
      li.innerHTML =
        '<span class="file-icon">' + getFileIcon(name) + '</span>' +
        '<span class="file-name" title="' + escapeHtml(file) + '">' + escapeHtml(name) + '</span>' +
        '<span class="file-status" id="file-status-' + index + '"></span>' +
        '<button class="file-remove" data-index="' + index + '"' +
        (isIngesting ? ' disabled' : '') + '>&times;</button>';
      fileList.appendChild(li);
    });

    filesCount.textContent = selectedFiles.length + ' file' + (selectedFiles.length !== 1 ? 's' : '') + ' selected';
    dropZone.classList.toggle('has-files', selectedFiles.length > 0);
    ingestAllBtn.disabled = isIngesting || selectedFiles.length === 0;
  }

  function updateFileStatus(index, status, message) {
    var el = document.getElementById('file-status-' + index);
    if (!el) return;
    el.className = 'file-status ' + status;
    el.textContent = message || '';
  }

  function setProgress(current, total) {
    var pct = total > 0 ? Math.round((current / total) * 100) : 0;
    progressFill.style.width = pct + '%';
    progressLabel.textContent = current + ' / ' + total + ' (' + pct + '%)';
  }

  function showProgress() {
    progressContainer.removeAttribute('hidden');
  }

  function hideProgress() {
    progressContainer.setAttribute('hidden', '');
    progressFill.style.width = '0%';
    progressLabel.textContent = '';
  }

  async function refreshSummary() {
    try {
      var res = await window.brain4me.getConfig();
      if (!res.db_path) {
        summaryCounts.textContent = '— entities, — relations';
        return;
      }
      var summary = await window.brain4me.getSummary();
      if (summary && summary.ok && summary.data && summary.data.counts) {
        var c = summary.data.counts;
        summaryCounts.textContent =
          (c.Entities || 0) + ' entities, ' +
          (c.Relations || 0) + ' relations';
      }
    } catch (e) {
      // Silently ignore — summary is best-effort
    }
  }

  // ── Event Handlers ────────────────────────────────────────────────────────

  // Config
  async function loadConfig() {
    try {
      var res = await window.brain4me.getConfig();
      if (res.db_path) {
        dbPathInput.value = res.db_path;
        configStatus.textContent = 'Database configured.';
        addLog('Database path loaded: ' + res.db_path);
        statusDot.className = 'status-dot ready';
        refreshSummary();
      }
    } catch (e) {
      configStatus.textContent = 'Failed to load configuration.';
    }
  }

  saveConfigBtn.addEventListener('click', async function () {
    var path = dbPathInput.value.trim();
    if (!path) {
      configStatus.textContent = 'Please enter a database path.';
      return;
    }
    try {
      await window.brain4me.setConfig('db_path', path);
      configStatus.textContent = 'Saved.';
      addLog('Database path set: ' + path);
      statusDot.className = 'status-dot ready';
      refreshSummary();
    } catch (e) {
      configStatus.textContent = 'Failed to save.';
    }
  });

  dbPathInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') saveConfigBtn.click();
  });

  // File picker
  addFilesBtn.addEventListener('click', async function () {
    if (isIngesting) return;
    try {
      var files = await window.brain4me.openFiles();
      if (files && files.length > 0) {
        // Deduplicate
        var existing = new Set(selectedFiles);
        files.forEach(function (f) {
          if (!existing.has(f)) {
            selectedFiles.push(f);
            existing.add(f);
          }
        });
        updateFileList();
        addLog(files.length + ' file(s) added to queue.');
      }
    } catch (e) {
      addLog('Failed to open file dialog: ' + e.message, 'error');
    }
  });

  // File remove via event delegation
  fileList.addEventListener('click', function (e) {
    var btn = e.target.closest('.file-remove');
    if (!btn || btn.disabled) return;
    var index = parseInt(btn.getAttribute('data-index'), 10);
    if (!isNaN(index)) {
      selectedFiles.splice(index, 1);
      updateFileList();
    }
  });

  // Clear
  clearFilesBtn.addEventListener('click', function () {
    if (isIngesting) return;
    selectedFiles = [];
    updateFileList();
    hideProgress();
  });

  // Ingest All
  ingestAllBtn.addEventListener('click', async function () {
    if (isIngesting || selectedFiles.length === 0) return;

    setIngesting(true);
    showProgress();
    setProgress(0, selectedFiles.length);

    // Reset all file statuses
    selectedFiles.forEach(function (_, i) {
      updateFileStatus(i, '', '');
    });

    addLog('Starting ingest of ' + selectedFiles.length + ' file(s)...');

    try {
      var results = await window.brain4me.ingestBatch(selectedFiles);
      var succeeded = 0;
      var failed = 0;
      var totalEntities = 0;
      var totalRelations = 0;

      results.forEach(function (r, i) {
        if (r.ok) {
          succeeded++;
          updateFileStatus(i, 'done', '\u2713');
          if (r.result && r.result.entities_created !== undefined) {
            totalEntities += r.result.entities_created;
          }
          if (r.result && r.result.relations_created !== undefined) {
            totalRelations += r.result.relations_created;
          }
          addLog('Ingested: ' + getFileName(r.filePath), 'success');
        } else {
          failed++;
          updateFileStatus(i, 'error', '\u2717');
          addLog('Failed: ' + getFileName(r.filePath) + ' — ' + r.error, 'error');
        }
      });

      var msg = succeeded + ' file(s) ingested, ' + failed + ' failed.';
      if (totalEntities || totalRelations) {
        msg += ' ' + totalEntities + ' entities, ' + totalRelations + ' relations detected.';
      }
      addLog(msg);
      setProgress(selectedFiles.length, selectedFiles.length);
      progressLabel.textContent = msg;
      refreshSummary();
    } catch (e) {
      addLog('Batch ingest error: ' + e.message, 'error');
    } finally {
      setIngesting(false);
    }
  });

  // Drag & drop
  dropZone.addEventListener('dragover', function (e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', function (e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', function (e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');

    var droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length === 0) return;

    var existing = new Set(selectedFiles);
    droppedFiles.forEach(function (f) {
      // Only accept files with supported extensions
      var ext = f.name.split('.').pop().toLowerCase();
      var supported = ['pdf', 'docx', 'doc', 'txt', 'md', 'markdown'];
      if (supported.indexOf(ext) === -1) return;
      // On drop we get File objects, not full paths — use the path property
      if (f.path && !existing.has(f.path)) {
        selectedFiles.push(f.path);
        existing.add(f.path);
      }
    });

    updateFileList();
    addLog(droppedFiles.length + ' file(s) dropped into queue.');
  });

  // Tray "Ingest Files" event
  window.brain4me.onIngestProgress(function (data) {
    if (data.status === 'processing') {
      setProgress(data.current, data.total);
      updateFileStatus(data.current - 1, 'processing', '\u23F3');
    } else if (data.status === 'done') {
      setProgress(data.current, data.total);
      updateFileStatus(data.current - 1, 'done', '\u2713');
      refreshSummary();
    } else if (data.status === 'error') {
      setProgress(data.current, data.total);
      updateFileStatus(data.current - 1, 'error', '\u2717');
    } else if (data.status === 'complete') {
      addLog('Ingest complete: ' + data.succeeded + ' succeeded, ' + data.failed + ' failed.');
      setIngesting(false);
    }
  });

  // Listen for tray "Ingest" action
  window.brain4me.onTrayIngest(function () {
    if (selectedFiles.length > 0 && !isIngesting) {
      ingestAllBtn.click();
    }
  });

  // ── Init ──────────────────────────────────────────────────────────────────

  loadConfig();
})();
