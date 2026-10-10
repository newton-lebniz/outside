import json
import threading
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import BASE_DIR, COMPLETIONS_PATH, DEFAULT_LAT, DEFAULT_LON, DEFAULT_PLACE, MODEL, OLLAMA_URL
from .context import build_context, load_completions
from .llm import warm_up
from .quest_engine import generate_quest

app = FastAPI(title="Outside API")

# Open CORS so the frontend works whether served by FastAPI or opened from another port.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _warm_model():
    threading.Thread(target=warm_up, daemon=True).start()


class QuestRequest(BaseModel):
    interests: list[str] = Field(default_factory=list)
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    place: str = DEFAULT_PLACE
    sim_weather: str | None = None   # clear | cloudy | rain | hot
    sim_time: str | None = None      # "19:42"
    use_llm: bool = True             # False = rule-based baseline
    events_mode: str = "real"        # real | demo | none (demo control)


class CompleteQuestRequest(BaseModel):
    quest_type: str
    xp: int = 0
    title: str | None = None


def _stats():
    today = datetime.now().date().isoformat()
    items = load_completions()
    todays = [i for i in items if i.get("date") == today]
    return {
        "today_xp": sum(i.get("xp", 0) for i in todays),
        "total_xp": sum(i.get("xp", 0) for i in items),
        "completed_today": [i["quest_type"] for i in todays],
        "total_quests": len(items),
    }


@app.get("/health")
def health():
    """Also reports whether Ollama is reachable and the model is pulled."""
    info = {"status": "ok", "model": MODEL, "ollama": False, "model_ready": False}
    try:
        tags = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2).json()
        names = [m.get("name", "") for m in tags.get("models", [])]
        info["ollama"] = True
        info["model_ready"] = any(n == MODEL or n.split(":")[0] == MODEL for n in names)
    except Exception:
        pass
    return info


@app.get("/stats")
def stats():
    return _stats()


@app.post("/quest")
def create_quest(request: QuestRequest):
    if request.events_mode not in ("real", "demo", "none"):
        raise HTTPException(400, "events_mode must be one of: real, demo, none")
    try:
        ctx = build_context(
            lat=request.lat,
            lon=request.lon,
            place=request.place,
            interests=request.interests,
            sim_weather=request.sim_weather,
            sim_time=request.sim_time,
            events_mode=request.events_mode,
        )
    except KeyError:
        raise HTTPException(400, "sim_weather must be one of: clear, cloudy, rain, hot")
    except (httpx.HTTPError, OSError) as e:
        raise HTTPException(503, f"Could not fetch weather ({type(e).__name__}). Check your internet connection.")

    result = generate_quest(ctx, use_llm=request.use_llm)
    return {**result, "context": ctx}


@app.post("/quest/complete")
def complete_quest(request: CompleteQuestRequest):
    items = load_completions()
    items.append({
        "date": datetime.now().date().isoformat(),
        "quest_type": request.quest_type,
        "xp": request.xp,
        "title": request.title,
    })
    Path(COMPLETIONS_PATH).write_text(json.dumps(items, indent=2), encoding="utf-8")
    return {"status": "completed", "quest_type": request.quest_type, **_stats()}


# Serve the frontend from /frontend. Mounted last so the API routes above win.
FRONTEND_DIR = BASE_DIR.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
