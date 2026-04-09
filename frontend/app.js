/**
 * app.js — Store Grading Tool Frontend Logic
 *
 * Handles:
 *  - API communication with Flask backend
 *  - Cascading filter population
 *  - Store grade search & pagination
 *  - Grade generation trigger with progress feedback
 *  - Table sorting & CSV export
 */

'use strict';

// ═══════════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════════

const API_BASE = '';  // Same origin — served by Flask

// ═══════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════

const state = {
  gradingLevel: 'class',      // 'class' | 'subclass'
  filters: {
    dept:     null,
    class:    null,
    subclass: null,
    country:  null,
    store:    null,
  },
  page:       1,
  pageSize:   50,
  totalRows:  0,
  tableData:  [],
  sortCol:    null,
  sortDir:    'asc',
  selectedClusters: 3,
  isGenerating: false,
};

// ═══════════════════════════════════════════════════════════════════
// DOM REFS
// ═══════════════════════════════════════════════════════════════════

const $ = id => document.getElementById(id);

const els = {
  statusDot:       $('status-dot'),
  statusText:      $('status-text'),
  levelClass:      $('level-class'),
  levelSubclass:   $('level-subclass'),
  deptSelect:      $('dept-select'),
  classSelect:     $('class-select'),
  subclassSelect:  $('subclass-select'),
  countrySelect:   $('country-select'),
  storeSelect:     $('store-select'),
  btnSearch:       $('btn-search'),
  btnGenerate:     $('btn-generate'),
  btnReset:        $('btn-reset'),
  progressBanner:  $('progress-banner'),
  progressBar:     $('progress-bar'),
  progressTitle:   $('progress-title'),
  progressSub:     $('progress-sub'),
  emptyState:      $('empty-state'),
  dataTable:       $('data-table'),
  tableBody:       $('table-body'),
  gridCountLabel:  $('grid-count-label'),
  btnExport:       $('btn-export'),
  btnPrev:         $('btn-prev'),
  btnNext:         $('btn-next'),
  pageInfo:        $('page-info'),
  confirmModal:    $('confirm-modal'),
  modalScope:      $('modal-scope'),
  modalCancel:     $('modal-cancel'),
  modalConfirm:    $('modal-confirm'),
  toastContainer:  $('toast-container'),
  statGrade1:      $('stat-grade1'),
  statGrade2:      $('stat-grade2'),
  statGrade3:      $('stat-grade3'),
  statTotal:       $('stat-total'),
};

// ═══════════════════════════════════════════════════════════════════
// API LAYER
// ═══════════════════════════════════════════════════════════════════

