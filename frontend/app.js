/**
 * app.js — Retail Analytics Suite
 *
 * Pages:
 *  - Store Grading (K-means)
 *  - Product Master (browse product_option_dim)
 *  - Sales History  (aggregated sales by hierarchy level + type)
 */

'use strict';

const API_BASE = '';

// ═══════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════

const $ = id => document.getElementById(id);

function esc(str) {
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmt(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString();
}

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
// TOAST
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
  toast.innerHTML = `${ICONS[type] || ICONS.info}
    <div class="toast-content">
      <strong>${esc(title)}</strong>
      <span>${esc(message)}</span>
    </div>`;
  $('toast-container').appendChild(toast);
  setTimeout(() => {
    toast.classList.add('leaving');
    setTimeout(() => toast.remove(), 350);
  }, duration);
}

// ═══════════════════════════════════════════════════════════════════
// HEALTH
// ═══════════════════════════════════════════════════════════════════

async function checkHealth() {
  try {
    await apiFetch('/api/health');
    $('status-dot').className = 'status-dot online';
    $('status-text').textContent = 'API Connected';
  } catch {
    $('status-dot').className = 'status-dot error';
    $('status-text').textContent = 'API Offline';
    showToast('error', 'Connection Failed', 'Cannot reach the backend API.');
  }
}

// ═══════════════════════════════════════════════════════════════════
// SIDEBAR NAVIGATION
// ═══════════════════════════════════════════════════════════════════

const sidebar   = $('sidebar');
const sidebarToggle = $('sidebar-toggle');
let sidebarCollapsed = false;

sidebarToggle.addEventListener('click', () => {
  sidebarCollapsed = !sidebarCollapsed;
  sidebar.classList.toggle('collapsed', sidebarCollapsed);
});

function navigateTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(n => {
    n.classList.remove('active');
    n.removeAttribute('aria-current');
  });

  const page = $(pageId);
  if (page) page.classList.remove('hidden');

  const navId = 'nav-' + pageId.replace('page-', '');
  const navEl = $(navId);
  if (navEl) {
    navEl.classList.add('active');
    navEl.setAttribute('aria-current', 'page');
  }
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigateTo(btn.dataset.page));
});

// ═══════════════════════════════════════════════════════════════════
// SHARED FILTER DATA (loaded once)
// ═══════════════════════════════════════════════════════════════════

let allFilters = { depts: [], classes: [], subclasses: [], stores: [], countries: [] };

async function loadFilters() {
  try {
    allFilters = await apiFetch('/api/filters');
    populateSharedFilters();
  } catch (e) {
    showToast('error', 'Filter Load Failed', e.message);
  }
}

function populateSharedFilters() {
  // ── Location Master selects ────────────────────────────────────
  const locCountrySel = $('loc-country-select');
  locCountrySel.innerHTML = '<option value="">All Countries</option>';
  allFilters.countries.forEach(c => {
    locCountrySel.appendChild(new Option(c.AREA_NAME, c.AREA_NAME));
  });

  const locTypeSel = $('loc-type-select');
  locTypeSel.innerHTML = '<option value="">All Types</option>';
  (allFilters.types || []).forEach(t => {
    locTypeSel.appendChild(new Option(t, t));
  });

  // ── Store Grading selects ──────────────────────────────────────
  const deptSel = $('dept-select');
  deptSel.innerHTML = '<option value="">Select Department...</option>';
  allFilters.depts.forEach(d => {
    deptSel.appendChild(new Option(d.DEPT_NAME ? `${d.DEPT} — ${d.DEPT_NAME}` : `${d.DEPT}`, d.DEPT));
  });

  const countrySel = $('country-select');
  countrySel.innerHTML = '<option value="">All Countries</option>';
  allFilters.countries.forEach(c => countrySel.appendChild(new Option(c.AREA_NAME, c.AREA_NAME)));

  const storeSel = $('store-select');
  storeSel.innerHTML = '<option value="">All Stores</option>';
  allFilters.stores.forEach(s => storeSel.appendChild(new Option(s.STORE_NAME || s.STORE, s.STORE)));

  // ── Product Master selects ─────────────────────────────────────
  const pmDeptSel = $('pm-dept-select');
  pmDeptSel.innerHTML = '<option value="">All Departments</option>';
  allFilters.depts.forEach(d => {
    pmDeptSel.appendChild(new Option(d.DEPT_NAME ? `${d.DEPT} — ${d.DEPT_NAME}` : `${d.DEPT}`, d.DEPT));
  });

  // ── Sales History selects ──────────────────────────────────────
  const shDeptSel = $('sh-dept-select');
  shDeptSel.innerHTML = '<option value="">All Departments</option>';
  allFilters.depts.forEach(d => {
    shDeptSel.appendChild(new Option(d.DEPT_NAME ? `${d.DEPT} — ${d.DEPT_NAME}` : `${d.DEPT}`, d.DEPT));
  });

  const shCountrySel = $('sh-country-select');
  shCountrySel.innerHTML = '<option value="">All Countries</option>';
  allFilters.countries.forEach(c => shCountrySel.appendChild(new Option(c.AREA_NAME, c.AREA_NAME)));

  const shStoreSel = $('sh-store-select');
  shStoreSel.innerHTML = '<option value="">All Stores</option>';
  allFilters.stores.forEach(s => shStoreSel.appendChild(new Option(s.STORE_NAME || s.STORE, s.STORE)));

  // Load brands for Product Master
  loadPmBrands();
}

