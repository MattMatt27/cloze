// Reports hub — entity-first browse.
//
// The rail is your STUDY, not a report taxonomy: rows are flows, people, and
// phases by name. Clicking a row selects that thing and shows an oriented
// pane (what it is, its activity, its report, its children). Chevrons expand;
// report-type language appears only inside the pane, in plain words.
import { enqueueReport, pollJob, progressLabel } from './jobs.js';
import { initTemplatesTab } from './templates.js';

const nav = document.getElementById('scopeNav');
const pane = document.getElementById('scopePane');

let tree = null;
let reportsByKey = new Map(); // "scope:id" -> report summary
let selected = null;          // node object (see makeNode)
const expanded = new Set();   // node keys with open chevrons

const esc = (s) => window.escapeHtml ? window.escapeHtml(String(s)) : String(s);
const fmtDate = (t) => (window.formatDate && t) ? window.formatDate(t) : '';
const keyOf = (scope, id) => `${scope}:${id}`;

// Plain-language framing per scope: what the report IS, without jargon.
const SCOPE_COPY = {
  account: {
    reportName: 'Account report',
    explains: 'Summarizes activity across every study flow in your account.',
  },
  flow: {
    reportName: 'Whole-study report',
    explains: 'Combines all participants in this study flow — completion, engagement, and shared themes.',
  },
  enrollment: {
    reportName: 'Participant journey report',
    explains: 'This participant’s full journey through the study — trends across phases, week by week.',
  },
  participant: {
    reportName: 'Participant overview report',
    explains: 'Everything this participant has done across all studies and free conversations.',
  },
  window: {
    reportName: 'Phase report',
    explains: 'What happened during this phase — conversations, sentiment, and themes.',
  },
};

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function loadReports() {
  const reports = await fetchJson('/api/v2/reports');
  reportsByKey = new Map(reports.map((r) => [keyOf(r.scope, r.scope_id), r]));
}

// --- node model ---------------------------------------------------------------

function makeNode({ scope, scopeId, name, meta, children = [], crossLink = null }) {
  return { scope, scopeId, name, meta, children, crossLink, key: keyOf(scope, scopeId) };
}

function buildNodes() {
  const flowNodes = tree.flows.map((flow) => makeNode({
    scope: 'flow',
    scopeId: flow.flow_id,
    name: flow.name,
    meta: `Study flow · ${flow.enrollment_count} participant${flow.enrollment_count === 1 ? '' : 's'}`,
    children: flow.enrollments.map((enrollment) => makeNode({
      scope: 'enrollment',
      scopeId: enrollment.enrollment_id,
      name: enrollment.username,
      meta: `In ${flow.name} since ${fmtDate(enrollment.enrolled_at)} · ${enrollment.conversations} conversation${enrollment.conversations === 1 ? '' : 's'}`,
      crossLink: { patientId: enrollment.patient_id, username: enrollment.username },
      children: enrollment.windows.map((w) => makeNode({
        scope: 'window',
        scopeId: w.window_id,
        name: w.phase_label || w.title,
        meta: `${fmtDate(w.start_date)} – ${fmtDate(w.end_date)} · ${w.conversations} conversation${w.conversations === 1 ? '' : 's'}`,
      })),
    })),
  }));

  const participantNodes = tree.participants.map((p) => makeNode({
    scope: 'participant',
    scopeId: p.patient_id,
    name: p.username,
    meta: `All activity, any study · ${p.conversations} conversation${p.conversations === 1 ? '' : 's'}`,
  }));

  const account = makeNode({
    scope: 'account',
    scopeId: tree.provider_id,
    name: 'Whole account',
    meta: `${tree.flows.length} study flow${tree.flows.length === 1 ? '' : 's'} · ${tree.participants.length} participant${tree.participants.length === 1 ? '' : 's'}`,
    children: flowNodes,
  });

  return { account, flowNodes, participantNodes };
}

function findNode(key) {
  const { account, participantNodes } = buildNodes();
  const stack = [account, ...participantNodes];
  while (stack.length) {
    const node = stack.pop();
    if (node.key === key) return node;
    stack.push(...node.children);
  }
  return null;
}

// --- rail ---------------------------------------------------------------------

function statusDot(key) {
  const report = reportsByKey.get(key);
  if (!report) {
    return '<span class="h-2 w-2 shrink-0 rounded-full border border-stone-300" title="No report yet"></span>';
  }
  if (report.is_stale) {
    return '<span class="h-2 w-2 shrink-0 rounded-full bg-amber-400" title="Report ready (analysis has changed since)"></span>';
  }
  return '<span class="h-2 w-2 shrink-0 rounded-full bg-emerald-500" title="Report ready"></span>';
}

function railRow(node, depth) {
  const hasChildren = node.children.length > 0;
  const isSelected = selected && selected.key === node.key;
  const isOpen = expanded.has(node.key);
  const chevron = hasChildren
    ? `<button class="rail-toggle -ml-1 shrink-0 rounded p-0.5 text-stone-400 hover:text-stone-600" data-key="${node.key}" aria-label="expand">
         <svg class="h-3.5 w-3.5 transition-transform ${isOpen ? 'rotate-90' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5l7 7-7 7"/></svg>
       </button>`
    : '<span class="w-[18px] shrink-0"></span>';

  return `<div class="flex items-center" style="padding-left:${depth * 14}px">
      ${chevron}
      <button class="rail-select flex min-w-0 flex-1 items-center gap-2 rounded px-2 py-1.5 text-left
          ${isSelected ? 'bg-indigo-50 font-medium text-indigo-900' : 'text-stone-700 hover:bg-stone-100'}"
          data-key="${node.key}">
        <span class="truncate">${esc(node.name)}</span>
        ${statusDot(node.key)}
      </button>
    </div>` + (isOpen
      ? node.children.map((child) => railRow(child, depth + 1)).join('')
      : '');
}

