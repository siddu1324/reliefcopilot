from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from typing import Dict
from pathlib import Path
import json

# --- use package-qualified imports when running `uvicorn backend.app:app` ---
from backend.rag import LocalRAG
from backend.llm import chat
from backend.prompts import (
    ACTION_PLAN_SYSTEM, ACTION_PLAN_DEVELOPER,
    ACTION_PLAN_FEWSHOT_USER, ACTION_PLAN_FEWSHOT_ASSISTANT,
    action_plan_user,
    BRIEFING_SYSTEM, BRIEFING_DEVELOPER, briefing_user
)
from backend.schemas import ActionPlan, Briefing
from backend.utils import extract_json, normalize_action_plan, safety_lint

app = FastAPI(title="ReliefCopilot")

# --- robust static dir detection (supports repo_root/static or backend/static) ---
BASE_DIR = Path(__file__).resolve().parent
STATIC_CANDIDATES = [BASE_DIR.parent / "static", BASE_DIR / "static"]
STATIC_DIR = next((p for p in STATIC_CANDIDATES if p.exists()), None)
if STATIC_DIR is None:
    # create an empty static dir so mount doesn't fail; you can add files later
    (BASE_DIR.parent / "static").mkdir(parents=True, exist_ok=True)
    STATIC_DIR = BASE_DIR.parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- RAG index (falls back internally if index file is missing) ---
rag = LocalRAG("backend/data/index/chunks.jsonl")

@app.get("/")
def root():
    return {"ok": True, "msg": "ReliefCopilot API running.", "static_dir": str(STATIC_DIR)}

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
        if warn:
            out["_warnings"] = warn
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
    # Return raw markdown; frontend renders it nicely
    return {"briefing_text": text}
