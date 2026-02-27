/* shared.js — Cloze common utilities
   Loaded by base.html on all authenticated pages. */

// ── Text helpers ──────────────────────────────────────────────

function escapeHtml(s) {
  if (!s) return '';
  return s.replace(/[&<>"'`=\/]/g, function (ch) {
    return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;',
             "'":'&#39;', '`':'&#96;', '=':'&#61;', '/':'&#47;' }[ch] || ch;
  });
}

function highlight(text, query) {
  if (!text || !query) return escapeHtml(text || '');
  var i = text.toLowerCase().indexOf(query.toLowerCase());
  if (i === -1) return escapeHtml(text);
  var before = escapeHtml(text.slice(0, i));
  var match  = escapeHtml(text.slice(i, i + query.length));
  var after  = escapeHtml(text.slice(i + query.length));
  return before + '<mark class="rounded bg-amber-100 px-0.5">' + match + '</mark>' + after;
}

function snippet(text, query, radius) {
  radius = radius || 40;
  var t = text || '';
  var q = (query || '').toLowerCase();
  var i = t.toLowerCase().indexOf(q);
  if (i === -1) return escapeHtml(t.slice(0, radius * 2));
  var start = Math.max(0, i - radius);
  var end   = Math.min(t.length, i + q.length + radius);
  var pre = start > 0 ? '\u2026' : '';
  var suf = end < t.length ? '\u2026' : '';
  return pre + highlight(t.slice(start, end), query) + suf;
}

// ── Date / time formatting ────────────────────────────────────

function formatDate(timestamp) {
  if (!timestamp) return '\u2014';
  var d = new Date(timestamp * 1000);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(timestamp) {
  if (!timestamp) return '\u2014';
  var d = new Date(timestamp * 1000);
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function formatRelativeTime(timestamp) {
  if (!timestamp) return '\u2014';
  var now = Date.now() / 1000;
  var diff = now - timestamp;
  if (diff < 3600) {
    var mins = Math.max(1, Math.floor(diff / 60));
    return mins + ' min' + (mins !== 1 ? 's' : '') + ' ago';
  } else if (diff < 86400) {
    var hours = Math.floor(diff / 3600);
    return hours + ' hour' + (hours !== 1 ? 's' : '') + ' ago';
  } else {
    var days = Math.floor(diff / 86400);
    return days + ' day' + (days !== 1 ? 's' : '') + ' ago';
  }
}

// ── Status constants ──────────────────────────────────────────

var STATUS_LABELS = {
  scheduled:         'Scheduled',
  active:            'Active',
  generating_report: 'Generating Report',
  report_ready:      'Report Ready'
};

var STATUS_CLASSES = {
  scheduled:         'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200',
  active:            'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200',
  generating_report: 'bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-200',
  report_ready:      'bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200'
};

// ── Auth ──────────────────────────────────────────────────────

async function logout() {
  await fetch('/logout');
  window.location.href = '/login';
}

// ── Sidebar toggle (mobile) ──────────────────────────────────

(function initSidebar() {
  var menuBtn = document.getElementById('menuBtn');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('overlay');

  if (!menuBtn || !sidebar) return;

  function openSide() {
    sidebar.classList.remove('-translate-x-full');
    if (overlay) overlay.classList.remove('hidden');
  }
  function closeSide() {
    sidebar.classList.add('-translate-x-full');
    if (overlay) overlay.classList.add('hidden');
  }

  menuBtn.addEventListener('click', function () {
    sidebar.classList.contains('-translate-x-full') ? openSide() : closeSide();
  });
  if (overlay) overlay.addEventListener('click', closeSide);
  if (window.innerWidth >= 1024) sidebar.classList.remove('-translate-x-full');
})();

// ── Active nav link highlighting ─────────────────────────────

(function markActive() {
  var path = location.pathname.replace(/\/+$/, '');
  var hash = location.hash || '';
  var fullUrl = path + hash;
  document.querySelectorAll('#sidebar a[href]').forEach(function (a) {
    var href = a.getAttribute('href').replace(/\/+$/, '');
    // For hash-based links (e.g. /admin/dashboard#patients), match exactly
    var isMatch = false;
    if (href.indexOf('#') !== -1) {
      isMatch = (href === fullUrl);
    } else {
      isMatch = href && (href === path || (href !== '/' && path.startsWith(href)));
    }
    if (isMatch) {
      a.classList.remove('text-stone-600', 'hover:bg-violet-50');
      a.classList.add('bg-cloze-lavender', 'text-cloze-indigo', 'font-medium');
      var icon = a.querySelector('svg');
      if (icon) {
        icon.classList.remove('text-stone-400');
        icon.classList.add('text-cloze-indigo');
      }
    }
  });
})();