function renderNav() {
  const { account, participantNodes } = buildNodes();
  nav.innerHTML = `
    ${railRow(account, 0)}
    ${account.children.length ? '' :
      '<p class="px-3 py-1 text-xs text-stone-400">No study flows yet — create one in Study Design.</p>'}
    <div class="mt-4 px-2 text-[11px] font-semibold uppercase tracking-wide text-stone-400">
      Participants <span class="font-normal normal-case">(across all studies)</span>
    </div>
    ${participantNodes.map((node) => railRow(node, 0)).join('')
      || '<p class="px-3 py-1 text-xs text-stone-400">No participants yet.</p>'}`;

  nav.querySelectorAll('.rail-toggle').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      const key = button.dataset.key;
      expanded.has(key) ? expanded.delete(key) : expanded.add(key);
      renderNav();
    });
  });
  nav.querySelectorAll('.rail-select').forEach((button) => {
    button.addEventListener('click', () => select(button.dataset.key));
  });
}

// --- detail pane --------------------------------------------------------------

function reportCard(node, statusHtml = '') {
  const copy = SCOPE_COPY[node.scope];
  const report = reportsByKey.get(node.key);

  let statusLine;
  if (report) {
    statusLine = `Generated ${fmtDate(report.generated_at)}` +
      (report.is_stale
        ? ' · <span class="text-amber-700">the analysis library has changed since — regenerate for current results</span>'
        : '');
  } else {
    statusLine = 'Not generated yet.';
  }

  return `
    <div class="mt-5 rounded-lg border border-stone-200 bg-stone-50/60 p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <h3 class="text-sm font-semibold text-stone-900">${esc(copy.reportName)}</h3>
          <p class="mt-0.5 text-xs text-stone-500">${esc(copy.explains)}</p>
          <p class="mt-1.5 text-xs ${report ? 'text-stone-600' : 'text-stone-400'}">${statusLine}</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          ${report ? `<a href="/reports/${report.id}"
              class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Read report</a>` : ''}
          <button id="generateBtn"
              class="rounded-md ${report ? 'border border-stone-200 bg-white text-stone-700 hover:bg-stone-50'
                                          : 'bg-indigo-600 text-white hover:bg-indigo-700'} px-3 py-1.5 text-sm font-medium">
            ${report ? 'Regenerate' : 'Generate'}
          </button>
        </div>
      </div>
      <div id="genStatus" class="${statusHtml ? '' : 'hidden'} mt-3 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm text-indigo-800">${statusHtml}</div>
    </div>`;
}

function childrenTable(node) {
  if (!node.children.length) return '';
  const childNoun = { account: 'Study flows', flow: 'Participants',
                      enrollment: 'Phases' }[node.scope] || 'Contains';
  const rows = node.children.map((child) => {
    const childReport = reportsByKey.get(child.key);
    return `<li class="flex items-center justify-between gap-3 px-3 py-2.5">
      <button class="child-select min-w-0 flex-1 text-left" data-key="${child.key}">
        <span class="block truncate text-sm font-medium text-stone-800 hover:text-indigo-700">${esc(child.name)}</span>
        <span class="block truncate text-xs text-stone-400">${esc(child.meta || '')}</span>
      </button>
      <span class="flex shrink-0 items-center gap-3">
        ${childReport
          ? `<a class="text-xs font-medium text-indigo-600 hover:underline" href="/reports/${childReport.id}">Read report</a>`
          : '<span class="text-xs text-stone-300">no report</span>'}
        ${statusDot(child.key)}
      </span>
    </li>`;
  }).join('');
  return `
    <h3 class="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-400">${childNoun}</h3>
    <ul class="mt-2 divide-y divide-stone-100 rounded-md border border-stone-200 bg-white">${rows}</ul>`;
}

function renderPane(statusHtml = '') {
  if (!selected) return;
  const node = selected;
  const crossLink = node.crossLink
    ? `<button id="crossLinkBtn" class="mt-1 text-xs text-indigo-600 hover:underline"
         data-key="participant:${node.crossLink.patientId}">
         See everything ${esc(node.crossLink.username)} has done, across all studies →
       </button>`
    : '';

  pane.innerHTML = `
    <div>
      <h2 class="text-lg font-semibold text-stone-900">${esc(node.name)}</h2>
      <p class="mt-0.5 text-sm text-stone-500">${esc(node.meta || '')}</p>
      ${crossLink}
    </div>
    ${reportCard(node, statusHtml)}
    ${childrenTable(node)}`;

  pane.querySelector('#generateBtn').addEventListener('click', generateSelected);
  pane.querySelectorAll('.child-select').forEach((button) => {
    button.addEventListener('click', () => select(button.dataset.key));
  });
  const crossBtn = pane.querySelector('#crossLinkBtn');
  if (crossBtn) crossBtn.addEventListener('click', () => select(crossBtn.dataset.key));
}

function select(key) {
  const node = findNode(key);
  if (!node) return;
  selected = node;
  // opening something in the rail should reveal where you are
  expanded.add(key);
  renderNav();
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

// --- tabs ---------------------------------------------------------------------

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

// --- boot ---------------------------------------------------------------------

(async function boot() {
  initTabs();
  initTemplatesTab();
  try {
    [tree] = await Promise.all([
      fetchJson('/api/v2/reports/navigator'),
      loadReports(),
    ]);
    select(keyOf('account', tree.provider_id));
  } catch (error) {
    nav.innerHTML = `<p class="px-2 text-sm text-red-600">Failed to load: ${esc(error.message)}</p>`;
  }
})();
