import json
import requests
from typing import Dict, Any, Tuple, Optional
from backend.config import OLLAMA_HOST, OLLAMA_MODEL, LLM_TIMEOUT

def generate_quest_llm(
    user_profile: Dict[str, Any],
    weather: Dict[str, Any],
    time_iso: str,
    events: list
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    meta = {"source": "llm", "rules_ok": False, "last_error": None}
    
    prompt = f"""
    Generate a personalized outdoor quest as valid JSON with keys:
    "title" (str), "description" (str), "duration_mins" (int), "xp_reward" (int), "is_special" (bool).

    User Profile: {json.dumps(user_profile)}
    Weather: {json.dumps(weather)}
    Time ISO: {time_iso}
    Events: {json.dumps(events)}

    Return ONLY raw JSON. No markdown formatting or extra text.
    """

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=LLM_TIMEOUT
        )
        if response.status_code == 200:
            res_data = response.json()
            quest_data = json.loads(res_data.get("response", "{}"))
            meta["rules_ok"] = True
            return quest_data, meta
        else:
            meta["last_error"] = f"HTTP {response.status_code}: {response.text}"
            return None, meta
    except Exception as e:
        meta["last_error"] = str(e)
        return None, meta
