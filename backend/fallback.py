from typing import Dict, Any, Tuple

def generate_fallback_quest(
    user_profile: Dict[str, Any],
    weather: Dict[str, Any],
    time_iso: str,
    events: list
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    meta = {"source": "fallback", "rules_ok": True, "last_error": None}
    
    is_rain = "rain" in weather.get("condition", "").lower()
    is_hot = weather.get("temp_c", 0) > 30
    has_event = len(events) > 0

    if has_event:
        evt = events[0]
        quest = {
            "title": f"Attend {evt.get('title', 'Local Event')}",
            "description": f"Walk over to {evt.get('title')} and enjoy the view.",
            "duration_mins": evt.get("walk_time_mins", 15) + 20,
            "xp_reward": 500,
            "is_special": True
        }
    elif is_rain:
        quest = {
            "title": "Sheltered Porch Stride",
            "description": "Take a short walk under covered areas to feel the cool rain air.",
            "duration_mins": 15,
            "xp_reward": 100,
            "is_special": False
        }
    elif is_hot:
        quest = {
            "title": "Shaded Hydration Stroll",
            "description": "Walk slowly in shaded paths with a bottle of water.",
            "duration_mins": 20,
            "xp_reward": 150,
            "is_special": False
        }
    else:
        quest = {
            "title": "Fresh Air Exploration",
            "description": "Step outside for a relaxing walk around your neighborhood.",
            "duration_mins": 25,
            "xp_reward": 200,
            "is_special": False
        }
        
    return quest, meta
