# Campus Navigator — AI-Powered Real-Time Campus Navigation

> An intelligent web application that provides **real-time, natural-language directions** to classrooms, laboratories, offices, parking areas, and event venues across a university campus.

---

## Project Overview

Navigating a large university campus is a daily challenge for students, faculty, and visitors alike. Finding the right classroom, locating available parking, or discovering today's campus events often requires juggling multiple apps, maps, and notices. **Campus Navigator** solves this by combining an interactive campus map with an AI-powered chat assistant that understands natural language and provides instant, real-time directions.

The system is built around a key principle: **the AI understands what the user asks, while a deterministic graph engine computes the route**. This separation ensures that directions are always fast and accurate, while the conversational interface makes the system feel natural and accessible to anyone.

---

## What This System Does

- **Interactive Campus Map** — A full SVG-rendered campus map showing all buildings, classrooms, labs, offices, parking lots, and event venues with labeled locations and color-coded categories.
- **AI Chat Assistant** — Ask questions in plain English like *"How do I get to the Robotics Lab?"* or *"Where can I park near the Engineering Center?"* and receive instant turn-by-turn directions.
- **Real-Time Parking Availability** — Live simulation of parking lot occupancy across four lots, with dynamic ETAs that account for current availability.
- **Walkway Congestion Awareness** — Path weights adjust in real time as simulated foot traffic congestion rises and falls, so routes and ETAs stay accurate.
- **Campus Event Awareness** — The system tracks scheduled events (symposia, career fairs, lectures, performances) and can route you directly to the venue.
- **Optional Cloud AI Upgrade** — Set an OpenAI API key to unlock GPT-powered disambiguation and natural-language response generation, while the core routing stays local and deterministic.

---

## Key Design Decision: Why This AI Split?

A naive approach would send every user query to an LLM and ask it to compute the route. This is problematic: LLMs can hallucinate distances, invent buildings, and add seconds-to-minutes of latency per query.

**Campus Navigator takes a different approach:**

| Concern | Handled By | Why |
|---|---|---|
| Understanding user intent | NLP Engine (offline) + LLM (optional) | Fast keyword matching for common queries; LLM disambiguates rare cases |
| Resolving place names | Fuzzy token matching + LLM fallback | Handles aliases ("chem lab" → Chemistry Lab A) and typos |
| Computing the shortest path | A* graph search (deterministic) | Guarantees optimal routes with real-world distances and live congestion |
| Generating directions text | Template engine + LLM (optional) | Templates are instant and reliable; LLM adds conversational polish |

The **LLM never computes a route**. It only helps with language understanding and phrasing. This means the system works offline at full speed by default, and the AI only enhances what the graph engine already guarantees.

---

## Architecture

### How a User Query Flows Through the System

```
User types: "How do I get to the Robotics Lab from the Library?"
                          │
                          ▼
              ┌──────────────────────┐
              │   Frontend (app.js)  │  Sends POST /api/chat with message + origin
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  FastAPI Backend     │  Orchestrates parsing, routing, reply
              │  (api.py)            │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐
   │  NLP Engine│ │   Router   │ │  Simulator │
   │  (nlp.py)  │ │(routing.py)│ │(simulator) │
   │            │ │            │ │            │
   │ Intent:    │ │ A* shortest│ │ Parking    │
   │ navigate   │ │ path with  │ │ spots +    │
   │ Dest:      │ │ live       │ │ walkway    │
   │ eng_robot  │ │ congestion │ │ congestion │
   │ Origin:    │ │ weights    │ │ factors    │
   │ lib_gate   │ │            │ │            │
   └─────┬──────┘ └─────┬──────┘ └────────────┘
         │              │
         ▼              ▼
   ┌──────────────────────────────┐
   │     Hybrid AI (ai.py)        │
   │                              │
   │  If OpenAI key present:      │
   │    → GPT generates friendly  │
   │      response from structured│
   │      route data              │
   │  Else:                       │
   │    → Template-based reply    │
   └──────────────┬───────────────┘
                  │
                  ▼
   ┌──────────────────────────────┐
   │   JSON Response to Frontend  │
   │  { reply, route, destination,│
   │    origin, parking, events } │
   └──────────────┬───────────────┘
                  │
                  ▼
   ┌──────────────────────────────┐
   │   Frontend renders:          │
   │  • Animated route on map     │
   │  • Turn-by-turn directions   │
   │  • Distance + ETA card       │
   │  • AI provider badge         │
   └──────────────────────────────┘
```

