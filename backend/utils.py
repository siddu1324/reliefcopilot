import json, re
from typing import Dict, Any

def extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("No JSON found")
    raw = m.group(0)
    json.loads(raw)
    return raw

# --- Normalization ---
ALLOWED_PRIORITIES = {"p0": "P0", "p1": "P1", "p2": "P2", "high":"P0","medium":"P1","low":"P2"}
ALLOWED_ROLES = {"logistics":"Logistics","operations":"Operations","planning":"Planning","volunteers":"Volunteers"}
ROLE_MAP = {
  "wash":"Operations","hygiene":"Operations","shelter":"Operations","triage":"Operations","medical":"Operations",
  "security":"Operations","supply":"Logistics","transport":"Logistics","procure":"Logistics",
  "comms":"Planning","communication":"Planning","coordination":"Planning","volunteer":"Volunteers"
}

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
    norm=[]
    for i,t in enumerate(obj.get("tasks") or []):
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

# --- Safety lint ---
FORBIDDEN_PATTERNS = [r"\bdose\b", r"\bmg\b", r"\btablet\b", r"\bml\b", r"\biv\b", r"\bantibiotic"]
def safety_lint(plan_dict: Dict):
    text = json.dumps(plan_dict, ensure_ascii=False).lower()
    return ["Contains possible medical dosing/clinical language. Escalate to clinician."] \
           if any(re.search(p, text) for p in FORBIDDEN_PATTERNS) else []

# --- Enforce policies ---
def enforce_policies(plan: Dict) -> Dict:
    # Each task should have evidence or be tagged as assumption
    for t in plan.get("tasks", []):
        if not t.get("sphere_refs"):
            t.setdefault("sphere_refs", []).append("assumption:missing-evidence")
        # Bound timebox and normalize priority
        t["timebox_minutes"] = max(0, min(int(t.get("timebox_minutes", 0)), 180))
        if t.get("priority") not in {"P0", "P1", "P2"}:
            t["priority"] = "P1"
    return plan

# --- Scenario injectors ---
def ensure_heatwave_bundle(logs: str, plan: dict) -> dict:
    L= (logs or "").lower()
    heat = any(k in L for k in ["heat", "heat index", "hot", "dizziness"])
    if not heat: return plan
    titles = " ".join(t.get("title","").lower() for t in plan.get("tasks",[]))
    if "triage" not in titles:
        plan["tasks"].insert(0, {
            "id": "T-HEAT-TRIAGE",
            "title": "Triage & dizziness screening area",
            "why": "Heat stress risk",
            "priority": "P0",
            "owner_role": "Operations",
            "steps": ["Chairs in shade/ventilation","Screen dizziness/confusion","Escalate if no improvement"],
            "resources": ["Chairs","Shade/Fan","Water"],
            "timebox_minutes": 10,
            "dependencies": [],
            "risks": ["Delayed care"],
            "sphere_refs": ["who:heat_public_advice#auto"]
        })
    return plan

def ensure_protection_bundle(logs: str, plan: dict) -> dict:
    L= (logs or "").lower()
    need_light = any(k in L for k in ["light", "dark", "night"])
    children   = any(k in L for k in ["child", "unaccompanied"])
    wheelchair = any(k in L for k in ["wheelchair", "ramp", "accessible", "access"])
    titles = " ".join(t.get("title","").lower() for t in plan.get("tasks",[]))
    def add(task): plan["tasks"].append(task)
    if need_light and "lighting" not in titles:
        add({"id":"T-PROT-001","title":"Restore lighting on latrine routes","why":"Night safety near WASH",
             "priority":"P0","owner_role":"Operations","steps":["Place lanterns","Nightly checks"],
             "resources":["Lanterns","Batteries"],"timebox_minutes":15,"dependencies":[],
             "risks":["Trip hazards"],"sphere_refs":["fema:shelter_accessibility#lighting"]})
    if children and "safe space" not in titles:
        add({"id":"T-PROT-002","title":"Set up child-safe space & escort","why":"Unaccompanied children",
             "priority":"P0","owner_role":"Volunteers","steps":["Assign escorts","Mark safe corner/room"],
             "resources":["Signs","Roster"],"timebox_minutes":20,"dependencies":[],
             "risks":["Child separation"],"sphere_refs":["ifrc:volunteer_management#child"]})
    if wheelchair and "accessible route" not in titles:
        add({"id":"T-PROT-003","title":"Mark accessible routes to toilets & water","why":"Wheelchair users",
             "priority":"P0","owner_role":"Operations","steps":["Mark ramp path","Remove obstacles"],
             "resources":["Tape","Boards"],"timebox_minutes":15,"dependencies":[],
             "risks":["Blocked access"],"sphere_refs":["fema:shelter_accessibility#routes"]})
    return plan
