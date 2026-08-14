"""Live simulator: models parking availability and walkway congestion in real time.

A background thread ticks periodically so the API always serves a "live" snapshot.
The snapshots drive parking spot counts and dynamic path weights used by the router.
"""

from __future__ import annotations

import random
import threading
import time

from .campus import Campus
from .config import TICK_SECONDS


class LiveSimulator:
    def __init__(self, campus: Campus, tick: float = TICK_SECONDS):
        self.campus = campus
        self.tick = tick
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self.parking: dict[str, int] = {}
        for nid, node in campus.nodes.items():
            if node.type == "parking" and node.capacity:
                self.parking[nid] = int(node.capacity * random.uniform(0.45, 0.8))
                node.spots_total = node.capacity

        self.congestion: dict[tuple[str, str], float] = {}
        self._cong_factor: dict[tuple[str, str], float] = {}
        for a, b, _name in campus.edges:
            pair = tuple(sorted((a, b)))
            self._cong_factor[pair] = random.uniform(0.0, 0.3)

    # -- public API --------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="live-simulator", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def snapshot(self) -> dict:
        with self._lock:
            parking = {
                nid: {
                    "available": available,
                    "total": self.campus.nodes[nid].capacity,
                    "pct": round(available / self.campus.nodes[nid].capacity, 3),
                }
                for nid, available in self.parking.items()
            }
            congestion = {
                f"{a}->{b}": round(factor, 3)
                for (a, b), factor in self._cong_factor.items()
            }
            return {
                "ts": time.time(),
                "tick": self.tick,
                "parking": parking,
                "congestion": congestion,
            }

    def congestion_factors(self) -> dict[str, float]:
        return {
            f"{a}->{b}": factor
            for (a, b), factor in self._cong_factor.items()
        }

    # -- simulation internals ---------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                pass
            self._stop.wait(self.tick)

    def _tick(self) -> None:
        with self._lock:
            # Parking: spots slowly free up and fill back up around a daily baseline.
            hour = time.localtime().tm_hour
            if hour < 8 or hour > 20:
                baseline = 0.25
            elif hour < 11:
                baseline = 0.15
            else:
                baseline = 0.55

            for nid, node in self.campus.nodes.items():
                if nid not in self.parking:
                    continue
                target = int(node.capacity * (baseline + random.uniform(-0.08, 0.08)))
                current = self.parking[nid]
                step = max(1, abs(target - current) // 3)
                self.parking[nid] = max(0, min(node.capacity, current + step * random.choice((-1, 1))))

            # Congestion drifts along the walkways.
            for pair in self._cong_factor:
                self._cong_factor[pair] = max(
                    0.0, min(0.9, self._cong_factor[pair] + random.uniform(-0.06, 0.06))
                )
