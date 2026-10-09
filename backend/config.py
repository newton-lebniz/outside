import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
