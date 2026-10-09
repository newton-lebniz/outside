from .context import is_wet
from .models import make_quest


def fmt_minutes(minutes):
    """Human-friendly 'in 3 h 20 min' style text."""
    minutes = max(int(minutes), 0)
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if m else f"{h} h"


def fallback_quest(ctx):
    """Rule-based quest. Used when the model fails, and as the baseline in the write-up."""
    w = ctx["weather"]
    sky = ctx["sky"]
    done = set(ctx["today"]["completed_types"])
    ev = ctx["nearby_event"]
    wet = is_wet(w)

    # 1. Special event always wins
    if ev:
        return make_quest(
            ev["quest_type"],
            f"Go: {ev['title']}",
            f"{ev['title']} is {ev['distance_km']} km away and starts in "
            f"{fmt_minutes(ev['starts_in_minutes'])}. Your mission: go. "
            f"About {ev['walk_minutes']} min on foot.",
            max(ev["walk_minutes"], 30),
            "A real event is happening nearby.",
            event=ev,
        )

    # 2. Sunset quest
    if (w["is_day"] and 0 <= sky["minutes_to_sunset"] <= 45
            and w["cloud_cover"] < 70 and not wet and "sky" not in done):
        return make_quest(
            "sky", "Chase the sunset",
            "Find an unobstructed western view and watch the sunset for 5 minutes without touching your phone.",
            25, f"Sunset is in {sky['minutes_to_sunset']} minutes and the sky is clear enough.",
        )

    # 3. Bad weather: short, gentle
    if wet:
        return make_quest(
            "nature", "Rain listening",
            "Step outside under cover and find three different sounds of the rain.",
            10, "It's wet outside, so we keep it short and sheltered.",
        )

    # 4. Hot: shade, not exercise
    if w["temp_c"] >= 33:
        return make_quest(
            "nature", "Shade hunt",
            "Find a tree you've never consciously noticed. Sit beneath it for 3 minutes.",
            10, "It's hot, so we skip exercise and find shade.",
        )

    # 5. Movement if not done yet
    if "movement" not in done and 14 <= w["temp_c"] < 33 and w["is_day"]:
        return make_quest(
            "movement", "Move your body",
            "Walk or run 1 km, then finish with 2 minutes of stretching.",
            15, "Comfortable weather and no movement logged today.",
        )

    # 6. Default: exploration
    return make_quest(
        "exploration", "New street",
        "Take a 15-minute walk and find three different sounds around you.",
        15, "A gentle way to get outside no matter the conditions.",
    )
