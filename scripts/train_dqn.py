"""
Top-level DQN training script.

Runs the full Phase 3 training loop, saves the trained model to
models/dqn_trained.keras, and produces:

    figures/03_dqn_training_curve.png   -- reward vs episode + epsilon decay

Usage:
    python train_dqn.py
"""



from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os

import numpy as np
import matplotlib.pyplot as plt

from core.trainer import train, TrainingConfig


MODEL_PATH = "models/dqn_trained.keras"
FIG_DIR = "figures"


def main() -> None:
    os.makedirs("models", exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    cfg = TrainingConfig(
        n_episodes=5000,
        Nt=4,
        snr_db_min=0.0,
        snr_db_max=30.0,
        kappa_min=0.2,
        kappa_max=0.8,
        batch_size=64,
        buffer_size=10_000,
        warmup=200,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_episodes=3000,
        target_sync_every=100,
        gamma=0.0,
        learning_rate=1e-3,
        log_every=250,
        seed=42,
    )

    bar = "=" * 72
    print(bar)
    print("  PHASE 3 -- DQN AGENT TRAINING")
    print(bar)

    agent, history = train(cfg)

    # ---- save model ----
    agent.save(MODEL_PATH)
    print(f"\n[SAVE] Model weights -> {MODEL_PATH}")

    # ---- plot training curve ----
    episodes = np.arange(1, len(history.running_reward) + 1)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.5, 6.8), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})

    ax1.plot(episodes, history.episode_reward,
             alpha=0.18, color="#1f4e79", label="per-episode Rs")
    ax1.plot(episodes, history.running_reward,
             color="#c0504d", linewidth=2.0, label="running avg (100 eps)")
    ax1.set_ylabel("Secrecy rate  Rs  (bits/s/Hz)")
    ax1.set_title(f"DQN training curve  --  "
                  f"Nt={cfg.Nt}, SNR in [{cfg.snr_db_min:.0f},"
                  f"{cfg.snr_db_max:.0f}] dB, "
                  f"kappa in [{cfg.kappa_min},{cfg.kappa_max}]")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="lower right")

    ax2.plot(episodes, history.epsilon,
             color="#7f7f7f", linewidth=1.8, label="epsilon")
    ax2.set_xlabel("Episode")
    ax2.set_ylabel("epsilon")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper right")

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "03_dqn_training_curve.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)

    # ---- final numbers ----
    final100 = float(np.mean(history.episode_reward[-100:]))
    first100 = float(np.mean(history.episode_reward[:100]))
    print(f"\n[STATS] First 100 episodes avg Rs: {first100:.3f} bits/s/Hz")
    print(f"[STATS] Last  100 episodes avg Rs: {final100:.3f} bits/s/Hz")
    print(f"[STATS] Improvement over training: +{final100 - first100:.3f}")
    print(f"\n[SAVE] Plot -> {out}")
    print("\n" + bar)
    print("  DONE.  Next: run demo_full.py for the 3-scheme comparison.")
    print(bar)


if __name__ == "__main__":
    main()
