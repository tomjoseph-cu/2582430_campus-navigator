"""Generate sticky notes from identified important content."""
import re
from collections import Counter
from pathlib import Path

import joblib
import pandas as pd

from src.config import MODELS_DIR, MAX_STICKY_WORDS
from src.features import extract_segment_features, extract_transcript_features

CATEGORY_KEYWORDS = {
    "Action Item": ["action", "will", "need to", "prepare", "create", "send", "submit",
                    "complete", "set up", "schedule", "follow up", "assign", "deploy",
                    "implement", "fix", "resolve", "test", "verify", "draft", "finalize",
                    "book", "organize", "contact", "reach out", "present", "check", "confirm"],
    "Decision": ["decided", "agreed", "confirmed", "approved", "consensus", "let's go with",
                 "the plan is", "final decision", "we will", "settled", "choose"],
    "Deadline": ["deadline", "by friday", "by monday", "by thursday", "by april", "by may",
                 "by june", "by march", "this week", "next week", "before the", "no extension"],
    "Question": ["?", "could you", "can you", "would you", "do you", "is there", "are there"],
    "Key Information": ["budget", "cost", "price", "million", "thousand", "$",
                        "percent", "rate", "result", "data", "report", "meeting"],
    "Event": ["meeting", "demo", "seminar", "conference", "workshop", "presentation",
              "deadline", "fest", "hackathon", "lunch"],
}

NOTE_COLORS = {
    "Action Item": "#FFD54F",
    "Decision": "#81C784",
    "Deadline": "#EF9A9A",
    "Question": "#90CAF9",
    "Key Information": "#CE93D8",
    "Event": "#FFAB91",
    "General": "#FFF9C4",
}


def _categorize_note(text: str) -> str:
    lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "General"


def _extract_title(text: str) -> str:
    text = text.strip()
    if len(text) <= 40:
        return text
    words = text.split()
    title = ""
    for w in words:
        if len(title) + len(w) + 1 > 35:
            break
        title = (title + " " + w).strip()
    return title + "..."


def _extract_key_phrases(text: str) -> list[str]:
    phrases = []
    if "?" in text:
        phrases.append("Question")
    lower = text.lower()
    for marker in ["we decided", "let's go with", "agreed", "confirmed"]:
        if marker in lower:
            phrases.append("Decision")
            break
    for marker in ["action item", "need to", "will prepare", "will create", "will send"]:
        if marker in lower:
            phrases.append("Action")
            break
    for marker in ["deadline", "by friday", "by monday", "by thursday"]:
        if marker in lower:
            phrases.append("Deadline")
            break
    return phrases


def generate_sticky_notes(transcript_text: str, model_bundle: dict = None) -> list[dict]:
    if model_bundle is None:
        model_path = MODELS_DIR / "important_content_classifier.joblib"
        if model_path.exists():
            model_bundle = joblib.load(model_path)
        else:
            model_bundle = None

    t_features = extract_transcript_features(transcript_text)
    segments = t_features["segments"]
    summary = t_features["summary"]

    if model_bundle is not None:
        model = model_bundle["model"]
        scaler = model_bundle.get("scaler")
        feature_cols = model_bundle["feature_cols"]

        X = []
        for seg in segments:
            row = [seg.get(col, 0) for col in feature_cols]
            X.append(row)
        X = pd.DataFrame(X, columns=feature_cols).fillna(0)

        if scaler is not None and model_bundle.get("best_model_name") in ("Logistic Regression", "SVM"):
            X = scaler.transform(X)

        probs = model.predict_proba(X)
        importance_scores = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
    else:
        importance_scores = []
        for seg in segments:
            score = 0.0
            if seg["has_action_verb"]:
                score += 0.3
            if seg["has_decision"]:
                score += 0.3
            if seg["has_question"]:
                score += 0.1
            if seg["contains_date_or_deadline"]:
                score += 0.2
            if seg["word_count"] > 8:
                score += 0.1
            importance_scores.append(min(score, 1.0))
        importance_scores = pd.Series(importance_scores)

    notes = []
    for i, (seg, score) in enumerate(zip(segments, importance_scores)):
        text = seg["text"]
        category = _categorize_note(text)
        title = _extract_title(text)
        tags = _extract_key_phrases(text)

        notes.append({
            "note_id": len(notes) + 1,
            "title": title,
            "full_text": text,
            "speaker": seg["speaker"],
            "category": category,
            "color": NOTE_COLORS.get(category, NOTE_COLORS["General"]),
            "importance_score": round(float(score), 3),
            "tags": tags,
            "segment_index": seg["segment_index"],
            "is_important": bool(score >= 0.35),
        })

    notes.sort(key=lambda n: (-int(n["is_important"]), -n["importance_score"]))

    for i, note in enumerate(notes):
        note["note_id"] = i + 1

    important_count = sum(1 for n in notes if n["is_important"])

    return {
        "meeting_summary": summary,
        "sticky_notes": notes,
        "total_segments": summary["total_segments"],
        "important_segments": important_count,
    }


def generate_sticky_notes_from_text(text: str) -> dict:
    return generate_sticky_notes(text)