### The Virtual Campus

The built-in sample campus models **Northbrook University** with:

| Metric | Count |
|---|---|
| Buildings | 11 |
| Routable locations (POIs) | 40+ |
| Walkway segments | 75 |
| Live events | 6 |
| Parking lots | 4 (total 930 spaces) |
| Location categories | 6 (Classrooms, Labs, Offices, Parking, Venues, Landmarks) |

**Buildings included:**
Main Hall (Administration) · University Library · Student Union · Science Hall · Engineering Center · Fine Arts Building · Business School · Health Sciences Center · Grand Auditorium · Eastfield Arena · Convention Hall

**Each building contains** internal rooms — classrooms, laboratories, offices, and event spaces — each with its own coordinates, capacity, description, and multiple searchable aliases.

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI + Uvicorn | High-performance async framework; automatic OpenAPI docs; ideal for real-time APIs |
| **AI — Offline** | Custom NLP engine (rule-based + fuzzy matching) | Zero-dependency, deterministic, sub-millisecond response; works without network |
| **AI — Cloud** | OpenAI GPT (gpt-4o-mini) | Natural-language disambiguation + conversational response generation |
| **Routing** | A* algorithm on weighted graph | Optimal shortest path with live congestion weights; O(E log V) performance |
| **Simulation** | Python threading + random-walk models | Background thread updates parking/congestion every 5 seconds |
| **Frontend** | Vanilla JavaScript + SVG | Zero build step, instant load, full interactivity |
| **Styling** | Custom CSS (no framework) | Lightweight, responsive grid layout, dark/light accents |

---

## Project Structure

```
campus-navigator/
├── campus_navigator/            # Python package — all backend logic
│   ├── __init__.py
│   ├── config.py                # Environment variable configuration
│   ├── campus.py                # Campus data model + sample campus builder
│   ├── routing.py               # A* graph engine + turn-by-turn directions
│   ├── nlp.py                   # Offline NLP: intent detection + POI resolution
│   ├── simulator.py             # Live parking + congestion simulation (threaded)
│   ├── ai.py                    # Hybrid AI layer (OpenAI + offline fallback)
│   └── api.py                   # FastAPI application + REST endpoints
├── static/                      # Frontend — served by FastAPI
│   ├── index.html               # App shell (map + chat layout)
│   ├── app.js                   # Map renderer, chat client, live polling
│   └── style.css                # Responsive UI styling
├── run.py                       # Application entry point
├── run.bat                      # Windows one-click launcher
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## REST API

The backend exposes a clean REST API. Interactive documentation is auto-generated at **http://127.0.0.1:8000/docs**.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/campus` | Full campus graph: nodes, buildings, edges, events, type colors |
| `GET` | `/api/state` | Live snapshot: parking availability per lot, walkway congestion factors |
| `GET` | `/api/search?q=` | Search POIs by name, type, or alias |
| `POST` | `/api/route` | Compute route: `{ origin, destination }` → path, distance, ETA, steps |
| `POST` | `/api/chat` | AI chat: `{ message, origin? }` → reply, route, destination, events |
| `GET` | `/api/health` | System status + which AI provider is active |

---

## Example Queries

