import time

from .config import MODEL
from .context import is_wet, preferred_types
from .fallback import fallback_quest, fmt_minutes
from .llm import generate_json
from .models import LLMQuest, make_quest

SYSTEM_PROMPT = """You are the quest engine of OUTSIDE, an app that gets people off their phones and into the real world.
Given the user's context, choose ONE real-world quest that fits right now.

Rules:
- quest_type must be one of: movement, nature, social, sky, exploration.
- Never give a sky quest if the cloud cover is high, it is raining, or it is daytime and sunset is not close.
- If it is raining, keep the quest short and sheltered.
- If it is hot (above 33C), do not give a running or exercise quest.
- Do not give a movement quest if the user already did movement today.
- Prefer quests that need almost no phone use. Never require taking photos.
- Never invent events, places or facts that are not in the context.
- Keep the title under 6 words. The action is one or two concrete sentences saying exactly what to do and where.
- duration_minutes is an integer. If the user prefers short activities, keep it at 30 or less.
- reason is one short sentence explaining why this quest fits right now.
Reply with JSON only."""


def context_to_prompt(ctx):
    w, s, u = ctx["weather"], ctx["sky"], ctx["user"]
    ev = ctx["nearby_event"]
    done = ", ".join(ctx["today"]["completed_types"]) or "nothing yet"
    lines = [
        f"TIME: {ctx['time']} ({ctx['daypart']}, {ctx['weekday']})",
        f"LOCATION: {ctx['location']['name']}",
        f"WEATHER: {w['condition']}, {w['temp_c']}C, cloud cover {w['cloud_cover']}%, "
        f"wind {w['wind_kmh']} km/h, rain {w['precipitation_mm']} mm",
        f"SKY: sunset at {s['sunset']} ({s['minutes_to_sunset']} min from now; negative means already set); "
        f"it is {'daytime' if w['is_day'] else 'night'}",
    ]
    guidance = ctx.get("weather_guidance")
    if guidance:
        lines.append(f"WEATHER GUIDANCE: {guidance['guidance']}")
    lines += [
        f"DONE TODAY: {done}",
        f"USER INTERESTS: {', '.join(u['interests']) or 'none given'}",
        f"USER PREFERS: {'short activities' if u['prefers_short'] else 'any length'}",
    ]
    pref = preferred_types(u["interests"])
    if pref:
        lines.append(
            f"USER'S PREFERRED QUEST TYPES: {', '.join(pref)} (choose one of these when the weather and sky rules "
            "allow, unless that type was already done today)"
        )
    if (w["is_day"] and 0 <= s["minutes_to_sunset"] <= 45 and w["cloud_cover"] < 70
            and not is_wet(w) and "sky" not in ctx["today"]["completed_types"]):
        lines.append(f"SKY NOTE: sunset is in {s['minutes_to_sunset']} minutes and the sky is clear. "
                     "Watching the sunset is a strong option.")
    if ev:
        lines.append(
            f"NEARBY EVENT: {ev['title']}, {ev['distance_km']} km away "
            f"(~{ev['walk_minutes']} min walk), starts in {fmt_minutes(ev['starts_in_minutes'])}"
        )
        lines.append(
            "SPECIAL QUEST MODE: the quest MUST be to attend this event. Use the exact event title "
            "in the title or action, and mention the distance and walk time."
        )
    else:
        lines.append("NEARBY EVENT: none")
    return "\n".join(lines)


def validate(q, ctx):
    """Hard rules. Returns an error string, or None if the quest is acceptable."""
    if not (3 <= len(q.title) <= 60):
        return "title length must be 3-60 characters"
    if not (30 <= len(q.action) <= 300):
        return "action must be one or two concrete sentences (30-300 characters)"
    if not (1 <= q.duration_minutes <= 90):
        return "duration_minutes must be between 1 and 90"

    ev = ctx["nearby_event"]
    if ev:
        # Special quest: type/XP are overridden by code, but the model must not invent a different event.
        text = f"{q.title} {q.action}".lower()
        if ev["title"].lower() not in text:
            return f"special quest must mention the exact event title '{ev['title']}'"
        return None

    w, s, u = ctx["weather"], ctx["sky"], ctx["user"]
    done = ctx["today"]["completed_types"]
    sky_ok = ctx.get("weather_guidance", {}).get("sky_ok", True)
    if q.quest_type == "sky":
        if not sky_ok or w["cloud_cover"] >= 70 or is_wet(w):
            return "sky quest not allowed: cloudy or wet"
        if w["is_day"] and not (0 <= s["minutes_to_sunset"] <= 60):
            return "sky quest not allowed in daytime unless sunset is within 60 minutes"
    if q.quest_type == "movement" and ("movement" in done or w["temp_c"] >= 33):
        return "movement quest not allowed: already done today or too hot"
    if is_wet(w) and q.duration_minutes > 20:
        return "quest too long for wet weather"
    if u["prefers_short"] and q.duration_minutes > 30:
        return "user prefers short activities (30 min or less)"
    return None


def generate_quest(ctx, use_llm=True):
    """Returns {"quest": {...}, "meta": {...}}. Never raises: falls back to rules."""
    meta = {"model": MODEL, "source": "llm", "attempts": 0, "last_error": None}
    t0 = time.time()
    quest = None

    if use_llm:
        feedback = ""
        for _ in range(2):
            meta["attempts"] += 1
            prompt = context_to_prompt(ctx) + feedback
            try:
                raw = generate_json(SYSTEM_PROMPT, prompt, LLMQuest.model_json_schema())
                q = LLMQuest.model_validate(raw)
            except Exception as e:  # Ollama down, bad JSON, schema mismatch
                meta["last_error"] = f"model error: {str(e)[:150]}"
                feedback = "\n\nYour previous reply was invalid JSON for the schema. Try again."
                continue
            err = validate(q, ctx)
            if err:
                meta["last_error"] = err
                feedback = f"\n\nYour previous reply was rejected: {err}. Choose a different quest."
                continue
            ev = ctx["nearby_event"]
            minutes = max(q.duration_minutes, ev["walk_minutes"], 30) if ev else q.duration_minutes
            quest = make_quest(q.quest_type, q.title, q.action, minutes, q.reason, event=ev)
            meta["last_error"] = None
            break

    if quest is None:
        meta["source"] = "fallback"
        quest = fallback_quest(ctx)

    meta["latency_s"] = round(time.time() - t0, 2)
    return {"quest": quest, "meta": meta}
