"use strict";

const SVGNS = "http://www.w3.org/2000/svg";

const state = {
  campus: null,
  originId: null,
  destinationId: null,
  route: null,
  setLocationMode: false,
};

const el = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
async function init() {
  try {
    const res = await fetch("/api/campus");
    state.campus = await res.json();
    document.title = `Campus Navigator — ${state.campus.name}`;
    el("campus-name").textContent = state.campus.name;
    renderLegend();
    renderMap();
    setOrigin("fountain");
    buildSuggestions();
    pollHealth();
    pollState();
    setInterval(pollState, 5000);
    wireUI();
    greet();
  } catch (err) {
    el("footer-state").textContent = "Failed to load campus data: " + err.message;
  }
}

// ---------------------------------------------------------------------------
// SVG helpers
// ---------------------------------------------------------------------------
function svgEl(tag, attrs, text) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
  if (text != null) n.textContent = text;
  return n;
}

function renderLegend() {
  const legend = el("legend");
  legend.innerHTML = "";
  for (const [cat, label] of Object.entries(state.campus.categories)) {
    const item = document.createElement("span");
    item.className = "legend-item";
    const dot = document.createElement("span");
    dot.className = "legend-dot";
    dot.style.background = state.campus.type_colors[cat];
    item.append(dot, document.createTextNode(label));
    legend.appendChild(item);
  }
}

// ---------------------------------------------------------------------------
// Map rendering
// ---------------------------------------------------------------------------
function renderMap() {
  const svg = el("campus-map");
  svg.innerHTML = "";
  svg.dataset.edges = "";

  const defs = svgEl("defs", {});
  const marker = svgEl("marker", {
    id: "arrow", viewBox: "0 0 10 10", refX: 8, refY: 5,
    markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse",
  });
  marker.appendChild(svgEl("path", { d: "M0 0 L10 5 L0 10 z", fill: "#0ea5e9" }));
  defs.appendChild(marker);
  svg.appendChild(defs);

  // Walkways / edges
  state.campus.edges.forEach((e) => {
    const a = state.campus.nodes[e.a];
    const b = state.campus.nodes[e.b];
    const line = svgEl("line", {
      x1: a.x, y1: a.y, x2: b.x, y2: b.y,
      class: "edge", "data-edge": `${e.a}->${e.b}`,
    });
    svg.appendChild(line);
  });

  // Buildings
  state.campus.buildings.forEach((b) => {
    const rect = svgEl("rect", {
      x: b.x, y: b.y, width: b.w, height: b.h, rx: 10,
      class: "building", fill: b.color, stroke: b.color,
      "data-building": b.id,
    });
    rect.appendChild(svgEl("title", {}, b.name));
    svg.appendChild(rect);
    svg.appendChild(svgEl("text", {
      x: b.x + b.w / 2, y: b.y + b.h / 2 + 4, class: "building-label",
    }, b.name));
  });

  // Nodes
  for (const [id, node] of Object.entries(state.campus.nodes)) {
    if (node.type === "junction") {
      svg.appendChild(svgEl("circle", {
        cx: node.x, cy: node.y, r: 3, class: "junction",
      }));
      continue;
    }
    if (node.type === "building") {
      const gate = svgEl("rect", {
        x: node.x - 4, y: node.y - 4, width: 8, height: 8,
        rx: 2, class: "gate", "data-id": id, "data-gate": id,
      });
      gate.appendChild(svgEl("title", {}, `${node.name} (entrance)`));
      svg.appendChild(gate);
      continue;
    }
    drawPoi(node);
  }

  // Venue "live now" pulse rings
  state.campus.events
    .filter((ev) => ev.status === "now")
    .forEach((ev) => {
      const venue = state.campus.nodes[ev.venue_id];
      if (!venue) return;
      const ring = svgEl("circle", {
        cx: venue.x, cy: venue.y, r: 11, class: "poi", fill: "none",
        stroke: "#ef4444", "stroke-width": 2,
      });
      ring.appendChild(svgEl("title", {}, `${ev.title} — happening now`));
      svg.appendChild(ring);
    });

  svg.addEventListener("click", onMapClick);
}

function drawPoi(node) {
  const svg = el("campus-map");
  const r = node.type === "venue" || node.type === "parking" ? 7 : node.type === "landmark" ? 5 : 4.5;
  const circle = svgEl("circle", {
    cx: node.x, cy: node.y, r, class: "poi",
    fill: state.campus.type_colors[node.type] || "#94a3b8",
    "data-id": node.id,
  });
  circle.appendChild(svgEl("title", {}, node.description || node.name));
  svg.appendChild(circle);

  // Label every routable location (rooms, lots, venues, landmarks).
  const hasBuilding = Boolean(node.building);
  const above = !hasBuilding || hashId(node.id) % 2 === 0;
  svg.appendChild(svgEl("text", {
    x: node.x,
    y: node.y + (above ? -9 : node.type === "parking" ? 6 : 16),
    class: `poi-label${hasBuilding ? " sm" : ""}`,
  }, node.name));
  if (node.type === "parking") {
    svg.appendChild(svgEl("text", {
      x: node.x, y: node.y + 6, class: "parking-count",
      "data-parking": node.id,
    }, "…"));
  }
}

