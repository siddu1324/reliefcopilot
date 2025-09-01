import os, httpx

# Prefer OpenAI-compatible endpoint if provided; otherwise use Ollama
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # e.g. http://localhost:8000/v1 for vLLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "EMPTY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss-20b")
OLLAMA_URL = "http://localhost:11434/api/chat"

def _chat_ollama(messages, temperature=0.2):
    payload = {"model": "gpt-oss:20b", "messages": messages, "stream": False,
               "options": {"temperature": temperature}}
    r = httpx.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"]

def _chat_openai(messages, temperature=0.2):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    r = httpx.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        json={"model": MODEL_NAME, "messages": messages, "temperature": temperature},
        headers=headers, timeout=120
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def chat(messages, temperature=0.2):
    if OPENAI_BASE_URL:
        return _chat_openai(messages, temperature)
    return _chat_ollama(messages, temperature)