async function loadPmBrands() {
  try {
    const data = await apiFetch('/api/product-master?page=1&page_size=1');
    const brandSel = $('pm-brand-select');
    brandSel.innerHTML = '<option value="">All Brands</option>';
    (data.brands || []).forEach(b => brandSel.appendChild(new Option(b, b)));
  } catch {}
}

// ═══════════════════════════════════════════════════════════════════
// ══════════════ PAGE 1: STORE GRADING ═══════════════════════════
// ═══════════════════════════════════════════════════════════════════

const sgState = {
  gradingLevel: 'class',
  filters: { dept: null, class: null, subclass: null, country: null, store: null },
  page: 1, pageSize: 50, totalRows: 0,
  tableData: [], sortCol: null, sortDir: 'asc',
  gradeCounts: {}, selectedClusters: 3, isGenerating: false,
};

// ── Cascading Class Filter ────────────────────────────────────────
function populateSgClasses(dept) {
  const sel = $('class-select');
  sel.innerHTML = '<option value="">Select Class...</option>';
  sel.disabled = true;
  const filtered = allFilters.classes.filter(c => c.DEPT == dept);
  filtered.forEach(c => sel.appendChild(new Option(c.CLASS_NAME ? `${c.CLASS} — ${c.CLASS_NAME}` : `${c.CLASS}`, c.CLASS)));
  sel.disabled = filtered.length === 0;
}

function populateSgSubclasses(dept, cls) {
  const sel = $('subclass-select');
  sel.innerHTML = '<option value="">All Subclasses</option>';
  const filtered = allFilters.subclasses.filter(s => s.DEPT == dept && s.CLASS == cls);
  filtered.forEach(s => sel.appendChild(new Option(s.SUB_NAME ? `${s.SUBCLASS} — ${s.SUB_NAME}` : `${s.SUBCLASS}`, s.SUBCLASS)));
  sel.disabled = (filtered.length === 0) || (sgState.gradingLevel === 'class');
}

$('dept-select').addEventListener('change', () => {
  sgState.filters.dept = $('dept-select').value || null;
  sgState.filters.class = null;
  sgState.filters.subclass = null;
  populateSgClasses(sgState.filters.dept || '');
  $('subclass-select').innerHTML = '<option value="">All Subclasses</option>';
  $('subclass-select').disabled = true;
  updateSgButtons();
});

$('class-select').addEventListener('change', () => {
  sgState.filters.class = $('class-select').value || null;
  sgState.filters.subclass = null;
  populateSgSubclasses(sgState.filters.dept || '', sgState.filters.class || '');
  updateSgButtons();
});

$('subclass-select').addEventListener('change',  () => { sgState.filters.subclass = $('subclass-select').value || null; });
$('country-select').addEventListener('change',   () => { sgState.filters.country  = $('country-select').value || null; });
$('store-select').addEventListener('change',     () => { sgState.filters.store    = $('store-select').value || null; });

function updateSgButtons() {
  const ok = !!(sgState.filters.dept && sgState.filters.class);
  $('btn-search').disabled   = !ok;
  $('btn-generate').disabled = !ok;
}

// ── Level Toggle ──────────────────────────────────────────────────
[$('level-class'), $('level-subclass')].forEach(btn => {
  btn.addEventListener('click', () => {
    sgState.gradingLevel = btn.dataset.level;
    $('level-class').classList.toggle('active',    sgState.gradingLevel === 'class');
    $('level-subclass').classList.toggle('active', sgState.gradingLevel === 'subclass');
    $('level-class').setAttribute('aria-pressed',    String(sgState.gradingLevel === 'class'));
    $('level-subclass').setAttribute('aria-pressed', String(sgState.gradingLevel === 'subclass'));
    if (sgState.gradingLevel === 'class') {
      $('subclass-select').value = '';
      sgState.filters.subclass = null;
      $('subclass-select').disabled = true;
    } else {
      $('subclass-select').disabled = !sgState.filters.class;
    }
    if (sgState.filters.dept && sgState.filters.class) { sgState.page = 1; fetchSgGrades(); }
  });
});

// ── Search & Fetch ────────────────────────────────────────────────
$('btn-search').addEventListener('click', () => { sgState.page = 1; fetchSgGrades(); });

async function fetchSgGrades() {
  if (!sgState.filters.dept || !sgState.filters.class) return;
  const params = new URLSearchParams({ dept: sgState.filters.dept, class: sgState.filters.class, level: sgState.gradingLevel, page: sgState.page, page_size: sgState.pageSize });
  if (sgState.filters.subclass) params.set('subclass', sgState.filters.subclass);
  if (sgState.filters.country)  params.set('country',  sgState.filters.country);
  if (sgState.filters.store)    params.set('store',    sgState.filters.store);
  $('grid-count-label').textContent = 'Loading...';
  $('btn-search').disabled = true;
  try {
    const data = await apiFetch(`/api/store-grades?${params}`);
    sgState.totalRows   = data.total;
    sgState.gradeCounts = data.grade_counts || {};
    sgState.tableData   = data.data;
    renderSgTable(); renderSgPagination(); renderSgStats();
    $('btn-export').disabled = data.data.length === 0;
  } catch (e) { showToast('error', 'Search Failed', e.message); }
  finally { $('btn-search').disabled = !(sgState.filters.dept && sgState.filters.class); }
}

