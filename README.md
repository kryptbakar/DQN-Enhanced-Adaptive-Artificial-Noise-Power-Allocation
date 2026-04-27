# DQN-Enhanced Adaptive Artificial Noise Power Allocation

MISO wiretap channel, imperfect CSI. Track 2 course project.

**Team:** M. Ismail (2023453), Abubakar Butt (2023352), Usman Ali (2023581).

---

## Status

Phase 1 + 2 + 3 complete. All three schemes implemented, trained, and
evaluated on unseen channels. Five figures produced.

## What's in `core/`

| File | Role | Phase |
|---|---|---|
| `channel.py` | Rayleigh channels, MRT beamformer, null-space projector | 1 |
| `csi.py` | Imperfect-CSI model `ĥE = √κ·hE + √(1-κ)·e` | 1 |
| `secrecy.py` | Secrecy-rate function `Rs(ρ)` (AN-averaged closed form) | 1 |
| `schemes.py` | Scheme 1 (Fixed), Scheme 2 (scipy opt), `make_dqn_scheme` wrapper | 2 + 3 |
| `replay_buffer.py` | Circular experience replay memory | 3 |
| `dqn_agent.py` | Q-network + target network + ε-greedy + Bellman update | 3 |
| `trainer.py` | Training loop with random SNR + random κ sampling | 3 |

## Quick start

```bash
pip install -r requirements.txt
python demo.py         # Phase 1+2 validation: null-space check + Scheme 1 vs 2
python train_dqn.py    # Phase 3: trains DQN for 5000 episodes (~40 s on CPU)
python demo_full.py    # Full 3-scheme comparison on unseen channels
```

## Figures produced

| File | What it shows |
|---|---|
| `figures/01_single_channel_sweep.png` | Rs(ρ) for one channel — clean peak |
| `figures/02_validation_scheme1_vs_scheme2.png` | Scheme 1 vs Scheme 2 at κ=1 — simulator validation |
| `figures/03_dqn_training_curve.png` | Reward vs episode + ε decay |
| `figures/04_three_scheme_comparison.png` | **Headline**: all 3 schemes, absolute Rs + gain-over-Fixed |
| `figures/05_dqn_action_distribution.png` | What ρ the DQN actually picks across SNR bands |

## Key result

On 400 unseen channels at κ=0.4 (imperfect CSI), Nt=4, across SNR 0–30 dB:

- **Scheme 2 (Traditional) with noisy CSI**: underperforms Fixed by up to
  −0.06 bits/s/Hz at mid-high SNR. **Trusting bad CSI can actively hurt you.**
- **Scheme 3 (DQN) with the same noisy CSI**: stays ≥ 0 over Fixed everywhere
  and captures ~70% of the perfect-CSI gain at low SNR.
- **Learned policy**: DQN shifts toward higher ρ at low SNR (more signal power
  when SNR is scarce) and toward ρ=0.5 at high SNR. This is the right
  qualitative behavior — learned from data with no analytical optimization.

## Next steps

- **Phase 4** — `core/experiments.py`: Experiments 2–5 from the proposal
  (κ sweep, antenna-count effect, secrecy outage probability, optimal-ρ
  comparison).
- **Phase 6** — `app/` Streamlit simulator with 2.5D Alice/Bob/Eve visualization.

## Key references

1. S. Goel & R. Negi, "Guaranteeing Secrecy Using Artificial Noise," IEEE TWC, 2008
2. D. Wang et al., "A Survey of Optimization Approaches for Wireless PLS," IEEE ComST, 2019
3. R. Lin et al., "Deep Reinforcement Learning for PLS...," Sensors, 2023
4. V. Mnih et al., "Human-level control through deep reinforcement learning," Nature, 2015 — DQN foundational paper
5. A. A. Qasem et al., "Physical-Layer Security Enhancement in WSNs through AN Optimization," Wiley S&P, 2024
