// Templates tab: list + editor with availability-aware component checkboxes.
// Intensive components render greyed with a "Request access" affordance until
// the admin grants them — the analysis library is visible, the compute gated.

const esc = (s) => window.escapeHtml ? window.escapeHtml(String(s)) : String(s);

const PARTICIPANT_VISIBLE_SCOPES = ['conversation', 'window', 'enrollment'];

let registry = null;   // {scopes, components:[{key,label,scopes,cost,access}]}
let flows = [];        // [{flow_id, name}]
let templates = [];
let editing = null;    // template object or {} for new

const listEl = () => document.getElementById('templateList');
const paneEl = () => document.getElementById('templatePane');

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).message || detail; } catch { /* html error page */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

const postJson = (url, body, method = 'POST') => fetchJson(url, {
  method, headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

async function reload() {
  [registry, templates] = await Promise.all([
    fetchJson('/api/v2/reports/registry'),
    fetchJson('/api/v2/report-templates'),
  ]);
  const navigator = await fetchJson('/api/v2/reports/navigator');
  flows = navigator.flows.map((f) => ({ flow_id: f.flow_id, name: f.name }));
  renderList();
}

function renderList() {
  listEl().innerHTML = templates.map((t) => `
    <button class="tpl-item flex w-full items-center justify-between rounded px-2 py-1.5 text-left hover:bg-stone-100"
        data-id="${t.id}">
      <span class="truncate">${esc(t.name)}</span>
      <span class="flex items-center gap-1">
        ${t.is_system ? '<span class="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] text-sky-800">system</span>' : ''}
        <span class="text-[10px] uppercase text-stone-400">${esc(t.scope)}</span>
      </span>
    </button>`).join('')
    || '<p class="px-2 text-xs text-stone-400">No templates yet.</p>';
  listEl().querySelectorAll('.tpl-item').forEach((item) => {
    item.addEventListener('click', () => {
      editing = templates.find((t) => t.id === Number(item.dataset.id));
      renderEditor();
    });
  });
}

function componentRow(component, checkedKeys) {
  const usable = component.access === 'available' || component.access === 'granted';
  const checked = checkedKeys === null || checkedKeys.includes(component.key);
  const scopeNote = component.scopes.join(', ');
  let gate = '';
  if (!usable) {
    gate = component.access === 'requested'
      ? '<span class="text-xs text-amber-700">access requested — awaiting admin</span>'
      : `<button type="button" class="request-access text-xs text-indigo-600 hover:underline"
           data-key="${component.key}">Request access</button>`;
  }
  return `<label class="flex items-start gap-2 rounded border border-stone-100 p-2 ${usable ? '' : 'opacity-60'}">
    <input type="checkbox" name="component" value="${component.key}"
      ${checked && usable ? 'checked' : ''} ${usable ? '' : 'disabled'} class="mt-0.5">
    <span class="min-w-0 flex-1">
      <span class="flex items-center gap-2 text-sm text-stone-800">
        ${esc(component.label)}
        ${component.cost === 'intensive'
          ? '<span class="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] text-violet-800">intensive</span>' : ''}
      </span>
      <span class="block text-xs text-stone-400">scopes: ${esc(scopeNote)}</span>
    </span>
    ${gate}
  </label>`;
}

function renderEditor() {
  const t = editing;
  const isNew = !t.id;
  const readOnly = t.is_system;
  const checkedKeys = t.components || null;

  paneEl().innerHTML = `
    <form id="tplForm" class="space-y-4">
      ${readOnly ? '<p class="rounded bg-sky-50 px-3 py-2 text-xs text-sky-800">System template — usable in your reports, editable only by admins.</p>' : ''}
      <div>
        <label class="text-xs font-semibold uppercase text-stone-500">Name</label>
        <input name="name" value="${esc(t.name || '')}" ${readOnly ? 'disabled' : ''}
          class="mt-1 w-full rounded-md border border-stone-200 px-3 py-2 text-sm" required>
      </div>
      <div class="flex flex-wrap gap-4">
        <div>
          <label class="text-xs font-semibold uppercase text-stone-500">Scope</label>
          <select name="scope" ${readOnly ? 'disabled' : ''}
            class="mt-1 rounded-md border border-stone-200 px-3 py-2 text-sm">
            ${registry.scopes.map((s) =>
              `<option value="${s}" ${t.scope === s ? 'selected' : ''}>${s}</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="text-xs font-semibold uppercase text-stone-500">Study flow</label>
          <select name="flow_id" ${readOnly ? 'disabled' : ''}
            class="mt-1 rounded-md border border-stone-200 px-3 py-2 text-sm">
            <option value="">Any (provider-wide)</option>
            ${flows.map((f) =>
              `<option value="${f.flow_id}" ${t.flow_id === f.flow_id ? 'selected' : ''}>${esc(f.name)}</option>`).join('')}
          </select>
        </div>
      </div>
      <div>
        <label class="text-xs font-semibold uppercase text-stone-500">Analyses</label>
        <p class="mb-2 mt-0.5 text-xs text-stone-400">Unchecked = all available analyses for the scope. Intensive analyses need a one-time admin grant.</p>
        <div id="componentGrid" class="grid gap-2 sm:grid-cols-2">
          ${registry.components.map((c) => componentRow(c, checkedKeys)).join('')}
        </div>
      </div>
      <div class="flex flex-wrap gap-6 text-sm">
        <label class="flex items-center gap-2">
          <input type="checkbox" name="auto_generate" ${t.auto_generate ? 'checked' : ''} ${readOnly ? 'disabled' : ''}>
          Auto-generate when a phase ends
        </label>
        <label class="flex items-center gap-2" id="visibleWrap">
          <input type="checkbox" name="participant_visible" ${t.participant_visible ? 'checked' : ''} ${readOnly ? 'disabled' : ''}>
          Participants can view
          <span class="text-xs text-stone-400">(conversation/window/enrollment scopes only)</span>
        </label>
      </div>
      <div id="tplStatus" class="hidden rounded-md px-3 py-2 text-sm"></div>
      ${readOnly ? '' : `
      <div class="flex items-center gap-2">
        <button type="submit" class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          ${isNew ? 'Create template' : 'Save changes'}
        </button>
        ${isNew ? '' : `<button type="button" id="tplDelete"
          class="rounded-md border border-red-200 px-4 py-2 text-sm text-red-700 hover:bg-red-50">Delete</button>`}
      </div>`}
    </form>`;

  const form = document.getElementById('tplForm');
  const status = document.getElementById('tplStatus');

  const showStatus = (message, ok) => {
    status.className = `rounded-md px-3 py-2 text-sm ${ok
      ? 'border border-emerald-200 bg-emerald-50 text-emerald-800'
      : 'border border-red-200 bg-red-50 text-red-800'}`;
    status.textContent = message;
    status.classList.remove('hidden');
  };

  form.querySelectorAll('.request-access').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        await postJson('/api/v2/reports/component-requests',
                       { component: button.dataset.key });
        registry = await fetchJson('/api/v2/reports/registry');
        renderEditor();
      } catch (error) { showStatus(`Request failed: ${error.message}`, false); }
    });
  });

  if (readOnly) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const componentBoxes = [...form.querySelectorAll('input[name=component]')];
    const checkedBoxes = componentBoxes.filter((b) => b.checked);
    const body = {
      name: data.get('name'),
      scope: data.get('scope'),
      flow_id: data.get('flow_id') ? Number(data.get('flow_id')) : null,
      // all enabled boxes checked → treat as "all for scope" (null)
      components: checkedBoxes.length &&
        checkedBoxes.length < componentBoxes.filter((b) => !b.disabled).length
        ? checkedBoxes.map((b) => b.value) : null,
      auto_generate: form.auto_generate.checked,
      participant_visible: form.participant_visible.checked,
    };
    if (body.participant_visible && !PARTICIPANT_VISIBLE_SCOPES.includes(body.scope)) {
      showStatus('Participant visibility is only allowed for conversation, window, or enrollment scopes.', false);
      return;
    }
    try {
      if (editing.id) {
        editing = await postJson(`/api/v2/report-templates/${editing.id}`, body, 'PUT');
        showStatus('Saved.', true);
      } else {
        editing = await postJson('/api/v2/report-templates', body);
        showStatus('Created.', true);
      }
      templates = await fetchJson('/api/v2/report-templates');
      renderList();
    } catch (error) { showStatus(`Save failed: ${error.message}`, false); }
  });

  const deleteBtn = document.getElementById('tplDelete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      const confirmed = window.showDialog
        ? await window.showDialog({ title: 'Delete template?',
            message: `Delete "${editing.name}"? Existing reports keep their content.`,
            confirmText: 'Delete', danger: true })
        : window.confirm('Delete template?');
      if (!confirmed) return;
      try {
        await fetchJson(`/api/v2/report-templates/${editing.id}`, {
          method: 'DELETE', headers: { 'Content-Type': 'application/json' } });
        editing = null;
        templates = await fetchJson('/api/v2/report-templates');
        renderList();
        paneEl().innerHTML = '<p class="text-sm text-stone-400">Template deleted.</p>';
      } catch (error) { showStatus(`Delete failed: ${error.message}`, false); }
    });
  }
}

export function initTemplatesTab() {
  document.getElementById('newTemplateBtn').addEventListener('click', () => {
    editing = { scope: 'window', flow_id: null, components: null,
                auto_generate: false, participant_visible: false };
    renderEditor();
  });
  reload().catch((error) => {
    listEl().innerHTML = `<p class="px-2 text-sm text-red-600">Failed to load: ${esc(error.message)}</p>`;
  });
}
