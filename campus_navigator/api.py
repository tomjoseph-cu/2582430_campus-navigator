"""FastAPI application: REST endpoints for campus data, routing, live state and chat."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .ai import NavigationAssistant
from .campus import TYPE_COLORS, CATEGORY_LABELS, build_campus
from .config import CAMPUS_NAME, HOST, PORT
from .routing import Router
from .simulator import LiveSimulator

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Campus Navigator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- singletons -----------------------------------------------------------
campus = build_campus()
router = Router(campus)
simulator = LiveSimulator(campus)
assistant = NavigationAssistant(campus, router, simulator)


@app.on_event("startup")
async def _startup():
    simulator.start()
    router.set_congestion(simulator.congestion_factors())


@app.on_event("shutdown")
async def _shutdown():
    simulator.stop()


# --- models ---------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    origin: str | None = None


class RouteRequest(BaseModel):
    origin: str
    destination: str


# --- helpers --------------------------------------------------------------
def _publish_node(node) -> dict:
    return {
        "id": node.id,
        "name": node.name,
        "type": node.type,
        "x": node.x,
        "y": node.y,
        "building": node.building,
        "floor": node.floor,
        "description": node.description,
        "aliases": node.aliases,
        "capacity": node.capacity,
        "routable": node.routable,
    }


# --- endpoints ------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "campus": CAMPUS_NAME,
        "ai": assistant.ai_provider_status,
        "tick": simulator.tick,
    }


@app.get("/api/campus")
def get_campus():
    """Full campus graph for the client map renderer."""
    edges = []
    for a, b, name in campus.edges:
        na, nb = campus.nodes[a], campus.nodes[b]
        base = abs(na.x - nb.x) + abs(na.y - nb.y) or 8.0
        edges.append({"a": a, "b": b, "name": name, "length_m": base})
    return {
        "name": campus.name,
        "width": campus.width,
        "height": campus.height,
        "nodes": {nid: _publish_node(node) for nid, node in campus.nodes.items()},
        "buildings": [
            {
                "id": b.id, "name": b.name, "x": b.x, "y": b.y, "w": b.w, "h": b.h,
                "category": b.category, "color": b.color, "gate": b.gate_id,
            }
            for b in campus.buildings.values()
        ],
        "edges": edges,
        "events": assistant.events_today(),
        "type_colors": TYPE_COLORS,
        "categories": CATEGORY_LABELS,
        "suggestions": [
            "How do I get to the Robotics Lab?",
            "Where can I park near the Engineering Center?",
            "What's happening at the Arena today?",
            "Where is the Student Health Center?",
            "Navigate to the Chemistry Lab from Main Hall",
            "Is the East Garage full?",
        ],
    }


@app.get("/api/state")
def get_state():
    """Live snapshot: parking availability + walkway congestion."""
    snap = simulator.snapshot()
    router.set_congestion(simulator.congestion_factors())
    snap["congestion"] = {
        f"{a}->{b}": factor
        for (a, b), factor in router.congestion.items()
        if a < b
    }
    return snap


@app.get("/api/search")
def search(q: str = ""):
    if not q.strip():
        return {"results": []}
    query = assistant.nlp.parse(q)
    results = []
    for nid, node in campus.nodes.items():
        if not node.routable:
            continue
        results.append(_publish_node(node))
    # simple ranked filter by token overlap
    toks = assistant.nlp.tokens(q)
    scored = []
    for item in results:
        haystack = " ".join([item["name"], item["type"], " ".join(item["aliases"]),
                             item.get("building") or ""]).lower()
        s = sum(1 for t in toks if t in haystack)
        if s:
            scored.append((s, item))
    scored.sort(key=lambda x: -x[0])
    return {"results": [r for _, r in scored[:8]]}


@app.post("/api/route")
def compute_route(body: RouteRequest):
    if body.origin not in campus.nodes or body.destination not in campus.nodes:
        raise HTTPException(status_code=404, detail="Unknown node id")
    try:
        path, dist = router.route(body.origin, body.destination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "origin": _publish_node(campus.nodes[body.origin]),
        "destination": _publish_node(campus.nodes[body.destination]),
        "route": router.summarize(path, dist),
    }


@app.post("/api/chat")
def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Empty message")
    result = assistant.answer(body.message, origin=body.origin)
    result["suggestions"] = get_campus()["suggestions"]
    return result


# --- static assets ----------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def run():
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    run()
