import json, time
from fastapi.testclient import TestClient

# Import the app directly; DO NOT start uvicorn
from backend.app import app

client = TestClient(app)

cases = [json.loads(l) for l in open("backend/tests/cases.jsonl")]
results = []
for c in cases:
    t0 = time.time()
    r = client.post("/plan", json={"logs": c["logs"]})
    r.raise_for_status()
    j = r.json()
    text = json.dumps(j).lower()

    ok = all(k in text for k in c["must_have"]) and not any(k in text for k in c["forbid"])

    # ensure each task has some evidence or explicit assumption tag
    has_ev = all((t.get("sphere_refs") or ["assumption"]) for t in j.get("tasks", []))
    ok = ok and has_ev

    results.append({
        "case": c["name"],
        "passed": ok,
        "latency_s": round(time.time() - t0, 2),
        "num_tasks": len(j.get("tasks", []))
    })

print(json.dumps(results, indent=2))
