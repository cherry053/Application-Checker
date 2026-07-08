from pathlib import Path

import streamlit as st

STATIC_DIR = Path(__file__).parent.parent / "static"

NSW_DESIGN_SYSTEM_CSS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/nsw-design-system@3.24.10/dist/css/main.min.css">
"""


def _load(*relative_path: str) -> str:
    return (STATIC_DIR / Path(*relative_path)).read_text()


def render_masthead():
    st.markdown(_load("html", "masthead.html"), unsafe_allow_html=True)

def render_nosection():
    st.markdown(_load("html", "nosection.html"), unsafe_allow_html=True)


def render_header(title: str):
    st.markdown(NSW_DESIGN_SYSTEM_CSS, unsafe_allow_html=True)
    st.markdown(f"<style>{_load('css', 'main.css')}</style>", unsafe_allow_html=True)
    st.markdown(_load("html", "header.html"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="header-bar"><span class="header-title">{title}</span></div>',
        unsafe_allow_html=True,
    )

def render_cards():
    st.markdown(_load("html", "cards.html"), unsafe_allow_html=True)

def render_errormessage():
    st.markdown(_load("html", "errormessage.html"), unsafe_allow_html=True)


def render_footer():
    st.markdown(_load("html", "footer.html"), unsafe_allow_html=True)

def render_uploadinfo():
    st.markdown(_load("html", "uploadinfo.html"), unsafe_allow_html=True)

def render_readiness_badge(status: str):
    status_map = {
        "PASS": ("Ready", "#00A908"),
        "FAIL": ("Needs review", "#B81237"),
        "PARTIAL": ("Partial", "#C4780A"),
    }
    label, colour = status_map.get(status, ("Unknown", "#666"))
    html = _load("html", "readiness_badge.html").format(label=label, colour=colour)
    st.markdown(html, unsafe_allow_html=True)

def render_status_pill(status: str):
    colours = {
        "Pass": "#00AA45",
        "Review": "#FAAF05",
        "Fail": "#D7153A",
    }
    colour = colours.get(status, "#666")
    html = _load("html", "status_pill.html").format(status=status, colour=colour)
    st.markdown(html, unsafe_allow_html=True)

def render_criteria_rows(criterion: dict):
    if criterion["passed"]:
        colour, badge, bg_colour = "#00AA45", "PASS", "#DBFADF"
    elif criterion["severity"] == "warning":
        colour, badge, bg_colour = "#FAAF05", "REVIEW", "#FFF4CF"
    else:
        colour, badge, bg_colour = "#D7153A", "FAIL", "#FFE6EA"

    html = _load("html", "criteria_rows.html").format(
        colour=colour,
        name=criterion["name"],
        badge=badge,
        bg_colour=bg_colour
    )
    st.markdown(html, unsafe_allow_html=True)