// ── Table Render ──────────────────────────────────────────────────
function getSgSorted() {
  if (!sgState.sortCol) return sgState.tableData;
  return [...sgState.tableData].sort((a, b) => {
    let av = a[sgState.sortCol] ?? '', bv = b[sgState.sortCol] ?? '';
    const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
    return sgState.sortDir === 'asc' ? cmp : -cmp;
  });
}

function gradeBadge(grade) {
  if (!grade && grade !== 0) return `<span class="grade-badge gx">—</span>`;
  const g = String(grade);
  const cls = g === '1' ? 'g1' : g === '2' ? 'g2' : g === '3' ? 'g3' : 'gx';
  return `<span class="grade-badge ${cls}">${esc(g)}</span>`;
}

function renderSgTable() {
  const data = getSgSorted();
  const total = sgState.totalRows, start = (sgState.page - 1) * sgState.pageSize + 1, end = Math.min(start + data.length - 1, total);

  if (data.length === 0) {
    $('empty-state').classList.remove('hidden');
    $('data-table').classList.add('hidden');
    $('grid-count-label').textContent = 'No results found';
    return;
  }
  $('empty-state').classList.add('hidden');
  $('data-table').classList.remove('hidden');
  $('grid-count-label').textContent = `Showing ${start}–${end} of ${total} store grades`;

  $('table-body').innerHTML = data.map(row => `<tr>
    <td class="mono">${row.STORE_GRADE_ID ?? '—'}</td>
    <td><strong>${esc(row.BRAND || '—')}</strong></td>
    <td class="mono">${row.LOCATION ?? '—'}</td>
    <td>${esc(row.STORE_NAME || '—')}</td>
    <td>${esc(row.COUNTRY || '—')}</td>
    <td class="mono">${row.DEPT ?? '—'}${row.DEPT_NAME ? `<br><span style="font-size:0.68rem;color:var(--text-muted)">${esc(row.DEPT_NAME)}</span>` : ''}</td>
    <td class="mono">${row.CLASS ?? '—'}${row.CLASS_NAME ? `<br><span style="font-size:0.68rem;color:var(--text-muted)">${esc(row.CLASS_NAME)}</span>` : ''}</td>
    <td class="mono">${row.SUBCLASS != null ? row.SUBCLASS : '<span class="text-dim">—</span>'}${row.SUB_NAME ? `<br><span style="font-size:0.68rem;color:var(--text-muted)">${esc(row.SUB_NAME)}</span>` : ''}</td>
    <td>${gradeBadge(row.GRADE)}</td>
    <td class="mono" style="font-size:0.7rem">${esc(row.CREATE_DATETIME ? row.CREATE_DATETIME.split(' ')[0] : '—')}</td>
    <td class="mono" style="font-size:0.7rem">${esc(row.LAST_UPDATE_DATETIME ? row.LAST_UPDATE_DATETIME.split(' ')[0] : '—')}</td>
  </tr>`).join('');
}

function renderSgStats() {
  const c = sgState.gradeCounts || {};
  $('stat-grade1').textContent = c['1'] || 0;
  $('stat-grade2').textContent = c['2'] || 0;
  $('stat-grade3').textContent = c['3'] || 0;
  $('stat-total').textContent  = sgState.totalRows;
}

function renderSgPagination() {
  const totalPages = Math.max(1, Math.ceil(sgState.totalRows / sgState.pageSize));
  $('page-info').textContent = `Page ${sgState.page} of ${totalPages}`;
  $('btn-prev').disabled = sgState.page <= 1;
  $('btn-next').disabled = sgState.page >= totalPages;
}

$('btn-prev').addEventListener('click', () => { if (sgState.page > 1) { sgState.page--; fetchSgGrades(); } });
$('btn-next').addEventListener('click', () => {
  const tp = Math.ceil(sgState.totalRows / sgState.pageSize);
  if (sgState.page < tp) { sgState.page++; fetchSgGrades(); }
});

// ── Sorting ───────────────────────────────────────────────────────
document.querySelectorAll('#data-table th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.sort;
    if (sgState.sortCol === col) sgState.sortDir = sgState.sortDir === 'asc' ? 'desc' : 'asc';
    else { sgState.sortCol = col; sgState.sortDir = 'asc'; }
    document.querySelectorAll('#data-table th').forEach(h => { h.classList.remove('sort-asc','sort-desc'); h.removeAttribute('aria-sort'); });
    th.classList.add(sgState.sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
    th.setAttribute('aria-sort', sgState.sortDir === 'asc' ? 'ascending' : 'descending');
    renderSgTable();
  });
});

// ── Reset ─────────────────────────────────────────────────────────
$('btn-reset').addEventListener('click', () => {
  ['dept-select','class-select','subclass-select','country-select','store-select'].forEach(id => { $(id).value = ''; });
  $('class-select').disabled = true;
  $('subclass-select').disabled = true;
  Object.assign(sgState.filters, { dept: null, class: null, subclass: null, country: null, store: null });
  sgState.tableData = []; sgState.totalRows = 0; sgState.gradeCounts = {}; sgState.page = 1; sgState.sortCol = null;
  $('btn-search').disabled = true; $('btn-generate').disabled = true; $('btn-export').disabled = true;
  $('empty-state').classList.remove('hidden'); $('data-table').classList.add('hidden');
  $('grid-count-label').textContent = 'Select filters and search to load data';
  ['stat-grade1','stat-grade2','stat-grade3','stat-total'].forEach(id => $(id).textContent = '—');
  renderSgPagination();
});

