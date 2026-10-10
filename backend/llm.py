import json
import httpx

from .config import OLLAMA_URL, MODEL


def generate_json(system_prompt, user_prompt, schema, timeout=180):
    """Calls Ollama locally and forces the reply to match a JSON schema."""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "format": schema,
        "stream": False,
        "keep_alive": "30m",  # keep the model in memory between quests
        "options": {
            "temperature": 0.7,
            "num_predict": 250,  # the schema is small; cap runaway output
        },
    }

    r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def warm_up():
    """Load the model into memory so the first real quest isn't slow. Never raises."""
    try:
        httpx.post(f"{OLLAMA_URL}/api/generate",
                   json={"model": MODEL, "keep_alive": "30m"}, timeout=180)
    except Exception:
        pass
