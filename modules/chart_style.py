"""Centralized color palette and chart themes.

Inspired by PyCon DE 2026: "Effective Data Visualizations" (Haitz).
Provides consistent styling for both matplotlib (PDF reports) and Plotly (dashboard).
"""
from __future__ import annotations

PALETTE = {
    "navy": "#0f172a",
    "slate": "#64748b",
    "blue": "#2563eb",
    "red": "#991b1b",
    "green": "#166534",
    "amber": "#b45309",
    "white": "#ffffff",
    "light_bg": "#f8fafc",
    "dark_bg": "#0f172a",
    "dark_surface": "#1e293b",
    "dark_text": "#e2e8f0",
}

COMPLIANCE_LIGHT = {
    "figure.facecolor": PALETTE["white"],
    "axes.facecolor": PALETTE["light_bg"],
    "axes.edgecolor": PALETTE["slate"],
    "axes.labelcolor": PALETTE["navy"],
    "text.color": PALETTE["navy"],
    "xtick.color": PALETTE["slate"],
    "ytick.color": PALETTE["slate"],
    "grid.color": "#e2e8f0",
    "grid.alpha": 0.7,
    "axes.grid": True,
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
}

COMPLIANCE_DARK = {
    "figure.facecolor": PALETTE["dark_bg"],
    "axes.facecolor": PALETTE["dark_surface"],
    "axes.edgecolor": PALETTE["slate"],
    "axes.labelcolor": PALETTE["dark_text"],
    "text.color": PALETTE["dark_text"],
    "xtick.color": PALETTE["dark_text"],
    "ytick.color": PALETTE["dark_text"],
    "grid.color": "#334155",
    "grid.alpha": 0.5,
    "axes.grid": True,
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
}


def apply_style(theme: str = "light") -> None:
    """Apply the compliance chart style to matplotlib."""
    import matplotlib.pyplot as plt

    style = COMPLIANCE_LIGHT if theme == "light" else COMPLIANCE_DARK
    plt.rcParams.update(style)


def get_colors() -> dict[str, str]:
    """Return the semantic color palette for Plotly/Streamlit use."""
    return dict(PALETTE)
