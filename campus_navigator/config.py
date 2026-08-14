import os


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


HOST = os.getenv("CAMPUS_HOST", "127.0.0.1")
PORT = int(os.getenv("CAMPUS_PORT", "8000"))
WALK_SPEED_MPS = float(os.getenv("CAMPUS_WALK_SPEED", "1.4"))
TICK_SECONDS = float(os.getenv("CAMPUS_TICK", "5"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AI_ENABLED = _env_bool("CAMPUS_AI_ENABLED", True)

CAMPUS_NAME = os.getenv("CAMPUS_NAME", "Northbrook University")
