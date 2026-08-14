"""Campus graph data model and the built-in sample campus for Northbrook University."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


@dataclass
class Node:
    """A routable point on the campus graph (junction, building entrance or POI)."""

    id: str
    name: str
    type: str
    x: float
    y: float
    building: str | None = None
    floor: int = 1
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    capacity: int | None = None
    spots_total: int | None = None
    spots_available: int | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def routable(self) -> bool:
        return self.type != "junction"


@dataclass
class Building:
    id: str
    name: str
    x: float
    y: float
    w: float
    h: float
    category: str
    color: str
    gate_id: str


@dataclass
class Event:
    id: str
    title: str
    venue_id: str
    start: str
    end: str
    description: str


@dataclass
class Campus:
    name: str
    width: float
    height: float
    nodes: dict[str, Node]
    buildings: dict[str, Building]
    events: list[Event]
    # (a, b, name) tuples; name may be empty
    edges: list[tuple[str, str, str]]

    def node(self, node_id: str) -> Node:
        return self.nodes[node_id]


TYPE_COLORS = {
    "classroom": "#3b82f6",
    "laboratory": "#8b5cf6",
    "office": "#14b8a6",
    "parking": "#f59e0b",
    "venue": "#ef4444",
    "landmark": "#22c55e",
    "building": "#64748b",
    "junction": "#94a3b8",
}

CATEGORY_LABELS = {
    "classroom": "Classrooms",
    "laboratory": "Laboratories",
    "office": "Offices",
    "parking": "Parking",
    "venue": "Event venues",
    "landmark": "Landmarks",
}


def manhattan(a: Node, b: Node) -> float:
    return abs(a.x - b.x) + abs(a.y - b.y)


# --------------------------------------------------------------------------
# Sample campus builder
# --------------------------------------------------------------------------


def _node(
    node_id,
    name,
    ntype,
    x,
    y,
    building=None,
    aliases=(),
    description="",
    capacity=None,
):
    return Node(
        id=node_id,
        name=name,
        type=ntype,
        x=x,
        y=y,
        building=building,
        aliases=list(aliases),
        description=description,
        capacity=capacity,
    )


def build_campus() -> Campus:
    nodes: dict[str, Node] = {}
    buildings: dict[str, Building] = {}
    events: list[Event] = []

    def add(n: Node) -> Node:
        nodes[n.id] = n
        return n

    # -- Walkway junctions -------------------------------------------------
    j = {}
    for jid, x, y in [
        ("nw", 170, 240), ("wnw", 320, 240), ("n", 500, 240), ("ene", 680, 240), ("east", 830, 240),
        ("sw", 170, 380), ("w", 320, 380), ("c", 500, 380), ("e", 680, 380), ("se", 830, 380),
        ("ssw", 170, 520), ("sw2", 320, 520), ("s", 500, 520), ("ese", 680, 520), ("sse", 830, 520),
    ]:
        j[jid] = add(_node(jid, "Path Intersection", "junction", x, y))

    j["c"].name = "Central Quad"
    j["n"].name = "North Walk Junction"
    j["s"].name = "South Plaza"
    j["w"].name = "West Walk Junction"
    j["e"].name = "East Walk Junction"

    # -- Buildings ---------------------------------------------------------
    def building(bid, name, x, y, w, h, category):
        b = Building(
            id=bid,
            name=name,
            x=x,
            y=y,
            w=w,
            h=h,
            category=category,
            color=TYPE_COLORS[category],
            gate_id=f"{bid}_gate",
        )
        buildings[bid] = b
        return b

    def gate(bid, x, y):
        b = buildings[bid]
        return add(_node(f"{bid}_gate", b.name, "building", x, y, building=bid,
                         description=f"Entrance to {b.name}."))

    # building(id, name, top-left x, top-left y, w, h, category)
    mh = building("mh", "Main Hall", 450, 395, 100, 90, "office")
    lib = building("lib", "University Library", 440, 100, 120, 120, "landmark")
    su = building("su", "Student Union", 440, 525, 120, 90, "landmark")
    sci = building("sci", "Science Hall", 250, 230, 140, 140, "laboratory")
    eng = building("eng", "Engineering Center", 610, 230, 140, 140, "laboratory")
    fa = building("fa", "Fine Arts Building", 250, 400, 140, 140, "classroom")
    biz = building("biz", "Business School", 610, 400, 140, 140, "classroom")
    hsc = building("hsc", "Health Sciences Center", 610, 90, 140, 140, "laboratory")
    aud = building("aud", "Grand Auditorium", 250, 100, 140, 120, "venue")
    arena = building("arena", "Eastfield Arena", 760, 90, 140, 140, "venue")
    conv = building("conv", "Convention Hall", 760, 400, 140, 140, "venue")

    gates = {
        "mh": gate("mh", 500, 440),
        "lib": gate("lib", 500, 220),
        "su": gate("su", 500, 525),
        "sci": gate("sci", 320, 340),
        "eng": gate("eng", 680, 340),
        "fa": gate("fa", 320, 520),
        "biz": gate("biz", 680, 520),
        "hsc": gate("hsc", 680, 230),
        "aud": gate("aud", 320, 230),
        "arena": gate("arena", 830, 230),
        "conv": gate("conv", 830, 520),
    }

    # -- Rooms / POIs inside buildings -------------------------------------
    def room(rid, name, rtype, building_id, gx, gy, aliases, description="", capacity=None):
        r = _node(
            rid, name, rtype, gx, gy,
            building=building_id,
            aliases=aliases,
            description=description,
            capacity=capacity,
        )
        return add(r)

    # Main Hall (offices)
    add(_node("mh_lobby", "Main Hall Lobby", "landmark", 500, 410, building="mh"))
    room("mh_registrar", "Registrar's Office", "office", "mh", 470, 450,
         ["registrar", "registration office", "registration"],
         "Enrolment, transcripts and academic records.", capacity=6)
    room("mh_dean", "Dean of Students Office", "office", "mh", 530, 450,
         ["dean of students", "dean", "student support"],
         "Student welfare, conduct and wellbeing services.", capacity=4)
    room("mh_security", "Campus Security Office", "office", "mh", 500, 470,
         ["security", "campus security", "lost and found"],
         "24/7 campus safety desk and lost-and-found.", capacity=3)

    # Library
    add(_node("lib_reading", "Main Reading Room", "landmark", 500, 150, building="lib",
              description="Quiet study space for 250 readers."))
    add(_node("lib_archives", "University Archives", "landmark", 470, 185, building="lib"))
    room("lib_study", "Group Study Rooms", "classroom", "lib", 535, 180,
         ["study rooms", "study area", "group study"],
         "Bookable group study rooms, capacity 12.", capacity=12)

    # Student Union
    room("su_ballroom", "Student Union Ballroom", "venue", "su", 470, 545,
         ["ballroom", "grand ballroom", "su ballroom"],
         "Main events hall of the Student Union.", capacity=400)
    add(_node("su_foodcourt", "Food Court", "landmark", 530, 545, building="su",
              aliases=["cafeteria", "dining hall", "food court"]))
    room("su_affairs", "Student Affairs Office", "office", "su", 500, 590,
         ["student affairs", "student services", "su office"],
         "Clubs, societies and student life.", capacity=8)

    # Science Hall
    room("sci_101", "SCI 101 Lecture Hall", "classroom", "sci", 300, 260,
         ["sci 101", "intro lecture hall", "chemistry lecture"],
         "Introductory science lectures.", capacity=150)
    room("sci_chemA", "Chemistry Lab A", "laboratory", "sci", 338, 260,
         ["chemistry lab", "chem lab", "chemistry", "chem lab a"],
         "Organic and analytical chemistry lab.", capacity=24)
    room("sci_chemB", "Chemistry Lab B", "laboratory", "sci", 265, 330,
         ["chem lab b", "chemistry lab b", "organic lab"],
         "Second-year chemistry teaching lab.", capacity=24)
    room("sci_phys", "Physics Laboratory", "laboratory", "sci", 338, 330,
         ["physics lab", "physics", "mechanics lab"],
         "Mechanics and electromagnetism lab.", capacity=20)
    room("sci_office", "Biology Department Office", "office", "sci", 300, 352,
         ["biology", "bio dept", "biology office"],
         "Academic office for the Biology department.", capacity=5)
    add(_node("sci_atrium", "Science Hall Atrium", "landmark", 300, 300, building="sci"))

    # Engineering Center
    room("eng_robotics", "Robotics Lab", "laboratory", "eng", 650, 260,
         ["robotics lab", "robotics", "robot lab", "automation lab"],
         "Autonomous systems and robotics workbench.", capacity=18)
    room("eng_mat", "Materials Science Lab", "laboratory", "eng", 712, 260,
         ["materials lab", "materials science", "metallurgy lab"],
         "Materials testing and fabrication.", capacity=16)
    room("eng_computer", "Computer Lab", "laboratory", "eng", 650, 330,
         ["computer lab", "computer science", "cs lab", "programming lab"],
         "Programming and simulation workstations.", capacity=40)
    room("eng_305", "ENG 305 Lecture Hall", "classroom", "eng", 712, 330,
         ["eng 305", "engineering lecture", "systems lecture"],
         "Systems and design lectures.", capacity=120)
    room("eng_dean", "Engineering Dean's Office", "office", "eng", 680, 352,
         ["engineering dean", "engineering office", "dean of engineering"],
         "Office of the Dean of Engineering.", capacity=3)

    # Fine Arts Building
    room("fa_studio", "FA 120 Art Studio", "classroom", "fa", 300, 440,
         ["art studio", "studio", "painting studio", "fa 120"],
         "Painting and drawing studio.", capacity=30)
    room("fa_theater", "Fine Arts Theater", "venue", "fa", 345, 465,
         ["theater", "theatre", "playhouse", "fine arts theater"],
         "200-seat theater for performances and film.", capacity=200)
    room("fa_office", "Art Department Office", "office", "fa", 280, 520,
         ["art department", "art office", "fine arts office"],
         "Academic office for the Art department.", capacity=4)

    # Business School
    room("biz_240", "BSB 240 Lecture Hall", "classroom", "biz", 712, 440,
         ["bsb 240", "business lecture", "finance lecture"],
         "Finance and economics lectures.", capacity=140)
    room("biz_career", "Career Services", "office", "biz", 650, 440,
         ["career services", "career center", "careers", "job center"],
         "Internships, placements and resume help.", capacity=10)
    room("biz_finance", "Finance Department Office", "office", "biz", 650, 515,
         ["finance office", "finance department", "accounting office"],
         "Academic office for the Finance department.", capacity=6)

    # Health Sciences Center
    room("hsc_anatomy", "HSC Anatomy Lecture Hall", "classroom", "hsc", 650, 140,
         ["anatomy", "anatomy hall", "hsc lecture"],
         "Anatomy and physiology lectures.", capacity=110)
    room("hsc_nursing", "Nursing Simulation Lab", "laboratory", "hsc", 712, 140,
         ["nursing lab", "simulation lab", "nursing"],
         "Clinical simulation suite.", capacity=16)
    room("hsc_bio", "Biomedical Research Lab", "laboratory", "hsc", 650, 200,
         ["biomedical lab", "bio lab", "research lab", "biomed"],
         "Molecular biology research lab.", capacity=12)
    room("hsc_clinic", "Student Health Center", "office", "hsc", 712, 200,
         ["health center", "clinic", "health office", "infirmary", "student health"],
         "Walk-in clinic and counseling.", capacity=8)

    # Grand Auditorium (venue node itself)
    add(_node("aud_main", "Grand Auditorium", "venue", 320, 160, building="aud",
              aliases=["auditorium", "grand auditorium", "aud", "main auditorium"],
              description="600-seat main auditorium for lectures and concerts.",
              capacity=600))

    # Eastfield Arena
    add(_node("arena_main", "Eastfield Arena", "venue", 830, 160, building="arena",
              aliases=["arena", "stadium", "sports arena", "gym", "eastfield arena"],
              description="Indoor arena for sports and large events.", capacity=8000))
    add(_node("arena_lockers", "Arena Locker Rooms", "landmark", 780, 210, building="arena"))

    # Convention Hall
    add(_node("conv_main", "Convention Hall", "venue", 830, 470, building="conv",
              aliases=["convention hall", "convention center", "conference center"],
              description="Conferences, symposia and trade shows.", capacity=1200))

    # -- Parking -----------------------------------------------------------
    add(_node("north_lot", "North Lot", "parking", 500, 80,
              aliases=["north lot", "north parking", "lot a"],
              description="Open-air lot near the Library.", capacity=200))
    add(_node("south_lot", "South Lot", "parking", 500, 660,
              aliases=["south lot", "south parking", "lot b"],
              description="Open-air lot behind the Student Union.", capacity=260))
    add(_node("west_lot", "West Lot", "parking", 90, 380,
              aliases=["west lot", "west parking", "lot c"],
              description="Small lot by the Science Hall.", capacity=120))
    add(_node("east_garage", "East Garage", "parking", 950, 380,
              aliases=["east garage", "parking garage", "garage", "east parking"],
              description="Multi-level parking structure.", capacity=350))

    # -- Landmarks ---------------------------------------------------------
    add(_node("fountain", "Memorial Fountain", "landmark", 500, 330,
              aliases=["fountain", "memorial fountain", "water feature"],
              description="Historic fountain at the heart of campus."))
    add(_node("rose_garden", "Rose Garden", "landmark", 170, 300,
              aliases=["rose garden", "garden", "botanical garden"],
              description="Quiet garden with seasonal flowers."))

    # -- Walkway edges (a, b, name) ---------------------------------------
    edges: list[tuple[str, str, str]] = []
    row_n = ("nw", "wnw", "n", "ene", "east")
    row_m = ("sw", "w", "c", "e", "se")
    row_s = ("ssw", "sw2", "s", "ese", "sse")
    for i in range(len(row_n) - 1):
        edges.append((row_n[i], row_n[i + 1], "North Mall"))
    for i in range(len(row_m) - 1):
        edges.append((row_m[i], row_m[i + 1], "Quad Walkway"))
    for i in range(len(row_s) - 1):
        edges.append((row_s[i], row_s[i + 1], "South Promenade"))
    for a, b in [("nw", "sw"), ("sw", "ssw")]:
        edges.append((a, b, "West Ring Path"))
    for a, b in [("wnw", "w"), ("w", "sw2")]:
        edges.append((a, b, "West Avenue"))
    for a, b in [("n", "c"), ("c", "s")]:
        edges.append((a, b, "Main Path"))
    for a, b in [("ene", "e"), ("e", "ese")]:
        edges.append((a, b, "East Avenue"))
    for a, b in [("east", "se"), ("se", "sse")]:
        edges.append((a, b, "East Ring Road"))

    # Gate connector edges (building entrance -> nearest walkway junction)
    gate_junctions = {
        "mh": "c", "lib": "n", "su": "s", "sci": "w", "eng": "e",
        "fa": "sw2", "biz": "ese", "hsc": "ene", "aud": "wnw",
        "arena": "east", "conv": "sse",
    }
    for bid, jid in gate_junctions.items():
        g = gates[bid]
        edges.append((g.id, jid, ""))

    # Parking connector edges
    edges.append(("north_lot", "n", ""))
    edges.append(("south_lot", "s", ""))
    edges.append(("west_lot", "sw", ""))
    edges.append(("east_garage", "se", ""))

    # Landmark connector edges
    edges.append(("fountain", "c", "Quad Path"))
    edges.append(("fountain", "n", "Quad Path"))
    edges.append(("rose_garden", "sw", "Garden Path"))

    # Room -> gate corridor edges (weight = manhattan distance)
    room_to_gate = {
        "mh": ["mh_lobby", "mh_registrar", "mh_dean", "mh_security"],
        "lib": ["lib_reading", "lib_archives", "lib_study"],
        "su": ["su_ballroom", "su_foodcourt", "su_affairs"],
        "sci": ["sci_101", "sci_chemA", "sci_chemB", "sci_phys", "sci_office", "sci_atrium"],
        "eng": ["eng_robotics", "eng_mat", "eng_computer", "eng_305", "eng_dean"],
        "fa": ["fa_studio", "fa_theater", "fa_office"],
        "biz": ["biz_240", "biz_career", "biz_finance"],
        "hsc": ["hsc_anatomy", "hsc_nursing", "hsc_bio", "hsc_clinic"],
        "aud": ["aud_main"],
        "arena": ["arena_main", "arena_lockers"],
        "conv": ["conv_main"],
    }
    for bid, room_ids in room_to_gate.items():
        g = gates[bid]
        for rid in room_ids:
            r = nodes[rid]
            w = manhattan(r, g)
            edges.append((rid, g.id, "Corridor"))

    # -- Events ------------------------------------------------------------
    events = [
        Event("EV-001", "AI & Robotics Symposium", "conv_main", "10:00", "12:00",
              "Keynote talks on autonomous systems and machine learning."),
        Event("EV-002", "Quantum Computing Lecture", "aud_main", "14:00", "15:30",
              "Public lecture on quantum information science."),
        Event("EV-003", "2026 Fall Career Fair", "su_ballroom", "09:00", "16:00",
              "Meet 80+ employers recruiting on campus."),
        Event("EV-004", "Homecoming Basketball", "arena_main", "19:00", "21:30",
              "Varsity basketball home opener."),
        Event("EV-005", "University Symphony", "fa_theater", "20:00", "22:00",
              "Evening performance of classical favorites."),
        Event("EV-006", "CS Study Jam", "eng_computer", "18:00", "21:00",
              "Drop-in group study with TA support."),
    ]

    return Campus(
        name="Northbrook University",
        width=1000,
        height=760,
        nodes=nodes,
        buildings=buildings,
        events=events,
        edges=edges,
    )
