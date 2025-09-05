#!/usr/bin/env bash
set -euo pipefail

echo "==> Creating folders"
mkdir -p backend/corpus/{sphere,ics,who,fema} backend/data/index backend/tests

echo "==> Writing backend/ingest.py"
cat > backend/ingest.py <<'PY'
import json, hashlib
from pathlib import Path

ROOT = Path("backend/corpus")
OUT  = Path("backend/data/index")
OUT.mkdir(parents=True, exist_ok=True)

def chunk_text(t, max_chars=700, overlap=80):
    t = " ".join(t.split()); out=[]; i=0
    while i < len(t):
        j = min(i+max_chars, len(t))
        k = t.rfind(". ", i, j); k = j if k == -1 or (j-k)>200 else k+1
        out.append(t[i:k].strip()); i = max(k-overlap, k)
    return [c for c in out if c]

def fid(p: Path):
    return hashlib.sha1(str(p).encode()).hexdigest()[:8]

recs=[]
for p in sorted(ROOT.rglob("*.txt")):
    if not p.is_file(): 
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    for n,ch in enumerate(chunk_text(text)):
        recs.append({
          "id": f"{fid(p)}-{n:03d}",
          "domain": p.parts[-2],
          "source_title": p.stem.replace("_"," "),
          "source_path": str(p),
          "chunk": ch
        })

outp = OUT/"chunks.jsonl"
outp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
print(f"wrote {len(recs)} chunks -> {outp}")
PY

echo "==> Overwriting backend/rag.py"
cat > backend/rag.py <<'PY'
from pathlib import Path
import json, re
from rank_bm25 import BM25Okapi

