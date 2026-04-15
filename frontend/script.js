/**
 * script.js — AI Background Remover frontend logic
 *
 * Responsibilities:
 *  - Drag-and-drop + click-to-browse file selection
 *  - Client-side file validation (size + type)
 *  - Calls FastAPI backend: /api/remove-bg or /api/replace-bg
 *  - Renders before / after preview
 *  - Provides one-click PNG download
 */

'use strict';

// ─────────────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────────────
const API_BASE        = '';          // Same origin — FastAPI serves both
const MAX_SIZE_MB     = 5;
const MAX_SIZE_BYTES  = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_TYPES   = new Set(['image/jpeg', 'image/png', 'image/webp']);

// ─────────────────────────────────────────────────────────────────────────────
// DOM refs
// ─────────────────────────────────────────────────────────────────────────────
const dropZone         = document.getElementById('drop-zone');
const fileInput        = document.getElementById('file-input');
const browseBtn        = document.getElementById('browse-btn');
const optionsRow       = document.getElementById('options-row');
const actionRow        = document.getElementById('action-row');
const processBtn       = document.getElementById('process-btn');
const clearBtn         = document.getElementById('clear-btn');
const errorBanner      = document.getElementById('error-banner');
const errorMsg         = document.getElementById('error-msg');
const previewSection   = document.getElementById('preview-section');
const imgOriginal      = document.getElementById('img-original');
const imgProcessed     = document.getElementById('img-processed');
const downloadLink     = document.getElementById('download-link');
const tryAnotherBtn    = document.getElementById('try-another-btn');
const processingOverlay= document.getElementById('processing-overlay');
const chkColor         = document.getElementById('chk-color');
const colorPicker      = document.getElementById('color-picker');
const btnLabel         = processBtn.querySelector('.btn-label');
const btnSpinner       = processBtn.querySelector('.btn-spinner');

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
let selectedFile = null;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Display an error message to the user. */
function showError(message) {
  errorMsg.textContent = message;
  errorBanner.hidden = false;
}

/** Hide the error banner. */
function clearError() {
  errorBanner.hidden = true;
  errorMsg.textContent = '';
}

/** Show / hide the full-screen processing overlay. */
function setProcessing(active) {
  processingOverlay.hidden = !active;
  processBtn.disabled = active;
  btnLabel.hidden = active;
  btnSpinner.hidden = !active;
}

/** Reset everything back to the initial empty state. */
function resetUI() {
  selectedFile = null;
  fileInput.value = '';
  dropZone.classList.remove('has-file');

  // Restore default drop-zone inner
  const inner = document.getElementById('dz-default');
  inner.hidden = false;

  // Remove any thumbnail that may have been inserted
  const thumb = dropZone.querySelector('.dz-preview');
  if (thumb) thumb.remove();

  optionsRow.hidden = true;
  actionRow.hidden  = true;
  previewSection.hidden = true;
  clearError();

  // Revoke previous object URLs to free memory
  if (imgOriginal.src.startsWith('blob:'))  URL.revokeObjectURL(imgOriginal.src);
  if (imgProcessed.src.startsWith('blob:')) URL.revokeObjectURL(imgProcessed.src);
  if (downloadLink.href.startsWith('blob:'))URL.revokeObjectURL(downloadLink.href);
}

/** Validate a file before accepting it. Returns true on success. */
function validateFile(file) {
  if (!ALLOWED_TYPES.has(file.type)) {
    showError(`Unsupported file type "${file.type}". Please upload a JPG, PNG, or WebP image.`);
    return false;
  }
  if (file.size > MAX_SIZE_BYTES) {
    const mb = (file.size / (1024 * 1024)).toFixed(1);
    showError(`File is ${mb} MB — exceeds the ${MAX_SIZE_MB} MB limit. Please choose a smaller image.`);
    return false;
  }
  return true;
}

/** Accept a validated File object and update the UI. */
function acceptFile(file) {
  clearError();
  selectedFile = file;

  // Show thumbnail inside drop zone
  const reader = new FileReader();
  reader.onload = (e) => {
    const inner = document.getElementById('dz-default');
    inner.hidden = true;

    // Remove old preview if present
    const oldThumb = dropZone.querySelector('.dz-preview');
    if (oldThumb) oldThumb.remove();

    const preview = document.createElement('div');
    preview.className = 'dz-preview';
    preview.innerHTML = `
      <img src="${e.target.result}" alt="Preview of ${file.name}" />
      <p class="dz-filename">📎 ${file.name} (${(file.size / 1024).toFixed(0)} KB)</p>
    `;
    dropZone.appendChild(preview);
  };
  reader.readAsDataURL(file);

  dropZone.classList.add('has-file');
  optionsRow.hidden = false;
  actionRow.hidden  = false;
  previewSection.hidden = true;
}

// ─────────────────────────────────────────────────────────────────────────────
// Drag & Drop
// ─────────────────────────────────────────────────────────────────────────────

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && validateFile(file)) acceptFile(file);
});

// Click anywhere on the drop zone (except the browse button itself)
dropZone.addEventListener('click', (e) => {
  if (e.target !== browseBtn) fileInput.click();
});

// Keyboard accessibility
dropZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});

browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file && validateFile(file)) acceptFile(file);
});

// ─────────────────────────────────────────────────────────────────────────────
// Colour-replace toggle
// ─────────────────────────────────────────────────────────────────────────────
chkColor.addEventListener('change', () => {
  colorPicker.disabled = !chkColor.checked;
});

// ─────────────────────────────────────────────────────────────────────────────
// Process
// ─────────────────────────────────────────────────────────────────────────────
processBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  clearError();
  setProcessing(true);

  try {
    const formData = new FormData();
    formData.append('file', selectedFile);

    let endpoint = `${API_BASE}/api/remove-bg`;

    if (chkColor.checked) {
      endpoint = `${API_BASE}/api/replace-bg`;
      formData.append('color', colorPicker.value);
    }

    const resp = await fetch(endpoint, {
      method: 'POST',
      body: formData,
    });

    if (!resp.ok) {
      // Try to extract a JSON detail message from FastAPI
      let detail = `Server error (HTTP ${resp.status})`;
      try {
        const json = await resp.json();
        detail = json.detail || detail;
      } catch (_) { /* ignore */ }
      throw new Error(detail);
    }

    // Convert response to a blob URL
    const blob = await resp.blob();
    const objectUrl = URL.createObjectURL(blob);

    // Show original
    imgOriginal.src = URL.createObjectURL(selectedFile);

    // Show processed
    imgProcessed.src = objectUrl;

    // Wire download link
    downloadLink.href = objectUrl;
    const baseName = selectedFile.name.replace(/\.[^.]+$/, '');
    downloadLink.download = `${baseName}_nobg.png`;

    previewSection.hidden = false;
    previewSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showError(err.message || 'An unexpected error occurred. Please try again.');
  } finally {
    setProcessing(false);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Clear / Try another
// ─────────────────────────────────────────────────────────────────────────────
clearBtn.addEventListener('click', resetUI);
tryAnotherBtn.addEventListener('click', () => {
  resetUI();
  dropZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
});
