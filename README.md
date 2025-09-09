# ReliefCopilot (offline)

Offline AI assistant that converts messy field notes into **actionable action plans and ICS-201 briefings**, grounded in humanitarian standards. Runs **fully offline** with Ollama and **gpt-oss-20B**.

## Why it matters
- **10–20× faster** for responders to structure plans during the first hour.
- **Grounded & safe**: Retrieval-augmented over Sphere/WHO/FEMA/IFRC; evidence citations; schema validation; safety lints (no clinical dosing).
- **Offline-first**: Works over localhost inside disaster sites.

## Quick start (Docker)
```bash
docker compose up -d
# In another shell (first-time only):
docker exec -it ollama ollama pull gpt-oss:20b
# Open UI
open http://127.0.0.1:8000/static/index.html

sh
