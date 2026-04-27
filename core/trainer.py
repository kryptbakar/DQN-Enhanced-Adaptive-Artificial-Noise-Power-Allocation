"""
Training loop for the DQN agent on the MISO wiretap AN-allocation task.

Each training episode is one independent channel realisation. The agent:

    1. Observes a 5-element state built from Bob's perfect channel info,
       Eve's NOISY channel estimate (from the imperfect-CSI model), the
       current transmit SNR, and the last-episode action/reward pair.
    2. Picks a discrete rho from {0.1, ..., 0.9} via epsilon-greedy.
    3. Receives the TRUE secrecy rate (scaled by REWARD_SCALE) as reward.
    4. Stores the transition, samples a batch, performs one Bellman update.

We randomise SNR (0..30 dB) and CSI quality (kappa in [0.2, 0.8]) per
episode so the policy generalises across all test-time conditions --
important for Experiment 2 (kappa sweep) and Experiment 1 (SNR sweep).

State vector layout (all approximately in [0, 1] range):

    state[0] = ||hB||^2 / Nt      -- Bob's channel gain, per-antenna
    state[1] = ||hE_est||^2 / Nt  -- Eve's NOISY gain estimate
    state[2] = snr_db / 30        -- transmit SNR normalised
    state[3] = last_rho           -- previous action
    state[4] = last_rs / 10       -- previous reward, normalised
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from .channel import generate_rayleigh_channel
from .csi import imperfect_csi
from .secrecy import compute_secrecy_rate
from .dqn_agent import DQNAgent, ACTION_RHOS, N_ACTIONS, STATE_DIM
from .replay_buffer import ReplayBuffer
from .state import build_state


REWARD_SCALE: float = 10.0     # multiply raw Rs by this before using as reward


# ---------------------------------------------------------------------------
# Training config
# ---------------------------------------------------------------------------

@dataclass
class TrainingConfig:
    n_episodes: int = 5000
    Nt: int = 4
    snr_db_min: float = 0.0
    snr_db_max: float = 30.0
    kappa_min: float = 0.2
    kappa_max: float = 0.8

    batch_size: int = 64
    buffer_size: int = 10_000
    warmup: int = 200              # episodes before any learning starts

    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_episodes: int = 3000  # linear decay length

    target_sync_every: int = 100   # sync target network every N steps
    gamma: float = 0.0             # one-step MDP => bootstrap is zero

    learning_rate: float = 1e-3
    log_every: int = 100
    seed: int = 42


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

@dataclass
class TrainingHistory:
    episode_reward: List[float] = field(default_factory=list)   # raw Rs
    running_reward: List[float] = field(default_factory=list)   # 100-ep avg
    epsilon: List[float] = field(default_factory=list)
    loss: List[float] = field(default_factory=list)


def _epsilon_at(ep: int, cfg: TrainingConfig) -> float:
    """Linear decay of epsilon from start -> end over `epsilon_decay_episodes`."""
    frac = min(ep / cfg.epsilon_decay_episodes, 1.0)
    return cfg.epsilon_start + (cfg.epsilon_end - cfg.epsilon_start) * frac


def train(cfg: TrainingConfig | None = None
          ) -> Tuple[DQNAgent, TrainingHistory]:
    """Run the full DQN training loop and return (agent, history)."""
    if cfg is None:
        cfg = TrainingConfig()

    rng = np.random.default_rng(cfg.seed)
    agent = DQNAgent(gamma=cfg.gamma,
                     learning_rate=cfg.learning_rate,
                     seed=cfg.seed)
    buffer = ReplayBuffer(capacity=cfg.buffer_size, seed=cfg.seed + 1)
    history = TrainingHistory()

    # Previous-step bookkeeping (forms part of the state).
    last_rho = 0.5
    last_rs  = 0.0

    print(f"[TRAIN] Starting {cfg.n_episodes} episodes "
          f"(Nt={cfg.Nt}, SNR in [{cfg.snr_db_min:.0f},{cfg.snr_db_max:.0f}] dB, "
          f"kappa in [{cfg.kappa_min},{cfg.kappa_max}])")
    print(f"        Action space: {list(ACTION_RHOS)}")
    print()

    recent_rewards: List[float] = []

    for ep in range(cfg.n_episodes):
        # ---- sample an environment instance for this episode ----
        hB = generate_rayleigh_channel(cfg.Nt, rng)
        hE = generate_rayleigh_channel(cfg.Nt, rng)
        snr_db = rng.uniform(cfg.snr_db_min, cfg.snr_db_max)
        kappa  = rng.uniform(cfg.kappa_min, cfg.kappa_max)
        snr_lin = 10.0 ** (snr_db / 10.0)
        hE_est = imperfect_csi(hE, kappa, rng)

        state = build_state(hB, hE_est, snr_db, last_rho, last_rs)

        # ---- act ----
        eps = _epsilon_at(ep, cfg)
        action = agent.act(state, eps)
        rho    = float(ACTION_RHOS[action])

        # ---- reward = true achieved secrecy rate ----
        rs_true = compute_secrecy_rate(hB, hE, rho, snr_lin)
        reward  = rs_true * REWARD_SCALE

        # ---- store transition (terminal after one step) ----
        # We reuse `state` as next_state since the episode ends here and
        # (1 - done) * bootstrap kills that term anyway. Done=True for
        # correctness and for future multi-step compatibility.
        buffer.push(state, action, reward, state, done=True)

        # ---- learn ----
        loss_val = np.nan
        if ep >= cfg.warmup and buffer.is_ready(cfg.batch_size):
            loss_val = agent.learn(buffer.sample(cfg.batch_size))

        # ---- target sync ----
        if (ep + 1) % cfg.target_sync_every == 0:
            agent.sync_target()

        # ---- bookkeeping ----
        last_rho = rho
        last_rs  = rs_true
        recent_rewards.append(rs_true)
        if len(recent_rewards) > 100:
            recent_rewards.pop(0)

        history.episode_reward.append(rs_true)
        history.running_reward.append(float(np.mean(recent_rewards)))
        history.epsilon.append(eps)
        history.loss.append(loss_val)

        if (ep + 1) % cfg.log_every == 0:
            if np.isnan(loss_val):
                loss_str = "loss=--(warmup)"
            else:
                loss_str = f"loss={loss_val:.4f}"
            print(f"  ep {ep+1:>5d}/{cfg.n_episodes}  "
                  f"eps={eps:.3f}  "
                  f"Rs_run100={history.running_reward[-1]:.3f}  "
                  f"{loss_str}")

    print("\n[TRAIN] Done.")
    return agent, history
