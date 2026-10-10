"""Builds a model comparison table from results/day1_<model>.json.

Run the test once per model (OUTSIDE_MODEL=... python -m backend.test_contexts),
then: python -m backend.compare
"""
import json
import statistics
from pathlib import Path

RESULTS = Path("results")

# What a sensible quest looks like in each test situation.
CHECKS = {
    "2_hot_after_run":    ("not a movement quest",    lambda q: q["quest_type"] != "movement"),
    "3_sunset_clear":     ("sky quest",               lambda q: q["quest_type"] == "sky"),
    "4_sunset_cloudy":    ("not a sky quest",         lambda q: q["quest_type"] != "sky"),
    "5_stargazing_event": ("special quest, 500 XP",   lambda q: q["is_special"] and q["xp"] == 500),
    "6_rain":             ("20 min or less",          lambda q: q["duration_minutes"] <= 20),
    "7_cloudy_night":     ("not a sky quest",         lambda q: q["quest_type"] != "sky"),
}


def load():
    out = {}
    for path in sorted(RESULTS.glob("day1_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):  # skip results from the old, pre-fix format
            out[path.stem.removeprefix("day1_")] = data
    return out


def main():
    all_results = load()
    if not all_results:
        print("No results found. Run: python -m backend.test_contexts")
        return

    lines = ["| Model | Answered by the model | Right on first try | Median latency | Situation checks passed |",
             "|---|---|---|---|---|"]
    detail = []
    for model, cases in all_results.items():
        n = len(cases)
        llm = [c["llm"] for c in cases.values() if c["llm"]["meta"]["source"] == "llm"]
        first_try = [c for c in llm if c["meta"]["attempts"] == 1]
        lat = [c["llm"]["meta"]["latency_s"] for c in cases.values() if c["llm"]["meta"]["source"] == "llm"]
        passed = sum(1 for k, (_, fn) in CHECKS.items() if k in cases and fn(cases[k]["llm"]["quest"]))
        lines.append(f"| {model} | {len(llm)}/{n} | {len(first_try)}/{n} | "
                     f"{(str(round(statistics.median(lat), 1)) + ' s') if lat else 'n/a'} | {passed}/{len(CHECKS)} |")
        detail.append(f"\n### {model}\n")
        for name, c in cases.items():
            q, m = c["llm"]["quest"], c["llm"]["meta"]
            detail.append(f"- **{name}** ({m['source']}, {m['latency_s']} s): {q['quest_type']}, \"{q['title']}\". {q['action']}")

    text = "\n".join(lines) + "\n" + "\n".join(detail) + "\n"
    (RESULTS / "comparison.md").write_text(text, encoding="utf-8")
    print(text)
    print("Saved to results/comparison.md")


if __name__ == "__main__":
    main()
