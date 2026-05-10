"""
Generate figures/13_training_curve_clean.png -- a clean, slide-friendly
training-progress curve that drops the noisy per-episode samples and
shows only the smoothed running-average reward.

Why a separate script:
The original figures/03_dqn_training_curve.png mixes a faint per-episode
scatter cloud with a running-average line.  That looks honest in a
report but reads as 'noisy' on a slide deck projected to a classroom.
This script produces a single smooth-line version for the slides.

What it does:
- Runs a short training pass at Nt = 4 (3000 episodes, ~15 s on CPU).
- Captures the 100-episode running average.
- Plots that single line, large fonts, big tick labels, with the
  epsilon-decay schedule on a small panel below.
- Does NOT overwrite the trained model weights.

Run from the repo root:
    python scripts/make_training_curve_clean.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.trainer import train, TrainingConfig


FIG_DIR = "figures"


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)

    cfg = TrainingConfig(
        n_episodes=3000,           # short, just for visualisation
        Nt=4,
        snr_db_min=0.0,
        snr_db_max=30.0,
        kappa_min=0.1,
        kappa_max=0.9,
        batch_size=64,
        buffer_size=10_000,
        warmup=200,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_episodes=1800,
        target_sync_every=100,
        gamma=0.0,
        learning_rate=1e-3,
        log_every=300,
        seed=42,
    )

    print("[CLEAN TRAINING CURVE] Running short training run "
          "for visualisation only (model weights NOT saved).")
    _, history = train(cfg)

    episodes = np.arange(1, len(history.running_reward) + 1)
    running  = np.asarray(history.running_reward)
    epsilon  = np.asarray(history.epsilon)

    # Extra smoothing on top of the 100-ep running mean for a really
    # clean line — Savitzky-Golay-style moving average.
    win = 51
    if running.size >= win:
        kernel = np.ones(win) / win
        smooth = np.convolve(running, kernel, mode="same")
        # Kill the edge artifacts where the convolution is boundary-biased
        smooth[:win // 2] = running[:win // 2]
        smooth[-win // 2:] = running[-win // 2:]
    else:
        smooth = running

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10.0, 5.6), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]}
    )

    # ---- Top panel: smoothed running-average reward ----
    ax1.plot(episodes, smooth, color="#1f4e79",
             linewidth=3.0,
             label="Smoothed running-average reward (Rs · 10)")
    ax1.fill_between(episodes, smooth, color="#1f4e79", alpha=0.10)
    ax1.set_ylabel("Reward  (running average)", fontsize=14)
    ax1.set_title(
        "DQN training progress  —  Nt = 4, 3000 episodes",
        fontsize=15, fontweight="bold", pad=10
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="lower right", fontsize=12)
    ax1.tick_params(axis="both", labelsize=12)

    # Annotation: where epsilon hits its floor
    eps_floor_ep = int(cfg.epsilon_decay_episodes)
    if eps_floor_ep < len(episodes):
        ax1.axvline(eps_floor_ep, color="#7f7f7f",
                    linestyle="--", linewidth=1.3, alpha=0.7)
        ax1.text(eps_floor_ep + 30, ax1.get_ylim()[0] + 0.3,
                 "ε reaches 0.05\n(exploration → exploitation)",
                 fontsize=10, color="#7f7f7f", style="italic")

    # ---- Bottom panel: epsilon decay ----
    ax2.plot(episodes, epsilon, color="#c0504d",
             linewidth=2.2, label="ε  (exploration prob.)")
    ax2.set_xlabel("Training episode", fontsize=14)
    ax2.set_ylabel("ε", fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper right", fontsize=11)
    ax2.tick_params(axis="both", labelsize=12)

    fig.tight_layout()

    out = os.path.join(FIG_DIR, "13_training_curve_clean.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[SAVE] {out}")


if __name__ == "__main__":
    main()