// ── Export CSV ────────────────────────────────────────────────────
$('btn-export').addEventListener('click', () => {
  if (!sgState.tableData.length) return;
  const headers = ['STORE_GRADE_ID','BRAND','LOCATION','STORE_NAME','COUNTRY','DEPT','DEPT_NAME','CLASS','CLASS_NAME','SUBCLASS','SUB_NAME','GRADE','CREATE_DATETIME','LAST_UPDATE_DATETIME'];
  const rows = sgState.tableData.map(r => headers.map(h => `"${String(r[h] ?? '').replace(/"/g,'""')}"`).join(','));
  const csv  = [headers.join(','), ...rows].join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = `store_grades_dept${sgState.filters.dept}_class${sgState.filters.class}_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  showToast('success', 'Exported', `${sgState.tableData.length} rows downloaded`);
});

// ── Grading Modal ─────────────────────────────────────────────────
$('btn-generate').addEventListener('click', openGenerateModal);

function openGenerateModal() {
  const dept    = $('dept-select').options[$('dept-select').selectedIndex]?.text    || sgState.filters.dept;
  const cls     = $('class-select').options[$('class-select').selectedIndex]?.text  || sgState.filters.class;
  const sub     = $('subclass-select').value ? ($('subclass-select').options[$('subclass-select').selectedIndex]?.text || sgState.filters.subclass) : null;
  const country = sgState.filters.country || 'All Countries';
  const store   = sgState.filters.store   ? ($('store-select').options[$('store-select').selectedIndex]?.text || sgState.filters.store) : 'All Stores';
  const levelLabel = sgState.gradingLevel === 'class' ? 'Class Level' : 'Subclass Level';
  const levelDesc  = sgState.gradingLevel === 'class'
    ? 'Generates <strong>one grade per store</strong> for the entire Class.'
    : sub ? `Grade for <strong>Subclass: ${esc(sub)}</strong> only.`
          : 'Generates grades <strong>independently per subclass</strong>.';

  $('modal-scope').innerHTML = `
    <div class="scope-row"><span class="scope-key">Granularity</span><span class="scope-value" style="color:var(--accent-generate)">${esc(levelLabel)}</span></div>
    <div class="scope-row" style="margin-bottom:10px;font-size:0.78rem;opacity:0.8">${levelDesc}</div>
    <div class="scope-row"><span class="scope-key">Dept</span><span class="scope-value">${esc(dept)}</span></div>
    <div class="scope-row"><span class="scope-key">Class</span><span class="scope-value">${esc(cls)}</span></div>
    ${sub ? `<div class="scope-row"><span class="scope-key">Subclass</span><span class="scope-value">${esc(sub)}</span></div>` : ''}
    <div class="scope-row"><span class="scope-key">Country</span><span class="scope-value">${esc(country)}</span></div>
    <div class="scope-row"><span class="scope-key">Store</span><span class="scope-value">${esc(store)}</span></div>`;
  $('confirm-modal').classList.remove('hidden');
}

document.querySelectorAll('.cluster-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.cluster-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    sgState.selectedClusters = parseInt(btn.dataset.clusters, 10);
  });
});

$('modal-cancel').addEventListener('click',  () => $('confirm-modal').classList.add('hidden'));
$('confirm-modal').addEventListener('click', e => { if (e.target === $('confirm-modal')) $('confirm-modal').classList.add('hidden'); });
$('modal-confirm').addEventListener('click', async () => { $('confirm-modal').classList.add('hidden'); await runSgGrading(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('confirm-modal').classList.add('hidden'); });

async function runSgGrading() {
  if (sgState.isGenerating) return;
  sgState.isGenerating = true;
  showSgProgress(true, 'Running K-means Clustering...', 'Preparing data');
  animateSgBar(0, 30, 1000);
  try {
    const payload = { dept: parseInt(sgState.filters.dept, 10), class: parseInt(sgState.filters.class, 10), level: sgState.gradingLevel, clusters: sgState.selectedClusters };
    if (sgState.filters.subclass) payload.subclass = parseInt(sgState.filters.subclass, 10);
    if (sgState.filters.country)  payload.country  = sgState.filters.country;
    if (sgState.filters.store)    payload.store     = parseInt(sgState.filters.store, 10);
    animateSgBar(30, 80, 4000);
    updateSgProgress('Computing grades...', 'K-means clustering in progress');
    const result = await apiFetch('/api/generate-grades', { method: 'POST', body: JSON.stringify(payload) });
    animateSgBar(80, 100, 500);
    await sleep(600);
    showSgProgress(false);
    showToast('success', 'Grading Complete!', `${result.inserts} inserted, ${result.updates} updated. ${result.rows_processed} stores processed.`);
    await fetchSgGrades();
  } catch (e) { showSgProgress(false); showToast('error', 'Grading Failed', e.message); }
  finally { sgState.isGenerating = false; }
}

function showSgProgress(show, title='', sub='') {
  if (show) {
    $('progress-title').textContent = title; $('progress-sub').textContent = sub;
    $('progress-banner').classList.remove('hidden'); $('progress-bar').style.width = '0%';
    $('btn-generate').disabled = true;
  } else { $('progress-banner').classList.add('hidden'); updateSgButtons(); }
}
function updateSgProgress(title, sub) { $('progress-title').textContent = title; $('progress-sub').textContent = sub; }
function animateSgBar(from, to, dur) {
  const s = Date.now();
  const step = () => { const p = Math.min(1,(Date.now()-s)/dur); $('progress-bar').style.width=`${from+(to-from)*p}%`; if(p<1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ═══════════════════════════════════════════════════════════════════
// ══════════════ PAGE 2: PRODUCT MASTER ══════════════════════════
// ═══════════════════════════════════════════════════════════════════

const pmState = { page: 1, pageSize: 50, total: 0, data: [] };

// Cascading selects
$('pm-dept-select').addEventListener('change', () => {
  const dept = $('pm-dept-select').value;
  const pmClassSel = $('pm-class-select');
  pmClassSel.innerHTML = '<option value="">All Classes</option>';
  pmClassSel.disabled  = !dept;
  if (dept) {
    allFilters.classes.filter(c => c.DEPT == dept).forEach(c => pmClassSel.appendChild(new Option(c.CLASS_NAME ? `${c.CLASS} — ${c.CLASS_NAME}` : `${c.CLASS}`, c.CLASS)));
  }
  $('pm-subclass-select').innerHTML = '<option value="">All Subclasses</option>';
  $('pm-subclass-select').disabled  = true;
});

$('pm-class-select').addEventListener('change', () => {
  const dept = $('pm-dept-select').value, cls = $('pm-class-select').value;
  const pmSubSel = $('pm-subclass-select');
  pmSubSel.innerHTML = '<option value="">All Subclasses</option>';
  pmSubSel.disabled  = !cls;
  if (cls) {
    allFilters.subclasses.filter(s => s.DEPT == dept && s.CLASS == cls).forEach(s => pmSubSel.appendChild(new Option(s.SUB_NAME ? `${s.SUBCLASS} — ${s.SUB_NAME}` : `${s.SUBCLASS}`, s.SUBCLASS)));
  }
});

$('pm-btn-reset').addEventListener('click', () => {
  ['pm-brand-select','pm-dept-select','pm-class-select','pm-subclass-select'].forEach(id => { $(id).value = ''; });
  $('pm-search').value = '';
  $('pm-class-select').disabled = $('pm-subclass-select').disabled = true;
  pmState.page = 1; pmState.total = 0; pmState.data = [];
  $('pm-empty-state').classList.remove('hidden'); $('pm-data-table').classList.add('hidden');
  $('pm-count-label').textContent = 'Use filters to search the product catalog';
  $('pm-btn-export').disabled = true;
  renderPmPagination();
});

$('pm-btn-search').addEventListener('click', () => { pmState.page = 1; fetchPm(); });

// Search on Enter in text input
$('pm-search').addEventListener('keydown', e => { if (e.key === 'Enter') { pmState.page = 1; fetchPm(); } });

async function fetchPm() {
  const params = new URLSearchParams({ page: pmState.page, page_size: pmState.pageSize });
  const dept = $('pm-dept-select').value, cls = $('pm-class-select').value, sub = $('pm-subclass-select').value;
  const brand = $('pm-brand-select').value, search = $('pm-search').value.trim();
  if (dept)   params.set('dept',     dept);
  if (cls)    params.set('class',    cls);
  if (sub)    params.set('subclass', sub);
  if (brand)  params.set('brand',    brand);
  if (search) params.set('search',   search);

  $('pm-count-label').textContent = 'Loading...';
  try {
    const data = await apiFetch(`/api/product-master?${params}`);
    pmState.total = data.total; pmState.data = data.data;
    renderPmTable(); renderPmPagination();
    $('pm-btn-export').disabled = data.data.length === 0;
  } catch (e) { showToast('error', 'Product Master Error', e.message); }
}

function renderPmTable() {
  if (pmState.data.length === 0) {
    $('pm-empty-state').classList.remove('hidden'); $('pm-data-table').classList.add('hidden');
    $('pm-count-label').textContent = 'No products found'; return;
  }
  $('pm-empty-state').classList.add('hidden'); $('pm-data-table').classList.remove('hidden');
  const start = (pmState.page - 1) * pmState.pageSize + 1, end = Math.min(start + pmState.data.length - 1, pmState.total);
  $('pm-count-label').textContent = `Showing ${start}–${end} of ${pmState.total} products`;

  $('pm-table-body').innerHTML = pmState.data.map(r => `<tr>
    <td><strong>${esc(r.BRAND || '—')}</strong></td>
    <td class="mono" style="font-size:0.72rem">${esc(r.OPTION_ID || '—')}</td>
    <td style="max-width:220px;white-space:normal">${esc(r.OPTION_DESC || '—')}</td>
    <td class="mono" style="font-size:0.7rem">${esc(r.VPN || '—')}</td>
    <td class="mono">${r.DEPT ?? '—'}<br><span style="font-size:0.68rem;color:var(--text-muted)">${esc(r.DEPT_NAME||'')}</span></td>
    <td class="mono">${r.CLASS ?? '—'}<br><span style="font-size:0.68rem;color:var(--text-muted)">${esc(r.CLASS_NAME||'')}</span></td>
    <td class="mono">${r.SUBCLASS ?? '—'}<br><span style="font-size:0.68rem;color:var(--text-muted)">${esc(r.SUB_NAME||'')}</span></td>
    <td>${esc(r.GENDER || '—')}</td>
    <td>${esc(r.FABRIC || '—')}</td>
    <td>${esc(r.COLOR_SHADE || '—')}</td>
    <td>${esc(r.SEASON_CODE || '—')}</td>
    <td>${esc(r.SILHOUETTE || '—')}</td>
    <td>${esc(r.PRICE_STRATEGY || '—')}</td>
    <td>${esc(r.SELLING_PHASE || '—')}</td>
    <td>${esc(r.LABEL || '—')}</td>
  </tr>`).join('');
}

function renderPmPagination() {
  const tp = Math.max(1, Math.ceil(pmState.total / pmState.pageSize));
  $('pm-page-info').textContent = `Page ${pmState.page} of ${tp}`;
  $('pm-btn-prev').disabled = pmState.page <= 1;
  $('pm-btn-next').disabled = pmState.page >= tp;
}

$('pm-btn-prev').addEventListener('click', () => { if (pmState.page > 1) { pmState.page--; fetchPm(); } });
$('pm-btn-next').addEventListener('click', () => { const tp=Math.ceil(pmState.total/pmState.pageSize); if(pmState.page<tp){pmState.page++;fetchPm();} });

$('pm-btn-export').addEventListener('click', () => {
  if (!pmState.data.length) return;
  const headers = ['BRAND','OPTION_ID','OPTION_DESC','VPN','DEPT','DEPT_NAME','CLASS','CLASS_NAME','SUBCLASS','SUB_NAME','GENDER','FABRIC','COLOR_SHADE','COLOR_FAMILY','SEASON_CODE','SEASONALITY','SILHOUETTE','PRICE_STRATEGY','SELLING_PHASE','LABEL','COLLECTION'];
  const rows = pmState.data.map(r => headers.map(h => `"${String(r[h]??'').replace(/"/g,'""')}"`).join(','));
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([[headers.join(','),...rows].join('\r\n')], {type:'text/csv'}));
  a.download = `product_master_${new Date().toISOString().slice(0,10)}.csv`; a.click();
  showToast('success', 'Exported', `${pmState.data.length} products downloaded`);
});

