from pydantic import BaseModel
from typing import List, Optional, Literal

Priority = Literal["P0","P1","P2"]

class Task(BaseModel):
    id: str
    title: str
    why: str
    priority: Priority
    owner_role: Literal["Logistics","Operations","Planning","Volunteers"]
    steps: List[str]
    resources: List[str] = []
    timebox_minutes: int = 0
    dependencies: List[str] = []
    risks: List[str] = []
    sphere_refs: List[str] = []

class Translations(BaseModel):
    hi: Optional[dict] = None
    te: Optional[dict] = None

class ActionPlan(BaseModel):
    incident: dict
    assumptions: List[str] = []
    tasks: List[Task]
    comms: dict
    translations: Translations | dict = {}
    evidence: List[str] = []

class Briefing(BaseModel):
    situation: str
    objectives: List[str]
    organization: List[str]
    resources: List[str]
    safety: List[str]
    comms: List[str]
