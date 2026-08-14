"""Launch the Campus Navigator web app.

    python run.py

Optional environment variables:
    OPENAI_API_KEY   API key to enable the OpenAI hybrid AI layer
    OPENAI_MODEL     model name (default gpt-4o-mini)
    CAMPUS_HOST      bind host (default 127.0.0.1)
    CAMPUS_PORT      bind port (default 8000)
    CAMPUS_WALK_SPEED  walking speed in m/s (default 1.4)
    CAMPUS_TICK      live simulation tick in seconds (default 5)
"""

from campus_navigator.api import run

if __name__ == "__main__":
    run()
