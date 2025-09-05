# app.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from typing import Dict
import json

from rag import LocalRAG
from llm import chat
from prompts import (
    ACTION_PLAN_SYSTEM,
    ACTION_PLAN_DEVELOPER,
    ACTION_PLAN_FEWSHOT_USER,
    ACTION_PLAN_FEWSHOT_ASSISTANT,
    action_plan_user,
    BRIEFING_SYSTEM,
    BRIEFING_DEVELOPER,
    briefing_user,
)
from schemas import ActionPlan, Briefing
from utils import extract_json, normalize_action_plan

app = FastAPI(title="ReliefCopilot")
app.mount("/static", StaticFiles(directory="static"), name="static")

# tiny local retrieval over cached guidance snippets
rag = LocalRAG("data/guides")

@app.get("/")
def root():
    return {"ok": True, "msg": "ReliefCopilot API running."}

@app.post("/plan")
def generate_plan(payload: Dict):
    logs = (payload.get("logs") or "").strip()
    if not logs:
        raise HTTPException(400, "Missing 'logs'")

    # retrieve short guidance snippets to ground the plan
    snippets = rag.topk(logs, k=3)

    # stricter messaging with a few-shot to anchor the exact JSON shape
    messages = [
        {"role": "system", "content": ACTION_PLAN_SYSTEM},
        {"role": "developer", "content": ACTION_PLAN_DEVELOPER},
        {"role": "user", "content": ACTION_PLAN_FEWSHOT_USER},
        {"role": "assistant", "content": ACTION_PLAN_FEWSHOT_ASSISTANT},
        {"role": "user", "content": action_plan_user(logs, snippets)},
    ]

    raw = chat(messages, temperature=0.2)
    try:
        # extract JSON, normalize shape, then validate via Pydantic
        plan_json = extract_json(raw)
        obj = json.loads(plan_json)
        obj = normalize_action_plan(obj)
        plan = ActionPlan.model_validate(obj)
        return plan.model_dump()
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

    # naive parsing into sections (MVP)
    sections = {
        "situation": "",
        "objectives": [],
        "organization": [],
        "resources": [],
        "safety": [],
        "comms": [],
    }
    current = "situation"
    for line in text.splitlines():
        L = line.strip()
        if not L:
            continue
        low = L.lower()
        if low.startswith("objectives"):
            current = "objectives"; continue
        if low.startswith("organization"):
            current = "organization"; continue
        if low.startswith("resources"):
            current = "resources"; continue
        if low.startswith("safety"):
            current = "safety"; continue
        if low.startswith("comms"):
            current = "comms"; continue
        if current == "situation":
            sections["situation"] += L + " "
        else:
            sections[current].append(L)

    return {"briefing_text": text}
