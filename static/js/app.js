// State Management
let currentTab = 'view-dashboard';
let currentInvoice = null;
let currentZoom = 1.0;
let invoicesList = [];

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  initNavigation();
  initDropzone();
  initReviewer();
  initWatcherHub();
  initSettings();
  
  // Initial Data Load
  fetchStats();
  fetchInvoices();
  fetchWatcherStatus();

  // Auto-refresh stats every 10 seconds
  setInterval(() => {
    fetchStats();
    if (currentTab === 'view-ledger') {
      fetchInvoices();
    }
  }, 10000);
});

// Navigation Handling
function initNavigation() {
  const navBtns = document.querySelectorAll('.nav-btn');
  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-target');
      switchToTab(target);
    });
  });
}

function switchToTab(targetId) {
  currentTab = targetId;
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-target') === targetId);
  });
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.toggle('active', sec.id === targetId);
  });
  
  if (targetId === 'view-ledger') {
    fetchInvoices();
  } else if (targetId === 'view-dashboard') {
    fetchStats();
  }
  lucide.createIcons();
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'error') iconName = 'alert-triangle';
  
  toast.innerHTML = `
    <i data-lucide="${iconName}" style="width: 18px; height: 18px;"></i>
    <div style="flex: 1;">${message}</div>
  `;
  container.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Fetch Dashboard Metrics & KPIs
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('kpi-total-docs').textContent = data.total_invoices || 0;
    document.getElementById('kpi-total-spend').textContent = `$${(data.total_spend || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('kpi-approved-count').textContent = data.approved_count || 0;
    document.getElementById('kpi-flagged-count').textContent = data.flagged_count || 0;
    document.getElementById('kpi-confidence-sub').textContent = `Avg Confidence: ${data.avg_confidence || 0}%`;
    document.getElementById('kpi-high-val-sub').textContent = `${data.high_value_count || 0} High-Value (≥$5k)`;
    document.getElementById('nav-count-badge').textContent = data.total_invoices || 0;

    // Render Vendor Spend Breakdown
    renderVendorSpend(data.top_vendors || []);

    // Render Alerts Feed
    renderAlertsFeed(data.recent_alerts || []);

  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

function renderVendorSpend(vendors) {
  const container = document.getElementById('vendor-spend-container');
  if (!vendors || vendors.length === 0) {
    container.innerHTML = '<p style="color: var(--text-dim); text-align: center; padding: 30px 0;">No documents ingested yet.</p>';
    return;
  }

  const maxSpend = Math.max(...vendors.map(v => v.total_spend), 1);
  let html = '';
  vendors.forEach(v => {
    const pct = Math.min(100, Math.round((v.total_spend / maxSpend) * 100));
    html += `
      <div class="vendor-item">
        <div class="vendor-meta">
          <span style="font-weight: 600; color: var(--text-main);">${escapeHtml(v.vendor)} <small style="color: var(--text-dim);">(${v.count} inv)</small></span>
          <span style="font-weight: 700; color: var(--accent-cyan);">$${v.total_spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
        </div>
        <div class="vendor-bar-bg">
          <div class="vendor-bar-fill" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

function renderAlertsFeed(alerts) {
  const container = document.getElementById('alert-feed-list');
  const badge = document.getElementById('badge-alert-count');
  badge.textContent = `${alerts.length} Alerts`;

  if (!alerts || alerts.length === 0) {
    container.innerHTML = '<p style="color: var(--text-dim); text-align: center; padding: 30px 0;">No active alerts.</p>';
    return;
  }

  let html = '';
  alerts.forEach(a => {
    html += `
      <div class="alert-feed-item ${a.severity}">
        <div class="alert-feed-title">
          <span>${escapeHtml(a.title)}</span>
          <span style="font-size: 0.7rem; color: var(--text-dim);">${formatTime(a.created_at)}</span>
        </div>
        <div class="alert-feed-msg">${escapeHtml(a.message)}</div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// Fetch Invoices for Ledger
async function fetchInvoices() {
  const status = document.getElementById('ledger-status-filter').value;
  const query = document.getElementById('ledger-search').value.trim();

  let url = '/api/invoices?';
  if (status && status !== 'ALL') url += `status=${status}&`;
  if (query) url += `q=${encodeURIComponent(query)}&`;

  try {
    const res = await fetch(url);
    if (!res.ok) return;
    invoicesList = await res.json();
    renderInvoicesTable(invoicesList);
  } catch (err) {
    console.error('Error fetching invoices:', err);
  }
}

function renderInvoicesTable(invoices) {
  const tbody = document.getElementById('invoices-table-body');
  if (!invoices || invoices.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; color: var(--text-dim); padding: 40px;">
          No matching documents found. Upload or generate sample invoices above.
        </td>
      </tr>
    `;
    return;
  }

  let html = '';
  invoices.forEach(inv => {
    let statusBadge = `<span class="status-badge badge-${inv.status.toLowerCase()}">${inv.status}</span>`;
    if (inv.is_high_value) {
      statusBadge += ` <span class="status-badge badge-high-val">HIGH-VAL</span>`;
    }

    const flagsCount = inv.validation_issues ? inv.validation_issues.length : 0;
    const flagsDisplay = flagsCount > 0 
      ? `<span style="color: var(--accent-rose); font-weight: 600; font-size: 0.8rem;">⚠️ ${flagsCount} issue(s)</span>`
      : `<span style="color: var(--accent-emerald); font-size: 0.8rem;">✓ Verified</span>`;

    html += `
      <tr>
        <td>${statusBadge}</td>
        <td>
          <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(inv.data.vendor_name || 'Unknown')}</div>
          <div style="font-size: 0.75rem; color: var(--text-dim);">${escapeHtml(inv.original_filename)}</div>
        </td>
        <td><code style="color: var(--accent-cyan);">${escapeHtml(inv.data.invoice_number || 'N/A')}</code></td>
        <td>${escapeHtml(inv.data.invoice_date || '-')}</td>
        <td style="font-weight: 700; color: var(--text-main);">$${(inv.data.total_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
        <td>${(inv.data.line_items || []).length}</td>
        <td><span style="font-weight: 600;">${Math.round((inv.data.confidence_score || 1.0) * 100)}%</span></td>
        <td>${flagsDisplay}</td>
        <td style="text-align: right;">
          <div style="display: inline-flex; gap: 6px;">
            <button class="btn btn-secondary btn-sm" onclick="openReviewer('${inv.id}')" title="Inspect and Review">
              <i data-lucide="edit-3" style="width: 14px; height: 14px;"></i> Review
            </button>
            <button class="btn-icon btn-sm" onclick="deleteInvoicePrompt('${inv.id}')" title="Delete">
              <i data-lucide="trash-2" style="width: 14px; height: 14px; color: var(--accent-rose);"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
  lucide.createIcons();
}

// Upload & Drag-Drop Handling
function initDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileUpload(fileInput.files);
    }
  });

  // Sample Generators
  document.getElementById('btn-quick-samples').addEventListener('click', triggerPresetGeneration);
  document.getElementById('btn-load-presets-dash').addEventListener('click', triggerPresetGeneration);

  // Search & Filter listeners
  document.getElementById('ledger-search').addEventListener('input', debounce(fetchInvoices, 300));
  document.getElementById('ledger-status-filter').addEventListener('change', fetchInvoices);
}

async function handleFileUpload(files) {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  showToast(`Uploading and extracting ${files.length} document(s)...`, 'info');
  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, 'success');
      fetchStats();
      fetchInvoices();
      if (data.records && data.records.length > 0) {
        openReviewer(data.records[0].id);
      }
    } else {
      showToast(`Upload failed: ${data.detail || 'Error'}`, 'error');
    }
  } catch (err) {
    showToast('Failed to upload file to server.', 'error');
  }
}

async function triggerPresetGeneration() {
  showToast('Generating 4 realistic test PDF invoices...', 'info');
  try {
    const res = await fetch('/api/generate-samples', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, 'success');
      fetchStats();
      fetchInvoices();
      switchToTab('view-ledger');
    } else {
      showToast('Sample generation error', 'error');
    }
  } catch (err) {
    showToast('Failed to generate sample invoices.', 'error');
  }
}

// Split Screen Reviewer Logic
function initReviewer() {
  // Zoom Buttons
  document.getElementById('btn-zoom-in').addEventListener('click', () => {
    currentZoom = Math.min(currentZoom + 0.2, 3.0);
    applyZoom();
  });
  document.getElementById('btn-zoom-out').addEventListener('click', () => {
    currentZoom = Math.max(currentZoom - 0.2, 0.5);
    applyZoom();
  });
  document.getElementById('btn-zoom-reset').addEventListener('click', () => {
    currentZoom = 1.0;
    applyZoom();
  });

  // Action Buttons
  document.getElementById('btn-add-line-row').addEventListener('click', () => addLineItemRow());
  document.getElementById('btn-recalculate-math').addEventListener('click', recalculateTotalsFromLines);
  document.getElementById('btn-approve-save').addEventListener('click', () => saveInvoiceChanges(ValidationStatusApproved = true));
  document.getElementById('btn-reject-invoice').addEventListener('click', () => saveInvoiceChanges(ValidationStatusApproved = false, isReject = true));
  document.getElementById('btn-reprocess-invoice').addEventListener('click', reprocessCurrentInvoice);

  // Live total inputs trigger recalculation
  ['edit-subtotal', 'edit-tax', 'edit-shipping', 'edit-discount'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', autoUpdateGrandTotal);
  });
}

function applyZoom() {
  const img = document.getElementById('preview-image');
  if (img) {
    img.style.transform = `scale(${currentZoom})`;
  }
}

async function openReviewer(invoiceId) {
  try {
    const res = await fetch(`/api/invoices/${invoiceId}`);
    if (!res.ok) {
      showToast('Could not load invoice details', 'error');
      return;
    }
    currentInvoice = await res.json();
    switchToTab('view-reviewer');
    populateReviewerUI(currentInvoice);
  } catch (err) {
    showToast('Error opening reviewer', 'error');
  }
}

function populateReviewerUI(record) {
  document.getElementById('reviewer-empty-state').style.display = 'none';
  document.getElementById('reviewer-split-container').style.display = 'grid';

  // Preview Pane
  document.getElementById('preview-filename').textContent = record.original_filename;
  document.getElementById('preview-filetype').textContent = record.file_type;
  document.getElementById('btn-open-raw-file').href = `/api/files/${record.filename}`;

  const previewImg = document.getElementById('preview-image');
  const previewPlaceholder = document.getElementById('preview-placeholder');
  
  previewImg.src = `/api/render-preview/${record.filename}?t=${Date.now()}`;
  previewImg.style.display = 'block';
  previewPlaceholder.style.display = 'none';
  currentZoom = 1.0;
  applyZoom();

  // Status Badge
  const statusPill = document.getElementById('review-status-pill');
  statusPill.className = `status-badge badge-${record.status.toLowerCase()}`;
  statusPill.textContent = record.status;

  // Issues Banner
  const banner = document.getElementById('review-issues-banner');
  const issueCount = document.getElementById('issue-count');
  const issueList = document.getElementById('issue-items-list');

  if (record.validation_issues && record.validation_issues.length > 0) {
    banner.style.display = 'block';
    issueCount.textContent = record.validation_issues.length;
    let issuesHtml = '';
    record.validation_issues.forEach(iss => {
      issuesHtml += `<div class="issue-item"><span>⚠️</span> <span>${escapeHtml(iss.message)}</span></div>`;
    });
    issueList.innerHTML = issuesHtml;
  } else {
    banner.style.display = 'none';
  }

  // Populate Form Fields
  document.getElementById('edit-vendor').value = record.data.vendor_name || '';
  document.getElementById('edit-invoice-num').value = record.data.invoice_number || '';
  document.getElementById('edit-date').value = record.data.invoice_date || '';
  document.getElementById('edit-due-date').value = record.data.due_date || '';
  document.getElementById('edit-po').value = record.data.po_number || '';

  document.getElementById('edit-subtotal').value = record.data.subtotal || 0;
  document.getElementById('edit-tax').value = record.data.tax_amount || 0;
  document.getElementById('edit-shipping').value = record.data.shipping_amount || 0;
  document.getElementById('edit-discount').value = record.data.discount_amount || 0;
  document.getElementById('edit-total').value = record.data.total_amount || 0;
  document.getElementById('edit-notes').value = record.reviewer_notes || '';

  // Line items
  renderLineItemRows(record.data.line_items || []);
  lucide.createIcons();
}

function renderLineItemRows(items) {
  const tbody = document.getElementById('line-items-body');
  document.getElementById('line-items-count').textContent = items.length;
  tbody.innerHTML = '';

  items.forEach((item, idx) => {
    const row = document.createElement('tr');
    const mathMismatch = !item.math_match;
    
    row.innerHTML = `
      <td><input type="text" class="form-control item-desc" value="${escapeHtml(item.description)}" style="padding: 6px 8px;"></td>
      <td><input type="number" step="0.5" class="form-control item-qty" value="${item.quantity}" style="padding: 6px 8px; text-align: right;" onchange="updateLineMath(this)"></td>
      <td><input type="number" step="0.01" class="form-control item-price" value="${item.unit_price}" style="padding: 6px 8px; text-align: right;" onchange="updateLineMath(this)"></td>
      <td><input type="number" step="0.01" class="form-control item-amount ${mathMismatch ? 'error' : ''}" value="${item.amount}" style="padding: 6px 8px; text-align: right; font-weight: 600;" onchange="autoUpdateSubtotalFromRows()"></td>
      <td style="text-align: center;">
        <button type="button" class="btn-icon" style="width: 26px; height: 26px; color: var(--accent-rose);" onclick="removeLineRow(this)" title="Delete Row">
          <i data-lucide="x" style="width: 14px; height: 14px;"></i>
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
  lucide.createIcons();
}

function addLineItemRow() {
  const tbody = document.getElementById('line-items-body');
  const row = document.createElement('tr');
  row.innerHTML = `
    <td><input type="text" class="form-control item-desc" value="New Line Item" style="padding: 6px 8px;"></td>
    <td><input type="number" step="1" class="form-control item-qty" value="1" style="padding: 6px 8px; text-align: right;" onchange="updateLineMath(this)"></td>
    <td><input type="number" step="0.01" class="form-control item-price" value="0.00" style="padding: 6px 8px; text-align: right;" onchange="updateLineMath(this)"></td>
    <td><input type="number" step="0.01" class="form-control item-amount" value="0.00" style="padding: 6px 8px; text-align: right; font-weight: 600;" onchange="autoUpdateSubtotalFromRows()"></td>
    <td style="text-align: center;">
      <button type="button" class="btn-icon" style="width: 26px; height: 26px; color: var(--accent-rose);" onclick="removeLineRow(this)">
        <i data-lucide="x" style="width: 14px; height: 14px;"></i>
      </button>
    </td>
  `;
  tbody.appendChild(row);
  document.getElementById('line-items-count').textContent = tbody.children.length;
  lucide.createIcons();
}

function removeLineRow(btn) {
  btn.closest('tr').remove();
  const tbody = document.getElementById('line-items-body');
  document.getElementById('line-items-count').textContent = tbody.children.length;
  autoUpdateSubtotalFromRows();
}

function updateLineMath(input) {
  const row = input.closest('tr');
  const qty = parseFloat(row.querySelector('.item-qty').value) || 0;
  const price = parseFloat(row.querySelector('.item-price').value) || 0;
  const amtInput = row.querySelector('.item-amount');
  
  const calculated = Math.round(qty * price * 100) / 100;
  amtInput.value = calculated.toFixed(2);
  amtInput.classList.remove('error');
  autoUpdateSubtotalFromRows();
}

function autoUpdateSubtotalFromRows() {
  const tbody = document.getElementById('line-items-body');
  let sum = 0;
  tbody.querySelectorAll('.item-amount').forEach(inp => {
    sum += parseFloat(inp.value) || 0;
  });
  document.getElementById('edit-subtotal').value = (Math.round(sum * 100) / 100).toFixed(2);
  autoUpdateGrandTotal();
}

function autoUpdateGrandTotal() {
  const subtotal = parseFloat(document.getElementById('edit-subtotal').value) || 0;
  const tax = parseFloat(document.getElementById('edit-tax').value) || 0;
  const shipping = parseFloat(document.getElementById('edit-shipping').value) || 0;
  const discount = parseFloat(document.getElementById('edit-discount').value) || 0;

  const grandTotal = Math.round((subtotal + tax + shipping - discount) * 100) / 100;
  document.getElementById('edit-total').value = grandTotal.toFixed(2);
}

function recalculateTotalsFromLines() {
  autoUpdateSubtotalFromRows();
  showToast('Recalculated line items and totals.', 'info');
}

async function saveInvoiceChanges(isApproved = true, isReject = false) {
  if (!currentInvoice) return;

  // Gather line items
  const lineItems = [];
  const tbody = document.getElementById('line-items-body');
  tbody.querySelectorAll('tr').forEach(tr => {
    const desc = tr.querySelector('.item-desc').value.trim();
    const qty = parseFloat(tr.querySelector('.item-qty').value) || 1;
    const price = parseFloat(tr.querySelector('.item-price').value) || 0;
    const amt = parseFloat(tr.querySelector('.item-amount').value) || 0;
    lineItems.push({
      description: desc || 'Item',
      quantity: qty,
      unit_price: price,
      amount: amt
    });
  });

  const payload = {
    vendor_name: document.getElementById('edit-vendor').value.trim(),
    invoice_number: document.getElementById('edit-invoice-num').value.trim(),
    invoice_date: document.getElementById('edit-date').value || null,
    due_date: document.getElementById('edit-due-date').value || null,
    po_number: document.getElementById('edit-po').value.trim() || null,
    subtotal: parseFloat(document.getElementById('edit-subtotal').value) || 0,
    tax_amount: parseFloat(document.getElementById('edit-tax').value) || 0,
    shipping_amount: parseFloat(document.getElementById('edit-shipping').value) || 0,
    discount_amount: parseFloat(document.getElementById('edit-discount').value) || 0,
    total_amount: parseFloat(document.getElementById('edit-total').value) || 0,
    line_items: lineItems,
    reviewer_notes: document.getElementById('edit-notes').value.trim(),
    status: isReject ? 'REJECTED' : (isApproved ? 'APPROVED' : null)
  };

  try {
    const res = await fetch(`/api/invoices/${currentInvoice.id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (res.ok) {
      showToast(result.message, 'success');
      currentInvoice = result.record;
      populateReviewerUI(currentInvoice);
      fetchStats();
      fetchInvoices();
    } else {
      showToast(`Save error: ${result.detail}`, 'error');
    }
  } catch (err) {
    showToast('Failed to save review changes', 'error');
  }
}

async function reprocessCurrentInvoice() {
  if (!currentInvoice) return;
  showToast('Re-running extraction pipeline...', 'info');
  try {
    const res = await fetch(`/api/invoices/${currentInvoice.id}/reprocess`, { method: 'POST' });
    const result = await res.json();
    if (res.ok) {
      showToast('Document reprocessed successfully', 'success');
      currentInvoice = result.record;
      populateReviewerUI(currentInvoice);
      fetchStats();
      fetchInvoices();
    } else {
      showToast('Reprocessing error', 'error');
    }
  } catch (err) {
    showToast('Reprocess request failed', 'error');
  }
}

async function deleteInvoicePrompt(id) {
  if (!confirm('Are you sure you want to permanently delete this invoice?')) return;
  try {
    const res = await fetch(`/api/invoices/${id}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Invoice deleted', 'info');
      fetchStats();
      fetchInvoices();
      if (currentInvoice && currentInvoice.id === id) {
        document.getElementById('reviewer-split-container').style.display = 'none';
        document.getElementById('reviewer-empty-state').style.display = 'block';
      }
    }
  } catch (err) {
    showToast('Delete failed', 'error');
  }
}

// Watcher Hub Logic
function initWatcherHub() {
  document.getElementById('btn-toggle-watcher').addEventListener('click', toggleWatcher);
  document.getElementById('btn-simulate-email-drop').addEventListener('click', simulateEmailDrop);
}

async function fetchWatcherStatus() {
  try {
    const res = await fetch('/api/watcher/status');
    if (!res.ok) return;
    const data = await res.json();
    
    document.getElementById('watcher-dir-path').textContent = data.watched_directory;
    const badge = document.getElementById('watcher-status-indicator');
    const toggleBtn = document.getElementById('btn-toggle-watcher');

    if (data.is_active) {
      badge.className = 'status-badge badge-approved';
      badge.innerHTML = '<i data-lucide="circle" style="width: 10px; height: 10px; fill: currentColor;"></i> ACTIVE';
      toggleBtn.textContent = 'Pause Watcher';
    } else {
      badge.className = 'status-badge badge-rejected';
      badge.innerHTML = '<i data-lucide="circle" style="width: 10px; height: 10px; fill: currentColor;"></i> PAUSED';
      toggleBtn.textContent = 'Start Watcher';
    }
    lucide.createIcons();
  } catch (err) {
    console.error('Watcher status error:', err);
  }
}

async function toggleWatcher() {
  const isCurrentlyActive = document.getElementById('watcher-status-indicator').classList.contains('badge-approved');
  const endpoint = isCurrentlyActive ? '/api/watcher/stop' : '/api/watcher/start';

  try {
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();
    showToast(data.message, 'info');
    fetchWatcherStatus();
  } catch (err) {
    showToast('Error changing watcher status', 'error');
  }
}

async function simulateEmailDrop() {
  showToast('Simulating incoming email attachment drop...', 'info');
  try {
    const res = await fetch('/api/inbox/simulate-drop', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(`Inbound Invoice Received: ${data.inbox_file}`, 'success');
      appendTerminalLog(`[INBOUND EVENT] Simulated Email Attachment arrived: ${data.inbox_file}`);
      setTimeout(() => {
        fetchStats();
        fetchInvoices();
      }, 1500);
    }
  } catch (err) {
    showToast('Simulation failed', 'error');
  }
}

function appendTerminalLog(msg) {
  const term = document.getElementById('watcher-terminal');
  const timeStr = new Date().toLocaleTimeString();
  term.innerHTML += `<br/>[${timeStr}] ${escapeHtml(msg)}`;
  term.scrollTop = term.scrollHeight;
}

// Settings Modal
function initSettings() {
  const modal = document.getElementById('modal-settings');
  document.getElementById('btn-open-settings').addEventListener('click', openSettingsModal);
  document.getElementById('btn-close-settings').addEventListener('click', () => modal.classList.remove('active'));
  document.getElementById('btn-cancel-settings').addEventListener('click', () => modal.classList.remove('active'));

  document.getElementById('settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      llm_provider: document.getElementById('setting-provider').value,
      gemini_api_key: document.getElementById('setting-gemini-key').value,
      openai_api_key: document.getElementById('setting-openai-key').value,
      high_value_threshold: parseFloat(document.getElementById('setting-high-value').value) || 5000,
      webhook_alert_url: document.getElementById('setting-webhook-url').value
    };

    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        showToast('Settings successfully updated', 'success');
        modal.classList.remove('active');
      }
    } catch (err) {
      showToast('Error saving settings', 'error');
    }
  });
}

async function openSettingsModal() {
  try {
    const res = await fetch('/api/settings');
    if (res.ok) {
      const s = await res.json();
      document.getElementById('setting-provider').value = s.llm_provider || 'heuristic';
      document.getElementById('setting-gemini-key').value = s.gemini_api_key || '';
      document.getElementById('setting-openai-key').value = s.openai_api_key || '';
      document.getElementById('setting-high-value').value = s.high_value_threshold || 5000;
      document.getElementById('setting-webhook-url').value = s.webhook_alert_url || '';
    }
    document.getElementById('modal-settings').classList.add('active');
  } catch (err) {
    showToast('Failed to load settings', 'error');
  }
}

// Helper Utilities
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  try {
    const dt = new Date(isoStr);
    return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}

function debounce(func, delay) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}