// ═══════════════════════════════════════════════════════════════════
// ══════════════ PAGE 4: LOCATION MASTER ══════════════════════════
// ═══════════════════════════════════════════════════════════════════

const locState = { page: 1, pageSize: 50, total: 0, data: [] };

$('loc-btn-reset').addEventListener('click', () => {
  $('loc-country-select').value = '';
  $('loc-type-select').value    = '';
  $('loc-search-input').value   = '';
  locState.page = 1; locState.total = 0; locState.data = [];
  $('loc-empty-state').classList.remove('hidden'); $('loc-data-table').classList.add('hidden');
  $('loc-count-label').textContent = 'Use filters to browse store locations';
  renderLocPagination();
});

$('loc-btn-search').addEventListener('click', () => { locState.page = 1; fetchLocs(); });

async function fetchLocs() {
  const params = new URLSearchParams({ page: locState.page, page_size: locState.pageSize });
  const country = $('loc-country-select').value;
  const type    = $('loc-type-select').value;
  const search  = $('loc-search-input').value.trim();

  if (country) params.set('country', country);
  if (type)    params.set('type',    type);
  if (search)  params.set('search',  search);

  $('loc-count-label').textContent = 'Loading...';
  try {
    const data = await apiFetch(`/api/location-master?${params}`);
    locState.total = data.total; locState.data = data.data;
    renderLocTable(); renderLocPagination();
  } catch (e) { showToast('error', 'Location Error', e.message); }
}

