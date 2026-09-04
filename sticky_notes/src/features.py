"""Extract NLP features from meeting transcripts."""
import re
from pathlib import Path

import pandas as pd

from src.config import (
    ACTION_VERBS,
    DATA_DIR,
    DECISION_MARKERS,
    FEATURES_PATH,
    NAMED_ENTITY_PATTERNS,
    QUESTION_MARKERS,
    STOPWORDS_EXTRA,
)


def _word_count(text: str) -> int:
    return len(text.split())


def _sentence_count(text: str) -> int:
    return max(1, len(re.split(r'[.!?]+', text.strip())))


def _keyword_density(text: str, keywords: set) -> float:
    words = set(text.lower().split())
    if not words:
        return 0.0
    return len(words & keywords) / len(words)


def _has_question(text: str) -> int:
    if "?" in text:
        return 1
    lower = text.lower()
    return int(any(m in lower for m in QUESTION_MARKERS))


def _has_action_verb(text: str) -> int:
    lower = text.lower()
    return int(any(av in lower for av in ACTION_VERBS))


def _has_decision(text: str) -> int:
    lower = text.lower()
    return int(any(dm in lower for dm in DECISION_MARKERS))


def _count_named_entities(text: str) -> dict:
    counts = {}
    for etype, pattern in NAMED_ENTITY_PATTERNS.items():
        counts[f"ne_{etype}"] = len(re.findall(pattern, text))
    return counts


def _contains_date_or_deadline(text: str) -> int:
    lower = text.lower()
    return int(bool(re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)) or
               "deadline" in lower or "by " in lower)


def _sentiment_indicators(text: str) -> dict:
    positive = {"great", "excellent", "good", "agree", "confirmed", "perfect", "love", "amazing"}
    negative = {"problem", "issue", "bug", "delay", "risk", "concern", "worried", "fail"}
    words = set(text.lower().split())
    return {
        "positive_words": len(words & positive),
        "negative_words": len(words & negative),
    }


def extract_segment_features(text: str, speaker: str = "", prev_speaker: str = "") -> dict:
    features = {}

    features["word_count"] = _word_count(text)
    features["sentence_count"] = _sentence_count(text)
    features["avg_word_length"] = sum(len(w) for w in text.split()) / max(1, _word_count(text))

    features["has_question"] = _has_question(text)
    features["has_action_verb"] = _has_action_verb(text)
    features["has_decision"] = _has_decision(text)
    features["contains_date_or_deadline"] = _contains_date_or_deadline(text)

    features["keyword_density_action"] = _keyword_density(text, ACTION_VERBS)
    features["keyword_density_stopword"] = _keyword_density(text, STOPWORDS_EXTRA)

    ne = _count_named_entities(text)
    features.update(ne)

    sent = _sentiment_indicators(text)
    features.update(sent)

    features["speaker_same_as_prev"] = int(speaker == prev_speaker) if prev_speaker else 0
    features["is_short_utterance"] = int(features["word_count"] < 5)

    features["exclamation_count"] = text.count("!")
    features["caps_ratio"] = sum(1 for c in text if c.isupper()) / max(1, len(text))

    return features


def extract_transcript_features(transcript_text: str) -> dict:
    lines = [l.strip() for l in transcript_text.split("\n") if l.strip()]

    speakers = []
    texts = []
    for line in lines:
        match = re.match(r"^(.+?):\s*(.+)$", line)
        if match:
            speakers.append(match.group(1).strip())
            texts.append(match.group(2).strip())

    all_features = []
    prev_speaker = None
    for i, (speaker, text) in enumerate(zip(speakers, texts)):
        feat = extract_segment_features(text, speaker, prev_speaker)
        feat["segment_index"] = i
        feat["speaker"] = speaker
        feat["text"] = text
        all_features.append(feat)
        prev_speaker = speaker

    summary = {
        "total_segments": len(lines),
        "unique_speakers": len(set(speakers)),
        "avg_segment_length": sum(f["word_count"] for f in all_features) / max(1, len(all_features)),
        "total_questions": sum(f["has_question"] for f in all_features),
        "total_action_items": sum(f["has_action_verb"] for f in all_features),
        "total_decisions": sum(f["has_decision"] for f in all_features),
        "total_dates_mentioned": sum(f["contains_date_or_deadline"] for f in all_features),
    }

    return {"summary": summary, "segments": all_features}


def build_feature_dataframe(segments_path: Path = None) -> pd.DataFrame:
    if segments_path is None:
        segments_path = DATA_DIR / "labeled_segments.csv"

    df = pd.read_csv(segments_path)

    feature_rows = []
    prev_speaker = None
    for _, row in df.iterrows():
        feat = extract_segment_features(row["text"], row["speaker"], prev_speaker)
        feat["transcript_id"] = row["transcript_id"]
        feat["theme"] = row["theme"]
        feat["speaker"] = row["speaker"]
        feat["text"] = row["text"]
        feat["label"] = row["label"]
        feature_rows.append(feat)
        prev_speaker = row["speaker"]

    result = pd.DataFrame(feature_rows)
    result.to_csv(FEATURES_PATH, index=False)
    print(f"Extracted features for {len(result)} segments -> {FEATURES_PATH}")
    return result


if __name__ == "__main__":
    build_feature_dataframe()