import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import MODEL, DEFAULT_LAT, DEFAULT_LON, DEFAULT_PLACE
from .context import assemble_context
from .models import LLMQuest
from .quest_engine import generate_quest, validate

IST = timezone(timedelta(hours=5, minutes=30))


def at(h, m):
    return datetime(2026, 10, 9, h, m, tzinfo=IST)


SUNRISE, SUNSET = at(6, 10), at(18, 5)


def W(condition, temp, cloud, precip=0.0, wind=8):
    return {"condition": condition, "temp_c": temp, "cloud_cover": cloud,
            "wind_kmh": wind, "precipitation_mm": precip}


STARGAZING = {
    "id": "stargazing-test", "title": "Public stargazing night", "quest_type": "sky",
    "distance_km": 3.2, "walk_minutes": 38, "starts_in_minutes": 90,
}


def ctx(now, weather, done=(), interests=("fitness",), event=None):
    return assemble_context(now, DEFAULT_LAT, DEFAULT_LON, DEFAULT_PLACE, weather,
                            SUNRISE, SUNSET, event, done, interests, True)


CASES = {
    "1_morning_clear":    ctx(at(8, 0),   W("clear", 22, 5)),
    "2_hot_after_run":    ctx(at(14, 0),  W("clear", 36, 10), done=["movement"]),
    "3_sunset_clear":     ctx(at(17, 45), W("clear", 26, 8), interests=("astronomy",)),
    "4_sunset_cloudy":    ctx(at(17, 45), W("overcast", 25, 95), interests=("astronomy",)),
    "5_stargazing_event": ctx(at(18, 30), W("clear", 24, 5), interests=("astronomy",), event=STARGAZING),
    "6_rain":             ctx(at(11, 0),  W("rain", 21, 100, precip=3.0)),
    "7_cloudy_night":     ctx(at(20, 30), W("overcast", 23, 90), interests=("astronomy",)),
}


def rules_ok(quest, ctx_):
    """Re-check the final quest (LLM or fallback) against the hard rules."""
    q = LLMQuest(quest_type=quest["quest_type"], title=quest["title"], action=quest["action"],
                 duration_minutes=quest["duration_minutes"], reason=quest["reason"])
    return validate(q, ctx_) is None


def main():
    print(f"MODEL: {MODEL}\n")
    results = {}
    for name, c in CASES.items():
        out = generate_quest(c, use_llm=True)
        base = generate_quest(c, use_llm=False)
        q, m = out["quest"], out["meta"]
        print("=" * 60)
        print(name)
        print(f"[{m['source']}] {q['quest_type'].upper()}  {q['title']}  ({q['duration_minutes']} min, +{q['xp']} XP)")
        print(q["action"])
        print(f"why: {q['reason']}")
        print(f"special={q['is_special']}  attempts={m['attempts']}  latency={m['latency_s']}s  "
              f"rules_ok={rules_ok(q, c)}  last_error={m['last_error']}")
        print(f"-- rule-based baseline: {base['quest']['title']}")
        results[name] = {"llm": out, "baseline": base["quest"]}

    Path("results").mkdir(exist_ok=True)
    out_path = Path("results") / f"day1_{MODEL.replace(':', '_').replace('/', '_')}.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
