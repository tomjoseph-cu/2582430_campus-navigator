"""Hybrid AI layer.

* Offline path is fully deterministic: the NLP engine parses intent + POI, the
  router computes the path, and template replies are generated instantly.
* When OPENAI_API_KEY is set, the LLM is used to (a) disambiguate
  low-confidence POI matches and (b) phrase a friendly natural-language answer
  from the structured route/state data.  The LLM never computes routes itself —
  routing stays in the graph engine for accuracy and low latency.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from .campus import Campus, Node
from .config import AI_ENABLED, OPENAI_API_KEY, OPENAI_MODEL
from .nlp import NLPEngine, Query
from .routing import Router
from .simulator import LiveSimulator

log = logging.getLogger("campus.ai")


def _hours_from_clock(clock: str) -> tuple[int, int]:
    h, m = clock.split(":")
    return int(h), int(m)


def _template_reply(context: dict) -> str:
    """Deterministic reply used when the LLM is unavailable or fails."""
    intent = context.get("intent")
    dest = context.get("destination")
    origin = context.get("origin")
    route = context.get("route")
    lines: list[str] = []

    if intent == "events" and context.get("events"):
        now = datetime.now()
        events = [ev for ev in context["events"] if ev["status"] in {"now", "upcoming"}]
        if events:
            lines.append("Here's what's happening today:")
            for ev in events:
                marker = "Now playing" if ev["status"] == "now" else f"At {ev['start']}"
                lines.append(f"\u2022 {marker}: {ev['title']} ({ev['venue']})")
    elif intent == "parking":
        focus = context.get("parking_focus")
        if focus:
            pct = round(focus["available"] / focus["total"] * 100, 1)
            lines.append(
                f"{focus['name']} has {focus['available']} of {focus['total']} spaces free "
                f"right now ({pct}% available)."
            )
        else:
            parking = context.get("parking") or []
            if parking:
                summary = ", ".join(
                    f"{p['name']}: {p['available']}/{p['total']} free" for p in parking
                )
                lines.append(f"Live parking availability \u2014 {summary}.")

    if route and dest:
        origin_txt = f" from {origin['name']}" if origin else " from your current location"
        lines.append(
            f"Route to {dest['name']}{origin_txt}: "
            f"{route['distance_m']:.0f} m, about {route['eta_min']:.0f} min."
        )
        for step in route.get("steps", [])[:3]:
            lines.append("\u2022 " + step)
    elif dest:
        lines.append(f"I found {dest['name']} and marked it on the map.")

    if not lines:
        lines.append(
            "I didn't quite catch a destination. Try 'How do I get to the Robotics Lab?' "
            "or 'Where's the nearest parking to the Library?'"
        )
    return "\n".join(lines)


class HybridAI:
    """OpenAI wrapper with graceful offline fallback."""

    def __init__(self):
        self.model = OPENAI_MODEL
        self._client = None
        if OPENAI_API_KEY:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception as exc:  # pragma: no cover - import edge cases
                log.warning("OpenAI client init failed: %s", exc)
                self._client = None

    @property
    def available(self) -> bool:
        return bool(AI_ENABLED and self._client)

    def disambiguate(self, text: str, candidates: list[str], campus: Campus) -> str | None:
        """Ask the LLM to pick the intended POI from a shortlist. Returns a node id."""
        if not self.available or not candidates:
            return None
        shortlist = [
            {"id": nid, "name": campus.nodes[nid].name,
             "type": campus.nodes[nid].type,
             "building": campus.buildings.get(campus.nodes[nid].building or "", None).name
             if campus.nodes[nid].building in campus.buildings else None,
             "aliases": campus.nodes[nid].aliases}
            for nid in candidates[:6]
        ]
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You resolve a user's campus-navigation query to exactly one place id from the "
                                "provided JSON list. Reply with ONLY the JSON object {\"id\": \"...\"}."},
                    {"role": "user",
                     "content": f"User query: {text}\nCandidates: {json.dumps(shortlist)}"},
                ],
                temperature=0,
                max_tokens=20,
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            chosen = parsed.get("id")
            return chosen if chosen in campus.nodes else None
        except Exception as exc:
            log.warning("OpenAI disambiguation failed: %s", exc)
            return None

    def respond(self, context: dict) -> tuple[str, str]:
        """Generate the final user-facing reply.

        Returns (reply, provider) where provider is "openai" or "offline".
        """
        template = _template_reply(context)
        if not self.available:
            return template, "offline"

        prompt = (
            "You are the assistant of a real-time campus navigation app. Use ONLY the facts in the "
            "JSON context. Reply in 2-4 concise, friendly sentences. Never invent distances, times, "
            "or facts not present. If the user asked for directions, lead with the route: destination, "
            "distance, ETA and the first two steps."
        )
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(context)},
                ],
                temperature=0.3,
                max_tokens=220,
            )
            reply = resp.choices[0].message.content.strip()
            return (reply, "openai") if reply else (template, "offline")
        except Exception as exc:
            log.warning("OpenAI reply generation failed: %s", exc)
            return template, "offline"


class NavigationAssistant:
    """Orchestrates query parsing, routing and reply generation."""

    def __init__(self, campus: Campus, router: Router, simulator: LiveSimulator):
        self.campus = campus
        self.router = router
        self.simulator = simulator
        self.nlp = NLPEngine(campus)
        self.ai = HybridAI()

    # -- event helpers -----------------------------------------------------
    def _now(self) -> datetime:
        return datetime.now()

    def events_today(self) -> list[dict]:
        now = self._now()
        out = []
        for ev in self.campus.events:
            sh, sm = _hours_from_clock(ev.start)
            eh, em = _hours_from_clock(ev.end)
            start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            status = "now" if start <= now < end else ("upcoming" if start > now else "ended")
            venue = self.campus.nodes.get(ev.venue_id)
            out.append({
                "id": ev.id, "title": ev.title,
                "venue_id": ev.venue_id,
                "venue": venue.name if venue else ev.venue_id,
                "start": ev.start, "end": ev.end,
                "description": ev.description,
                "status": status,
            })
        return out

    # -- main entry point --------------------------------------------------
    def answer(self, message: str, origin: str | None = None) -> dict:
        q = self.nlp.parse(message, default_origin=origin)

        if q.intent in {"greeting", "help", "locate_me"}:
            return self._meta_reply(q)

        if q.intent == "events":
            return self._events_reply(q)

        if q.intent == "parking":
            return self._parking_reply(q)

        return self._navigation_reply(q, origin)

    # -- reply builders ----------------------------------------------------
    def _meta_reply(self, q: Query) -> dict:
        origin_node = self.campus.nodes.get(q.origin_id) if q.origin_id else None
        if q.intent == "greeting":
            template = (
                "Hello! I'm your AI campus guide for Northbrook University. Ask me things like "
                "'How do I get to the Robotics Lab?', 'Where's the nearest parking to the Library?' "
                "or 'What's happening at the Auditorium today?'"
            )
            provider = "offline"
        elif q.intent == "locate_me":
            template = (
                f"Your current location is set to {origin_node.name}."
                if origin_node else
                "Pick your current location on the map, or say 'from Main Hall' in your query."
            )
            provider = "offline"
        else:
            template = (
                "I can help you navigate the campus in real time:\n\n"
                "\u2022 Directions — 'How do I get to the Chemistry Lab?'\n"
                "\u2022 Parking — 'Where can I park near the Engineering Center?'\n"
                "\u2022 Events — 'What's happening today at the Arena?'\n"
                "\u2022 Places — 'Where is the Student Health Center?'\n\n"
                "Tap any building on the map to set a destination, or pick your location and ask."
            )
            provider = "offline"
        return {
            "intent": q.intent,
            "reply": template,
            "provider": provider,
            "destination": None,
            "origin": self._node_brief(origin_node),
            "route": None,
        }

    def _events_reply(self, q: Query) -> dict:
        events = self.events_today()
        reply = "Here's what's on at Northbrook today:"
        lines = []
        for ev in events:
            marker = {"now": "\u25b6 Now", "upcoming": "At", "ended": "Earlier"} [ev["status"]]
            lines.append(f"{marker} {ev['start']}\u2013{ev['end']}: {ev['title']} ({ev['venue']})")
        reply += "\n" + "\n".join(lines) if lines else " Nothing scheduled."

        # If a venue was mentioned, offer directions to it.
        route = None
        dest = None
        if q.destination_id:
            origin_node = self.campus.nodes.get(q.origin_id) if q.origin_id else None
            dest = self._node_brief(self.campus.nodes[q.destination_id])
            try:
                start_id = q.origin_id or self._pick_default_origin(q)
                if start_id:
                    path, dist = self.router.route(start_id, q.destination_id)
                    route = self.router.summarize(path, dist)
                    reply += f"\n\nRoute to {dest['name']} ready \u2014 {route['distance_m']:.0f} m, about {route['eta_min']:.0f} min."
            except ValueError:
                pass

        return {
            "intent": "events",
            "reply": reply,
            "provider": "offline",
            "destination": dest,
            "origin": self._node_brief(self.campus.nodes.get(q.origin_id)) if q.origin_id else None,
            "route": route,
            "events": events,
        }

    def _parking_reply(self, q: Query) -> dict:
        anchor = self.campus.nodes.get(q.destination_id) if q.destination_id else None
        lots = self._parking_with_availability()
        reply_lines: list[str] = []

        if anchor and anchor.type == "parking":
            # The user asked about a specific lot ("is the East Garage full?").
            info = lots[anchor.id]
            route = self._route_between(q.origin_id, anchor.id)
            origin_node = self.campus.nodes.get(q.origin_id) if q.origin_id else None
            pct = round(info["available"] / info["total"] * 100)
            line = (
                f"{anchor.name} has {info['available']} of {info['total']} spaces free "
                f"right now ({pct}% available)."
            )
            if route:
                line += f" It's {route['distance_m']:.0f} m from your location, about {route['eta_min']:.0f} min."
            reply_lines.append(line)
            reply = self._ai_enhance(q, None, route, destination_node=anchor, origin_node=origin_node)
            return {
                "intent": "parking",
                "reply": reply,
                "provider": self._provider,
                "destination": self._node_brief(anchor),
                "origin": self._node_brief(origin_node) if origin_node else None,
                "route": route,
                "parking": info,
            }

        if anchor and anchor.type != "parking":
            # Nearest parking to the mentioned building/place.
            nearest = self.router.nearest(q.destination_id, {"parking"})
            if not nearest:
                return self._fallback("No parking found near that location.")
            nid, dist = nearest[0]
            lot = self.campus.nodes[nid]
            info = lots.get(nid)
            reply_lines.append(
                f"The nearest parking to {anchor.name} is {lot.name}, {dist:.0f} m away "
                f"({info['available']} of {info['total']} spaces free)."
            )
            route = self._route_between(q.destination_id, nid)
            q.destination_id = nid
            q.origin_id = anchor.id
            reply = "\n".join(reply_lines)
            reply = self._ai_enhance(q, reply, route, destination_node=lot)
            return {
                "intent": "parking",
                "reply": reply,
                "provider": self._provider,
                "destination": self._node_brief(lot),
                "origin": self._node_brief(anchor),
                "route": route,
                "parking": info,
            }

        # No anchor: show live availability of all lots, nearest first.
        origin_node = self.campus.nodes.get(q.origin_id) if q.origin_id else None
        order = []
        if q.origin_id:
            order = self.router.nearest(q.origin_id, {"parking"})
        else:
            order = [(nid, 0.0) for nid in lots]
        for nid, dist in order:
            info = lots[nid]
            label = self.campus.nodes[nid].name
            dpart = f" \u2014 {dist:.0f} m from you" if dist else ""
            reply_lines.append(f"\u2022 {label}: {info['available']}/{info['total']} free{dpart}")
        reply = "Live parking availability:\n" + "\n".join(reply_lines)

        # Auto-route to the closest lot with free spaces.
        target = None
        for nid, _dist in order:
            if lots[nid]["available"] > 0:
                target = nid
                break
        route = self._route_between(q.origin_id, target) if target and q.origin_id else None
        q.destination_id = target
        target_node = self.campus.nodes[target] if target else None
        reply = self._ai_enhance(q, reply, route, destination_node=target_node)
        return {
            "intent": "parking",
            "reply": reply,
            "provider": self._provider,
            "destination": self._node_brief(target_node) if target_node else None,
            "origin": self._node_brief(origin_node) if origin_node else None,
            "route": route,
            "parking": lots.get(target),
        }

    def _navigation_reply(self, q: Query, raw_origin: str | None) -> dict:
        # Resolve the destination; if confidence is low, let the LLM disambiguate.
        dest_node = self.campus.nodes.get(q.destination_id) if q.destination_id else None

        if q.confidence < 3.0 and q.intent in {"find", "navigate"}:
            candidates = self.nlp.candidates_for(q.category, q.origin_id) or list(self.campus.nodes)
            if self.ai.available and len(candidates) > 1:
                chosen = self.ai.disambiguate(q.text, candidates, self.campus)
                if chosen:
                    dest_node = self.campus.nodes[chosen]
                    q.destination_id = chosen
                    q.confidence = 5.0

        if dest_node is None:
            if q.category:
                options = self.nlp.candidates_for(q.category, q.origin_id)
                names = [self.campus.nodes[nid].name for nid in options[:5]]
                hint = ", ".join(names) if names else "anything yet"
                reply = f"I couldn't pinpoint a specific place. Try being more specific \u2014 I know about {hint}."
                return {
                    "intent": q.intent,
                    "reply": reply,
                    "provider": "offline",
                    "destination": None,
                    "origin": self._node_brief(self.campus.nodes.get(q.origin_id)) if q.origin_id else None,
                    "route": None,
                }

        start_id = q.origin_id or raw_origin or self._pick_default_origin(q)
        origin_node = self.campus.nodes.get(start_id) if start_id else None

        if dest_node is None:
            return self._fallback("I couldn't find that place. Ask for a building, lab, office, lot or venue.")

        route = self._route_between(start_id, dest_node.id)
        if route is None:
            return self._fallback(f"Sorry, I couldn't compute a route to {dest_node.name}.")

        reply = self._ai_enhance(q, None, route, destination_node=dest_node, origin_node=origin_node)
        return {
            "intent": q.intent,
            "reply": reply,
            "provider": self._provider,
            "destination": self._node_brief(dest_node),
            "origin": self._node_brief(origin_node) if origin_node else None,
            "route": route,
        }

    # -- helpers -----------------------------------------------------------
    def _pick_default_origin(self, q: Query) -> str | None:
        # Fall back to the fountain (campus center) so routing always works.
        if "fountain" in self.campus.nodes:
            return "fountain"
        return next(iter(self.campus.nodes))

    def _route_between(self, start_id: str | None, goal_id: str | None) -> dict | None:
        if not start_id or not goal_id:
            return None
        try:
            path, dist = self.router.route(start_id, goal_id)
            return self.router.summarize(path, dist)
        except ValueError:
            return None

    def _parking_with_availability(self) -> dict:
        snap = self.simulator.snapshot()
        return snap["parking"]

    def _node_brief(self, node: Node | None) -> dict | None:
        if node is None:
            return None
        return {
            "id": node.id, "name": node.name, "type": node.type,
            "x": node.x, "y": node.y,
            "description": node.description,
            "building": node.building,
        }

    def _fallback(self, message: str) -> dict:
        return {
            "intent": "unknown",
            "reply": message,
            "provider": "offline",
            "destination": None,
            "origin": None,
            "route": None,
        }

    def _ai_enhance(self, q: Query, fallback: str | None,
                    route: dict | None = None,
                    destination_node: Node | None = None,
                    origin_node: Node | None = None) -> str:
        context = {
            "query": q.text,
            "intent": q.intent,
            "destination": self._node_brief(destination_node),
            "origin": self._node_brief(origin_node),
            "route": {
                "distance_m": route["distance_m"] if route else None,
                "eta_min": route["eta_min"] if route else None,
                "steps": (route["steps"][1:4] if route and route.get("steps") else []),
            } if route else None,
        }
        if q.intent == "parking":
            lots = self._parking_with_availability()
            context["parking"] = [
                {
                    "name": self.campus.nodes[nid].name,
                    "available": info["available"],
                    "total": info["total"],
                }
                for nid, info in lots.items()
            ]
            if destination_node and destination_node.type == "parking":
                info = lots.get(destination_node.id)
                if info:
                    context["parking_focus"] = {
                        "name": destination_node.name,
                        "available": info["available"],
                        "total": info["total"],
                    }
        if q.intent == "events":
            context["events"] = self.events_today()

        reply, self._provider = self.ai.respond(context)
        if fallback and not reply:
            reply = fallback
        return reply

    # -- state -------------------------------------------------------------
    @property
    def ai_provider_status(self) -> dict:
        return {
            "provider": "openai" if self.ai.available else "offline",
            "model": self.ai.model if self.ai.available else "built-in rule-based NLP",
            "enabled": AI_ENABLED,
        }