| User says | System understands | Response |
|---|---|---|
| *"How do I get to the Robotics Lab?"* | Intent: navigate, Dest: Robotics Lab | Route from current location: 424 m, 5 min. Head north along Quad Path → turn right on Quad Walkway → turn right on East Avenue |
| *"Where can I park near the Engineering Center?"* | Intent: parking, Anchor: Engineering Center | Nearest lot: East Garage, 359 m away, 181/350 spaces free |
| *"Is the East Garage full?"* | Intent: parking, Dest: East Garage | East Garage has 181 of 350 spaces free (52% available) |
| *"What's happening at the Arena today?"* | Intent: events, Venue: Eastfield Arena | Homecoming Basketball at 19:00–21:30. Route to Arena: 518 m, 6 min |
| *"Navigate to Chemistry Lab A from the Library"* | Intent: navigate, Origin: Library, Dest: Chem Lab A | Route from University Library: 554 m, 7 min |
| *"Where is the Student Health Center?"* | Intent: find, Dest: Health Center | Location found + route: 403 m, 5 min from campus center |

---

## Live Simulation

The system includes a **real-time simulation engine** that runs as a background thread:

### Parking Availability
- 4 parking lots with capacities ranging from 120 (West Lot) to 350 (East Garage)
- Spot counts drift every 5 seconds based on a time-of-day model:
  - **Morning (before 8 AM):** lots are mostly empty (~25% occupancy)
  - **Late morning:** spots fill rapidly (~85% occupancy)
  - **Afternoon/evening:** spots gradually free up (~45% occupancy)
- Parking counts are displayed live on the map and affect routing recommendations

### Walkway Congestion
- Each of the 75 walkway segments has a congestion factor (0.0 = empty → 0.9 = very busy)
- Congestion drifts randomly each tick, simulating foot traffic patterns
- **Routes dynamically recalculate** with congestion-weighted distances, so the AI avoids congested paths when possible
- ETAs increase proportionally: a path at 0.6 congestion takes 60% longer than the same path when empty

---

## Quick Start

### Prerequisites
- **Python 3.10+** installed on your system

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/tomjoseph-cu/campus-navigator.git
cd campus-navigator

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
python run.py
```

**Or on Windows**, simply double-click `run.bat` — it handles steps 2–4 automatically.

Open **http://127.0.0.1:8000** in your browser to see the campus map and start navigating.

---

## Optional: Enable the OpenAI Layer

The app works fully offline by default. To unlock GPT-powered natural-language responses:

```bash
# Set your OpenAI API key before launching
set OPENAI_API_KEY=sk-your-key-here
python run.py
```

- The **AI pill** in the header will show the active model name (default: `gpt-4o-mini`)
- Without a key, the app uses the built-in offline NLP engine — no functionality is lost
- The LLM is only used for **language understanding and response phrasing**; routing always runs on the local A* engine

---

## Configuration

All settings are controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Enables the OpenAI hybrid layer when set |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for disambiguation and response generation |
| `CAMPUS_HOST` | `127.0.0.1` | Server bind address |
| `CAMPUS_PORT` | `8000` | Server port |
| `CAMPUS_WALK_SPEED` | `1.4` | Walking speed in m/s (used for ETA calculation) |
| `CAMPUS_TICK` | `5` | Live simulation update interval in seconds |
| `CAMPUS_AI_ENABLED` | `true` | Master switch for the AI layer |
| `CAMPUS_NAME` | `Northbrook University` | Campus name shown in the UI |

---

## Future Enhancements

These extensions would make the system production-ready for a real campus:

- **Real GPS Integration** — Replace the simulated origin with phone GPS / Wi-Fi positioning for automatic "where am I" detection
- **Multi-Floor Navigation** — Extend the graph model with floor transitions (elevators, stairs) for indoor routing in multi-story buildings
- **Mobile App** — Build a React Native / Flutter companion app with push notifications for event reminders and parking alerts
- **Accessibility Routes** — Add wheelchair-accessible paths (ramps, elevators, automatic doors) as a routing constraint
- **Campus Database Integration** — Pull real class schedules, room bookings, and parking sensor data from the university's existing systems
- **Multi-Language Support** — Extend the NLP layer to handle queries in multiple languages for international students
- **Voice Interface** — Add speech-to-text input for hands-free navigation while walking

---

## License

This project was developed as an academic project. For usage rights, contact the repository owner.

---

*Built with Python, FastAPI, and vanilla JavaScript — no heavy frameworks, no build steps, just a working campus navigator.*
