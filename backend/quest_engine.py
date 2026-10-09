from typing import Dict, Any, List, Tuple
from backend.llm import generate_quest_llm
from backend.fallback import generate_fallback_quest

def generate_quest(user_profile: Dict[str, Any], weather: Dict[str, Any], time_iso: str, events: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    quest, meta = generate_quest_llm(user_profile, weather, time_iso, events)
    if quest is None:
        quest, meta = generate_fallback_quest(user_profile, weather, time_iso, events)
    return quest, meta
