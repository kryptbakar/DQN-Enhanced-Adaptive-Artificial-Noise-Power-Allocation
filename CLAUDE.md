# pls-dqn-miso — project context for Claude

## What this project is

DQN-enhanced adaptive artificial-noise (AN) power allocation for the
**MISO wiretap channel under imperfect CSI**. Course project, Track 2.

Three schemes are compared on the same Monte Carlo channel set:

| Scheme | What it does | Role |
|---|---|---|
| 1 — Fixed | `rho = 0.5` always (Goel & Negi 2008) | Naive baseline |
| 2 — Traditional | `scipy.optimize.minimize_scalar` on `Rs(rho)` | Perfect-CSI upper bound; FAILS under noisy CSI |
| 3 — DQN | Trained Q-network picks `rho` from the noisy state | The proposed contribution |

The split between the CSI a scheme is *allowed to see* (`hE_estimate`,
possibly noisy) and the channel that determines the *achieved reward*
(`hE_true`) is what makes the kappa story honest. This separation lives
inside `evaluate_scheme()` in `core/schemes.py` — do not bypass it.

## File map

### `core/`
| File | Role |
|---|---|
| `channel.py` | Rayleigh CN(0, I) channels, MRT beamformer `w = hB*/||hB||`, null-space projector `P_perp` |
| `csi.py` | Imperfect-CSI model: `ĥE = √κ·hE + √(1-κ)·e`, with `e ~ CN(0, I)` |
| `secrecy.py` | `compute_secrecy_rate(hB, hE, rho, snr_linear)` — AN-averaged closed form, deterministic per channel |
| `state.py` | `build_state(hB, hE_est, snr_db, last_rho, last_rs)` — 5-element state vector for the DQN |
| `replay_buffer.py` | Circular `(s, a, r, s', done)` buffer with random minibatch sampling |
| `dqn_agent.py` | Q-network (64-64-32-9), target net, ε-greedy, Huber-loss Bellman update |
| `trainer.py` | Training loop: random SNR + random κ per episode, one-step MDP (gamma=0) |
| `schemes.py` | `fixed_scheme`, `traditional_optimizer`, `make_dqn_scheme` factory, `evaluate_scheme` harness |
| `experiments.py` | Phase 4 sweeps: kappa, antenna count, secrecy outage probability |

### `scripts/`
| File | Role |
|---|---|
| `demo.py` | Phase 1+2 validation — null-space check, single-channel `Rs(ρ)` peak, Scheme 1 vs 2 at κ=1 |
| `train_dqn.py` | Phase 3 — trains DQN for 5000 episodes, saves `models/dqn_trained.keras` and figure 03 |
| `demo_full.py` | Headline 3-scheme comparison on unseen channels at κ=0.4, figures 04 + 05 |
| `run_experiments.py` | Phase 4 — runs all three experiments end-to-end, figures 06 + 07 + 08 |

### `models/`, `figures/`
- `models/dqn_trained.keras` is **tracked** (it's the headline result and small).
  Other model files are gitignored.
- `figures/*.png` regenerate from scripts; gitignored.

## Conventions

- **Python 3.10+** (uses `from __future__ import annotations`, PEP 604 `int | None`).
- **Channel shape**: `(Nt,)`, `complex128` (numpy default for complex). Never `(Nt, 1)`.
- **SNR is linear internally** (`snr_linear = P/sigma^2`). `snr_db` only at I/O / state
  encoding boundaries — convert with `10**(snr_db/10)`.
- **`rho` is in `(0, 1)`**, the fraction of total power on the *signal* (1 - rho on AN).
- **Action space**: discrete `{0.1, 0.2, ..., 0.9}` → `ACTION_RHOS` in `core.dqn_agent`.
- **State vector** (5 elements, all roughly in `[0, 1]`):
  `[||hB||²/Nt, ||ĥE||²/Nt, snr_db/30, last_rho, last_rs/10]`
- **Reward** = `REWARD_SCALE * compute_secrecy_rate(hB, hE_TRUE, rho, snr_linear)`,
  evaluated against the **true** Eve channel even though the agent only sees a noisy
  estimate. `REWARD_SCALE = 10.0`.
- **Gamma = 0** because each episode is a one-step decision (one channel → one ρ → done).
  The full bootstrap form is implemented anyway for future multi-step extensions.
- **Imports inside `core/`** use relative form (`from .channel import ...`).
- **Reproducibility**: every stochastic function takes an optional `rng:
  np.random.Generator`. Default seed is 42 in training, 2026 in evaluation.
- **Scripts** all start with the same `sys.path` injection so `python scripts/foo.py`
  works from the repo root without installing the package.

## Current status

- **Phase 1** (channel + CSI + secrecy primitives): done.
- **Phase 2** (Scheme 1 + Scheme 2 + simulator validation): done — figures 01, 02.
- **Phase 3** (DQN training + 3-scheme comparison): done — figures 03, 04, 05.
  Model in `models/dqn_trained.keras` was trained at **Nt=4** with κ ∈ [0.2, 0.8],
  SNR ∈ [0, 30] dB.
- **Phase 4** (experiments 2/4/5 — kappa, antenna count, outage): in progress.
- **Phase 6** (Streamlit simulator): not started.

## Key references

1. S. Goel & R. Negi, "Guaranteeing Secrecy Using Artificial Noise," *IEEE TWC*, 2008.
2. D. Wang et al., "A Survey of Optimization Approaches for Wireless PLS," *IEEE ComST*, 2019.
3. R. Lin et al., "Deep Reinforcement Learning for PLS...," *Sensors*, 2023.
4. V. Mnih et al., "Human-level control through deep reinforcement learning," *Nature*, 2015 — DQN foundational paper.
