import json
import os
from datetime import datetime, timezone
from backend.quest_engine import generate_quest

TEST_CASES = [
    {
        "id": "1_morning_clear",
        "user_profile": {"fitness_level": "moderate", "recent_activities": []},
        "weather": {"temp_c": 18, "condition": "Clear", "is_day": 1, "uv_index": 2},
        "time_iso": "2026-05-10T08:00:00Z",
        "events": []
    },
    {
        "id": "2_hot_after_run",
        "user_profile": {"fitness_level": "active", "recent_activities": ["5k_run"]},
        "weather": {"temp_c": 34, "condition": "Sunny", "is_day": 1, "uv_index": 8},
        "time_iso": "2026-05-10T14:00:00Z",
        "events": []
    },
    {
        "id": "3_sunset_clear",
        "user_profile": {"fitness_level": "casual", "recent_activities": []},
        "weather": {"temp_c": 22, "condition": "Clear", "is_day": 1, "uv_index": 1},
        "time_iso": "2026-05-10T19:15:00Z",
        "events": []
    },
    {
        "id": "4_sunset_cloudy",
        "user_profile": {"fitness_level": "casual", "recent_activities": []},
        "weather": {"temp_c": 20, "condition": "Overcast", "is_day": 1, "uv_index": 0},
        "time_iso": "2026-05-10T19:15:00Z",
        "events": []
    },
    {
        "id": "5_stargazing_event",
        "user_profile": {"fitness_level": "casual", "recent_activities": []},
        "weather": {"temp_c": 16, "condition": "Clear", "is_day": 0, "uv_index": 0},
        "time_iso": "2026-05-10T21:00:00Z",
        "events": [{
            "id": "evt_meteor_01",
            "title": "Lyrid Meteor Shower Peak",
            "type": "astronomy",
            "start": "2026-05-10T20:30:00Z",
            "end": "2026-05-10T23:00:00Z",
            "walk_time_mins": 12
        }]
    },
    {
        "id": "6_rain",
        "user_profile": {"fitness_level": "moderate", "recent_activities": []},
        "weather": {"temp_c": 15, "condition": "Light Rain", "is_day": 1, "uv_index": 1},
        "time_iso": "2026-05-10T11:00:00Z",
        "events": []
    },
    {
        "id": "7_cloudy_night",
        "user_profile": {"fitness_level": "moderate", "recent_activities": []},
        "weather": {"temp_c": 14, "condition": "Cloudy", "is_day": 0, "uv_index": 0},
        "time_iso": "2026-05-10T22:00:00Z",
        "events": []
    }
]

def run_tests():
    os.makedirs("results", exist_ok=True)
    results = []

    print("=" * 60)
    print("RUNNING OUTSIDE DAY 1 CONTEXT TESTS")
    print("=" * 60)

    for case in TEST_CASES:
        print(f"\n[Testing Case: {case['id']}]")
        quest, meta = generate_quest(
            user_profile=case["user_profile"],
            weather=case["weather"],
            time_iso=case["time_iso"],
            events=case["events"]
        )

        output = {
            "case_id": case["id"],
            "source": meta.get("source"),
            "rules_ok": meta.get("rules_ok"),
            "quest": quest.dict() if hasattr(quest, "dict") else quest
        }
        results.append(output)

        print(f"  Source   : {meta.get('source')}")
        print(f"  Rules OK : {meta.get('rules_ok')}")
        print(f"  Title    : {output['quest'].get('title')}")
        print(f"  XP       : {output['quest'].get('xp_reward')}")
        if meta.get("last_error"):
            print(f"  Error    : {meta.get('last_error')}")

    out_file = "results/day1_gemma3_4b.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print(f"SUCCESS: Results saved to {out_file}")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