function renderLocTable() {
  if (locState.data.length === 0) {
    $('loc-empty-state').classList.remove('hidden'); $('loc-data-table').classList.add('hidden');
    $('loc-count-label').textContent = 'No locations found'; return;
  }
  $('loc-empty-state').classList.add('hidden'); $('loc-data-table').classList.remove('hidden');
  const start = (locState.page-1)*locState.pageSize+1, end = Math.min(start+locState.data.length-1, locState.total);
  $('loc-count-label').textContent = `Showing ${start}–${end} of ${locState.total} rows`;

  $('loc-table-body').innerHTML = locState.data.map(r => `
    <tr>
      <td class="mono">${r.STORE}</td>
      <td>${esc(r.STORE_NAME)}</td>
      <td>${esc(r.COUNTRY)}</td>
      <td>${esc(r.CITY)}</td>
      <td class="mono">${esc(r.CURRENCY_CODE)}</td>
      <td><span class="unit-badge">${esc(r.CHANNEL_TYPE)}</span></td>
      <td class="mono">${fmt(r.TOTAL_SQUARE_FT)}</td>
      <td class="text-sm">${esc(r.MALL_NAME)}</td>
      <td class="mono text-sm">${esc(r.DEFAULT_WH)}</td>
    </tr>
  `).join('');
}

function renderLocPagination() {
  const tp = Math.max(1, Math.ceil(locState.total / locState.pageSize));
  $('loc-page-info').textContent = `Page ${locState.page} of ${tp}`;
  $('loc-btn-prev').disabled = locState.page <= 1;
  $('loc-btn-next').disabled = locState.page >= tp;
}

