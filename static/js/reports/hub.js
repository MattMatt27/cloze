// Reports hub: scope navigator + per-scope detail pane + generation.
// Tree comes from /reports/navigator; report existence joins client-side from
// /reports so chip updates never rebuild the tree.
import { enqueueReport, pollJob, progressLabel } from './jobs.js';
import { initTemplatesTab } from './templates.js';

const nav = document.getElementById('scopeNav');
const pane = document.getElementById('scopePane');

let tree = null;
let reportsByKey = new Map(); // "scope:id" -> report summary
let selected = null;          // {scope, scopeId, label, children?}

const esc = (s) => window.escapeHtml ? window.escapeHtml(String(s)) : String(s);
const keyOf = (scope, id) => `${scope}:${id}`;

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function loadReports() {
  const reports = await fetchJson('/api/v2/reports');
  reportsByKey = new Map(reports.map((r) => [keyOf(r.scope, r.scope_id), r]));
}

function chip(scope, scopeId) {
  const report = reportsByKey.get(keyOf(scope, scopeId));
  if (!report) {
    return '<span class="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-500">none</span>';
  }
  if (report.is_stale) {
    return '<span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">stale</span>';
  }
  return '<span class="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">ready</span>';
}

// --- navigator rail ----------------------------------------------------------

function navItem(scope, scopeId, label, indentClass = '') {
  return `<button class="nav-node flex w-full items-center justify-between rounded px-2 py-1.5 text-left hover:bg-stone-100 ${indentClass}"
      data-scope="${scope}" data-scope-id="${scopeId}" data-label="${esc(label)}">
    <span class="truncate">${esc(label)}</span>${chip(scope, scopeId)}
  </button>`;
}

function renderNav() {
  const flows = tree.flows.map((flow) => `
    <details class="group" open>
      <summary class="cursor-pointer list-none rounded px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500 hover:bg-stone-100">
        ${esc(flow.name)}
      </summary>
      ${navItem('flow', flow.flow_id, 'Cohort report', 'pl-4')}
      ${flow.enrollments.map((enrollment) => `
        <details class="pl-4">
          <summary class="cursor-pointer list-none rounded px-2 py-1 hover:bg-stone-100">
            ${esc(enrollment.username)}
          </summary>
          ${navItem('enrollment', enrollment.enrollment_id, 'Study report', 'pl-6')}
          ${enrollment.windows.map((w) =>
            navItem('window', w.window_id, w.phase_label || w.title, 'pl-6')).join('')}
        </details>`).join('')}
    </details>`).join('');

  const participants = tree.participants.map((p) =>
    navItem('participant', p.patient_id, p.username, 'pl-4')).join('');

  nav.innerHTML = `
    ${navItem('account', tree.provider_id, 'Account overview')}
    <div class="pt-3">${flows ||
      '<p class="px-2 text-xs text-stone-400">No study flows yet.</p>'}</div>
    <details class="pt-3" ${tree.flows.length ? '' : 'open'}>
      <summary class="cursor-pointer list-none rounded px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500 hover:bg-stone-100">
        All participants
      </summary>
      ${participants || '<p class="px-2 text-xs text-stone-400">No participants.</p>'}
    </details>`;

  nav.querySelectorAll('.nav-node').forEach((button) => {
    button.addEventListener('click', () => {
      select(button.dataset.scope, Number(button.dataset.scopeId), button.dataset.label);
    });
  });
}

// --- detail pane -------------------------------------------------------------

function childRows() {
  if (!selected) return [];
  if (selected.scope === 'flow') {
    const flow = tree.flows.find((f) => f.flow_id === selected.scopeId);
    return (flow?.enrollments || []).map((enrollment) => ({
      scope: 'enrollment', scopeId: enrollment.enrollment_id,
      label: `${enrollment.username} — study report`,
    }));
  }
  if (selected.scope === 'enrollment') {
    for (const flow of tree.flows) {
      const enrollment = flow.enrollments.find(
        (e) => e.enrollment_id === selected.scopeId);
      if (enrollment) {
        return enrollment.windows.map((w) => ({
          scope: 'window', scopeId: w.window_id,
          label: w.phase_label || w.title,
        }));
      }
    }
  }
  if (selected.scope === 'account') {
    return tree.flows.map((flow) => ({
      scope: 'flow', scopeId: flow.flow_id, label: `${flow.name} — cohort report`,
    }));
  }
  return [];
}

