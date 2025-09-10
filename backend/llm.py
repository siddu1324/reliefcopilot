import requests, os, json

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("MODEL_NAME", "gpt-oss:20b")

DET_OPTS = {"seed": 42, "temperature": 0.2, "top_p": 0.9, "repeat_penalty": 1.1}
ADAPT_OPTS = {"temperature": 0.6, "top_p": 0.95, "repeat_penalty": 1.05}

def _post(path: str, payload: dict, timeout=120):
    url = f"{OLLAMA_URL}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def chat(messages, mode="deterministic"):
    opts = DET_OPTS if mode == "deterministic" else ADAPT_OPTS
    req = {"model": MODEL, "messages": messages, "options": opts, "stream": False}
    try:
        resp = _post("/api/chat", req)
    except Exception as e:
        # Return a clear JSON error slice so UI shows something useful
        return '{"error": "LLM call failed: %s"}' % str(e)
    # Ollama returns {"message":{"content":...}}
    content = (resp.get("message") or {}).get("content") or ""
    return content
