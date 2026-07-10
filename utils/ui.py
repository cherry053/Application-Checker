"""Streamlit rendering helpers: NSW-branded page chrome and HTML fragments.

All HTML lives in static/html templates; all styling lives in static/css and
the locally vendored NSW Design System stylesheet (no CDN dependency, so the
branding still renders inside firewalled government networks).
"""

from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from core.models import CompletenessReport

STATIC_DIR = Path(__file__).parent.parent / "static"

# Served by Streamlit's static file route (server.enableStaticServing).
NSW_DESIGN_SYSTEM_CSS = (
    '<link rel="stylesheet" href="/app/static/vendor/nsw-design-system-3.24.10.css">'
)

# NSW Design System palette. Every text/background pairing used below meets
# WCAG AA contrast (white on the status colours, dark text on the tints).
NSW_BRAND_DARK = "#002664"
NSW_BRAND_RED = "#D7153A"
NSW_TEXT_DARK = "#22272B"
NSW_SUCCESS = "#008A07"
NSW_WARNING = "#C95000"
NSW_ERROR = "#B81237"
NSW_SUCCESS_BG = "#E5F6E6"
NSW_WARNING_BG = "#FDEDDF"
NSW_ERROR_BG = "#F7E7EB"
WHITE = "#FFFFFF"

# status -> (fill colour, text colour) for the results-list pills.
_PILL_STYLES = {
    "Pass": (NSW_SUCCESS, WHITE),
    "Review": (NSW_WARNING, WHITE),
    "Fail": (NSW_ERROR, WHITE),
}

# overall check status -> (label, colour) for the readiness badge.
_READINESS_STYLES = {
    "PASS": ("Ready", NSW_SUCCESS),
    "FAIL": ("Needs review", NSW_ERROR),
    "PARTIAL": ("Partial", NSW_WARNING),
}

# completeness status -> (css level, label, headline message).
_COMPLETENESS_LEVELS = {
    "complete": (
        "success",
        "Complete",
        "All detected information has been successfully extracted.",
    ),
    "review": (
        "warning",
        "Review Required",
        "Some information could not be verified automatically.",
    ),
    "incomplete": (
        "error",
        "Incomplete",
        "The uploaded table appears to contain information that was not successfully extracted.",
    ),
}

_MAX_PANEL_ISSUES = 8


@lru_cache(maxsize=None)
def _load(*relative_path: str) -> str:
    """Read a static template once per process; templates never change at runtime."""
    return (STATIC_DIR / Path(*relative_path)).read_text()


def render_masthead() -> None:
    st.markdown(_load("html", "masthead.html"), unsafe_allow_html=True)


def render_nosection() -> None:
    st.markdown(_load("html", "nosection.html"), unsafe_allow_html=True)


def render_splash() -> None:
    """Branded loading splash, shown once per session on first page load.

    Pure CSS: the overlay fades out on its own, so it costs no reruns and no
    artificial delay. Re-runs skip it entirely.
    """
    if st.session_state.get("_splash_shown"):
        return
    st.session_state["_splash_shown"] = True
    st.markdown(_load("html", "splash.html"), unsafe_allow_html=True)


def render_header(title: str) -> None:
    """Inject the stylesheets and render the NSW masthead, header, and title bar."""
    st.markdown(NSW_DESIGN_SYSTEM_CSS, unsafe_allow_html=True)
    st.markdown(f"<style>{_load('css', 'main.css')}</style>", unsafe_allow_html=True)
    render_masthead()
    st.markdown(_load("html", "header.html"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="header-bar" id="main-content"><h1 class="header-title">{escape(title)}</h1></div>',
        unsafe_allow_html=True,
    )


def render_cards() -> None:
    st.markdown(_load("html", "cards.html"), unsafe_allow_html=True)


def render_errormessage() -> None:
    st.markdown(_load("html", "errormessage.html"), unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(_load("html", "footer.html"), unsafe_allow_html=True)


def render_uploadinfo() -> None:
    st.markdown(_load("html", "uploadinfo.html"), unsafe_allow_html=True)


def render_readiness_badge(status: str) -> None:
    label, colour = _READINESS_STYLES.get(status, ("Unknown", NSW_TEXT_DARK))
    html = _load("html", "readiness_badge.html").format(label=escape(label), colour=colour)
    st.markdown(html, unsafe_allow_html=True)


def render_status_pill(status: str) -> None:
    colour, text_colour = _PILL_STYLES.get(status, (NSW_TEXT_DARK, WHITE))
    html = _load("html", "status_pill.html").format(
        status=escape(status), colour=colour, text_colour=text_colour
    )
    st.markdown(html, unsafe_allow_html=True)


def render_criteria_rows(criterion: dict) -> None:
    if criterion["passed"]:
        colour, badge, bg_colour = NSW_SUCCESS, "PASS", NSW_SUCCESS_BG
    elif criterion["severity"] == "warning":
        colour, badge, bg_colour = NSW_WARNING, "REVIEW", NSW_WARNING_BG
    else:
        colour, badge, bg_colour = NSW_ERROR, "FAIL", NSW_ERROR_BG

    html = _load("html", "criteria_rows.html").format(
        colour=colour,
        name=escape(criterion["name"]),
        badge=badge,
        bg_colour=bg_colour,
        text_colour=WHITE,
    )
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(title: str, message: str) -> None:
    html = _load("html", "empty_state.html").format(title=escape(title), message=escape(message))
    st.markdown(html, unsafe_allow_html=True)


def render_validation_panel(report: CompletenessReport) -> None:
    """Render the Table Completeness Check outcome as an NSW-styled panel."""
    level, status_label, message = _COMPLETENESS_LEVELS[report.status]

    stats = (
        ("Rows declared (PDF)", "—" if report.rows_declared is None else report.rows_declared),
        ("Rows detected", report.rows_detected),
        ("Rows extracted", report.rows_extracted),
        ("Rows missing", report.rows_missing),
        ("Duplicate rows", report.duplicate_rows),
        ("Columns detected", report.columns_expected),
        ("Columns extracted", report.columns_extracted),
        ("Empty values", report.empty_fields),
        ("Validation confidence", report.confidence_label),
    )
    stats_rows = "".join(
        f'<div class="completeness-panel__stat"><dt>{escape(str(label))}</dt>'
        f"<dd>{escape(str(value))}</dd></div>"
        for label, value in stats
    )

    issues_html = ""
    if report.issues:
        shown = report.issues[:_MAX_PANEL_ISSUES]
        items = "".join(
            f'<li class="completeness-issue completeness-issue--{issue.severity}">'
            f"{escape(issue.message)}</li>"
            for issue in shown
        )
        remainder = len(report.issues) - len(shown)
        if remainder > 0:
            items += (
                '<li class="completeness-issue completeness-issue--info">'
                f"…and {remainder} further finding(s).</li>"
            )
        issues_html = (
            '<details class="completeness-panel__issues">'
            f"<summary>{len(report.issues)} finding(s) from the completeness check</summary>"
            f"<ul>{items}</ul></details>"
        )

    review_html = ""
    if report.manual_review_recommended:
        review_html = (
            '<p class="completeness-panel__review"><strong>Manual review recommended:</strong> '
            "automatic verification could not confidently confirm every value against the "
            "source table.</p>"
        )

    html = _load("html", "validation_panel.html").format(
        level=level,
        status_label=status_label,
        message=message,
        score=report.score,
        stats_rows=stats_rows,
        issues_html=issues_html,
        review_html=review_html,
    )
    st.markdown(html, unsafe_allow_html=True)
