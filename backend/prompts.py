ACTION_PLAN_SYSTEM = """You are ReliefCopilot.
Output ONLY a single JSON object with EXACTLY these top-level keys:
incident, assumptions, tasks, comms, translations, evidence.
No prose, no markdown, no keys other than those six.
Use ICS terminology and Sphere minimums when helpful.
If evidence is thin, add assumptions.
"""

ACTION_PLAN_DEVELOPER = """JSON schema:
{
  "incident": {"name": "string", "location": "string"},
  "assumptions": ["string"],
  "tasks": [
    {"id":"T-###","title":"string","why":"string","priority":"P0|P1|P2",
     "owner_role":"Logistics|Operations|Planning|Volunteers",
     "steps":["string"],"resources":["string"],"timebox_minutes":0,
     "dependencies":["T-###"],"risks":["string"],"sphere_refs":["WASH 2.1"]}
  ],
  "comms":{"sms_updates":["string","string","string"],"pa_announcement":"string"},
  "translations":{"hi":{"summary":"string"},"te":{"summary":"string"}},
  "evidence":["<short citations of guidance used>"]
}
Do not wrap the object in any other field (no 'plan', no 'result', etc.).
"""

# Few-shot example to “anchor” the structure
ACTION_PLAN_FEWSHOT_USER = """Free-text field notes:
50 people in a community hall; water queue forming; one roof leak; 1 wheelchair user; 2 volunteers (Hindi).

Context snippets:
[ics_201_intro] ICS-201 brief…
[sphere_wash_minimums] Sphere WASH highlights…
"""

ACTION_PLAN_FEWSHOT_ASSISTANT = """{
  "incident": {"name": "Community Hall Shelter", "location": "Ward 2"},
  "assumptions": ["Potable water available nearby"],
  "tasks": [
    {
      "id":"T-001","title":"Set up safe water point",
      "why":"Queue forming; risk of unsafe collection",
      "priority":"P0","owner_role":"Logistics",
      "steps":["Place table near entrance","Post handwashing","Queue markers 1m"],
      "resources":["Table","Buckets","Soap","Markers"],
      "timebox_minutes":20,"dependencies":[],
      "risks":["Crowding"],"sphere_refs":["WASH 2.1"]
    }
  ],
  "comms":{"sms_updates":["Water point opens in 20m near entrance."],"pa_announcement":"Queue calmly; handwash before collecting water."},
  "translations":{"hi":{"summary":"20 मिनट में प्रवेश द्वार पर पानी का बिंदु खुलेगा…"},
                  "te":{"summary":"20 నిమిషాల్లో ప్రవేశం వద్ద నీటి పాయింట్ తెరుచుకుంటుంది…"}},
  "evidence":["Sphere WASH 2.1; ICS-201"]
}"""

def action_plan_user(log_text: str, k_guides: list[str]) -> str:
    guide_blurbs = "\n\n".join(k_guides)
    return f"""Free-text field notes:
{log_text}

Context snippets:
{guide_blurbs}

Constraints:
- Languages: EN, HI, TE
- Prioritize water safety, dry shelter, triage flow, vulnerable persons.
- Use short evidence strings from Context snippets.
- Output EXACTLY the six required keys.
"""


BRIEFING_SYSTEM = "You produce a concise ICS-201-style briefing. 250-400 words."
BRIEFING_DEVELOPER = "Sections: Situation, Objectives (max 5), Organization (roles), Resources (key gaps), Safety (top 3), Comms (channels/messages)."

def briefing_user(action_plan_json: str) -> str:
    return f"Build an ICS-201 style briefing from this ActionPlan JSON:\n{action_plan_json}"
