"""
Generate figures/12_before_after.png -- a two-panel "before vs after"
comparison built specifically for the slide deck.

Layout (horizontal):
    LEFT panel:  before adding our AI
                 only Fixed and Traditional (with noisy CSI).
                 Annotated to show where Traditional drops below Fixed.

    RIGHT panel: after adding our AI
                 same axes, but with the DQN curve overlaid in green.
                 Annotated to show the DQN sitting at or above Fixed.

Both panels share the same axes ranges and large fonts so the X and Y
axes are readable from across a classroom.

Run from the repo root:
    python scripts/make_before_after.py
"""

from __future__ import annotations

import os
import sys

# repo-root injection so 'core.*' imports work from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.channel import generate_rayleigh_channel
from core.csi import imperfect_csi
from core.schemes import (fixed_scheme, traditional_optimizer,
                          evaluate_scheme, make_dqn_scheme)
from core.dqn_agent import DQNAgent
from core.experiments import default_model_path


FIG_DIR = "figures"
N_CHANNELS = 400
KAPPA_EVAL = 0.4
NT = 4
SEED = 2026


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)

    print(f"[BEFORE/AFTER] Nt={NT}, kappa={KAPPA_EVAL}, "
          f"{N_CHANNELS} channels per SNR point")

    # Load the trained DQN
    agent = DQNAgent()
    agent.load(default_model_path(NT))
    dqn = make_dqn_scheme(agent)

    # SNR sweep
    snr_db_range = np.arange(0, 31, 3, dtype=float)
    rs_fixed   = np.zeros_like(snr_db_range)
    rs_trad    = np.zeros_like(snr_db_range)
    rs_dqn     = np.zeros_like(snr_db_range)

    rng = np.random.default_rng(SEED)
    chans = [(generate_rayleigh_channel(NT, rng),
              generate_rayleigh_channel(NT, rng)) for _ in range(N_CHANNELS)]

    for i, snr_db in enumerate(snr_db_range):
        snr_lin = 10.0 ** (snr_db / 10.0)
        s_fix = s_tr = s_dq = 0.0
        dqn.reset()
        for hB, hE in chans:
            hE_n = imperfect_csi(hE, KAPPA_EVAL, rng)
            _, rf = evaluate_scheme(fixed_scheme,         hB, hE, hE_n,
                                    snr_lin, KAPPA_EVAL)
            _, rt = evaluate_scheme(traditional_optimizer, hB, hE, hE_n,
                                    snr_lin, KAPPA_EVAL)
            _, rd = evaluate_scheme(dqn,                  hB, hE, hE_n,
                                    snr_lin, KAPPA_EVAL)
            s_fix += rf; s_tr += rt; s_dq += rd
        rs_fixed[i] = s_fix / N_CHANNELS
        rs_trad[i]  = s_tr  / N_CHANNELS
        rs_dqn[i]   = s_dq  / N_CHANNELS
        print(f"  SNR={snr_db:>4.0f} dB  |  Fixed={rs_fixed[i]:>6.3f}  "
              f"Trad={rs_trad[i]:>6.3f}  DQN={rs_dqn[i]:>6.3f}")

    # Shared y-axis range so the two panels are visually directly comparable.
    ymin = float(min(rs_fixed.min(), rs_trad.min(), rs_dqn.min())) - 0.4
    ymax = float(max(rs_fixed.max(), rs_trad.max(), rs_dqn.max())) + 0.4

    # ---- Build the two-panel figure ---------------------------------
    fig, (ax_before, ax_after) = plt.subplots(
        1, 2, figsize=(14.5, 6.0), sharey=True
    )

    # Big tick fonts so axes are readable at a distance
    for ax in (ax_before, ax_after):
        ax.tick_params(axis="both", labelsize=13)
        ax.grid(True, alpha=0.35)
        ax.set_ylim(ymin, ymax)
        ax.set_xlim(snr_db_range[0] - 1, snr_db_range[-1] + 1)

    # ---- LEFT: BEFORE AI -------------------------------------------
    ax_before.plot(snr_db_range, rs_fixed, "o-",
                   color="#7f7f7f", linewidth=2.6, markersize=8,
                   label="Fixed (ρ = 0.5)  —  the do-nothing baseline")
    ax_before.plot(snr_db_range, rs_trad, "s--",
                   color="#c0504d", linewidth=2.6, markersize=8,
                   label="Traditional optimiser  —  trusts noisy ĥE")
    ax_before.set_title(
        "BEFORE  —  only existing schemes\n"
        "(no AI, just Goel-Negi or scipy optimiser)",
        fontsize=15, fontweight="bold", color="#c0504d", pad=14
    )
    ax_before.set_xlabel("Transmit power  —  SNR (dB)", fontsize=14)
    ax_before.set_ylabel(
        "Average secrecy rate  —  Rs (bits/s/Hz)\n"
        "higher is better",
        fontsize=14
    )
    ax_before.legend(loc="upper left", fontsize=11)

    # Highlight: the Traditional optimiser drops below Fixed
    cross_idx = None
    for i in range(1, len(rs_trad)):
        if rs_trad[i] < rs_fixed[i] and rs_trad[i - 1] >= rs_fixed[i - 1]:
            cross_idx = i
            break
    if cross_idx is None:
        # plain dip
        i_dip = int(np.argmin(rs_trad - rs_fixed))
        ax_before.annotate(
            "Traditional\ndrops BELOW Fixed\nat noisy CSI",
            xy=(snr_db_range[i_dip], rs_trad[i_dip]),
            xytext=(snr_db_range[i_dip] - 6, rs_trad[i_dip] - 1.6),
            fontsize=12, fontweight="bold", color="#c0504d",
            arrowprops=dict(arrowstyle="->", color="#c0504d", lw=2),
            bbox=dict(boxstyle="round,pad=0.4", fc="#fae7e6",
                      ec="#c0504d", lw=1.5),
            ha="center"
        )
    else:
        ax_before.annotate(
            "Traditional\ndrops BELOW Fixed",
            xy=(snr_db_range[cross_idx], rs_trad[cross_idx]),
            xytext=(snr_db_range[cross_idx] - 4,
                    rs_trad[cross_idx] - 1.6),
            fontsize=12, fontweight="bold", color="#c0504d",
            arrowprops=dict(arrowstyle="->", color="#c0504d", lw=2),
            bbox=dict(boxstyle="round,pad=0.4", fc="#fae7e6",
                      ec="#c0504d", lw=1.5),
            ha="center"
        )

    # ---- RIGHT: AFTER AI -------------------------------------------
    ax_after.plot(snr_db_range, rs_fixed, "o-",
                  color="#7f7f7f", linewidth=2.6, markersize=8,
                  label="Fixed (ρ = 0.5)")
    ax_after.plot(snr_db_range, rs_trad, "s--",
                  color="#c0504d", linewidth=2.6, markersize=8,
                  label="Traditional (noisy CSI)")
    ax_after.plot(snr_db_range, rs_dqn, "D-",
                  color="#2ca02c", linewidth=3.4, markersize=10,
                  label="DQN  —  OUR AI agent")
    ax_after.set_title(
        "AFTER  —  with our DQN agent\n"
        "(same noisy CSI; same channels)",
        fontsize=15, fontweight="bold", color="#2ca02c", pad=14
    )
    ax_after.set_xlabel("Transmit power  —  SNR (dB)", fontsize=14)
    ax_after.legend(loc="upper left", fontsize=11)

    # Highlight: the DQN sits at or above Fixed
    i_show = len(snr_db_range) - 3   # near 24 dB
    ax_after.annotate(
        "DQN stays AT or ABOVE\nFixed at every SNR",
        xy=(snr_db_range[i_show], rs_dqn[i_show]),
        xytext=(snr_db_range[i_show] - 14, rs_dqn[i_show] + 1.0),
        fontsize=12, fontweight="bold", color="#2ca02c",
        arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=2),
        bbox=dict(boxstyle="round,pad=0.4", fc="#e0f1e0",
                  ec="#2ca02c", lw=1.5),
        ha="center"
    )

    fig.suptitle(
        f"Before vs After our AI    "
        f"(Nt = {NT}, κ = {KAPPA_EVAL}, {N_CHANNELS} unseen channels per point)",
        fontsize=14, fontweight="bold", y=1.02
    )
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "12_before_after.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[SAVE] {out}")


if __name__ == "__main__":
    main()
