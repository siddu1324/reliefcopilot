import json, re
from typing import Any, Dict

RE_JSON = re.compile(r"\{.*\}", flags=re.S)

def extract_json(text: str) -> str:
    m = RE_JSON.search(text)
    if not m:
        raise ValueError("No JSON found")
    raw = m.group(0)
    json.loads(raw)  # validate shape is JSON
    return raw

REMAP_TASK_KEYS = {
    "action_items": "tasks",
    "actions": "tasks",
    "steps": "tasks",
}
REMAP_TOPLEVEL = {
    "plan": None,      # unwrap container if present
    "result": None,
    "data": None,
}

# Allowed schema values
ALLOWED_ROLES = {"logistics": "Logistics",
                 "operations": "Operations",
                 "planning": "Planning",
                 "volunteers": "Volunteers"}

# Common role aliases coming from the model → map to our four buckets
ROLE_MAP = {
    "hygiene": "Operations",
    "wash": "Operations",
    "water": "Operations",
    "shelter": "Operations",
    "triage": "Operations",
    "medical": "Operations",
    "security": "Operations",
    "safety": "Operations",
    "supply": "Logistics",
    "supplies": "Logistics",
    "procurement": "Logistics",
    "transport": "Logistics",
    "comms": "Planning",
    "communication": "Planning",
    "documentation": "Planning",
    "coordination": "Planning",
    "volunteer": "Volunteers",
    "volunteers": "Volunteers",
}

# Priority normalization
ALLOWED_PRIORITIES = {"p0": "P0", "p1": "P1", "p2": "P2", "high": "P0", "medium": "P1", "low": "P2"}

def _ensure_dict(obj: Any) -> Dict:
    if isinstance(obj, dict): return obj
    raise ValueError("Top-level JSON is not an object")

def _norm_priority(val: Any) -> str:
    if not isinstance(val, str):
        return "P1"
    key = val.strip().lower()
    return ALLOWED_PRIORITIES.get(key, "P1")

def _norm_role(val: Any) -> str:
    """
    Map arbitrary role strings to one of: Logistics, Operations, Planning, Volunteers.
    Default to Operations if unclear.
    """
    if not isinstance(val, str):
        return "Operations"
    key = val.strip().lower()
    if key in ALLOWED_ROLES:
        return ALLOWED_ROLES[key]
    # try alias map and some heuristics
    if key in ROLE_MAP:
        return ROLE_MAP[key]
    # heuristic keywords
    if any(k in key for k in ["wash", "shelter", "triage", "hygiene", "medical", "security"]):
        return "Operations"
    if any(k in key for k in ["supply", "suppl", "procure", "transport", "logist"]):
        return "Logistics"
    if any(k in key for k in ["plan", "coord", "comm", "docu"]):
        return "Planning"
    if "volun" in key:
        return "Volunteers"
    return "Operations"

def normalize_action_plan(obj: Dict) -> Dict:
    """
    Coerce common variants into the ActionPlan schema:
      - Unwrap if everything is under {"plan": {...}} or similar
      - Rename task containers (actions/action_items/steps -> tasks)
      - Create minimal incident/comms if missing
      - Normalize task fields (owner_role, priority, optional lists)
    """
    obj = _ensure_dict(obj)

    # Unwrap level
    for k in list(obj.keys()):
        if k in REMAP_TOPLEVEL and isinstance(obj[k], dict):
            obj = obj[k]
            break

    # Rename task container if needed
    for wrong, right in REMAP_TASK_KEYS.items():
        if wrong in obj and "tasks" not in obj and isinstance(obj[wrong], list):
            obj["tasks"] = obj.pop(wrong)

    # Ensure required keys exist
    obj.setdefault("incident", {"name": "Unknown Incident", "location": "Unknown"})
    obj.setdefault("assumptions", [])
    obj.setdefault("tasks", [])
    obj.setdefault("comms", {"sms_updates": [], "pa_announcement": ""})
    obj.setdefault("translations", {"hi": {"summary": ""}, "te": {"summary": ""}})
    obj.setdefault("evidence", [])

    # Normalize each task
    tasks = obj.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            tasks[i] = {
                "id": f"T-{i+1:03d}",
                "title": str(t),
                "why": "",
                "priority": "P1",
                "owner_role": "Operations",
                "steps": [],
                "resources": [],
                "timebox_minutes": 0,
                "dependencies": [],
                "risks": [],
                "sphere_refs": [],
            }
            continue

        t.setdefault("id", f"T-{i+1:03d}")
        t.setdefault("title", "Untitled task")
        t.setdefault("why", "")
        t["priority"] = _norm_priority(t.get("priority", "P1"))
        t["owner_role"] = _norm_role(t.get("owner_role", "Operations"))
        t.setdefault("steps", [])
        t.setdefault("resources", [])
        t.setdefault("timebox_minutes", 0)
        t.setdefault("dependencies", [])
        t.setdefault("risks", [])
        t.setdefault("sphere_refs", [])

    obj["tasks"] = tasks
    return obj