function renderPane(statusHtml = '') {
  if (!selected) return;
  const report = reportsByKey.get(keyOf(selected.scope, selected.scopeId));
  const children = childRows();

  pane.innerHTML = `
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-lg font-semibold text-stone-900">${esc(selected.label)}</h2>
        <p class="mt-0.5 text-xs uppercase tracking-wide text-stone-400">${esc(selected.scope)} scope</p>
      </div>
      <div class="flex items-center gap-2">
        ${report ? `<a href="/reports/${report.id}"
            class="rounded-md border border-stone-200 bg-white px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-50">Open report</a>` : ''}
        <button id="generateBtn"
            class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
          ${report ? 'Regenerate' : 'Generate report'}
        </button>
      </div>
    </div>
    <div id="genStatus" class="${statusHtml ? '' : 'hidden'} mt-3 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm text-indigo-800">${statusHtml}</div>
    ${report ? `<p class="mt-3 text-sm text-stone-500">
        Report generated ${window.formatDate ? window.formatDate(report.generated_at) : ''}
        ${report.is_stale ? ' — <span class="text-amber-700">analysis library has changed since; consider regenerating</span>' : ''}
      </p>` : `<p class="mt-3 text-sm text-stone-400">No report yet for this ${esc(selected.scope)}.</p>`}
    ${children.length ? `
      <h3 class="mt-6 text-sm font-semibold text-stone-700">Contains</h3>
      <ul class="mt-2 divide-y divide-stone-100 rounded-md border border-stone-200">
        ${children.map((child) => {
          const childReport = reportsByKey.get(keyOf(child.scope, child.scopeId));
          return `<li class="flex items-center justify-between px-3 py-2 text-sm">
            <button class="child-node truncate text-left text-stone-700 hover:text-indigo-700"
                data-scope="${child.scope}" data-scope-id="${child.scopeId}"
                data-label="${esc(child.label)}">${esc(child.label)}</button>
            <span class="flex items-center gap-2">
              ${childReport ? `<a class="text-xs text-indigo-600 hover:underline" href="/reports/${childReport.id}">open</a>` : ''}
              ${chip(child.scope, child.scopeId)}
            </span>
          </li>`;
        }).join('')}
      </ul>` : ''}`;

  pane.querySelector('#generateBtn').addEventListener('click', generateSelected);
  pane.querySelectorAll('.child-node').forEach((button) => {
    button.addEventListener('click', () => {
      select(button.dataset.scope, Number(button.dataset.scopeId), button.dataset.label);
    });
  });
}

function select(scope, scopeId, label) {
  selected = { scope, scopeId, label };
  renderPane();
}

async function generateSelected() {
  const button = pane.querySelector('#generateBtn');
  const status = pane.querySelector('#genStatus');
  button.disabled = true;
  status.classList.remove('hidden');
  status.textContent = 'Queued…';
  try {
    const job = await enqueueReport(selected.scope, selected.scopeId);
    const finished = await pollJob(job.id, (j) => {
      status.textContent = progressLabel(j);
    });
    if (finished.status === 'done') {
      await loadReports();
      renderNav();
      renderPane();
    } else {
      status.textContent = `Generation ${finished.status}: ${finished.error || 'unknown error'}`;
      button.disabled = false;
    }
  } catch (error) {
    status.textContent = `Error: ${error.message}`;
    button.disabled = false;
  }
}

// --- tabs --------------------------------------------------------------------

function initTabs() {
  const tabs = document.querySelectorAll('.hub-tab');
  const panes = { browse: document.getElementById('tab-browse'),
                  templates: document.getElementById('tab-templates') };
  function activate(name) {
    Object.entries(panes).forEach(([key, el]) =>
      el.classList.toggle('hidden', key !== name));
    tabs.forEach((tab) => {
      const active = tab.dataset.tab === name;
      tab.classList.toggle('bg-indigo-600', active);
      tab.classList.toggle('text-white', active);
      tab.classList.toggle('text-stone-600', !active);
    });
  }
  tabs.forEach((tab) => tab.addEventListener('click', () => activate(tab.dataset.tab)));
  activate('browse');
}

// --- boot --------------------------------------------------------------------

(async function boot() {
  initTabs();
  initTemplatesTab();
  try {
    [tree] = await Promise.all([
      fetchJson('/api/v2/reports/navigator'),
      loadReports(),
    ]);
    renderNav();
    select('account', tree.provider_id, 'Account overview');
  } catch (error) {
    nav.innerHTML = `<p class="px-2 text-sm text-red-600">Failed to load: ${esc(error.message)}</p>`;
  }
})();