$('loc-btn-prev').addEventListener('click', () => { if(locState.page>1){locState.page--;fetchLocs();} });
$('loc-btn-next').addEventListener('click', () => { const tp=Math.ceil(locState.total/locState.pageSize);if(locState.page<tp){locState.page++;fetchLocs();} });


// ══════════════ PAGE 3: SALES HISTORY ═══════════════════════════
// ═══════════════════════════════════════════════════════════════════

const shState = { level: 'class', locLevel: 'store', page: 1, pageSize: 50, total: 0, data: [] };

// Level Buttons
document.querySelectorAll('[data-sh-level]').forEach(btn => {
  btn.addEventListener('click', () => {
    shState.level = btn.dataset.shLevel;
    document.querySelectorAll('[data-sh-level]').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-pressed','false'); });
    btn.classList.add('active'); btn.setAttribute('aria-pressed','true');
  });
});

// Location Level Buttons (Country/Store)
document.querySelectorAll('[data-sh-loc]').forEach(btn => {
  btn.addEventListener('click', () => {
    shState.locLevel = btn.dataset.shLoc;
    document.querySelectorAll('[data-sh-loc]').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-pressed','false'); });
    btn.classList.add('active'); btn.setAttribute('aria-pressed','true');
    
    // Disable store filter if country level is selected
    const storeSel = $('sh-store-select');
    if (shState.locLevel === 'country') {
      storeSel.value = '';
      storeSel.disabled = true;
    } else {
      storeSel.disabled = false;
    }
  });
});

// Cascading selects for Sales History
$('sh-dept-select').addEventListener('change', () => {
  const dept = $('sh-dept-select').value;
  const shClassSel = $('sh-class-select');
  shClassSel.innerHTML = '<option value="">All Classes</option>';
  shClassSel.disabled  = !dept;
  if (dept) allFilters.classes.filter(c => c.DEPT == dept).forEach(c => shClassSel.appendChild(new Option(c.CLASS_NAME ? `${c.CLASS} — ${c.CLASS_NAME}` : `${c.CLASS}`, c.CLASS)));
  $('sh-subclass-select').innerHTML = '<option value="">All Subclasses</option>';
  $('sh-subclass-select').disabled  = true;
});

$('sh-class-select').addEventListener('change', () => {
  const dept = $('sh-dept-select').value, cls = $('sh-class-select').value;
  const shSubSel = $('sh-subclass-select');
  shSubSel.innerHTML = '<option value="">All Subclasses</option>';
  shSubSel.disabled  = !cls;
  if (cls) allFilters.subclasses.filter(s => s.DEPT == dept && s.CLASS == cls).forEach(s => shSubSel.appendChild(new Option(s.SUB_NAME ? `${s.SUBCLASS} — ${s.SUB_NAME}` : `${s.SUBCLASS}`, s.SUBCLASS)));
});

$('sh-btn-reset').addEventListener('click', () => {
  ['sh-dept-select','sh-class-select','sh-subclass-select','sh-country-select','sh-store-select'].forEach(id => { $(id).value=''; });
  $('sh-date-from').value = ''; $('sh-date-to').value = '';
  $('sh-class-select').disabled = $('sh-subclass-select').disabled = true;
  shState.page = 1; shState.total = 0; shState.data = [];
  $('sh-empty-state').classList.remove('hidden'); $('sh-data-table').classList.add('hidden');
  $('sh-count-label').textContent = 'Use filters to explore sales data';
  $('sh-btn-export').disabled = true;
  ['sh-stat-regular','sh-stat-promo','sh-stat-mrkdwn','sh-stat-total'].forEach(id => $(id).textContent='—');
  renderShPagination();
});

$('sh-btn-search').addEventListener('click', () => { shState.page = 1; fetchSh(); });

async function fetchSh() {
  const params = new URLSearchParams({ level: shState.level, loc_level: shState.locLevel, page: shState.page, page_size: shState.pageSize });
  const dept     = $('sh-dept-select').value;
  const cls      = $('sh-class-select').value;
  const sub      = $('sh-subclass-select').value;
  const country  = $('sh-country-select').value;
  const store    = $('sh-store-select').value;
  const dateFrom = $('sh-date-from').value.trim();
  const dateTo   = $('sh-date-to').value.trim();
  if (dept)     params.set('dept',      dept);
  if (cls)      params.set('class',     cls);
  if (sub)      params.set('subclass',  sub);
  if (country)  params.set('country',   country);
  if (store)    params.set('store',     store);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo)   params.set('date_to',   dateTo);

  $('sh-count-label').textContent = 'Loading...';
  try {
    const data = await apiFetch(`/api/sales-history?${params}`);
    shState.total = data.total; shState.data = data.data;
    renderShTable(data.level); renderShPagination(); renderShStats();
    $('sh-btn-export').disabled = data.data.length === 0;
  } catch (e) { showToast('error', 'Sales History Error', e.message); }
}

function renderShStats() {
  let reg=0, pro=0, mkd=0, tot=0;
  shState.data.forEach(r => { reg += r.REGULAR_UNITS||0; pro += r.PROMO_UNITS||0; mkd += r.MRKDWN_UNITS||0; tot += r.TOTAL_UNITS||0; });
  $('sh-stat-regular').textContent = fmt(reg);
  $('sh-stat-promo').textContent   = fmt(pro);
  $('sh-stat-mrkdwn').textContent  = fmt(mkd);
  $('sh-stat-total').textContent   = fmt(tot);
}

