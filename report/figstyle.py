"""Shared figure style for the presentation figures (report/figures/).

Palette = the dataviz skill's validated reference instance, light mode,
categorical slots used in FIXED order (never cycled). Validator run
2026-09-23 on slots 1-4: all hard gates pass; slots 3 (aqua) and 4
(yellow) are below 3:1 contrast on the surface -> any series drawn in them
MUST carry a visible direct label (the relief rule).

Rules every figure follows:
- one y-axis per panel (never twin axes); different measures -> panels
- legend whenever >= 2 series, plus direct labels when <= 4 series
- text in ink colors, never in the series color
- 2 px lines, >= 8 px markers, recessive grid
- status colors (good/critical) only for "works / broken" semantics, with a
  text label, never as a series color
- images: amplitude in grayscale, phase in a cyclic map (twilight)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
FIG_DIR = REPO / "report" / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8984"
GRID = "#e4e3df"

# Categorical, fixed order (skill reference palette, light).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# Semantic aliases used consistently across figures.
C_OK = SERIES[0]        # "corrected / after" condition (blue)
C_BAD = SERIES[1]       # "default / before / frozen" condition (orange)
C_THIRD = SERIES[2]     # third condition (aqua) -> needs direct label
NOISE_REF = INK_MUTED   # reference lines (noise floor, nominal value)

STATUS = {"good": "#0ca30c", "critical": "#d03b3b"}

SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
            "#256abf", "#184f95", "#0d366b"]

AMP_CMAP = "gray"
PHASE_CMAP = "twilight"

LINEWIDTH = 2.0
MARKERSIZE = 8  # points; ~>= 8 px at 100 dpi


def apply() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 11,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": GRID,
        "axes.linewidth": 1.0,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": plt.cycler(color=SERIES),
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "text.color": INK,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "lines.linewidth": LINEWIDTH,
        "lines.markersize": MARKERSIZE,
        "lines.solid_capstyle": "round",
    })


def direct_label(ax, x, y, text, dx=4, dy=0, ha="left", va="center"):
    """Label a series at a point, in ink (never the series color)."""
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points",
                ha=ha, va=va, color=INK, fontsize=10)


def caption(fig, text):
    """One-line takeaway under the figure, muted ink."""
    # Below the axes: savefig(bbox_inches="tight") grows the canvas to include
    # it, so it never collides with the x label.
    fig.text(0.01, -0.02, text, ha="left", va="top", color=INK_2,
             fontsize=10, wrap=True)


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path