async function apiFetch(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

// ═══════════════════════════════════════════════════════════════════
// STATUS / HEALTH
// ═══════════════════════════════════════════════════════════════════

async function checkHealth() {
  try {
    await apiFetch('/api/health');
    els.statusDot.className = 'status-dot online';
    els.statusText.textContent = 'API Connected';
  } catch {
    els.statusDot.className = 'status-dot error';
    els.statusText.textContent = 'API Offline';
    showToast('error', 'Connection Failed', 'Cannot reach the backend API. Make sure Flask is running.');
  }
}

// ═══════════════════════════════════════════════════════════════════
// FILTER INITIALISATION
// ═══════════════════════════════════════════════════════════════════

let allFilters = { depts: [], classes: [], subclasses: [], stores: [], countries: [] };

async function loadFilters() {
  try {
    allFilters = await apiFetch('/api/filters');
    populateDepts();
    populateCountries();
    populateStores();
  } catch (e) {
    showToast('error', 'Filter Load Failed', e.message);
  }
}

function populateDepts() {
  const sel = els.deptSelect;
  sel.innerHTML = '<option value="">Select Department...</option>';
  allFilters.depts.forEach(d => {
    const label = d.DEPT_NAME ? `${d.DEPT} — ${d.DEPT_NAME}` : `${d.DEPT}`;
    sel.appendChild(new Option(label, d.DEPT));
  });
}

function populateClasses(dept) {
  const sel = els.classSelect;
  sel.innerHTML = '<option value="">Select Class...</option>';
  sel.disabled = true;
  const filtered = allFilters.classes.filter(c => c.DEPT == dept);
  filtered.forEach(c => {
    const label = c.CLASS_NAME ? `${c.CLASS} — ${c.CLASS_NAME}` : `${c.CLASS}`;
    sel.appendChild(new Option(label, c.CLASS));
  });
  sel.disabled = filtered.length === 0;
}

function populateSubclasses(dept, cls) {
  const sel = els.subclassSelect;
  sel.innerHTML = '<option value="">All Subclasses</option>';
  sel.disabled = true;
  const filtered = allFilters.subclasses.filter(s => s.DEPT == dept && s.CLASS == cls);
  filtered.forEach(s => {
    const label = s.SUB_NAME ? `${s.SUBCLASS} — ${s.SUB_NAME}` : `${s.SUBCLASS}`;
    sel.appendChild(new Option(label, s.SUBCLASS));
  });
  sel.disabled = filtered.length === 0;
}

function populateCountries() {
  const sel = els.countrySelect;
  sel.innerHTML = '<option value="">All Countries</option>';
  allFilters.countries.forEach(c => {
    sel.appendChild(new Option(c.AREA_NAME, c.AREA_NAME));
  });
}

function populateStores() {
  const sel = els.storeSelect;
  sel.innerHTML = '<option value="">All Stores</option>';
  allFilters.stores.forEach(s => {
    const label = s.STORE_NAME || `${s.STORE}`;
    sel.appendChild(new Option(label, s.STORE));
  });
}

// ═══════════════════════════════════════════════════════════════════
// FILTER EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════════

els.deptSelect.addEventListener('change', () => {
  state.filters.dept = els.deptSelect.value || null;
  state.filters.class = null;
  state.filters.subclass = null;
  populateClasses(state.filters.dept || '');
  els.subclassSelect.innerHTML = '<option value="">All Subclasses</option>';
  els.subclassSelect.disabled = true;
  updateSearchButtonState();
});

els.classSelect.addEventListener('change', () => {
  state.filters.class = els.classSelect.value || null;
  state.filters.subclass = null;
  populateSubclasses(state.filters.dept || '', state.filters.class || '');
  updateSearchButtonState();
});

els.subclassSelect.addEventListener('change', () => {
  state.filters.subclass = els.subclassSelect.value || null;
});

els.countrySelect.addEventListener('change', () => {
  state.filters.country = els.countrySelect.value || null;
});

els.storeSelect.addEventListener('change', () => {
  state.filters.store = els.storeSelect.value || null;
});

function updateSearchButtonState() {
  const valid = !!state.filters.dept && !!state.filters.class;
  els.btnSearch.disabled  = !valid;
  els.btnGenerate.disabled = !valid;
}

// ═══════════════════════════════════════════════════════════════════
// LEVEL TOGGLE
// ═══════════════════════════════════════════════════════════════════

[els.levelClass, els.levelSubclass].forEach(btn => {
  btn.addEventListener('click', () => {
    state.gradingLevel = btn.dataset.level;
    els.levelClass.classList.toggle('active',    state.gradingLevel === 'class');
    els.levelSubclass.classList.toggle('active', state.gradingLevel === 'subclass');
    els.levelClass.setAttribute('aria-pressed',    String(state.gradingLevel === 'class'));
    els.levelSubclass.setAttribute('aria-pressed', String(state.gradingLevel === 'subclass'));
  });
});

// ═══════════════════════════════════════════════════════════════════
// SEARCH
// ═══════════════════════════════════════════════════════════════════

els.btnSearch.addEventListener('click', () => {
  state.page = 1;
  fetchGrades();
});

async function fetchGrades() {
  if (!state.filters.dept || !state.filters.class) return;

  const params = new URLSearchParams({
    dept:      state.filters.dept,
    class:     state.filters.class,
    page:      state.page,
    page_size: state.pageSize,
  });
  if (state.filters.subclass) params.set('subclass', state.filters.subclass);
  if (state.filters.country)  params.set('country',  state.filters.country);
  if (state.filters.store)    params.set('store',    state.filters.store);

  setTableLoading(true);
  try {
    const data = await apiFetch(`/api/store-grades?${params}`);
    state.totalRows = data.total;
    state.tableData = data.data;
    renderTable();
    renderPagination();
    renderStats();
    els.btnExport.disabled = data.data.length === 0;
  } catch (e) {
    showToast('error', 'Search Failed', e.message);
  } finally {
    setTableLoading(false);
  }
}

function setTableLoading(loading) {
  if (loading) {
    els.gridCountLabel.textContent = 'Loading...';
    els.btnSearch.disabled = true;
  } else {
    els.btnSearch.disabled = !(state.filters.dept && state.filters.class);
  }
}

// ═══════════════════════════════════════════════════════════════════
// TABLE RENDER
// ═══════════════════════════════════════════════════════════════════

function renderTable() {
  const data = getSortedData();

  if (data.length === 0) {
    els.emptyState.classList.remove('hidden');
    els.dataTable.classList.add('hidden');
    els.gridCountLabel.textContent  = 'No results found';
    return;
  }

  els.emptyState.classList.add('hidden');
  els.dataTable.classList.remove('hidden');

  const total   = state.totalRows;
  const start   = (state.page - 1) * state.pageSize + 1;
  const end     = Math.min(start + data.length - 1, total);
  els.gridCountLabel.textContent = `Showing ${start}–${end} of ${total} store grades`;

  els.tableBody.innerHTML = data.map(row => `
    <tr>
      <td class="mono">${row.STORE_GRADE_ID ?? '—'}</td>
      <td><strong>${esc(row.BRAND || '—')}</strong></td>
      <td class="mono">${row.LOCATION ?? '—'}</td>
      <td>${esc(row.STORE_NAME || '')}<span class="text-dim">${!row.STORE_NAME ? '—' : ''}</span></td>
      <td>${esc(row.COUNTRY || '—')}</td>
      <td class="mono">${row.DEPT ?? '—'}${row.DEPT_NAME ? `<br><span style="font-size:0.7rem;color:var(--text-muted)">${esc(row.DEPT_NAME)}</span>` : ''}</td>
      <td class="mono">${row.CLASS ?? '—'}${row.CLASS_NAME ? `<br><span style="font-size:0.7rem;color:var(--text-muted)">${esc(row.CLASS_NAME)}</span>` : ''}</td>
      <td class="mono">${row.SUBCLASS != null ? row.SUBCLASS : '<span class="text-dim">—</span>'}${row.SUB_NAME ? `<br><span style="font-size:0.7rem;color:var(--text-muted)">${esc(row.SUB_NAME)}</span>` : ''}</td>
      <td>${gradeBadge(row.GRADE)}</td>
      <td class="mono" style="font-size:0.72rem">${esc(row.CREATE_DATETIME ? row.CREATE_DATETIME.split(' ')[0] : '—')}</td>
      <td class="mono" style="font-size:0.72rem">${esc(row.LAST_UPDATE_DATETIME ? row.LAST_UPDATE_DATETIME.split(' ')[0] : '—')}</td>
    </tr>
  `).join('');
}

function esc(str) {
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function gradeBadge(grade) {
  if (!grade && grade !== 0) return `<span class="grade-badge gx">—</span>`;
  const g = String(grade);
  const cls = g === '1' ? 'g1' : g === '2' ? 'g2' : g === '3' ? 'g3' : 'gx';
  return `<span class="grade-badge ${cls}">${esc(g)}</span>`;
}

// ─── Sorting ─────────────────────────────────────────────────────

function getSortedData() {
  if (!state.sortCol) return state.tableData;
  return [...state.tableData].sort((a, b) => {
    let av = a[state.sortCol], bv = b[state.sortCol];
    if (av == null) av = '';
    if (bv == null) bv = '';
    const cmp = typeof av === 'number' && typeof bv === 'number'
      ? av - bv
      : String(av).localeCompare(String(bv));
    return state.sortDir === 'asc' ? cmp : -cmp;
  });
}

document.querySelectorAll('.data-table th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.sort;
    if (state.sortCol === col) {
      state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortCol = col;
      state.sortDir = 'asc';
    }
    document.querySelectorAll('.data-table th').forEach(h => {
      h.classList.remove('sort-asc', 'sort-desc');
      h.removeAttribute('aria-sort');
    });
    th.classList.add(state.sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
    th.setAttribute('aria-sort', state.sortDir === 'asc' ? 'ascending' : 'descending');
    renderTable();
  });
});