// Dynamic column headers per level
const SH_LEVEL_COLS = {
  dept:     ['BRAND','DEPT','DEPT_NAME'],
  class:    ['BRAND','DEPT','DEPT_NAME','CLASS','CLASS_NAME'],
  subclass: ['BRAND','DEPT','DEPT_NAME','CLASS','CLASS_NAME','SUBCLASS','SUB_NAME'],
  sku:      ['BRAND','DEPT','DEPT_NAME','CLASS','CLASS_NAME','SUBCLASS','SUB_NAME','OPTION_ID','OPTION_DESC'],
};

// User-friendly column labels
const COL_LABELS = {
  BRAND:'Brand', DEPT:'Dept', DEPT_NAME:'Dept Name', CLASS:'Class', CLASS_NAME:'Class Name',
  SUBCLASS:'Subclass', SUB_NAME:'Sub Name', OPTION_ID:'Option ID', OPTION_DESC:'Description',
  STORE:'Store', STORE_NAME:'Store Name', COUNTRY:'Country',
  REGULAR_UNITS:'Regular', PROMO_UNITS:'Promo', MRKDWN_UNITS:'Markdown', TOTAL_UNITS:'Total Units',
  BASE_HISTORY:'Base Hist', WEEKS_WITH_SALES:'Weeks',
};

function renderShTable(level) {
  if (shState.data.length === 0) {
    $('sh-empty-state').classList.remove('hidden'); $('sh-data-table').classList.add('hidden');
    $('sh-count-label').textContent = 'No sales data found'; return;
  }
  $('sh-empty-state').classList.add('hidden'); $('sh-data-table').classList.remove('hidden');
  const start = (shState.page-1)*shState.pageSize+1, end = Math.min(start+shState.data.length-1, shState.total);
  $('sh-count-label').textContent = `Showing ${start}–${end} of ${shState.total} rows`;

  const baseAlwaysCols = ['COUNTRY','REGULAR_UNITS','PROMO_UNITS','MRKDWN_UNITS','TOTAL_UNITS','BASE_HISTORY','WEEKS_WITH_SALES'];
  const locCols = shState.locLevel === 'store' ? ['STORE','STORE_NAME'] : [];
  const cols = [...(SH_LEVEL_COLS[level] || SH_LEVEL_COLS.class), ...locCols, ...baseAlwaysCols];

  // Header
  $('sh-table-head').innerHTML = cols.map(c => `<th>${COL_LABELS[c] || c}</th>`).join('');

  // Body
  const unitCols = new Set(['REGULAR_UNITS','PROMO_UNITS','MRKDWN_UNITS','TOTAL_UNITS','BASE_HISTORY','WEEKS_WITH_SALES']);
  const badgeMap = { REGULAR_UNITS:'reg', PROMO_UNITS:'pro', MRKDWN_UNITS:'mkd', TOTAL_UNITS:'tot' };

  $('sh-table-body').innerHTML = shState.data.map(row => `<tr>${cols.map(c => {
    const v = row[c];
    if (badgeMap[c] !== undefined) {
      return `<td><span class="unit-badge ${badgeMap[c]}">${fmt(v)}</span></td>`;
    }
    if (unitCols.has(c)) return `<td class="mono">${fmt(v)}</td>`;
    if (c === 'DEPT' || c === 'CLASS' || c === 'SUBCLASS' || c === 'STORE') return `<td class="mono">${v ?? '—'}</td>`;
    return `<td>${esc(v ?? '—')}</td>`;
  }).join('')}</tr>`).join('');
}

function renderShPagination() {
  const tp = Math.max(1, Math.ceil(shState.total / shState.pageSize));
  $('sh-page-info').textContent = `Page ${shState.page} of ${tp}`;
  $('sh-btn-prev').disabled = shState.page <= 1;
  $('sh-btn-next').disabled = shState.page >= tp;
}

$('sh-btn-prev').addEventListener('click', () => { if(shState.page>1){shState.page--;fetchSh();} });
$('sh-btn-next').addEventListener('click', () => { const tp=Math.ceil(shState.total/shState.pageSize);if(shState.page<tp){shState.page++;fetchSh();} });

$('sh-btn-export').addEventListener('click', () => {
  if (!shState.data.length) return;
  const baseAlwaysCols = ['COUNTRY','REGULAR_UNITS','PROMO_UNITS','MRKDWN_UNITS','TOTAL_UNITS','BASE_HISTORY','WEEKS_WITH_SALES'];
  const locCols = shState.locLevel === 'store' ? ['STORE','STORE_NAME'] : [];
  const cols = [...(SH_LEVEL_COLS[shState.level]||SH_LEVEL_COLS.class), ...locCols, ...baseAlwaysCols];
  const rows = shState.data.map(r => cols.map(c => `"${String(r[c]??'').replace(/"/g,'""')}"`).join(','));
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([[cols.join(','),...rows].join('\r\n')],{type:'text/csv'}));
  a.download = `sales_history_${shState.level}_${new Date().toISOString().slice(0,10)}.csv`; a.click();
  showToast('success', 'Exported', `${shState.data.length} rows downloaded`);
});

// ═══════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════

async function init() {
  await checkHealth();
  await loadFilters();
}

init();