function hashId(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

function onMapClick(evt) {
  const svg = el("campus-map");
  const target = evt.target;
  let nodeId = target && target.getAttribute("data-id");

  if (!nodeId && target && target.hasAttribute("data-building")) {
    const bid = target.getAttribute("data-building");
    const building = state.campus.buildings.find((b) => b.id === bid);
    if (building) nodeId = building.gate;
  }

  if (state.setLocationMode) {
    let pickId = nodeId;
    if (!pickId) {
      // nearest node to click point
      const pt = svg.createSVGPoint();
      pt.x = evt.offsetX * (1000 / svg.clientWidth);
      pt.y = evt.offsetY * (760 / svg.clientHeight);
      pickId = nearestNode(pt.x, pt.y);
    }
    if (pickId) setOrigin(pickId);
    toggleLocationMode(false);
    showHint("Location set.");
    return;
  }

  if (nodeId) setDestination(nodeId);
}

function nearestNode(x, y) {
  let best = null;
  let bestD = Infinity;
  for (const [id, n] of Object.entries(state.campus.nodes)) {
    if (n.type === "junction" || n.type === "building") continue;
    const d = (n.x - x) ** 2 + (n.y - y) ** 2;
    if (d < bestD) { bestD = d; best = id; }
  }
  return best;
}

// ---------------------------------------------------------------------------
// Route drawing
// ---------------------------------------------------------------------------
function clearRoute() {
  const svg = el("campus-map");
  svg.querySelectorAll(".route-line, .route-start, .route-end").forEach((n) => n.remove());
  svg.querySelectorAll(".poi.origin, .poi.destination").forEach((n) => {
    n.classList.remove("origin", "destination");
  });
  state.route = null;
}

function drawRoute(route) {
  clearRoute();
  if (!route || !route.path || route.path.length < 2) return;
  const svg = el("campus-map");

  const d = route.path.map((p) => `${p.x},${p.y}`).join(" L ");
  const poly = svgEl("path", {
    d: `M ${d}`, class: "route-line", "marker-end": "url(#arrow)",
  });
  svg.appendChild(poly);

  const first = route.path[0];
  const last = route.path[route.path.length - 1];
  svg.appendChild(svgEl("circle", { cx: first.x, cy: first.y, r: 7, class: "route-start" }));
  svg.appendChild(svgEl("circle", { cx: last.x, cy: last.y, r: 8, class: "route-end" }));

  state.route = route;

  const startPoi = svg.querySelector(`.poi[data-id="${first.id}"]`);
  const endPoi = svg.querySelector(`.poi[data-id="${last.id}"]`);
  if (startPoi) startPoi.classList.add("origin");
  if (endPoi) endPoi.classList.add("destination");
}

// ---------------------------------------------------------------------------
// Origin / destination
// ---------------------------------------------------------------------------
function setOrigin(id) {
  state.originId = id;
  const node = state.campus.nodes[id];
  el("origin-badge").textContent = node ? `From: ${node.name}` : "From: —";
  if (state.destinationId) computeRoute();
}

function setDestination(id) {
  state.destinationId = id;
  computeRoute();
  if (state.setLocationMode) toggleLocationMode(false);
  const node = state.campus.nodes[id];
  if (node) showHint(`Destination: ${node.name}`);
}

async function computeRoute() {
  if (!state.originId || !state.destinationId) return;
  try {
    const res = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ origin: state.originId, destination: state.destinationId }),
    });
    const data = await res.json();
    drawRoute(data.route);
  } catch (err) {
    console.error(err);
  }
}

// ---------------------------------------------------------------------------
// Live state polling
// ---------------------------------------------------------------------------
async function pollState() {
  try {
    const res = await fetch("/api/state");
    const snap = await res.json();

    // parking counts
    for (const [id, info] of Object.entries(snap.parking)) {
      const t = document.querySelector(`.parking-count[data-parking="${id}"]`);
      if (t) t.textContent = `${info.available}/${info.total}`;
    }
    // congestion -> edge styling
    for (const [key, factor] of Object.entries(snap.congestion)) {
      const edge = document.querySelector(`.edge[data-edge="${key}"]`);
      if (!edge) continue;
      edge.classList.toggle("severe", factor > 0.6);
      edge.classList.toggle("congested", factor > 0.3 && factor <= 0.6);
    }
    el("live-pill").classList.remove("off");
    el("footer-state").textContent =
      `Live every ${snap.tick}s · ${Object.keys(snap.parking).length} parking lots tracked`;
  } catch (err) {
    el("live-pill").classList.add("off");
    el("footer-state").textContent = "Live feed offline";
  }
}

