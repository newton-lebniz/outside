import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EVENTS_PATH = BASE_DIR / "events.json"
COMPLETIONS_PATH = BASE_DIR / "completions.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

MODEL = os.getenv("OUTSIDE_MODEL", "gemma3:1b")

DEFAULT_LAT = 16.2076
DEFAULT_LON = 77.3463
DEFAULT_PLACE = "Raichur, Karnataka, India"
