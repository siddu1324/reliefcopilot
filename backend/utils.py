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
