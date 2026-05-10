# DQN-Enhanced Adaptive Artificial Noise Power Allocation

MISO wiretap channel under imperfect CSI. CY315 Wireless and Mobile
Security course project, Spring 2026. Track 2 (Implementation &
Optimisation).

**Team:** M. Ismail (2023453), Abubakar Butt (2023352), Usman Ali (2023581).

---

## Status

All implementation phases complete. The DQN policy is trained at three
antenna counts and evaluated against two non-learning baselines on
unseen channels. Eight result figures plus a runtime micro-benchmark
back the report.

| Phase | Scope | Status |
|---|---|---|
| 1 | Channel + CSI + secrecy primitives | done |
| 2 | Scheme 1 (Fixed) + Scheme 2 (scipy opt) + simulator validation | done |
| 3 | DQN agent + training loop + 3-scheme comparison at Nt={2, 4, 8} | done |
| 4 | Follow-up sweeps (kappa, antenna count, outage, optimal-rho, Eve-strength) | done |
| 5 | Report (IEEE LaTeX) | drafting |
| 6 | Streamlit GUI + standalone HTML demo | done |

## What's in `core/`

| File | Role |
|---|---|
| `channel.py` | Rayleigh channels, MRT beamformer, null-space projector |
| `csi.py` | Imperfect-CSI model `ĥE = √κ·hE + √(1-κ)·e` |
| `secrecy.py` | Secrecy-rate function `Rs(ρ)` (AN-averaged closed form) |
| `state.py` | 5-element state vector for the DQN |
| `replay_buffer.py` | Circular experience replay memory |
| `dqn_agent.py` | Q-network (5-64-64-32-9), target net, ε-greedy, Huber Bellman |
| `trainer.py` | Training loop with random SNR + random κ sampling |
| `schemes.py` | Scheme 1 (Fixed), Scheme 2 (scipy optimiser), DQN-scheme factory, eval harness |
| `experiments.py` | Phase 4 sweeps + policy heatmap + Eve-strength + optimal-rho oracle |

## What's in `scripts/`

| File | Role |
|---|---|
| `demo.py` | Phase 1+2 — null-space sanity + Rs(ρ) peak + Scheme 1 vs 2 at κ=1 |
| `train_dqn.py` | Phase 3 — train one DQN at Nt ∈ {2, 4, 8} |
| `train_all_nt.py` | Trains all three Nt models in sequence |
| `demo_full.py` | Phase 3 evaluation — figures 04 + 05 |
| `run_experiments.py` | Phase 4 — figures 06 + 07 + 08 |
| `make_policy_heatmap.py` | Figure 09 — learned DQN policy as 2D heatmap |
| `make_eve_strength.py` | Figure 10 — Qasem-inspired Eve-strength sweep |
| `make_optimal_rho.py` | Figure 11 — per-channel oracle ρ* comparison |
| `bench_runtimes.py` | Per-call runtime comparison (for the report) |

## Quick start

```bash
pip install -r requirements.txt
python -m pytest tests/                          # 38 tests, ~7 sec
python scripts/demo.py                           # Phase 1+2 sanity figures
python scripts/train_all_nt.py                   # Phase 3 — trains DQN at Nt ∈ {2, 4, 8}
python scripts/demo_full.py                      # 3-scheme headline comparison
python scripts/run_experiments.py                # κ-sweep, Nt panels, outage
python scripts/make_policy_heatmap.py            # learned policy heatmap
python scripts/make_eve_strength.py              # Eve-strength sweep
python scripts/make_optimal_rho.py               # oracle ρ* comparison
python scripts/bench_runtimes.py                 # per-call runtime numbers

streamlit run app/streamlit_app.py               # interactive GUI (5 tabs)
# app/demo.html — open in any browser, no install needed
```

## Figures produced

| File | What it shows |
|---|---|
| `figures/01_single_channel_sweep.png` | Rs(ρ) for one channel — clean concave peak |
| `figures/02_validation_scheme1_vs_scheme2.png` | Scheme 1 vs Scheme 2 at κ=1 — simulator validation |
| `figures/03_dqn_training_curve{,_nt2,_nt8}.png` | Reward and ε vs episode (one per Nt) |
| `figures/04_three_scheme_comparison.png` | **Headline** — all 3 schemes, absolute Rs + gain over Fixed |
| `figures/05_dqn_action_distribution.png` | Which ρ DQN picks across SNR bands |
| `figures/06_kappa_sweep.png` | Rs vs κ — the "trusting noisy CSI hurts" story |
| `figures/07_antenna_count.png` | Rs vs SNR for Nt ∈ {2, 4, 8} |
| `figures/08_secrecy_outage.png` | Empirical SOP(R₀) for each scheme |
| `figures/09_policy_heatmap.png` | Learned DQN policy ρ(SNR, κ) + marginal SNR plot |
| `figures/10_eve_strength.png` | Rs vs Eve-channel-gain advantage β (Qasem-inspired) |
| `figures/11_optimal_rho_comparison.png` | Per-channel oracle ρ* — how close each scheme lands |

## Key result

On 400 unseen channels at κ=0.4, Nt=4, across SNR 0–30 dB:

- **Scheme 2 (Traditional) with noisy CSI** underperforms Fixed by up to
  ~0.06 bits/s/Hz at mid-high SNR. **Trusting bad CSI can hurt you more
  than ignoring it.**
- **Scheme 3 (DQN) with the same noisy CSI** stays at or above Fixed
  everywhere and captures roughly 70 % of the perfect-CSI gain at low
  SNR.
- **Learned policy** (figure 09): DQN pushes ρ high (≈0.79) at low SNR
  and converges to ρ ≈ 0.5 at high SNR, regardless of κ — a robust,
  CSI-quality-agnostic strategy.

## Key references

1. S. Goel & R. Negi, "Guaranteeing Secrecy Using Artificial Noise," IEEE TWC, 2008
2. D. Wang et al., "A Survey of Optimization Approaches for Wireless PLS," IEEE ComST, 2019
3. R. Lin et al., "Deep Reinforcement Learning for PLS...," Sensors, 2023
4. V. Mnih et al., "Human-level control through deep reinforcement learning," Nature, 2015 — DQN foundational paper
5. A. A. Qasem, M. Shokair, F. E. Abd El-Samie, "Physical-Layer Security Enhancement in WSNs through AN Optimization," Security and Privacy (Wiley), 2024 — inspiration paper
