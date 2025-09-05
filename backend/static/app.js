const logsEl = document.getElementById('logs');
const planRawEl = document.getElementById('planRaw');
const planSummaryEl = document.getElementById('planSummary');
const briefBtn = document.getElementById('btnBrief');
const briefingHtmlEl = document.getElementById('briefingHtml');
const briefingRawEl = document.getElementById('briefingRaw');

let lastPlan = null;

// --- helpers ---
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// very tiny markdown → html (bold, headings, lists, code blocks)
function miniMarkdown(md) {
  let html = md;
  // code blocks ``` ```
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre>${escapeHtml(code)}</pre>`);
  // headings ###, ##, #
  html = html.replace(/^###\s?(.*)$/gm, '<h3>$1</h3>')
             .replace(/^##\s?(.*)$/gm, '<h2>$1</h2>')
             .replace(/^#\s?(.*)$/gm, '<h1>$1</h1>');
  // bold **text**
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // lists
  html = html.replace(/^\s*-\s+(.*)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
  // line breaks
  html = html.replace(/\n{2,}/g, '</p><p>').replace(/\n/g,'<br>');
  return `<p>${html}</p>`;
}

function renderPlanSummary(plan) {
  // top box
  const head =
    `<div class="pillrow">
       <span class="pill"><strong>Incident:</strong> ${escapeHtml(plan.incident?.name || '—')}</span>
       <span class="pill"><strong>Location:</strong> ${escapeHtml(plan.incident?.location || '—')}</span>
     </div>`;

  // task table
  const rows = (plan.tasks || []).map(t => {
    const dep = (t.dependencies||[]).join(', ') || '—';
    return `<tr>
      <td>${escapeHtml(t.id||'')}</td>
      <td>${escapeHtml(t.title||'')}</td>
      <td>${escapeHtml(t.owner_role||'')}</td>
      <td>${escapeHtml(t.priority||'')}</td>
      <td>${t.timebox_minutes ?? 0} min</td>
      <td>${escapeHtml(dep)}</td>
    </tr>`;
  }).join('');

  const table = `
    <table class="tasks">
      <thead><tr>
        <th>ID</th><th>Title</th><th>Owner</th><th>Priority</th><th>Timebox</th><th>Deps</th>
      </tr></thead>
      <tbody>${rows || '<tr><td colspan="6">No tasks</td></tr>'}</tbody>
    </table>`;

  // comms chips
  const sms = (plan.comms?.sms_updates || []).map(s => `<div class="chip">SMS: ${escapeHtml(s)}</div>`).join('');
  const pa = plan.comms?.pa_announcement ? `<div class="chip">PA: ${escapeHtml(plan.comms.pa_announcement)}</div>` : '';

    const hi = plan.translations?.hi?.summary;
  const te = plan.translations?.te?.summary;
  const i18n = `
    <div class="i18n">
      ${hi ? `<div class="chip">HI: ${escapeHtml(hi)}</div>` : ''}
      ${te ? `<div class="chip">TE: ${escapeHtml(te)}</div>` : ''}
    </div>`;
  const ev = (plan.evidence || []).map(e => `<li>${escapeHtml(e)}</li>`).join('');
  const evidenceBlock = ev ? `<h3>Evidence</h3><ul>${ev}</ul>` : '';
  const warn = (plan._warnings || []).map(w => `<div class="chip" style="background:#712e2e;border-color:#a33">⚠️ ${escapeHtml(w)}</div>`).join('');
  return warn + head + table + `<div class="chips">${sms}${pa}</div>` + i18n + evidenceBlock;
}

// --- actions ---
document.getElementById('btnPlan').onclick = async () => {
  planSummaryEl.innerHTML = '<div class="muted">Working…</div>';
  planRawEl.textContent = '';
  briefingHtmlEl.innerHTML = '';
  briefingRawEl.textContent = '';
  briefBtn.disabled = true;

  const r = await fetch('/plan', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({logs: logsEl.value})
  });

  const j = await r.json();
  lastPlan = j;

  // summary + raw
  planSummaryEl.innerHTML = renderPlanSummary(j);
  planRawEl.textContent = JSON.stringify(j, null, 2);
  briefBtn.disabled = false;
};

briefBtn.onclick = async () => {
  if (!lastPlan) return;
  briefingHtmlEl.innerHTML = '<div class="muted">Building briefing…</div>';
  briefingRawEl.textContent = '';

  const r = await fetch('/briefing', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({plan: lastPlan})
  });
  const j = await r.json();

  const raw = j.briefing_text || j.raw_briefing || JSON.stringify(j, null, 2);
  briefingRawEl.textContent = raw;
  briefingHtmlEl.innerHTML = miniMarkdown(raw);
};

// clipboard/download/print
document.getElementById('btnCopy').onclick = () => {
  if (!lastPlan) return;
  navigator.clipboard?.writeText(JSON.stringify(lastPlan, null, 2));
};

document.getElementById('btnDownload').onclick = () => {
  if (!lastPlan) return;
  const blob = new Blob([JSON.stringify(lastPlan, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `action_plan_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
};

document.getElementById('btnPrint').onclick = () => {
  // print only the briefing card
  const win = window.open('', '_blank');
  const html = `
    <html><head>
      <meta charset="utf-8">
      <title>Briefing</title>
      <style>
        body { font-family: system-ui, sans-serif; margin: 24px; }
        h1,h2,h3 { margin: 0 0 8px; }
        .prose p { line-height: 1.4; }
        pre { background: #0e1116; color:#d1d5db; padding:12px; border-radius:8px; }
      </style>
    </head><body>
      <h2>ICS-201 Briefing</h2>
      <div class="prose">${briefingHtmlEl.innerHTML || '<em>No briefing yet</em>'}</div>
    </body></html>`;
  win.document.write(html);
  win.document.close();
  win.focus();
  win.print();
  // win.close(); // optionally close after printing
};
