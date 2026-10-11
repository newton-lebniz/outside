# OUTSIDE

An app that looks at the sky, the weather and what you've already done today, then asks a local open-weight model to pick one real-world quest: go watch the sunset, sit under a tree you've never noticed, walk to a stargazing night 3 km away. You start it, put your phone away, and come back to mark it done.

Built for the DEV Hacktoberfest Open-Source AI Challenge, Week 1 (theme: Touch Grass).

## How it works

```
location + time + weather + sunset + nearby events + what you did today
                              |
                      context engine (context.py)
                              |
            local Gemma via Ollama, JSON-schema constrained
                              |
        rule check (quest_engine.py): allowed types, length, weather, events
              |                                      |
         accepted quest                  rejected twice -> rule-based fallback
```

- The model writes the quest. Plain code decides what is allowed right now (no sky quests under cloud, no running on a hot day or after you already ran, no inventing events), and code owns XP and event details.
- If the model fails or breaks a rule twice, a rule-based generator (`fallback.py`) answers instead. The UI says which one answered.
- Special quests: if a relevant event is within 5 km and 36 hours, the quest becomes "go to this event" for 500 XP.

## What is local and what is not

- Quest generation runs on your machine through Ollama. No quest prompt goes to a hosted AI API.
- The weather lookup uses [Open-Meteo](https://open-meteo.com) (free, no key). It receives your coordinates rounded to about 1 km. This is the only call that leaves your machine, and it needs internet. Without internet the app cannot build a context.

## Run it

Requires Python 3.10+ and [Ollama](https://ollama.com).

```bash
git clone <this repo> && cd outside
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt

ollama pull gemma3:1b            # or gemma3:4b for better quests, slower
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000. To use it from a phone on the same Wi-Fi, run uvicorn with `--host 0.0.0.0`, open `http://<your-computer-ip>:8000`, and choose "Use the demo location" (browsers only allow "Use my location" on localhost or HTTPS).

### Swap the model

```bash
# Windows: set OUTSIDE_MODEL=qwen2.5:3b     Mac/Linux: export OUTSIDE_MODEL=qwen2.5:3b
ollama pull qwen2.5:3b
uvicorn backend.main:app --reload
```

Any Ollama model that supports structured output works. `OLLAMA_URL` points at a different Ollama server.

### Set your place and events

- `backend/config.py`: `DEFAULT_LAT`, `DEFAULT_LON`, `DEFAULT_PLACE`
- `frontend/app.js`: `DEMO_LOC`
- `backend/events.json`: a real event has `lat`, `lon` and `start` (for example `"2026-10-12T17:00"`). Entries with `"placeholder": true` are demo events. They are placed relative to the user (`offset_km` = [east, north]) and start `start_in_hours` from now, so they never expire. They are only used when Demo controls > Nearby events is set to "Include demo events", and the UI labels them "(demo event)".

## Demo controls

The collapsible panel on the home screen lets you simulate weather (clear, heavy cloud, rain, hot), set the time of day, choose which events are visible, and switch the model off to see the rule-based baseline. This is how the "the sky isn't cooperating" adaptation is shown without waiting for real clouds.

## Tests and model comparison

```bash
python -m backend.test_contexts      # 7 fixed situations through the model, saves results/day1_<model>.json
# switch OUTSIDE_MODEL and run again for each model, then:
python -m backend.compare            # writes results/comparison.md
```

`test_contexts` stops with a message if Ollama is not running or the model is not pulled, so a results file always comes from a real model.

## Project layout

```
backend/
  context.py       builds the context: weather, sunset, events, today's completions
  quest_engine.py  prompt, allowed quest types, validation, retry, fallback
  fallback.py      rule-based quest generator
  llm.py           Ollama client (schema-constrained JSON)
  models.py        quest schema and XP rules
  main.py          FastAPI: /quest, /quest/complete, /stats, /health, and serves frontend/
  events.json      events (real and demo)
frontend/          plain HTML, CSS and JS, no build step
results/           model test runs and the comparison table
```

## Limitations

- Completion is an honor-system button. Nothing verifies you went outside.
- Events are demo data unless you add real ones. There is no live event discovery.
- Small local models are slow (several seconds per quest) and repeat themselves. The rule check and fallback exist because of this.
- No Jupiter or planet visibility yet. Sky quests rely on sunset time, cloud cover and time of day.

## Challenge notes

The repository was started on Oct 8, 2026, inside the challenge window. Commits made after the Oct 11, 2026 11:59 PM PDT deadline: none yet. (Edit this line if that changes.)
