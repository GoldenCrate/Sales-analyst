"""Shared Storytelling-with-Data chart styling.

Mute everything to grey and spend an accent colour on what matters; declutter the
chrome; keep a soft background grid. Two semantic accents: BLUE for positive /
opportunity framings, ACCENT (red) for risk / problem framings.
"""

import streamlit as st

GREY = "#bfbfbf"
ACCENT = "#c00000"   # red — risk / problem (bottlenecks, stalled, slowest)
BLUE = "#1434cb"     # Visa blue — positive / focus (top performer, the series that matters)
LINE = "#8c8c8c"
TEXT = "#595959"
GRID = "#ebebeb"
INSIGHT_TEXT = "#3b3b3b"

# Restrained categorical palette for genuine multi-series charts (lines/scatter
# where each colour encodes a distinct, meaningful category).
CATEGORY_RANGE = ["#1434cb", "#7a8cff", "#8c8c8c", "#c9a227", "#c00000"]


def style(chart):
    """Apply the shared decluttered, gridded styling to an Altair chart."""
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            grid=True,
            gridColor=GRID,
            domainColor="#d9d9d9",
            tickColor="#d9d9d9",
            labelColor=TEXT,
            titleColor=TEXT,
        )
        .configure_title(color=TEXT, fontSize=15, anchor="start")
        .configure_legend(labelColor=TEXT, titleColor=TEXT)
    )


def insight(text: str) -> None:
    """Render a readable one-line insight under a chart (higher contrast than st.caption).

    Accepts simple inline HTML such as <b>...</b> for emphasis.
    """
    st.markdown(
        f"<p style='font-size:0.9rem; color:{INSIGHT_TEXT}; line-height:1.45; "
        f"margin-top:-0.4rem'>{text}</p>",
        unsafe_allow_html=True,
    )


def fmt_big(value: float, money: bool = False) -> str:
    """Human-readable magnitude: 5.42B, $6.51B, 812.3M, $45.0K."""
    prefix = "$" if money else ""
    a = abs(value)
    if a >= 1e9:
        return f"{prefix}{value / 1e9:.2f}B"
    if a >= 1e6:
        return f"{prefix}{value / 1e6:.1f}M"
    if a >= 1e3:
        return f"{prefix}{value / 1e3:.1f}K"
    return f"{prefix}{value:,.0f}"
