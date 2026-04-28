"""
Top-level DQN training script (parametrised by antenna count Nt).

Runs the full Phase 3 training loop and saves:

    models/dqn_trained_nt{Nt}.keras
    figures/03_dqn_training_curve.png         (when Nt=4, the headline run)
    figures/03_dqn_training_curve_nt{Nt}.png  (otherwise)

Usage:
    python scripts/train_dqn.py                 # defaults to Nt=4
    python scripts/train_dqn.py --nt 2
    python scripts/train_dqn.py --nt 8 --episodes 5000

Hyperparameters are otherwise fixed across all Nt so the per-Nt models are
directly comparable: SNR in [0,30] dB, kappa in [0.2,0.8], 5000 episodes,
seed 42.
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse

import numpy as np
import matplotlib.pyplot as plt

from core.trainer import train, TrainingConfig


FIG_DIR = "figures"
MODEL_DIR = "models"


def model_path_for(Nt: int) -> str:
    """Canonical path for the trained DQN at a given antenna count."""
    return os.path.join(MODEL_DIR, f"dqn_trained_nt{Nt}.keras")


def _figure_path_for(Nt: int) -> str:
    if Nt == 4:
        return os.path.join(FIG_DIR, "03_dqn_training_curve.png")
    return os.path.join(FIG_DIR, f"03_dqn_training_curve_nt{Nt}.png")


def train_one(Nt: int, n_episodes: int = 5000, seed: int = 42) -> str:
    """Train one DQN at the given Nt and save the weights. Returns model path."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    cfg = TrainingConfig(
        n_episodes=n_episodes,
        Nt=Nt,
        snr_db_min=0.0,
        snr_db_max=30.0,
        kappa_min=0.2,
        kappa_max=0.8,
        batch_size=64,
        buffer_size=10_000,
        warmup=200,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay_episodes=int(n_episodes * 0.6),
        target_sync_every=100,
        gamma=0.0,
        learning_rate=1e-3,
        log_every=max(n_episodes // 20, 50),
        seed=seed,
    )

    bar = "=" * 72
    print(bar)
    print(f"  PHASE 3 -- DQN AGENT TRAINING  (Nt = {Nt})")
    print(bar)

    agent, history = train(cfg)

    model_path = model_path_for(Nt)
    agent.save(model_path)
    print(f"\n[SAVE] Model weights -> {model_path}")

    # ---- training curve ----
    episodes = np.arange(1, len(history.running_reward) + 1)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.5, 6.8), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(episodes, history.episode_reward,
             alpha=0.18, color="#1f4e79", label="per-episode Rs")
    ax1.plot(episodes, history.running_reward,
             color="#c0504d", linewidth=2.0, label="running avg (100 eps)")
    ax1.set_ylabel("Secrecy rate  Rs  (bits/s/Hz)")
    ax1.set_title(f"DQN training curve  --  Nt={cfg.Nt}, "
                  f"SNR in [{cfg.snr_db_min:.0f},{cfg.snr_db_max:.0f}] dB, "
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

    fig_out = _figure_path_for(Nt)
    fig.savefig(fig_out, dpi=120)
    plt.close(fig)

    final100 = float(np.mean(history.episode_reward[-100:]))
    first100 = float(np.mean(history.episode_reward[:100]))
    print(f"\n[STATS] First 100 episodes avg Rs: {first100:.3f} bits/s/Hz")
    print(f"[STATS] Last  100 episodes avg Rs: {final100:.3f} bits/s/Hz")
    print(f"[STATS] Improvement over training: +{final100 - first100:.3f}")
    print(f"\n[SAVE] Plot -> {fig_out}")
    print(bar)
    return model_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nt", type=int, default=4,
                        help="Number of transmit antennas (default 4)")
    parser.add_argument("--episodes", type=int, default=5000,
                        help="Training episodes (default 5000)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train_one(Nt=args.nt, n_episodes=args.episodes, seed=args.seed)


if __name__ == "__main__":
    main()
