"""Sticky Note Generator — Streamlit App with a fancy sticky-note corkboard UI."""
import json
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.config import MODELS_DIR, DATA_DIR, PLOTS_DIR, REPORTS_DIR
from src.sticky_notes import generate_sticky_notes, NOTE_COLORS, CATEGORY_KEYWORDS
from src.generate_dataset import TOPICS

st.set_page_config(
    page_title="Sticky Note Generator",
    page_icon="🗒️",
    layout="wide",
    initial_sidebar_state="expanded",
)

THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&family=Patrick+Hand&family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --wall: #8b5a2b;
        --wall-dark: #6b4423;
        --ink: #2a2a2a;
        --accent: #ffb300;
    }

    .stApp {
        background:
            radial-gradient(circle at 20% 30%, rgba(255,255,255,0.05), transparent 40%),
            radial-gradient(circle at 80% 70%, rgba(0,0,0,0.08), transparent 45%),
            #7a4e23;
        font-family: 'Inter', sans-serif;
        color: #f5efe0;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background-image:
            repeating-linear-gradient(45deg, rgba(0,0,0,0.03) 0 2px, transparent 2px 14px),
            repeating-linear-gradient(-45deg, rgba(255,255,255,0.02) 0 2px, transparent 2px 18px);
        opacity: 0.6;
    }

    header[data-testid="stHeader"] {
        background: rgba(0,0,0,0.25);
        backdrop-filter: blur(6px);
        border-bottom: 1px solid rgba(255,255,255,0.12);
    }
    header[data-testid="stHeader"] * {
        color: #f5efe0 !important;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #5d3a1e, #4a2e17);
        color: #f5efe0;
        border-right: 3px solid #3a2410;
    }
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown li,
    div[data-testid="stSidebar"] .stRadio label,
    div[data-testid="stSidebar"] label,
    div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        color: #f5efe0 !important;
    }
    div[data-testid="stSidebar"] .stMarkdown h1,
    div[data-testid="stSidebar"] .stMarkdown h2,
    div[data-testid="stSidebar"] .stMarkdown h3 {
        color: #ffd54f !important;
    }
    div[data-testid="stSidebar"] .stCaption {
        color: #cbb8a0 !important;
    }

    .hero {
        background: linear-gradient(135deg, rgba(0,0,0,0.35), rgba(0,0,0,0.15));
        border-radius: 18px;
        padding: 34px 34px 26px 34px;
        margin-bottom: 22px;
        border: 1px solid rgba(255,255,255,0.15);
        backdrop-filter: blur(4px);
        position: relative;
    }
    .hero-title {
        font-family: 'Caveat', cursive;
        font-size: 3.2em;
        color: #fff8e1;
        margin: 0;
        line-height: 1.05;
        text-shadow: 0 3px 8px rgba(0,0,0,0.45);
    }
    .hero-sub {
        font-family: 'Patrick Hand', cursive;
        color: #ffe082;
        font-size: 1.25em;
        margin-top: 6px;
    }
    .hero-tags {
        margin-top: 16px;
    }
    .hero-tag {
        display: inline-block;
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.2);
        color: #fff;
        border-radius: 20px;
        padding: 5px 14px;
        font-size: 0.85em;
        margin-right: 8px;
        margin-bottom: 6px;
        font-family: 'Inter', sans-serif;
    }

    .section-title {
        font-family: 'Caveat', cursive;
        font-size: 2.1em;
        color: #fff8e1;
        margin: 26px 0 12px 0;
        text-shadow: 0 2px 6px rgba(0,0,0,0.4);
        border-bottom: 2px dashed rgba(255,255,255,0.25);
        padding-bottom: 6px;
    }
    .section-title small {
        font-family: 'Inter', sans-serif;
        font-size: 0.4em;
        color: #ffe082;
        margin-left: 10px;
        letter-spacing: 0.5px;
    }

    .corkboard {
        background:
            radial-gradient(circle at 30px 40px, rgba(255,255,255,0.03), transparent 120px),
            radial-gradient(circle at 70% 20%, rgba(0,0,0,0.06), transparent 150px),
            #9a6b38;
        border-radius: 16px;
        border: 6px solid #6b4423;
        box-shadow: inset 0 0 40px rgba(0,0,0,0.35), 0 10px 30px rgba(0,0,0,0.5);
        padding: 34px 26px;
        min-height: 320px;
        background-image:
            repeating-linear-gradient(45deg, rgba(0,0,0,0.04) 0 2px, transparent 2px 12px),
            repeating-linear-gradient(-45deg, rgba(255,255,255,0.03) 0 2px, transparent 2px 16px);
    }

    .note-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 22px;
        padding: 6px;
    }

    .sticky-note {
        border-radius: 2px 8px 6px 2px;
        padding: 34px 16px 14px 16px;
        min-height: 170px;
        position: relative;
        box-shadow: 3px 5px 12px rgba(0,0,0,0.35), -1px -1px 3px rgba(255,255,255,0.2);
        transition: transform 0.25s cubic-bezier(.2,.8,.2,1), box-shadow 0.25s ease, z-index 0s;
        cursor: default;
        margin-bottom: 10px;
        border-bottom: 8px solid rgba(0,0,0,0.09);
        transform: rotate(var(--rot, 0deg));
        will-change: transform;
        overflow: hidden;
    }
    .sticky-note:hover {
        transform: rotate(0deg) scale(1.06) translateY(-4px);
        box-shadow: 6px 10px 26px rgba(0,0,0,0.5), -2px -2px 6px rgba(255,255,255,0.25);
        z-index: 30;
    }
    .sticky-note::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 30px;
        background: rgba(255,255,255,0.28);
        border-bottom: 1px dashed rgba(0,0,0,0.12);
    }
    .sticky-note::after {
        content: "";
        position: absolute;
        right: -2px; bottom: -2px;
        width: 26px; height: 26px;
        background: linear-gradient(135deg, transparent 60%, rgba(0,0,0,0.18));
        border-radius: 0 0 8px 0;
    }
    .note-pin {
        position: absolute;
        top: -8px; left: 50%;
        transform: translateX(-50%);
        width: 20px; height: 20px;
        border-radius: 50%;
        z-index: 5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.4), inset 0 2px 3px rgba(255,255,255,0.5);
    }
    .pin-red    { background: radial-gradient(circle at 32% 32%, #ff8a80, #c62828); }
    .pin-blue   { background: radial-gradient(circle at 32% 32%, #82b1ff, #1565c0); }
    .pin-green  { background: radial-gradient(circle at 32% 32%, #69f0ae, #00897b); }
    .pin-yellow { background: radial-gradient(circle at 32% 32%, #ffe082, #f9a825); }
    .pin-purple { background: radial-gradient(circle at 32% 32%, #b388ff, #6a1b9a); }
    .pin-pink   { background: radial-gradient(circle at 32% 32%, #ff80ab, #c2185b); }

    .note-tape {
        position: absolute;
        top: -14px; left: 20%;
        width: 90px; height: 26px;
        background: rgba(255,255,255,0.35);
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        transform: rotate(-4deg);
        z-index: 4;
        border-left: 1px solid rgba(255,255,255,0.4);
        border-right: 1px solid rgba(255,255,255,0.4);
    }

    .cat-badge {
        display: inline-block;
        background: rgba(0,0,0,0.12);
        color: #222;
        border-radius: 14px;
        padding: 3px 12px;
        font-size: 0.72em;
        font-weight: 700;
        font-family: 'Inter', sans-serif;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .imp-badge {
        background: #ff7043;
        color: #fff;
    }
    .note-title {
        font-family: 'Caveat', cursive;
        font-size: 1.45em;
        font-weight: 700;
        color: #202124;
        line-height: 1.15;
        margin: 2px 0 6px 0;
    }
    .note-text {
        font-family: 'Inter', sans-serif;
        font-size: 0.8em;
        color: #333;
        line-height: 1.45;
        margin-bottom: 10px;
    }
    .note-meta {
        font-family: 'Inter', sans-serif;
        font-size: 0.7em;
        color: #555;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: auto;
        padding-top: 6px;
        border-top: 1px dashed rgba(0,0,0,0.15);
    }
    .note-speaker { font-weight: 700; color: #333; }
    .note-tag {
        display: inline-block;
        background: rgba(0,0,0,0.09);
        border-radius: 9px;
        padding: 1px 7px;
        font-size: 0.85em;
        margin: 1px 2px;
    }
    .note-score {
        background: rgba(0,0,0,0.13);
        border-radius: 8px;
        padding: 2px 8px;
        font-weight: 700;
        color: #333;
    }

    .stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 14px;
        margin: 10px 0 8px 0;
    }
    .stat-card {
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 14px;
        padding: 18px 10px;
        text-align: center;
        backdrop-filter: blur(3px);
    }
    .stat-icon { font-size: 1.8em; }
    .stat-value {
        font-family: 'Caveat', cursive;
        font-size: 2.2em;
        color: #fff8e1;
        line-height: 1;
        margin-top: 4px;
    }
    .stat-label {
        font-size: 0.75em;
        color: #ffe082;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 2px;
        font-family: 'Inter', sans-serif;
    }

    .card {
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 10px;
        backdrop-filter: blur(3px);
        transition: transform 0.15s ease, background 0.15s ease;
    }
    .card:hover { background: rgba(255,255,255,0.16); transform: translateY(-2px); }
    .card h4 {
        color: #ffd54f;
        font-family: 'Inter', sans-serif;
        margin: 0 0 6px 0;
        font-size: 0.98em;
    }
    .card p {
        color: #f0e6d6;
        font-family: 'Inter', sans-serif;
        margin: 0;
        font-size: 0.85em;
        line-height: 1.5;
    }

    .transcript-box {
        background: rgba(0,0,0,0.22);
        backdrop-filter: blur(3px);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 14px;
        padding: 18px;
        max-height: 460px;
        overflow-y: auto;
    }
    .transcript-line {
        padding: 7px 8px;
        border-radius: 5px;
        border-left: 3px solid transparent;
        margin-bottom: 4px;
        font-family: 'Inter', sans-serif;
        font-size: 0.85em;
        color: #efe6d5;
        background: rgba(255,255,255,0.03);
    }
    .transcript-line.imp {
        background: rgba(255,213,79,0.16);
        border-left: 4px solid #ffd54f;
    }
    .transcript-speaker { font-weight: 700; color: #ffd54f; }

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #d8c8b2;
        font-family: 'Inter', sans-serif;
    }
    .empty-state .icon { font-size: 4.5em; margin-bottom: 14px; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3)); }
    .empty-state h3 { color: #f5efe0; font-family: 'Caveat', cursive; font-size: 1.8em; margin: 0 0 8px 0; }

    .warn-note {
        background: rgba(255,171,64,0.18);
        border: 1px solid rgba(255,171,64,0.4);
        border-radius: 12px;
        padding: 14px 16px;
        color: #ffe0b2;
        font-size: 0.9em;
    }

    .chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 16px 0; }
    .chip {
        background: rgba(0,0,0,0.25);
        border: 1px solid rgba(255,255,255,0.2);
        color: #f5efe0;
        border-radius: 20px;
        padding: 5px 14px;
        font-size: 0.85em;
        cursor: pointer;
        font-family: 'Inter', sans-serif;
        transition: background 0.15s ease;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 14px;
        padding: 14px;
        backdrop-filter: blur(3px);
    }
    div[data-testid="stMetricValue"] { color: #fff8e1; }
    div[data-testid="stMetricLabel"] { color: #ffe082; }

    .expander-transparent details { background: transparent !important; }

    .stButton > button {
        border-radius: 22px;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #ffb300, #f57c00);
        color: #2a2a2a;
        border: none;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(255,179,0,0.35);
        color: #2a2a2a;
    }

    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.92) !important;
        color: #222 !important;
        border-radius: 12px !important;
        border: 1px solid #ccc !important;
    }
</style>
"""

st.markdown(THEME_CSS, unsafe_allow_html=True)

# Shared CSS for non-note HTML fragments. Each st.html() fragment is rendered
# in its own isolated container, so the CSS must be embedded within the same
# fragment for the classes to take effect. This block is prepended to every
# HTML fragment rendered via _html().
CHROME_CSS = """
<style>
.hero {
    background: linear-gradient(135deg, rgba(0,0,0,0.35), rgba(0,0,0,0.15));
    border-radius: 18px; padding: 30px 32px 22px 32px; margin-bottom: 18px;
    border: 1px solid rgba(255,255,255,0.15);
    font-family: 'Segoe UI', Arial, sans-serif;
}
.hero-title {
    font-size: 2.6em; color: #fff8e1; margin: 0; line-height: 1.05;
    text-shadow: 0 3px 8px rgba(0,0,0,0.45);
}
.hero-sub { color: #ffe082; font-size: 1.2em; margin-top: 6px; }
.hero-tags { margin-top: 14px; }
.hero-tag {
    display: inline-block; background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.2); color: #fff;
    border-radius: 20px; padding: 5px 14px; font-size: 0.8em;
    margin-right: 8px; margin-bottom: 6px;
}
.section-title {
    font-size: 1.9em; color: #fff8e1; margin: 22px 0 10px 0;
    text-shadow: 0 2px 6px rgba(0,0,0,0.4);
    border-bottom: 2px dashed rgba(255,255,255,0.25); padding-bottom: 6px;
    font-family: 'Segoe UI', Arial, sans-serif;
}
.section-title small { font-size: 0.4em; color: #ffe082; margin-left: 10px; letter-spacing: 0.5px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin: 10px 0 8px 0; }
.stat-card { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18); border-radius: 14px; padding: 16px 10px; text-align: center; }
.stat-icon { font-size: 1.8em; }
.stat-value { font-size: 2.1em; color: #fff8e1; line-height: 1; margin-top: 4px; font-family: 'Segoe UI', Arial, sans-serif; }
.stat-label { font-size: 0.72em; color: #ffe082; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
.card { background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.16); border-radius: 14px; padding: 15px 18px; margin-bottom: 10px; font-family: 'Segoe UI', Arial, sans-serif; }
.card h4 { color: #ffd54f; margin: 0 0 6px 0; font-size: 0.98em; }
.card p { color: #f0e6d6; margin: 0; font-size: 0.85em; line-height: 1.5; }
.warn-note { background: rgba(255,171,64,0.18); border: 1px solid rgba(255,171,64,0.4); border-radius: 12px; padding: 13px 16px; color: #ffe0b2; font-size: 0.9em; }
.empty-state { text-align: center; padding: 50px 20px; color: #d8c8b2; font-family: 'Segoe UI', Arial, sans-serif; }
.empty-state .eicon { font-size: 4em; margin-bottom: 12px; }
.empty-state h3 { color: #f5efe0; font-size: 1.6em; margin: 0 0 8px 0; }
.transcript-box { background: rgba(0,0,0,0.22); border: 1px solid rgba(255,255,255,0.15); border-radius: 14px; padding: 16px; max-height: 460px; overflow-y: auto; font-family: 'Segoe UI', Arial, sans-serif; }
.transcript-line { padding: 7px 8px; border-radius: 5px; border-left: 3px solid transparent; margin-bottom: 4px; font-size: 0.85em; color: #efe6d5; background: rgba(255,255,255,0.03); }
.transcript-line.imp { background: rgba(255,213,79,0.16); border-left: 4px solid #ffd54f; }
.transcript-speaker { font-weight: 700; color: #ffd54f; }
</style>
"""


def _html(fragment: str):
    """Render an HTML fragment with embedded CSS via st.html().

    st.html() renders raw HTML as real DOM (never as literal text), which
    prevents the backend <div>/code from appearing on screen — unlike
    st.markdown(unsafe_allow_html=True) which leaks raw tags in some versions.
    """
    st.html(CHROME_CSS + fragment)


def render_hero(title: str, sub: str, tags: list):
    tag_html = "".join(f'<span class="hero-tag">{t}</span>' for t in tags)
    _html(f"""
    <div class="hero">
        <div class="hero-title">{title}</div>
        <div class="hero-sub">{sub}</div>
        <div class="hero-tags">{tag_html}</div>
    </div>
    """)


def render_section(title: str, small: str = ""):
    _html(f'<div class="section-title">{title}<small>{small}</small></div>')


def render_stats(stats: list):
    cards = ""
    for icon, value, label in stats:
        cards += f'<div class="stat-card"><div class="stat-icon">{icon}</div><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>'
    _html(f'<div class="stat-grid">{cards}</div>')


NOTE_CSS = """
<style>
.sn-body {
    display: flex; flex-wrap: wrap; gap: 26px;
    padding: 34px 26px; min-height: 280px;
    background:
        radial-gradient(circle at 30px 40px, rgba(255,255,255,0.04), transparent 120px),
        radial-gradient(circle at 70% 20%, rgba(0,0,0,0.08), transparent 150px),
        #9a6b38;
    border-radius: 16px;
    border: 6px solid #6b4423;
    box-shadow: inset 0 0 40px rgba(0,0,0,0.35), 0 10px 30px rgba(0,0,0,0.5);
    background-image:
        repeating-linear-gradient(45deg, rgba(0,0,0,0.04) 0 2px, transparent 2px 12px),
        repeating-linear-gradient(-45deg, rgba(255,255,255,0.03) 0 2px, transparent 2px 16px);
}
.sn-note {
    display: flex; flex-direction: column;
    width: 250px; min-height: 170px;
    border-radius: 2px 8px 6px 2px;
    padding: 34px 16px 14px 16px;
    position: relative;
    box-shadow: 3px 5px 12px rgba(0,0,0,0.35), -1px -1px 3px rgba(255,255,255,0.2);
    border-bottom: 8px solid rgba(0,0,0,0.10);
    border: 2px solid rgba(0,0,0,0.22);
    transition: transform 0.25s cubic-bezier(.2,.8,.2,1), box-shadow 0.25s ease;
    will-change: transform;
    font-family: 'Segoe UI', Arial, sans-serif;
    overflow: hidden;
}
.sn-note:hover { transform: scale(1.05) translateY(-4px); box-shadow: 6px 10px 26px rgba(0,0,0,0.5); }
.sn-note .sn-top {
    position: absolute; top: 0; left: 0; right: 0; height: 30px;
    background: rgba(255,255,255,0.30);
    border-bottom: 1px dashed rgba(0,0,0,0.12);
}
.sn-pin {
    position: absolute; top: -8px; left: 50%; transform: translateX(-50%);
    width: 20px; height: 20px; border-radius: 50%;
    box-shadow: 0 2px 5px rgba(0,0,0,0.4), inset 0 2px 3px rgba(255,255,255,0.5);
}
.sn-badge {
    display: inline-block; background: rgba(0,0,0,0.12); color: #222;
    border-radius: 14px; padding: 3px 12px; font-size: 0.72em; font-weight: 700;
    letter-spacing: 0.3px; text-transform: uppercase; margin-bottom: 5px;
}
.sn-badge-imp { background: #ff7043; color: #fff; }
.sn-title {
    font-size: 1.25em; font-weight: 700; color: #202124;
    line-height: 1.15; margin: 2px 0 6px 0;
}
.sn-text { font-size: 0.85em; color: #333; line-height: 1.45; margin-bottom: 10px; }
.sn-meta {
    margin-top: auto; padding-top: 6px; border-top: 1px dashed rgba(0,0,0,0.15);
    font-size: 0.7em; color: #555; display: flex; justify-content: space-between; align-items: center;
}
.sn-speaker { font-weight: 700; color: #333; }
.sn-tag { display: inline-block; background: rgba(0,0,0,0.09); border-radius: 9px; padding: 1px 7px; font-size: 0.85em; margin: 1px 2px; }
.sn-score { background: rgba(0,0,0,0.13); border-radius: 8px; padding: 2px 8px; font-weight: 700; color: #333; }
</style>
"""


def render_board(notes: list, cols_per_row: int = 3, show_tape: bool = True):
    """Render the corkboard + sticky notes as a single st.html() fragment.

    st.html() renders raw HTML as real DOM (never as literal text), which
    prevents the backend <div>/code from appearing on the notes — unlike
    st.markdown(unsafe_allow_html=True) which is unreliable across versions.
    All styling is self-contained inside the fragment.
    """
    import html as _html
    notes_html = []
    colors = {
        "pin": ["radial-gradient(circle at 32% 32%, #ff8a80, #c62828)",
                "radial-gradient(circle at 32% 32%, #82b1ff, #1565c0)",
                "radial-gradient(circle at 32% 32%, #69f0ae, #00897b)",
                "radial-gradient(circle at 32% 32%, #ffe082, #f9a825)",
                "radial-gradient(circle at 32% 32%, #b388ff, #6a1b9a)",
                "radial-gradient(circle at 32% 32%, #ff80ab, #c2185b)"],
        "rot": ["-2deg", "1.6deg", "-1deg", "2.2deg", "-0.6deg", "1.2deg", "-1.8deg", "0.8deg", "-2.5deg", "1.8deg"],
    }

    for i, note in enumerate(notes):
        bg = _html.escape(str(note.get("color", NOTE_COLORS["General"])), quote=False)
        pin_bg = colors["pin"][i % len(colors["pin"])]
        rot = colors["rot"][i % len(colors["rot"])]
        is_imp = bool(note.get("is_important", True))
        try:
            score = int(float(note.get("importance_score", 0)) * 100)
        except Exception:
            score = 0

        def clean(v):
            if not isinstance(v, str):
                v = str(v)
            return _html.escape(v, quote=False)

        title = clean(note.get("title", ""))
        text = clean(note.get("full_text", note.get("text", "")))
        speaker = clean(note.get("speaker", ""))
        cat = clean(note.get("category", "General"))
        tags = "".join(f'<span class="sn-tag">{clean(t)}</span>' for t in note.get("tags", []) or [])

        imp_badge = '<span class="sn-badge sn-badge-imp">★ Important</span>' if is_imp else ""
        opacity = "1" if is_imp else "0.75"

        notes_html.append(f"""
        <div class="sn-note" style="background:{bg}; transform:rotate({rot}); opacity:{opacity};">
            <div class="sn-top"></div>
            <div class="sn-pin" style="background:{pin_bg};"></div>
            <div><span class="sn-badge">{cat}</span>{imp_badge}</div>
            <div class="sn-title">{title}</div>
            <div class="sn-text">{text}</div>
            <div class="sn-meta">
                <span class="sn-speaker">{speaker}</span>
                <span>{tags}</span>
                <span class="sn-score">{score}%</span>
            </div>
        </div>""")

    fragment = NOTE_CSS + f'<div class="sn-body">' + "".join(notes_html) + "</div>"
    st.html(fragment)


def page_home():
    render_hero(
        "Sticky Note Generator 🗒️",
        "Turn casual meeting conversations into concise, actionable sticky notes — automatically!",
        ["🎯 NLP", "🤖 Machine Learning", "📊 Evaluation", "📝 Action Items", "🗂️ Categories", "💡 Decisions & Deadlines"],
    )

    render_section("What does it do?")
    colA, colB, colC = st.columns(3)
    with colA:
        _html("""
        <div class="card">
            <h4>🧠 Smart Analysis</h4>
            <p>Analyzes meetings in real-time using NLP feature extraction — action verbs, decisions,
            deadlines, questions, named entities and more.</p>
        </div>
        """)
    with colB:
        _html("""
        <div class="card">
            <h4>📝 Sticky Notes</h4>
            <p>Generates color-coded sticky notes pinned to a virtual corkboard, each categorized
            and scored by importance for clarity.</p>
        </div>
        """)
    with colC:
        _html("""
        <div class="card">
            <h4>🔬 Model Driven</h4>
            <p>Built on a trained classifier (Logistic Regression) with 89% test accuracy.
            Models are compared and evaluated rigorously.</p>
        </div>
        """)

    render_section("Ready to try?")
    _html("""
    <div class="card">
        <p style="font-size:1em;">
            🚀 <strong>Head over to <span style="color:#ffd54f;">Generate Notes</span></strong> to paste
            a meeting transcript or pick a sample meeting, and watch it transform into a colorful
            board of sticky notes. Explore the dataset, model, and evaluation in the other pages!
        </p>
    </div>
    """)

    render_section("Sample preview", "auto-generated")
    sample_topic = TOPICS[0]
    sample_text = "\n".join(f"{s}: {t}" for s, t in sample_topic["important_segments"] + sample_topic["casual_segments"])
    result = generate_sticky_notes(sample_text)
    notes = result["sticky_notes"]
    render_board(notes[:6], show_tape=True)


def _parse_uploaded_text(uploaded) -> str:
    raw = uploaded.getvalue().decode("utf-8", errors="replace")
    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(io.StringIO(raw))
            if "transcript" in df.columns:
                lines = []
                for _, row in df.iterrows():
                    for l in str(row["transcript"]).split("\n"):
                        if l.strip():
                            lines.append(l.strip())
                return "\n".join(lines)
    except Exception:
        pass
    return raw


def page_generate():
    render_hero(
        "Generate Meeting Sticky Notes",
        "Paste a conversation or choose a sample — the system builds your board instantly.",
        ["📝 Paste", "💾 Upload", "🗂️ Samples"],
    )

    if "active_transcript" not in st.session_state:
        st.session_state.active_transcript = None
    if "show_paste" not in st.session_state:
        st.session_state.show_paste = True

    render_section("1. Choose your transcript")
    tab_paste, tab_upload, tab_sample = st.tabs(["📝 Paste Transcript", "📄 Upload File", "🗂️ Sample Meetings"])

    with tab_paste:
        st.markdown("Paste a transcript where each line begins with the speaker name followed by a colon:")
        st.text_area(
            "Transcript",
            height=240,
            placeholder="Alice: We need to finalize the API design by Friday.\nBob: I will prepare the database schema.\nCarol: The deployment should happen next Monday.\nDave: That sounds great, I agree.",
            label_visibility="collapsed",
            key="paste_area",
        )
        if st.button("✨ Generate Notes from Paste", type="primary", width="stretch", key="btn_paste"):
            st.session_state.active_transcript = st.session_state.paste_area

    with tab_upload:
        st.markdown("Upload a **.txt** or **.csv** transcript file (drag & drop works too).")
        up = st.file_uploader("Upload transcript", type=["txt", "csv"], key="file_upload")
        if up is not None:
            parsed = _parse_uploaded_text(up)
            if parsed.strip():
                st.session_state.active_transcript = parsed
                st.success(f"Loaded '{up.name}' ({len(parsed.splitlines())} lines). Now generating notes…")

    with tab_sample:
        sample_names = [t["theme"] for t in TOPICS]
        cols = st.columns(2)
        pick_col = cols[0].selectbox("Choose a sample meeting theme:", sample_names, key="sample_select")
        idx = sample_names.index(pick_col)
        topic = TOPICS[idx]
        with cols[1]:
            _html(
                f'<div class="card" style="margin-top:2px;"><h4>Context</h4><p>{topic["context"]} · '
                f'Participants: {", ".join(topic["members"])}</p></div>'
            )
        if st.button("✨ Generate Notes from This Sample", type="primary", width="stretch", key="btn_sample"):
            st.session_state.active_transcript = "\n".join(
                f"{s}: {t}" for s, t in topic["important_segments"] + topic["casual_segments"]
            )

    transcript_text = st.session_state.active_transcript

    if transcript_text and transcript_text.strip():
        render_section("2. Meeting board", "click a note to inspect it")
        with st.spinner("Analyzing the conversation and pinning notes…"):
            result = generate_sticky_notes(transcript_text)

        summary = result["meeting_summary"]
        render_stats([
            ("🗣️", result["total_segments"], "Segments"),
            ("⭐", result["important_segments"], "Important"),
            ("👥", summary["unique_speakers"], "Speakers"),
            ("❓", summary["total_questions"], "Questions"),
            ("✅", summary["total_action_items"], "Actions"),
            ("📅", summary["total_dates_mentioned"], "Deadlines"),
        ])

        notes = result["sticky_notes"]

        render_section("Your Sticky Notes", f"{len(notes)} notes · click a note to inspect it")

        categories = sorted(set(n["category"] for n in notes))
        all_cats = ["All", "Important Only"] + categories

        fcol1, fcol2, fcol3 = st.columns([1, 2, 1])
        with fcol1:
            selected_cat = st.selectbox("Filter by category", all_cats, key="cat_filter")
        with fcol2:
            search_q = st.text_input("Search notes", placeholder="Type to search…", key="note_search")
        with fcol3:
            order = st.selectbox("Sort", ["Importance", "Category", "Speaker"], key="sort_order")

        filtered = list(notes)
        if selected_cat == "Important Only":
            filtered = [n for n in filtered if n["is_important"]]
        elif selected_cat != "All":
            filtered = [n for n in filtered if n["category"] == selected_cat]

        if search_q:
            q = search_q.lower()
            filtered = [n for n in filtered if q in n["title"].lower() or q in n["full_text"].lower() or q in n["speaker"].lower()]

        if order == "Importance":
            filtered.sort(key=lambda n: (-int(n["is_important"]), -n["importance_score"]))
        elif order == "Category":
            filtered.sort(key=lambda n: (n["category"], -n["importance_score"]))
        else:
            filtered.sort(key=lambda n: (n["speaker"].lower(), -n["importance_score"]))

        if filtered:
            render_board(filtered, show_tape=True)

            with st.expander("📥 Export notes"):
                df_notes = pd.DataFrame([{
                    "Category": n["category"],
                    "Important": "Yes" if n["is_important"] else "No",
                    "Speaker": n["speaker"],
                    "Title": n["title"],
                    "Importance%": int(n["importance_score"] * 100),
                    "Tags": ", ".join(n["tags"]),
                    "Text": n["full_text"],
                } for n in filtered])
                st.download_button(
                    "⬇️ Download notes as CSV",
                    df_notes.to_csv(index=False).encode("utf-8"),
                    file_name="sticky_notes.csv",
                    mime="text/csv",
                )
                csv_buf = io.StringIO()
                df_notes.to_csv(csv_buf, index=False)
                txt_buf = "\n\n".join(f"[{n['category']}] ({n['speaker']}) {n['title']}\n{n['full_text']}" for n in filtered)
                st.download_button(
                    "⬇️ Download notes as TXT",
                    txt_buf.encode("utf-8"),
                    file_name="sticky_notes.txt",
                    mime="text/plain",
                )

            with st.expander("📋 View as data table"):
                st.dataframe(df_notes, width="stretch", hide_index=True)

            with st.expander("🧩 Meeting summary"):
                _html(
                    f"<div class='card'><p>This meeting had <strong>{result['total_segments']}</strong> "
                    f"utterances across <strong>{summary['unique_speakers']}</strong> participants. "
                    f"The system flagged <strong>{result['important_segments']}</strong> as important, "
                    f"including <strong>{summary['total_action_items']}</strong> action items, "
                    f"<strong>{summary['total_decisions']}</strong> decisions, and "
                    f"<strong>{summary['total_dates_mentioned']}</strong> date/deadline references.</p></div>"
                )
        else:
            _html('<div class="warn-note">No notes match the current filter/search. Try widening it.</div>')
    else:
        _html("""
        <div class="empty-state">
            <div class="icon">🗒️</div>
            <h3>Ready when you are.</h3>
            <p>Paste a meeting transcript, upload a file, or pick a sample <br>to generate your sticky note board.</p>
        </div>
        """)


def page_features():
    render_hero(
        "Feature Analysis",
        "The signals our model uses to decide what matters in a conversation.",
        ["🧪 19 Features", "🔤 Lexical", "🏷️ Structural", "🌐 Semantic"],
    )

    render_section("Important Content Features", "that distinguish key info from chatter")
    features = [
        ("Word Count", "Number of words in the utterance. Important items tend to be longer and more detailed."),
        ("Sentence Count", "Number of sentences. Multi-sentence utterances often contain decisions or summaries."),
        ("Average Word Length", "Avg characters per word — signals technical/formal vocabulary."),
        ("Has Question", "Question marks and question phrases — Q&A drives key info and next steps."),
        ("Has Action Verb", "Detects action verbs like 'prepare', 'send', 'create', 'submit', 'finalize'."),
        ("Has Decision", "Decision markers: 'decided', 'agreed', 'confirmed', 'let's go with'."),
        ("Contains Date/Deadline", "Dates, 'deadline', 'next week', 'by Friday' etc."),
        ("Keyword Density (Action)", "Ratio of action keywords to total words."),
        ("Named Entities", "Person names, dates, times, and emails mentioned."),
        ("Sentiment Indicators", "Positive/negative word counts — agreements vs. concerns."),
        ("Speaker Continuity", "Whether the speaker is the same as the previous turn (context)."),
        ("Is Short Utterance", "Fewer than 5 words — usually casual backchannels ('yeah', 'okay')."),
    ]

    cols = st.columns(2)
    for i, (feat, desc) in enumerate(features):
        with cols[i % 2]:
            _html(f"""<div class="card" style="margin-bottom:10px;"><h4>🧪 {feat}</h4><p>{desc}</p></div>""")

    render_section("Training Visualizations")
    plot_files = [
        ("03_feature_importance.png", "Feature Importance (Best Model)"),
        ("01_model_comparison.png", "Model Comparison"),
        ("02_confusion_matrix.png", "Confusion Matrix"),
    ]
    for fname, caption in plot_files:
        p = PLOTS_DIR / fname
        if p.exists():
            st.image(str(p), caption=caption, width="stretch")
        else:
            _html(f'<div class="warn-note">{caption} not yet generated. Run the training pipeline first.</div>')


def page_evaluation():
    render_hero(
        "Model Evaluation",
        "How accurately the system identifies important content and builds summaries.",
        ["🎯 Precision", "🔁 Recall", "⚖️ F1-Score", "🎯 Accuracy", "📰 ROUGE", "🎨 BLEU", "🌠 METEOR"],
    )

    eval_path = REPORTS_DIR / "evaluation_metrics.json"
    if eval_path.exists():
        with open(eval_path) as f:
            metrics = json.load(f)
        render_section("Classification Performance", f"best model: {metrics.get('best_model','—')}")

        render_stats([
            ("🎯", f"{metrics['accuracy']*100:.1f}%", "Accuracy"),
            ("🎯", f"{metrics['precision_macro']*100:.1f}%", "Precision"),
            ("🔁", f"{metrics['recall_macro']*100:.1f}%", "Recall"),
            ("⚖️", f"{metrics['f1_macro']*100:.1f}%", "F1 Macro"),
            ("⚖️", f"{metrics['f1_weighted']*100:.1f}%", "F1 Weighted"),
        ])

        with st.expander("📊 Detailed Classification Report"):
            st.code(metrics.get("classification_report", "N/A"))

        with st.expander("🔢 Confusion Matrix"):
            cm = pd.DataFrame(
                metrics["confusion_matrix"],
                index=["True: Casual", "True: Important"],
                columns=["Pred: Casual", "Pred: Important"],
            )
            st.dataframe(cm, width="stretch")

    else:
        _html('<div class="warn-note">Evaluation metrics not found. Run the training & evaluation pipeline first.</div>')

    summary_path = REPORTS_DIR / "summary_evaluation.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summ = json.load(f)
        render_section("Summary Quality Metrics", "generated notes vs. reference")
        cards = ""
        for k, v in summ.items():
            cards += f'<div class="stat-card"><div class="stat-icon">📝</div><div class="stat-value">{v:.3f}</div><div class="stat-label">{k.upper()}</div></div>'
        _html(f'<div class="stat-grid">{cards}</div>')

    plot_path = PLOTS_DIR / "04_full_confusion_matrix.png"
    if plot_path.exists():
        render_section("Visualizations")
        st.image(str(plot_path), caption="Full Dataset Confusion Matrix", width="stretch")

    comparison_path = MODELS_DIR / "model_comparison.json"
    if comparison_path.exists():
        with open(comparison_path) as f:
            comp = json.load(f)
        render_section("All Model Comparisons")
        c1, c2 = st.columns(2)
        box = []
        for name, res in comp.items():
            box.append({
                "Model": name,
                "Accuracy": res["accuracy"],
                "Precision": res["precision"],
                "Recall": res["recall"],
                "F1-Macro": res["f1_macro"],
                "CV-F1": res["cv_f1_mean"],
            })
        st.dataframe(pd.DataFrame(box), width="stretch", hide_index=True)


def page_transcript_viewer():
    render_hero(
        "Transcript Viewer & Analyzer",
        "Paste a transcript and see exactly which lines were flagged as important.",
        ["🔍 Highlighting", "🎯 Importance", "👥 Speakers"],
    )

    transcript_input = st.text_area(
        "Paste transcript to analyze",
        height=200,
        key="viewer_area",
        placeholder="Alice: We need to finalize the API design by Friday.\nBob: I will prepare the database schema.\nCarol: Sounds good, let's do it.",
    )

    if transcript_input and transcript_input.strip():
        result = generate_sticky_notes(transcript_input)

        important_indices = set()
        for note in result["sticky_notes"]:
            if note["is_important"]:
                important_indices.add(note["segment_index"])

        render_section("Transcript with Highlights", "yellow = important content")

        lines = transcript_input.strip().split("\n")
        import html as _h
        frag = '<div class="transcript-box">'
        for i, line in enumerate(lines):
            match = re.match(r"^(.+?):\s*(.+)$", line)
            cls = "transcript-line imp" if i in important_indices else "transcript-line"
            if match:
                speaker, text = match.group(1), match.group(2)
                safe_speaker = _h.escape(speaker, quote=False)
                safe_text = _h.escape(text, quote=False)
                frag += f'<div class="{cls}"><span class="transcript-speaker">{safe_speaker}:</span> {safe_text}</div>'
            else:
                safe_line = _h.escape(line, quote=False)
                frag += f'<div class="{cls}">{safe_line}</div>'
        frag += "</div>"
        _html(frag)

        _html(f"""
        <div class="card" style="margin-top:14px;">
            <h4>Analysis Summary</h4>
            <p>Found <strong style="color:#ffd54f;">{result['important_segments']}</strong> important segments
            out of <strong style="color:#ffd54f;">{result['total_segments']}</strong> total.
            Important lines are highlighted in yellow.</p>
        </div>
        """)
    else:
        _html("""
        <div class="empty-state">
            <div class="icon">🔍</div>
            <h3>Paste a transcript to highlight the important parts</h3>
            <p>Important lines will be highlighted in yellow on a virtual board.</p>
        </div>
        """)


st.sidebar.markdown("# 🗒️ Sticky Notes")
st.sidebar.markdown("Meeting-to-notes intelligence")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📝 Generate Notes", "🔬 Feature Analysis", "📊 Evaluation", "📜 Transcript Viewer"],
)

st.sidebar.divider()
st.sidebar.markdown("### About")
st.sidebar.markdown(
    "Analyzes casual meeting conversations with NLP + ML to generate concise, "
    "color-coded sticky notes for action items, decisions, deadlines, and key info."
)
st.sidebar.divider()
st.sidebar.caption("Sticky Note Generator v2.0 · NLP + ML")

if page == "🏠 Home":
    page_home()
elif page == "📝 Generate Notes":
    page_generate()
elif page == "🔬 Feature Analysis":
    page_features()
elif page == "📊 Evaluation":
    page_evaluation()
elif page == "📜 Transcript Viewer":
    page_transcript_viewer()