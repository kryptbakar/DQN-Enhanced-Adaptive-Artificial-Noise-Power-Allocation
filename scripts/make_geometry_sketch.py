"""
Generate figures/14_geometry_sketch.png -- a clean conceptual diagram
of Alice (multi-antenna transmitter), Bob (legitimate receiver), and
Eve (passive eavesdropper) with the MRT beam toward Bob and the
artificial-noise lobe sprayed elsewhere.

Used on slide 3 of the deck to give the audience a literal picture of
the geometry before any math.

Run from the repo root:
    python scripts/make_geometry_sketch.py
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Wedge, Circle, FancyBboxPatch


FIG_DIR = "figures"


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12.0, 6.5))

    NAVY    = "#1f4e79"
    GREEN   = "#2ca02c"
    RED     = "#c0504d"
    GREY    = "#7f7f7f"
    SOFT_G  = "#e0f1e0"
    SOFT_R  = "#fae7e6"
    YELLOW  = "#f7d774"

    # Coordinate system: Alice at the origin, looking right.
    # Bob is at +x, Eve is up-and-right.
    alice_xy = (0.0, 0.0)
    bob_xy   = (8.0, 0.5)
    eve_xy   = (5.5, 3.5)

    # === MRT beam toward Bob: a tight green wedge ====================
    bob_angle = np.degrees(np.arctan2(bob_xy[1] - alice_xy[1],
                                      bob_xy[0] - alice_xy[0]))
    beam = Wedge(alice_xy, 9.0,
                 bob_angle - 8, bob_angle + 8,
                 facecolor=SOFT_G, edgecolor=GREEN, linewidth=2.0,
                 alpha=0.55, zorder=1)
    ax.add_patch(beam)

    # === AN coverage: wide red wedge sweeping the rest of space ======
    # Two arc segments: above and below Bob's line, avoiding the green wedge.
    # We draw the AN as two soft red wedges.
    an_top = Wedge(alice_xy, 8.5,
                   bob_angle + 12, bob_angle + 100,
                   facecolor=SOFT_R, edgecolor=RED, linewidth=1.5,
                   alpha=0.35, zorder=0, hatch="///")
    an_bot = Wedge(alice_xy, 8.5,
                   bob_angle - 100, bob_angle - 12,
                   facecolor=SOFT_R, edgecolor=RED, linewidth=1.5,
                   alpha=0.35, zorder=0, hatch="///")
    ax.add_patch(an_top)
    ax.add_patch(an_bot)

    # === Alice (multi-antenna array) =================================
    Nt = 4
    ant_y = np.linspace(-0.4, 0.4, Nt)
    for y in ant_y:
        circle = Circle((0.0, y), 0.13, facecolor=NAVY,
                        edgecolor="white", linewidth=1.2,
                        zorder=10)
        ax.add_patch(circle)
    ax.add_patch(Circle((0.0, 0.0), 0.65, facecolor="none",
                        edgecolor=NAVY, linewidth=2.5, zorder=9))
    ax.text(-0.25, -1.05, "Alice",
            fontsize=18, fontweight="bold", color=NAVY,
            ha="center", va="top")
    ax.text(-0.25, -1.5, f"{Nt} transmit antennas",
            fontsize=11, color=NAVY,
            ha="center", va="top", style="italic")

    # === Bob =========================================================
    bob_circle = Circle(bob_xy, 0.45,
                        facecolor=GREEN, edgecolor="white",
                        linewidth=2.0, zorder=10)
    ax.add_patch(bob_circle)
    ax.text(bob_xy[0], bob_xy[1] - 1.0, "Bob",
            fontsize=18, fontweight="bold", color=GREEN,
            ha="center", va="top")
    ax.text(bob_xy[0], bob_xy[1] - 1.45,
            "legitimate receiver\n(hears clean signal,\nAN cancels here)",
            fontsize=10, color=GREEN, ha="center", va="top",
            style="italic")

    # === Eve =========================================================
    eve_circle = Circle(eve_xy, 0.45,
                        facecolor=RED, edgecolor="white",
                        linewidth=2.0, zorder=10)
    ax.add_patch(eve_circle)
    ax.text(eve_xy[0] + 0.15, eve_xy[1] + 0.85, "Eve",
            fontsize=18, fontweight="bold", color=RED,
            ha="left", va="bottom")
    ax.text(eve_xy[0] + 0.15, eve_xy[1] + 0.40,
            "passive eavesdropper\n(hears signal + AN;\nAN drowns the leak)",
            fontsize=10, color=RED, ha="left", va="bottom",
            style="italic")

    # === Beam arrow toward Bob ======================================
    ax.annotate(
        "", xy=bob_xy, xytext=alice_xy,
        arrowprops=dict(arrowstyle="->", color=GREEN, linewidth=3.5,
                        mutation_scale=22),
        zorder=5
    )
    # Annotate beam
    ax.text(4.2, 0.95, "MRT beam  w = hB / ‖hB‖",
            fontsize=12, color=GREEN, fontweight="bold",
            ha="center", style="italic")

    # === Some leak toward Eve (faint red arrow) =====================
    ax.annotate(
        "", xy=eve_xy, xytext=alice_xy,
        arrowprops=dict(arrowstyle="->", color=RED, linewidth=2.0,
                        alpha=0.55, mutation_scale=18,
                        linestyle=(0, (4, 3))),
        zorder=4
    )
    ax.text(2.4, 2.4, "signal leak +\nAN spray to Eve",
            fontsize=11, color=RED, alpha=0.85,
            ha="center", style="italic")

    # === Caption-style labels in floating boxes =====================
    legend_x, legend_y = 8.2, 4.7
    box = FancyBboxPatch(
        (legend_x, legend_y), 4.2, 1.4,
        boxstyle="round,pad=0.15", linewidth=1.5,
        edgecolor=GREY, facecolor="#f4f4f6", zorder=8
    )
    ax.add_patch(box)
    ax.text(legend_x + 0.2, legend_y + 1.05,
            "Green wedge  →  MRT beam toward Bob",
            fontsize=11, color=GREEN, fontweight="bold")
    ax.text(legend_x + 0.2, legend_y + 0.62,
            "Red shading  →  AN sprayed elsewhere",
            fontsize=11, color=RED, fontweight="bold")
    ax.text(legend_x + 0.2, legend_y + 0.20,
            "ρ controls the green/red split of total power",
            fontsize=10, color="#1a1a1a", style="italic")

    # Title
    ax.set_title(
        "MISO wiretap channel  —  who sits where, who hears what",
        fontsize=16, fontweight="bold", pad=14
    )

    ax.set_xlim(-2.2, 12.7)
    ax.set_ylim(-2.5, 6.5)
    ax.set_aspect("equal")
    ax.axis("off")

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "14_geometry_sketch.png")
    fig.savefig(out, dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print(f"[SAVE] {out}")


if __name__ == "__main__":
    main()
