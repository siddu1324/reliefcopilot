// backend/static/app.js

const $ = (s) => document.querySelector(s);
const api = (p, body) =>
  fetch(p, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => r.json());

// ---------- helpers ----------
const escapeHtml = (s) =>
  (s ?? "").toString().replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[m]);

// tiny JSON viewer
function jsonTree(node) {
  if (node === null) return '<span class="n">null</span>';
  if (Array.isArray(node)) return `[${node.map(jsonTree).join(", ")}]`;
  switch (typeof node) {
    case "string":
      return `<span class="s">"${escapeHtml(node)}"</span>`;
    case "number":
    case "boolean":
      return `<span class="n">${node}</span>`;
    case "object":
      return (
        '{<div style="padding-left:14px">' +
        Object.entries(node)
          .map(
            ([k, v]) =>
              `<div><span class="k">"${escapeHtml(k)}"</span>: ${jsonTree(v)}</div>`
          )
          .join("") +
        "</div>}"
      );
    default:
      return String(node);
  }
}

function evidenceLabel(tag) {
  const m = String(tag).match(/^([^:]+):([^#]+)#(.+)$/);
  if (!m) return tag;
  return `${m[1].toUpperCase()} • ${m[2].replace(/_/g, " ")} (${m[3].slice(
    0,
    8
  )})`;
}

// ---------- Action Plan rendering ----------
function renderTasks(tasks) {
  return `<table class="table">
    <thead><tr><th>ID</th><th>Title</th><th>Owner</th><th>Priority</th><th>Timebox</th><th>Deps</th></tr></thead>
    <tbody>${(tasks || [])
      .map(
        (t) => `
      <tr>
        <td>${escapeHtml(t.id || "")}</td>
        <td>${escapeHtml(t.title || "")}</td>
        <td>${escapeHtml(t.owner_role || "")}</td>
        <td class="p-${escapeHtml(t.priority || "P1")}">${escapeHtml(
          t.priority || ""
        )}</td>
        <td>${escapeHtml(String(t.timebox_minutes || 0))} min</td>
        <td>${escapeHtml((t.dependencies || []).join(", ") || "—")}</td>
      </tr>`
      )
      .join("")}
    </tbody></table>`;
}

function renderPlan(plan) {
  if (plan.error)
    return `<div class="chip warn">LLM error: ${escapeHtml(plan.error)}</div>`;

  const inc = plan.incident || {};
  const chips = [];
  for (const s of plan.comms?.sms_updates || [])
    chips.push(`<span class="chip">SMS: ${escapeHtml(s)}</span>`);
  if (plan.comms?.pa_announcement)
    chips.push(
      `<span class="chip">PA: ${escapeHtml(plan.comms.pa_announcement)}</span>`
    );
  if (plan.translations?.hi?.summary)
    chips.push(
      `<span class="chip">HI: ${escapeHtml(plan.translations.hi.summary)}</span>`
    );
  if (plan.translations?.te?.summary)
    chips.push(
      `<span class="chip">TE: ${escapeHtml(plan.translations.te.summary)}</span>`
    );

  const ev = (plan.evidence || [])
    .map((e) => `<li>${escapeHtml(evidenceLabel(e))}</li>`)
    .join("");
  const warn = (plan._warnings || [])
    .map((w) => `<span class="chip warn">⚠ ${escapeHtml(w)}</span>`)
    .join("");

  // scenario badge (if provided by backend)
  if (plan._matched_risks && $("#scenarioBadge")) {
    $("#scenarioBadge").textContent = `Risks: ${plan._matched_risks}`;
    $("#scenarioBadge").style.display = "inline-block";
  }

  return `
    <div class="chips">
      <span class="badge">Incident: ${escapeHtml(inc.name || "")}</span>
      <span class="badge">Location: ${escapeHtml(inc.location || "")}</span>
    </div>
    ${renderTasks(plan.tasks)}
    <div class="chips">${chips.join("")}${warn}</div>
    ${ev ? `<div class="evidence"><h3>Evidence</h3><ul>${ev}</ul></div>` : ""}
  `;
}

// ---------- Minimal Markdown → HTML for Briefing ----------
function mdToHtml(src) {
  if (!src) return "";
  // escape HTML
  let s = String(src).replace(/[&<>]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
  s = s.replace(/\r\n?/g, "\n");

  // table blocks
  const lines = s.split("\n");
  let out = [];
  let i = 0;
  while (i < lines.length) {
    if (/\|/.test(lines[i])) {
      const block = [];
      while (i < lines.length && /\|/.test(lines[i])) block.push(lines[i++]);
      const rows = block.filter((ln, idx) => !(idx === 1 && /^\s*\|?\s*:?-{3,}/.test(ln)));
      const cells = rows.map((r) =>
        r.replace(/^\s*\|?|\|?\s*$/g, "").split("|").map((c) => c.trim())
      );
      if (cells.length) {
        const thead = cells[0];
        out.push("<table><thead><tr>" + thead.map((h) => `<th>${h}</th>`).join("") + "</tr></thead>");
        if (cells.length > 1) {
          out.push("<tbody>");
          for (let r = 1; r < cells.length; r++)
            out.push("<tr>" + cells[r].map((c) => `<td>${c || ""}</td>`).join("") + "</tr>");
          out.push("</tbody>");
        }
        out.push("</table>");
      }
      continue;
    }
    out.push(lines[i++]);
  }
  s = out.join("\n");

  // headings, rules, bold, bullets
  s = s
    .replace(/^###\s+(.*)$/gm, "<h3>$1</h3>")
    .replace(/^##\s+(.*)$/gm, "<h2>$1</h2>")
    .replace(/^#\s+(.*)$/gm, "<h1>$1</h1>")
    .replace(/^---\s*$/gm, "<hr/>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(?:^|\n)(-\s+.+(?:\n-\s+.+)*)/g, (m) => {
      const items = m
        .trim()
        .split("\n")
        .map((l) => l.replace(/-\s+/, ""))
        .map((t) => `<li>${t}</li>`)
        .join("");
      return `\n<ul>${items}</ul>`;
    });

  // paragraph fallback
  s = s.replace(/(^|\n)([^<\n][^\n]*)/g, (m, p1, p2) => {
    if (/^\s*<(h1|h2|h3|ul|li|table|tr|th|td|hr)/i.test(p2)) return m;
    const txt = p2.trim();
    return txt ? `${p1}<p>${txt}</p>` : m;
  });

  return s;
}

// ---------- actions ----------
let LAST_PLAN = null;

async function generate() {
  const logs = $("#logs").value;
  const mode = $("#mode").value;
  $("#planOut").innerHTML = "…generating…";
  const plan = await api("/plan", { logs, mode });
  LAST_PLAN = plan;
  $("#planOut").innerHTML = renderPlan(plan);
  $("#jsonTree").innerHTML = jsonTree(plan);
}

async function makeBrief() {
  // if user hasn’t generated yet, do it once
  if (!LAST_PLAN) await generate();

  $("#briefOut").innerHTML = '<div class="chip">…building briefing…</div>';

  try {
    const b = await api("/briefing", { plan: LAST_PLAN });
    const text =
      (b && (b.briefing_text || b.raw_briefing || b.text || b.briefing)) || "";

    if (!text.trim()) {
      $("#briefOut").innerHTML =
        '<div class="chip warn">No briefing text returned.</div>' +
        '<pre class="mono" style="white-space:pre-wrap;">' +
        escapeHtml(JSON.stringify(b, null, 2)) +
        "</pre>";
      return;
    }

    // Build the tabs & views (no inline script)
    const container = $("#briefOut");
    container.innerHTML = `
      <div class="toolbar">
        <button class="tab" data-view="rendered">Rendered</button>
        <button class="tab" data-view="raw">Raw</button>
        <button class="tab" data-view="json">JSON</button>
      </div>
      <div id="brief-rendered" class="markdown"></div>
      <pre id="brief-raw" class="mono" style="display:none;white-space:pre-wrap;"></pre>
      <pre id="brief-json" class="mono" style="display:none;"></pre>
    `;

    $("#brief-rendered").innerHTML = mdToHtml(text.trim());
    $("#brief-raw").textContent = text.trim();
    $("#brief-json").textContent = JSON.stringify(
      { briefing_text: text.trim() },
      null,
      2
    );

    const show = (v) => {
      $("#brief-rendered").style.display = v === "rendered" ? "block" : "none";
      $("#brief-raw").style.display = v === "raw" ? "block" : "none";
      $("#brief-json").style.display = v === "json" ? "block" : "none";
    };
    container.querySelectorAll(".tab").forEach((btn) => {
      btn.onclick = () => show(btn.dataset.view);
    });
    show("rendered");
  } catch (err) {
    $("#briefOut").innerHTML =
      '<div class="chip warn">Briefing request failed.</div>' +
      '<pre class="mono" style="white-space:pre-wrap;">' +
      escapeHtml(String(err)) +
      "</pre>";
  }
}

// buttons
$("#gen").onclick = generate;
$("#brief").onclick = makeBrief;

// toolbar
$("#copyPlan").onclick = () => {
  const txt = $("#planOut").innerText;
  navigator.clipboard.writeText(txt);
};
$("#downloadJson").onclick = () => {
  const plan = LAST_PLAN || {};
  const blob = new Blob([JSON.stringify(plan, null, 2)], {
    type: "application/json",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "action_plan.json";
  a.click();
};
$("#printBriefing").onclick = () => window.print();

// theme toggle + remember
const storedTheme =
  localStorage.getItem("theme") ||
  (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
document.body.setAttribute("data-theme", storedTheme);
$("#themeToggle")?.addEventListener("click", () => {
  const next =
    document.body.getAttribute("data-theme") === "dark" ? "light" : "dark";
  document.body.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
});
