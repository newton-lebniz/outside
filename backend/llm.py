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
        "options": {
            "temperature": 0.7
        },
    }

    r = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=timeout,
    )

    r.raise_for_status()

    return json.loads(r.json()["message"]["content"])