// ─── Stats ───────────────────────────────────────────────────────

function renderStats() {
  const data = state.tableData;
  const g = grade => data.filter(r => String(r.GRADE) === grade).length;
  els.statGrade1.textContent = g('1');
  els.statGrade2.textContent = g('2');
  els.statGrade3.textContent = g('3');
  els.statTotal.textContent  = state.totalRows;
}

// ─── Pagination ───────────────────────────────────────────────────

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(state.totalRows / state.pageSize));
  els.pageInfo.textContent = `Page ${state.page} of ${totalPages}`;
  els.btnPrev.disabled = state.page <= 1;
  els.btnNext.disabled = state.page >= totalPages;
}

els.btnPrev.addEventListener('click', () => {
  if (state.page > 1) { state.page--; fetchGrades(); }
});

els.btnNext.addEventListener('click', () => {
  const totalPages = Math.ceil(state.totalRows / state.pageSize);
  if (state.page < totalPages) { state.page++; fetchGrades(); }
});

// ═══════════════════════════════════════════════════════════════════
// RESET
// ═══════════════════════════════════════════════════════════════════

els.btnReset.addEventListener('click', () => {
  els.deptSelect.value     = '';
  els.classSelect.value    = '';
  els.subclassSelect.value = '';
  els.countrySelect.value  = '';
  els.storeSelect.value    = '';
  els.classSelect.disabled    = true;
  els.subclassSelect.disabled = true;
  Object.assign(state.filters, { dept: null, class: null, subclass: null, country: null, store: null });
  state.tableData = [];
  state.totalRows = 0;
  state.page      = 1;
  state.sortCol   = null;
  els.btnSearch.disabled   = true;
  els.btnGenerate.disabled = true;
  els.btnExport.disabled   = true;
  els.emptyState.classList.remove('hidden');
  els.dataTable.classList.add('hidden');
  els.gridCountLabel.textContent = 'Select filters and search to load data';
  els.statGrade1.textContent = '—';
  els.statGrade2.textContent = '—';
  els.statGrade3.textContent = '—';
  els.statTotal.textContent  = '—';
  renderPagination();
});

