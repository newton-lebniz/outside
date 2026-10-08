import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EVENTS_PATH = BASE_DIR / "events.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

MODEL = os.getenv("OUTSIDE_MODEL", "gemma3:1b")

DEFAULT_LAT = 12.2958
DEFAULT_LON = 76.6394
DEFAULT_PLACE = "Mysuru, India"
