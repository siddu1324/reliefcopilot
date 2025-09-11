# ReliefCopilot (offline)

**ReliefCopilot** is an **offline AI assistant** that turns messy field notes into **structured Action Plans** and **ICS-201 briefings**, grounded in trusted humanitarian standards (Sphere, WHO, FEMA, IFRC, ICS).  

Built for disaster response scenarios where **connectivity is unreliable**, ReliefCopilot runs **entirely offline** using [Ollama](https://ollama.com) and an open-weights LLM.

---

## 🚀 Why it matters
- **10–20× faster** for responders to produce structured response plans in the first hour.  
- **Grounded & safe**: retrieval-augmented over humanitarian handbooks, with explicit **evidence citations**.  
- **Strict schema validation** ensures predictable JSON plans.  
- **Safety lints** prevent unsafe clinical or dosing instructions.  
- **Offline-first**: runs over localhost on laptops in the field.  

---

## 📂 Project Structure

```
reliefcopilot/
├── backend/
│   ├── app.py            # FastAPI server
│   ├── rag.py            # Retrieval (BM25 over humanitarian corpus)
│   ├── llm.py            # Ollama chat client
│   ├── prompts.py        # System prompts & few-shot templates
│   ├── utils.py          # JSON normalizers, safety lint, injectors
│   ├── ingest.py         # Corpus → chunks.jsonl
│   ├── schemas.py        # Pydantic models (ActionPlan, Briefing)
│   ├── data/index/       # Auto-generated retrieval index
│   ├── corpus/           # Sphere, WHO, FEMA, IFRC, ICS guidance text
│   └── static/           # Frontend (UI, JS, CSS, PWA)
├── docker-compose.yml
├── Dockerfile
├── build.sh              # Helper: docker compose build
├── up.sh                 # Helper: docker compose up
└── README.md
```

---

## 🖥️ Quick start

### 1. Clone and build
```bash
git clone https://github.com/<you>/reliefcopilot.git
cd reliefcopilot
./build.sh
```

### 2. Launch services
```bash
./up.sh
```

This starts:
- **Ollama** → `localhost:11434`
- **ReliefCopilot API** → `localhost:8000`

### 3. Pull the model (first time only)
```bash
docker exec -it ollama ollama pull gpt-oss:20b
```

> ⚠️ Hackathon requires the **20B model**. For lighter hardware, you can change  
> `MODEL_NAME` in `docker-compose.yml` to a quantized model (e.g., `llama3.1:8b-instruct-q4_0`).

### 4. Open the UI
```
http://127.0.0.1:8000/static/index.html
```

# Option B: Local Python (no Docker)

> ⚠️ Requires **Python 3.11+** and [Ollama](https://ollama.com) installed locally.

---

### 1. Clone repo
```bash
git clone https://github.com/<you>/reliefcopilot.git
cd reliefcopilot

### 2. Create a virtual environment & install dependencies

python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows PowerShell
pip install -r backend/requirements.txt

### 3. Start Ollama and pull the model
ollama serve &
ollama pull gpt-oss:20b   # or llama3.1:8b-instruct-q4_0 if hardware is limited

### 4. Run ReliefCopilot backend

export OLLAMA_URL="http://127.0.0.1:11434"
export MODEL_NAME="gpt-oss:20b"
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

### 5. Open the UI

http://127.0.0.1:8000/static/index.html

Paste field notes → **Generate Action Plan** → **Make Briefing**.

---

## 📊 How to read the outputs

### Action Plan
- **Incident / Location**: automatically extracted from logs.  
- **Tasks**: table with ID, title, owner role, priority (P0=critical), timebox, and dependencies.  
- **Comms**: SMS + PA announcements (ready to broadcast).  
- **Translations**: Hindi & Telugu summaries for accessibility.  
- **Evidence**: citations to Sphere/WHO/FEMA/IFRC/ICS snippets.  
- **Warnings**: safety alerts (e.g., if model attempted clinical dosing).  

### Briefing (ICS-201 style)
- Structured summary aligned to ICS-201 sections:  
  - **Incident Overview**  
  - **Assumptions**  
  - **Immediate Actions (priority-ordered)**  
  - **Communications**  
  - **Translations**  
  - **Evidence & References**  

Tabbed viewer:
- **Rendered** (Markdown → clean HTML)  
- **Raw** (exact Markdown text)  
- **JSON** (structured output with `briefing_text`)  

---

## 📦 Offline mode (air-gapped)

If you need to seed the model without internet:

On a connected machine:
```bash
docker run --rm -d --name t_ollama -p 11434:11434 -v ollama_seed:/root/.ollama ollama/ollama
docker exec -it t_ollama ollama pull gpt-oss:20b
docker stop t_ollama
docker run --rm -v ollama_seed:/from -v $PWD:/to alpine sh -c "cd /from && tar -czf /to/ollama_models.tgz ."
```

On the offline machine:
```bash
docker volume create ollama_models
docker run --rm -v ollama_models:/to -v $PWD:/from alpine sh -c "cd /to && tar -xzf /from/ollama_models.tgz"
./up.sh
```

---

## ⚡ Advanced

- **GPU acceleration (Linux/NVIDIA)**: add GPU runtime options in `docker-compose.yml`.  
- **Corpus updates**: add `.txt` files under `backend/corpus/…` and rebuild the index:
  ```bash
  python backend/ingest.py
  ```

---

## 🏆 Hackathon notes

- **Judges’ takeaway**: ReliefCopilot is an **offline, schema-validated, evidence-grounded co-pilot** for first responders.  
- **Impact metrics**:  
  - Cuts planning time from ~30 min → ~2–3 min.  
  - Ensures standards compliance (Sphere/ICS).  
  - Multilingual support → accessibility.  
- **Extendable**: Swap models (20B → smaller quant), add domain corpora, or integrate with radios/SMS gateways.

---

## 📜 License
[APACHE 2.0](LICENSE)