// ═══════════════════════════════════════════════════════════════════
// GENERATE GRADES MODAL
// ═══════════════════════════════════════════════════════════════════

els.btnGenerate.addEventListener('click', () => openGenerateModal());

function openGenerateModal() {
  // Build scope display
  const dept    = els.deptSelect    .options[els.deptSelect.selectedIndex]?.text    || state.filters.dept;
  const cls     = els.classSelect   .options[els.classSelect.selectedIndex]?.text   || state.filters.class;
  const sub     = els.subclassSelect.value
    ? (els.subclassSelect.options[els.subclassSelect.selectedIndex]?.text || state.filters.subclass)
    : null;
  const country = state.filters.country || 'All Countries';
  const store   = state.filters.store
    ? (els.storeSelect.options[els.storeSelect.selectedIndex]?.text || state.filters.store)
    : 'All Stores';
  const levelLabel = state.gradingLevel === 'class' ? 'Class Level (Subclass = NULL)' : 'Subclass Level';

  els.modalScope.innerHTML = `
    <div class="scope-row"><span class="scope-key">Level</span>  <span class="scope-value">${esc(levelLabel)}</span></div>
    <div class="scope-row"><span class="scope-key">Dept</span>   <span class="scope-value">${esc(dept)}</span></div>
    <div class="scope-row"><span class="scope-key">Class</span>  <span class="scope-value">${esc(cls)}</span></div>
    ${sub ? `<div class="scope-row"><span class="scope-key">Subclass</span><span class="scope-value">${esc(sub)}</span></div>` : ''}
    <div class="scope-row"><span class="scope-key">Country</span><span class="scope-value">${esc(country)}</span></div>
    <div class="scope-row"><span class="scope-key">Store</span>  <span class="scope-value">${esc(store)}</span></div>
  `;

  els.confirmModal.classList.remove('hidden');
}

// Cluster selector in modal
document.querySelectorAll('.cluster-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.cluster-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.selectedClusters = parseInt(btn.dataset.clusters, 10);
  });
});

els.modalCancel.addEventListener('click', () => els.confirmModal.classList.add('hidden'));

els.confirmModal.addEventListener('click', e => {
  if (e.target === els.confirmModal) els.confirmModal.classList.add('hidden');
});