class LocalRAG:
    """BM25 retriever over pre-built data/index/chunks.jsonl with citation tags."""
    def __init__(self, index_path="backend/data/index/chunks.jsonl"):
        path = Path(index_path)
        if not path.exists():
            # Fallback mini-guides if no index yet
            self.recs = [
                {"id":"guide-001","domain":"ics","source_title":"ics_201_intro","chunk":"ICS-201 brief: Situation, Objectives, Org, Resources, Safety, Comms."},
                {"id":"guide-002","domain":"sphere","source_title":"wash_minimums","chunk":"Safe water point; handwashing at critical points; sanitation distance; queue management; chlorine guidance."},
            ]
        else:
            self.recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        docs = [r["chunk"] for r in self.recs]
        self.tok = [re.findall(r"[a-z0-9]+", d.lower()) for d in docs]
        self.bm25 = BM25Okapi(self.tok)

    def _tok(self, s): 
        return re.findall(r"[a-z0-9]+", s.lower())

    def topk(self, query: str, k=5, prefer=("sphere","ics","who","fema","ifrc")):
        scores = self.bm25.get_scores(self._tok(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        cand = [self.recs[i] for i in order[:k*2]]
        cand.sort(key=lambda r: 0 if r["domain"] in prefer else 1)
        return cand[:k]

    def blurbs(self, recs):
        lines=[]
        for r in recs:
            tag = f"[{r['domain'].upper()} | {r['source_title']} | {r['id']}]"
            lines.append(f"{tag} {r['chunk']}")
        return "\n\n".join(lines)

    def cite_ids(self, recs):
        return [f"{r['domain']}:{r['source_title']}#{r['id']}" for r in recs]
PY

echo "==> Overwriting backend/prompts.py"
cat > backend/prompts.py <<'PY'
# Prompts for ReliefCopilot

ACTION_PLAN_SYSTEM = """You are ReliefCopilot.
Output ONLY a single JSON object with EXACTLY these keys:
incident, assumptions, tasks, comms, translations, evidence.
- Base recommendations on the provided "Context evidence".
- Cite the evidence by including its tags (e.g., SPHERE:wash_safe_water#abcd-000).
- If evidence is insufficient, add an explicit assumption.
- No medical dosing or prescriptions; use advice-not-directive wording for health.
"""

ACTION_PLAN_DEVELOPER = """JSON schema (keys/shape):
incident: {name: str, location: str}
assumptions: [str]
tasks: [{
  id: str, title: str, why: str, priority: 'P0'|'P1'|'P2',
  owner_role: 'Logistics'|'Operations'|'Planning'|'Volunteers',
  steps: [str], resources: [str], timebox_minutes: int,
  dependencies: [str], risks: [str], sphere_refs: [str]
}]
comms: {sms_updates: [str], pa_announcement: str}
translations: {hi:{summary:str}, te:{summary:str}}
evidence: [str]
Rules:
- Prefer fewer, high-impact tasks. Include dependencies if any.
- Each task SHOULD include a related evidence tag in sphere_refs OR mark 'assumption'.
"""

# Few-shot pair to anchor the JSON shape
ACTION_PLAN_FEWSHOT_USER = "50 people in a hall; low water; 2 elderly; hot weather; fans only."
ACTION_PLAN_FEWSHOT_ASSISTANT = """{
  "incident":{"name":"Community Hall","location":"Ward 1"},
  "assumptions":["Fans available"],
  "tasks":[
    {"id":"T-001","title":"Set up safe water point","why":"Low water","priority":"P0","owner_role":"Logistics",
     "steps":["Table at entrance","Queue lines","Chlorinated water"],
     "resources":["Table","Buckets","Soap"],"timebox_minutes":20,"dependencies":[],"risks":["Crowding"],"sphere_refs":["sphere:wash_safe_water#demo-000"]}],
  "comms":{"sms_updates":["Water point open 20 min"],"pa_announcement":"Queue calmly, handwash before water."},
  "translations":{"hi":{"summary":"20 मिनट में पानी बिंदु खुलेगा।"},"te":{"summary":"నీటి పాయింట్ 20 నిమిషాల్లో తెరుస్తాం."}},
  "evidence":["sphere:wash_safe_water#demo-000"]
}"""

def action_plan_user(log_text: str, evidence_blurbs: str, cite_ids: list[str]) -> str:
    return f"""Free-text field notes:
{log_text}

Context evidence (tagged):
{evidence_blurbs}

Constraints:
- Languages: EN, HI, TE
- Prioritize water safety, dry shelter, triage flow, vulnerable persons.
- Use evidence tags {", ".join(cite_ids)} in 'evidence' and in each task's 'sphere_refs' where relevant.
- Output EXACTLY the six required keys.
"""

# Briefing prompts (simple)
BRIEFING_SYSTEM = "You are ReliefCopilot and write a concise ICS-201 style briefing in markdown."
BRIEFING_DEVELOPER = "Sections: 1. Incident Overview, 2. Task Summary, 3. Resources, 4. Comms, 5. Translations (HI/TE), 6. Evidence."
def briefing_user(plan_json: str) -> str:
    return "Create a readable briefing based on this ActionPlan JSON:\n" + plan_json
PY

echo "==> Overwriting backend/utils.py"
cat > backend/utils.py <<'PY'
import json, re
from typing import Dict

def extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("No JSON found")
    raw = m.group(0)
    json.loads(raw)  # validate
    return raw

# --- normalization & safety ---
ALLOWED_PRIORITIES = {"p0": "P0", "p1": "P1", "p2": "P2", "high":"P0","medium":"P1","low":"P2"}
ALLOWED_ROLES = {"logistics":"Logistics","operations":"Operations","planning":"Planning","volunteers":"Volunteers"}
ROLE_MAP = {"wash":"Operations","hygiene":"Operations","shelter":"Operations","triage":"Operations","medical":"Operations",
            "security":"Operations","supply":"Logistics","transport":"Logistics","procure":"Logistics",
            "comms":"Planning","communication":"Planning","coordination":"Planning","volunteer":"Volunteers"}

def _norm_priority(v): 
    return ALLOWED_PRIORITIES.get(str(v).lower(), "P1")
def _norm_role(v):
    k=str(v).lower()
    if k in ALLOWED_ROLES: return ALLOWED_ROLES[k]
    for key,val in ROLE_MAP.items():
        if key in k: return val
    return "Operations"

def normalize_action_plan(obj: Dict) -> Dict:
    obj.setdefault("incident", {"name":"Unknown Incident","location":"Unknown"})
    obj.setdefault("assumptions", [])
    obj.setdefault("tasks", [])
    obj.setdefault("comms", {"sms_updates": [], "pa_announcement": ""})
    obj.setdefault("translations", {"hi":{"summary":""}, "te":{"summary":""}})
    obj.setdefault("evidence", [])
    tasks = obj.get("tasks") or []
    norm=[]
    for i,t in enumerate(tasks):
        t = t if isinstance(t,dict) else {"title": str(t)}
        t.setdefault("id", f"T-{i+1:03d}")
        t.setdefault("title","Untitled task")
        t.setdefault("why","")
        t["priority"] = _norm_priority(t.get("priority","P1"))
        t["owner_role"] = _norm_role(t.get("owner_role","Operations"))
        t.setdefault("steps", []); t.setdefault("resources", [])
        t.setdefault("timebox_minutes", 0); t.setdefault("dependencies", [])
        t.setdefault("risks", []); t.setdefault("sphere_refs", [])
        norm.append(t)
    obj["tasks"]=norm
    return obj

FORBIDDEN_PATTERNS = [r"\bdose\b", r"\bmg\b", r"\btablet\b", r"\bml\b"]
def safety_lint(plan_dict: Dict):
    text = json.dumps(plan_dict, ensure_ascii=False).lower()
    return ["Contains possible medical dosing language. Escalate to clinician."] \
           if any(re.search(p, text) for p in FORBIDDEN_PATTERNS) else []
PY

echo "==> Patching backend/app.py imports and handler"
# We only touch the parts we control; if this overwrite is too aggressive for your app.py, back it up first.
cp backend/app.py backend/app.py.bak

cat > backend/app.py <<'PY'
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from typing import Dict
import json

from rag import LocalRAG
from llm import chat
from prompts import (
    ACTION_PLAN_SYSTEM, ACTION_PLAN_DEVELOPER,
    ACTION_PLAN_FEWSHOT_USER, ACTION_PLAN_FEWSHOT_ASSISTANT,
    action_plan_user,
    BRIEFING_SYSTEM, BRIEFING_DEVELOPER, briefing_user
)
from schemas import ActionPlan, Briefing
from utils import extract_json, normalize_action_plan, safety_lint

app = FastAPI(title="ReliefCopilot")
app.mount("/static", StaticFiles(directory="static"), name="static")

rag = LocalRAG("backend/data/index/chunks.jsonl")

@app.get("/")
def root():
    return {"ok": True, "msg": "ReliefCopilot API running."}

@app.post("/plan")
def generate_plan(payload: Dict):
    logs = (payload.get("logs") or "").strip()
    if not logs:
        raise HTTPException(400, "Missing 'logs'")

    recs = rag.topk(logs, k=5)
    blurbs = rag.blurbs(recs)
    cite = rag.cite_ids(recs)

    messages = [
        {"role": "system", "content": ACTION_PLAN_SYSTEM},
        {"role": "developer", "content": ACTION_PLAN_DEVELOPER},
        {"role": "user", "content": ACTION_PLAN_FEWSHOT_USER},
        {"role": "assistant", "content": ACTION_PLAN_FEWSHOT_ASSISTANT},
        {"role": "user", "content": action_plan_user(logs, blurbs, cite)},
    ]
    raw = chat(messages, temperature=0.2)
    try:
        plan_json = extract_json(raw)
        obj = json.loads(plan_json)
        obj = normalize_action_plan(obj)
        plan = ActionPlan.model_validate(obj)
        out = plan.model_dump()
        warn = safety_lint(out)
        if warn: out["_warnings"] = warn
        return out
    except ValidationError as ve:
        raise HTTPException(500, f"Schema validation failed: {ve}") from ve
    except Exception as e:
        raise HTTPException(500, f"Parse error: {e}") from e

@app.post("/briefing")
def make_briefing(payload: Dict):
    plan = payload.get("plan")
    if not plan:
        raise HTTPException(400, "Missing 'plan'")
    plan_str = json.dumps(plan, ensure_ascii=False)
    messages = [
        {"role": "system", "content": BRIEFING_SYSTEM},
        {"role": "developer", "content": BRIEFING_DEVELOPER},
        {"role": "user", "content": briefing_user(plan_str)},
    ]
    text = chat(messages, temperature=0.2).strip()
    # return raw markdown (UI renders it)
    return {"briefing_text": text}
PY

echo "==> Extending frontend to show evidence/warnings"
# append or replace app.js section that renders summary (safe to overwrite for MVP)
# only replace if file exists
if [ -f backend/static/app.js ]; then
  python3 - <<'PY'
from pathlib import Path
p=Path("backend/static/app.js")
s=p.read_text()
s=s.replace(
  "return head + table + `<div class=\"chips\">${sms}${pa}</div>`;",
  """  const hi = plan.translations?.hi?.summary;
  const te = plan.translations?.te?.summary;
  const i18n = `
    <div class="i18n">
      ${hi ? `<div class="chip">HI: ${escapeHtml(hi)}</div>` : ''}
      ${te ? `<div class="chip">TE: ${escapeHtml(te)}</div>` : ''}
    </div>`;
  const ev = (plan.evidence || []).map(e => `<li>${escapeHtml(e)}</li>`).join('');
  const evidenceBlock = ev ? `<h3>Evidence</h3><ul>${ev}</ul>` : '';
  const warn = (plan._warnings || []).map(w => `<div class="chip" style="background:#712e2e;border-color:#a33">⚠️ ${escapeHtml(w)}</div>`).join('');
  return warn + head + table + `<div class="chips">${sms}${pa}</div>` + i18n + evidenceBlock;"""
)
p.write_text(s)
print("Patched backend/static/app.js")
PY
fi

echo "==> Adding tests"
cat > backend/tests/cases.jsonl <<'JSON'
{"name":"heatwave_hall","logs":"Heat index 44C; 120 ppl; fans only; 200L water; 30 elderly; 3 dizziness","must_have":["water","handwash","triage"],"forbid":["dose","tablet"]}
{"name":"cyclone_school","logs":"200 ppl school; roof leak; smell near latrine; no chlorine","must_have":["water","handwash","shelter"],"forbid":["dose"]}
JSON

cat > backend/tests/run_eval.py <<'PY'
import json, httpx, time
cases=[json.loads(l) for l in open("backend/tests/cases.jsonl")]
url="http://127.0.0.1:8000/plan"
res=[]
for c in cases:
  t=time.time()
  j = httpx.post(url, json={"logs": c["logs"]}).json()
  text=json.dumps(j).lower()
  ok = all(k in text for k in c["must_have"]) and not any(k in text for k in c["forbid"])
  res.append({"case":c["name"],"passed":ok,"latency_s":round(time.time()-t,2)})
print(json.dumps(res, indent=2))
PY

echo "==> Done."
