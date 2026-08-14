"""Graph routing engine: A* shortest path + turn-by-turn directions."""

from __future__ import annotations

import heapq
import math

from .campus import Campus, Node, manhattan
from .config import WALK_SPEED_MPS

COMPASS = ["East", "Northeast", "North", "Northwest", "West", "Southwest", "South", "Southeast"]


def compass_dir(dx: float, dy: float) -> str:
    ang = math.degrees(math.atan2(dy, dx))
    idx = int(round(((ang + 360.0) % 360.0) / 45.0)) % 8
    return COMPASS[idx]


def _wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


class Router:
    """Holds the campus graph and computes shortest paths under live congestion."""

    def __init__(self, campus: Campus):
        self.campus = campus
        self.nodes = campus.nodes
        self.adj: dict[str, list[tuple[str, float, str]]] = {nid: [] for nid in self.nodes}
        self.edge_names: dict[tuple[str, str], str] = {}
        self.base_weights: dict[tuple[str, str], float] = {}

        for a, b, name in campus.edges:
            na, nb = self.nodes[a], self.nodes[b]
            w = manhattan(na, nb)
            if w <= 0:
                w = 8.0
            self.adj[a].append((b, w, name))
            self.adj[b].append((a, w, name))
            self.base_weights[(a, b)] = w
            self.base_weights[(b, a)] = w
            self.edge_names[(a, b)] = name
            self.edge_names[(b, a)] = name

        self.congestion: dict[tuple[str, str], float] = {}

    # -- congestion --------------------------------------------------------
    def set_congestion(self, edge_factor_map: dict[str, float]) -> None:
        """edge_factor_map: key 'a->b' (both directions stored) -> 0..1 factor."""
        self.congestion = {}
        for key, factor in edge_factor_map.items():
            a, _, b = key.partition("->")
            if a in self.nodes and b in self.nodes:
                self.congestion[(a, b)] = max(0.0, min(1.0, factor))
                self.congestion[(b, a)] = max(0.0, min(1.0, factor))

    def _weight(self, a: str, b: str) -> float:
        base = self.base_weights[(a, b)]
        return base * (1.0 + self.congestion.get((a, b), 0.0))

    def edge_name(self, a: str, b: str) -> str:
        return self.edge_names.get((a, b), "")

    # -- pathfinding -------------------------------------------------------
    def route(self, start: str, goal: str):
        """A* search. Returns (path_ids, weighted_distance)."""
        if start not in self.nodes or goal not in self.nodes:
            raise ValueError("Unknown node id")
        if start == goal:
            return [start], 0.0

        def heuristic(nid: str) -> float:
            return manhattan(self.nodes[nid], self.nodes[goal])

        open_heap: list[tuple[float, float, str]] = []
        g_score = {start: 0.0}
        came_from: dict[str, str] = {}
        start_key = (heuristic(start), 0.0, start)
        heapq.heappush(open_heap, start_key)
        closed: set[str] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == goal:
                break
            closed.add(current)
            for nxt, _base, _name in self.adj[current]:
                if nxt in closed:
                    continue
                tentative = g_score[current] + self._weight(current, nxt)
                if tentative < g_score.get(nxt, float("inf")):
                    g_score[nxt] = tentative
                    came_from[nxt] = current
                    heapq.heappush(open_heap, (tentative + heuristic(nxt), tentative, nxt))
        else:
            raise ValueError("No route found")

        path = [goal]
        while path[-1] != start:
            path.append(came_from[path[-1]])
        path.reverse()
        total = g_score[goal]
        return path, total

    # -- directions --------------------------------------------------------
    def directions(self, path: list[str]) -> tuple[list[str], list[str]]:
        """Return (turn-by-turn steps, names of landmarks passed along the way)."""
        steps: list[str] = []
        landmarks: list[str] = []
        if not path:
            return steps, landmarks

        origin = self.nodes[path[0]]
        goal = self.nodes[path[-1]]
        steps.append(f"Start at {origin.name}.")

        for i in range(1, len(path)):
            a, b = self.nodes[path[i - 1]], self.nodes[path[i]]
            seg_dir = compass_dir(b.x - a.x, b.y - a.y).lower()
            ename = self.edge_name(path[i - 1], path[i]) or "the walkway"

            if i == 1:
                steps.append(f"Head {seg_dir} along {ename}.")
            else:
                prev = self.nodes[path[i - 2]]
                prev_ang = math.degrees(math.atan2(a.y - prev.y, a.x - prev.x))
                cur_ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
                delta = _wrap180(cur_ang - prev_ang)
                label = a.name if a.name != "Path Intersection" else "the intersection"
                if abs(delta) >= 22:
                    turn = "right" if delta < 0 else "left"
                    steps.append(f"At {label}, turn {turn} toward the {seg_dir} on {ename}.")
                else:
                    steps.append(f"Continue {seg_dir} along {ename}.")

        for nid in path[1:-1]:
            node = self.nodes[nid]
            if node.type == "landmark" and node.name not in {origin.name, goal.name}:
                landmarks.append(node.name)

        steps.append(f"Arrive at {goal.name}. You've reached your destination.")
        return steps, landmarks

    def summarize(self, path: list[str], weighted_distance: float) -> dict:
        eta_min = weighted_distance / WALK_SPEED_MPS / 60.0
        steps, landmarks = self.directions(path)
        return {
            "path_ids": path,
            "path": [
                {"id": nid, "name": self.nodes[nid].name, "type": self.nodes[nid].type,
                 "x": self.nodes[nid].x, "y": self.nodes[nid].y}
                for nid in path
            ],
            "distance_m": round(weighted_distance, 1),
            "eta_min": round(eta_min, 1),
            "steps": steps,
            "landmarks": landmarks,
        }

    def nearest(self, node_id: str, types: set[str]) -> list[tuple[str, float]]:
        """Return routable nodes of the given types ranked by weighted distance."""
        results = []
        origin = self.nodes[node_id]
        for nid, node in self.nodes.items():
            if node.type not in types or nid == node_id:
                continue
            try:
                _path, dist = self.route(node_id, nid)
            except ValueError:
                continue
            results.append((nid, dist))
        results.sort(key=lambda t: t[1])
        return results