els.modalConfirm.addEventListener('click', async () => {
  els.confirmModal.classList.add('hidden');
  await runGrading();
});

// Keyboard close
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') els.confirmModal.classList.add('hidden');
});

// ═══════════════════════════════════════════════════════════════════
// RUN GRADING
// ═══════════════════════════════════════════════════════════════════

async function runGrading() {
  if (state.isGenerating) return;
  state.isGenerating = true;

  showProgress(true, 'Running K-means Clustering...', 'Preparing data and running grading algorithm');
  animateProgressBar(0, 30, 1000);

  try {
    const payload = {
      dept:     parseInt(state.filters.dept, 10),
      class:    parseInt(state.filters.class, 10),
      level:    state.gradingLevel,
      clusters: state.selectedClusters,
    };
    if (state.filters.subclass) payload.subclass = parseInt(state.filters.subclass, 10);
    if (state.filters.country)  payload.country  = state.filters.country;
    if (state.filters.store)    payload.store     = parseInt(state.filters.store, 10);

    animateProgressBar(30, 80, 4000);
    updateProgress('Computing store grades...', 'K-means clustering in progress');

    const result = await apiFetch('/api/generate-grades', {
      method:  'POST',
      body:    JSON.stringify(payload),
    });

    animateProgressBar(80, 100, 500);
    await sleep(600);

    showProgress(false);
    showToast(
      'success',
      'Grading Complete!',
      `${result.inserts} new grades inserted, ${result.updates} updated. ${result.rows_processed} stores processed.`
    );

    // Auto-refresh the grid
    await fetchGrades();

  } catch (e) {
    showProgress(false);
    showToast('error', 'Grading Failed', e.message);
  } finally {
    state.isGenerating = false;
  }
}

function showProgress(show, title = '', sub = '') {
  if (show) {
    els.progressTitle.textContent = title;
    els.progressSub.textContent   = sub;
    els.progressBanner.classList.remove('hidden');
    els.progressBar.style.width = '0%';
    els.btnGenerate.disabled = true;
  } else {
    els.progressBanner.classList.add('hidden');
    updateSearchButtonState();
  }
}

function updateProgress(title, sub) {
  els.progressTitle.textContent = title;
  els.progressSub.textContent   = sub;
}

function animateProgressBar(from, to, duration) {
  const start = Date.now();
  const step = () => {
    const pct = Math.min(1, (Date.now() - start) / duration);
    els.progressBar.style.width = `${from + (to - from) * pct}%`;
    if (pct < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ═══════════════════════════════════════════════════════════════════
// EXPORT CSV
// ═══════════════════════════════════════════════════════════════════

els.btnExport.addEventListener('click', () => {
  if (!state.tableData.length) return;

  const headers = ['STORE_GRADE_ID','BRAND','LOCATION','STORE_NAME','COUNTRY',
                    'DEPT','DEPT_NAME','CLASS','CLASS_NAME','SUBCLASS','SUB_NAME',
                    'GRADE','CREATE_DATETIME','CREATE_ID','LAST_UPDATE_DATETIME','LAST_UPDATE_ID'];

  const rows = state.tableData.map(r =>
    headers.map(h => {
      const v = r[h] ?? '';
      return `"${String(v).replace(/"/g, '""')}"`;
    }).join(',')
  );

  const csv = [headers.join(','), ...rows].join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');

  const ts = new Date().toISOString().slice(0,10);
  a.href     = url;
  a.download = `store_grades_dept${state.filters.dept}_class${state.filters.class}_${ts}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('success', 'Export successful', `${state.tableData.length} rows exported to CSV`);
});

// ═══════════════════════════════════════════════════════════════════
// TOAST SYSTEM
// ═══════════════════════════════════════════════════════════════════

const ICONS = {
  success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="9,12 12,15 17,9"/></svg>`,
  error:   `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  info:    `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  warning: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
};

function showToast(type, title, message, duration = 5000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    ${ICONS[type] || ICONS.info}
    <div class="toast-content">
      <strong>${esc(title)}</strong>
      <span>${esc(message)}</span>
    </div>
  `;
  els.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('leaving');
    setTimeout(() => toast.remove(), 350);
  }, duration);
}

// ═══════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════

async function init() {
  await checkHealth();
  await loadFilters();
}

init();
