"""Configuration and constants for the Sticky Note Generator."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MODELS_DIR = OUTPUT_DIR / "models"
PLOTS_DIR = OUTPUT_DIR / "plots"
REPORTS_DIR = OUTPUT_DIR / "reports"

TRANSCRIPTS_PATH = DATA_DIR / "meeting_transcripts.csv"
FEATURES_PATH = DATA_DIR / "extracted_features.csv"

RANDOM_STATE = 42
TEST_SIZE = 0.2
MAX_STICKY_WORDS = 30

STOPWORDS_EXTRA = {
    "um", "uh", "like", "you know", "so", "well", "okay", "yeah",
    "right", "actually", "basically", "literally", "i mean", "kind of",
}

ACTION_VERBS = {
    "send", "prepare", "submit", "complete", "review", "schedule",
    "arrange", "set up", "create", "draft", "finalize", "update",
    "assign", "follow up", "check", "confirm", "book", "organize",
    "contact", "reach out", "present", "discuss", "implement",
    "deploy", "fix", "resolve", "test", "verify", "approve",
}

DECISION_MARKERS = {
    "we decided", "let's go with", "agreed", "approved", "final decision",
    "we will", "the plan is", "confirmed", "it's settled", "consensus",
}

QUESTION_MARKERS = {"?", "could you", "can you", "would you", "do you", "is there", "are there"}

NAMED_ENTITY_PATTERNS = {
    "person": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
    "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:,? \d{4})?\b",
    "time": r"\b\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}

for d in (DATA_DIR, MODELS_DIR, PLOTS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)