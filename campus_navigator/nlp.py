"""Offline natural-language understanding: intent detection + POI entity resolution.

The offline engine is deterministic, fast and works with no network access.
The hybrid AI layer uses this output and optionally asks a cloud LLM to
disambiguate low-confidence matches and to phrase the final answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .campus import Campus, Node

_STOPWORDS = {
    "a", "an", "the", "to", "from", "at", "of", "in", "on", "for", "is", "are",
    "am", "i", "me", "my", "me", "how", "what", "where", "which", "can", "could",
    "please", "tell", "show", "find", "get", "go", "going", "want", "need", "do",
    "does", "it", "that", "this", "there", "you", "your", "with", "and", "or",
    "be", "about", "around", "near", "toward", "towards", "closest", "nearest",
}

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("greeting", ["hello", "hi ", "^hi", "hey", "good morning", "good afternoon", "good evening", "what's up"]),
    ("help", ["help", "what can you do", "commands", "how do i use", "what do you know", "assist"]),
    ("navigate", ["navigate", "directions", "direction to", "how do i get", "how to get", "route to",
                  "route from", "take me to", "way to", "get me to", "walk to", "reach", "guide me"]),
    ("parking", ["park", "parking", "where can i park", "spot available", "parking spot",
                 "parking spot", "lot", "garage", "full", "spaces free", "spots left", "vacancy"]),
    ("events", ["event", "events", "happening", "what's on", "whats on", "schedule", "upcoming",
                "today", "tonight", "going on", "concert", "talk", "symposium", "lecture schedule"]),
    ("nearest", ["nearest", "closest", "nearby", "closest parking", "near me", "around me"]),
    ("find", ["where is", "where's", "find", "locate", "where can i", "where do i", "search"]),
    ("locate_me", ["where am i", "my location", "where am", "current location", "set location"]),
]

_ORIGIN_RE = re.compile(r"\b(?:from|starting from|beginning at|leaving)\s+([\w\s.'&-]+?)(?:\s*(?:to|going to|towards|for)\b|$)", re.IGNORECASE)


@dataclass
class Query:
    intent: str = "find"
    text: str = ""
    origin_id: str | None = None
    destination_id: str | None = None
    category: str | None = None
    confidence: float = 0.0
    matched: str = ""
    candidates: list[str] = field(default_factory=list)

    @property
    def is_routable(self) -> bool:
        return self.intent in {"navigate", "find", "nearest", "parking", "events"} and self.destination_id is not None


class NLPEngine:
    def __init__(self, campus: Campus):
        self.campus = campus
        self._index = self._build_index()

    # -- text helpers ------------------------------------------------------
    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s'-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def tokens(text: str) -> list[str]:
        return [t for t in NLPEngine.normalize(text).split() if t not in _STOPWORDS and len(t) > 1]

    def _build_index(self):
        index = {}
        for nid, node in self.campus.nodes.items():
            keys = set()
            keys.add(self.normalize(node.name))
            for alias in node.aliases:
                keys.add(self.normalize(alias))
            if node.building:
                b = self.campus.buildings.get(node.building)
                if b:
                    keys.add(self.normalize(b.name))
            if node.type in {"classroom", "laboratory", "office", "parking", "venue"}:
                keys.add(node.type)
            index[nid] = keys
        return index

    # -- intent ------------------------------------------------------------
    def detect_intent(self, text: str) -> str:
        norm = self.normalize(text)
        for intent, patterns in _INTENT_PATTERNS:
            for pat in patterns:
                if re.search(pat, norm):
                    return intent
        return "find"

    # -- entity resolution -------------------------------------------------
    def resolve(self, text: str) -> tuple[str | None, float, str]:
        qtokens = self.tokens(text)
        if not qtokens:
            return None, 0.0, ""
        best_nid: str | None = None
        best_score = 0.0
        best_match = ""

        for nid, keys in self._index.items():
            node = self.campus.nodes[nid]
            score = 0.0
            matched = ""
            for qtok in qtokens:
                for key in keys:
                    key_tokens = key.split()
                    if qtok in key_tokens:
                        score += 5.0 if node.routable else 2.0
                        matched += f"{qtok} "
                        break
                    elif any(kt.startswith(qtok) or qtok.startswith(kt) for kt in key_tokens if len(kt) > 2):
                        score += 2.5 if node.routable else 1.0
                        break
            if score > best_score:
                best_score = score
                best_nid = nid
                best_match = matched.strip()

        return best_nid, best_score, best_match

    def extract_origin(self, text: str) -> str | None:
        m = _ORIGIN_RE.search(text)
        if not m:
            return None
        phrase = m.group(1).strip()
        nid, _score, _m = self.resolve(phrase)
        return nid

    # -- full parse --------------------------------------------------------
    def parse(self, text: str, default_origin: str | None = None) -> Query:
        intent = self.detect_intent(text)
        q = Query(intent=intent, text=text.strip())

        # origin: explicit "from X" first, else default (user's live location)
        explicit_origin = self.extract_origin(text)
        q.origin_id = explicit_origin or default_origin

        if intent in {"greeting", "help", "locate_me"}:
            return q

        dest_nid, score, matched = self.resolve(text)
        q.confidence = round(score, 2)
        q.matched = matched

        if intent == "parking" and dest_nid and self.campus.nodes[dest_nid].type != "parking":
            # "parking near the engineering building" -> engineering is the anchor.
            q.destination_id = dest_nid
            q.category = "parking"
            return q

        if dest_nid:
            q.destination_id = dest_nid
            q.category = self.campus.nodes[dest_nid].type
            return q

        # No entity found but the intent needs one: fall back to category keywords.
        q.category = self._category_from_text(text)
        return q

    def _category_from_text(self, text: str) -> str | None:
        norm = self.normalize(text)
        mapping = [
            ("classroom", ["classroom", "class", "lecture hall", "lecture", "seminar", "course"]),
            ("laboratory", ["lab", "laboratory", "experiment"]),
            ("office", ["office", "administrative", "dean", "advisor", "professor"]),
            ("parking", ["parking", "park", "lot", "garage"]),
            ("venue", ["auditorium", "theater", "theatre", "arena", "stadium", "venue", "event"]),
            ("landmark", ["fountain", "garden", "quad", "cafeteria", "food", "library", "bookstore"]),
        ]
        for category, keywords in mapping:
            for kw in keywords:
                if kw in norm:
                    return category
        return None

    def candidates_for(self, category: str | None, origin_id: str | None) -> list[str]:
        if category is None:
            return []
        out = []
        for nid, node in self.campus.nodes.items():
            if node.type != category or not node.routable:
                continue
            if nid == origin_id:
                continue
            out.append(nid)
        return out
