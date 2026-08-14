# Campus Navigator — AI-powered real-time campus navigation

An AI-powered campus navigation system that gives **real-time directions to
classrooms, laboratories, offices, parking areas and event venues** on a
simulated university campus ("Northbrook University").

* **Web app** — interactive SVG campus map + AI chat assistant (FastAPI backend,
  no-build vanilla JS frontend).
* **AI hybrid layer** — a fast, deterministic offline NLP engine that works with
  zero configuration, upgraded automatically to **OpenAI (GPT)** for
  disambiguation and natural-language replies when `OPENAI_API_KEY` is set.
* **Real-time simulation** — live parking availability and walkway congestion
  that continuously affect the routes and ETAs the AI reports.

> The LLM is deliberately never used for pathfinding: routing runs on an A*
> graph engine for accuracy and low latency. The AI handles natural-language
> understanding and phrasing, which is the feasible split for a navigation use
> case.

---

## Quick start

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

(or just double-click `run.bat`, which provisions the venv and starts the app.)

Open http://127.0.0.1:8000 in your browser.

### Optional: enable the OpenAI layer

Set one environment variable before launching:

```bat
set OPENAI_API_KEY=sk-...
python run.py
```

With a key present, the AI pill in the header shows the active model
(`gpt-4o-mini` by default, override with `OPENAI_MODEL`). Without a key the
app still works fully using the built-in offline NLP.

---

## How it works

```
   user text
      │
   NLPEngine (offline) ── intent + entity resolution ──┐
      │                                                │
      │  low confidence? ──► HybridAI.disambiguate (GPT) 
      ▼                                                │
   Router (A* on campus graph, live congestion weights) │
      │                                                │
      ▼                                                ▼
   Directions + ETA        HybridAI.respond (GPT) or template
      └──────────────► JSON to web app (reply, route, live state)
```

### Modules

| File | Role |
|---|---|
| `campus_navigator/campus.py` | Campus data model + built-in sample campus (buildings, rooms, lots, venues, events, walkways) |
| `campus_navigator/routing.py` | Undirected graph, A* shortest path, turn-by-turn directions, nearest-POI |
| `campus_navigator/nlp.py` | Offline intent detection + fuzzy POI entity resolution |
| `campus_navigator/simulator.py` | Live thread simulating parking availability + walkway congestion |
| `campus_navigator/ai.py` | Hybrid AI layer (OpenAI wrapper + offline fallback) and the navigation assistant orchestrator |
| `campus_navigator/api.py` | FastAPI app with REST endpoints |
| `static/` | Frontend: SVG map renderer, chat UI, live updates |

### REST API

| Endpoint | Description |
|---|---|
| `GET /api/campus` | Full campus graph for the map renderer |
| `GET /api/state` | Live snapshot (parking availability, congestion) |
| `GET /api/search?q=` | POI search |
| `POST /api/route` | Route `{origin, destination}` |
| `POST /api/chat` | Chat `{message, origin?}` → reply + route + live data |
| `GET /api/health` | Status + active AI provider |

Interactive API docs at http://127.0.0.1:8000/docs.

### Example queries

* "How do I get to the Robotics Lab?"
* "Where can I park near the Engineering Center?"
* "Is the East Garage full?"
* "What's happening at the Arena today?"
* "Navigate to the Chemistry Lab from Main Hall"
* "Where is the Student Health Center?"

### Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Enables the GPT hybrid layer |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used by the hybrid layer |
| `CAMPUS_HOST` / `CAMPUS_PORT` | `127.0.0.1` / `8000` | Bind address |
| `CAMPUS_WALK_SPEED` | `1.4` | Walking speed in m/s used for ETAs |
| `CAMPUS_TICK` | `5` | Live-simulation tick in seconds |
| `CAMPUS_AI_ENABLED` | `true` | Master switch for the AI layer |