async function pollHealth() {
  try {
    const res = await fetch("/api/health");
    const h = await res.json();
    el("ai-pill").textContent =
      h.ai.provider === "openai" ? `AI: ${h.ai.model}` : "AI: Offline NLP";
  } catch (err) {
    el("ai-pill").textContent = "AI: —";
  }
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------
function wireUI() {
  const input = el("search-input");
  const results = el("search-results");
  let timer = null;

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = input.value.trim();
      if (!q) { results.classList.add("hidden"); results.innerHTML = ""; return; }
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        results.innerHTML = "";
        data.results.forEach((r) => {
          const item = document.createElement("div");
          item.className = "dropdown-item";
          item.innerHTML = `<div class="t">${escapeHtml(r.name)}</div>
            <div class="d">${state.campus.categories[r.type] || r.type}${r.description ? " · " + escapeHtml(r.description) : ""}</div>`;
          item.addEventListener("click", () => {
            setDestination(r.id);
            results.classList.add("hidden");
            input.value = "";
          });
          results.appendChild(item);
        });
        results.classList.toggle("hidden", data.results.length === 0);
      } catch (err) { /* ignore */ }
    }, 200);
  });
  input.addEventListener("blur", () => setTimeout(() => results.classList.add("hidden"), 150));

  el("set-location-btn").addEventListener("click", () => toggleLocationMode(!state.setLocationMode));
  el("reset-view-btn").addEventListener("click", () => {
    state.destinationId = null;
    clearRoute();
    showHint("Destination cleared.");
  });

  el("chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = el("chat-input").value.trim();
    if (!text) return;
    el("chat-input").value = "";
    sendMessage(text);
  });

  el("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      el("chat-form").requestSubmit();
    }
  });
}

function toggleLocationMode(on) {
  state.setLocationMode = on;
  el("set-location-btn").classList.toggle("active", on);
  el("set-location-btn").textContent = on ? "Click on the map…" : "📍 Set my location";
  showHint(on ? "Click anywhere on the map to set your current location." : "");
}

function showHint(text, ms = 1800) {
  const hint = el("map-hint");
  hint.textContent = text;
  hint.classList.toggle("show", Boolean(text));
  clearTimeout(showHint._t);
  if (text) showHint._t = setTimeout(() => hint.classList.remove("show"), ms);
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
function addMessage(role, text, meta) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta";
    m.innerHTML = meta;
    wrap.appendChild(m);
  }
  el("chat-messages").appendChild(wrap);
  scrollChat();
  return wrap;
}

function scrollChat() {
  const box = el("chat-messages");
  box.scrollTop = box.scrollHeight;
}

function buildSuggestions() {
  const box = el("suggestions");
  box.innerHTML = "";
  (state.campus.suggestions || []).forEach((s) => {
    const chip = document.createElement("span");
    chip.className = "suggestion";
    chip.textContent = s;
    chip.addEventListener("click", () => sendMessage(s));
    box.appendChild(chip);
  });
}

async function sendMessage(text) {
  addMessage("user", text);
  const thinking = addMessage("ai", "Thinking…", "");
  thinking.classList.add("thinking");

  const origin = state.originId || "fountain";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, origin }),
    });
    if (!res.ok) throw new Error("Request failed");
    const data = await res.json();

    thinking.classList.remove("thinking");
    thinking.querySelector(".bubble").textContent = data.reply;
    const meta = document.createElement("div");
    meta.className = "meta";
    const provider = data.provider === "openai" ? "OpenAI" : "Offline NLP";
    meta.innerHTML = `<span class="provider">${provider}</span> · ${data.intent}`;
    thinking.appendChild(meta);

    if (data.route) {
      drawRoute(data.route);
      addRouteCard(data.route);
      if (data.destination) state.destinationId = data.destination.id;
    }
    if (data.origin) {
      state.originId = data.origin.id;
      el("origin-badge").textContent = `From: ${data.origin.name}`;
    }
    if (data.destination && !data.route) {
      state.destinationId = data.destination.id;
      setDestination(data.destination.id);
    }
    if (data.suggestions) buildSuggestions();
  } catch (err) {
    thinking.classList.remove("thinking");
    thinking.querySelector(".bubble").textContent = "Sorry, something went wrong. Please try again.";
  }
  scrollChat();
}

function addRouteCard(route) {
  const wrap = document.createElement("div");
  wrap.className = "route-card";
  wrap.innerHTML =
    `<b>${route.distance_m.toFixed(0)} m</b> · about <b>${route.eta_min.toFixed(1)} min</b>` +
    (route.landmarks && route.landmarks.length ? `<br>Pass by: ${route.landmarks.join(", ")}` : "");
  el("chat-messages").appendChild(wrap);
  scrollChat();
}

function greet() {
  addMessage(
    "ai",
    "Welcome! I'm your AI campus guide. Ask me for directions to any classroom, lab, office, parking lot or event venue — for example:\n\n\u2022 How do I get to the Robotics Lab?\n\u2022 Where can I park near the Engineering Center?\n\u2022 What's happening at the Arena today?",
    '<span class="provider">Offline NLP</span> · greeting'
  );
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

init();
