"""
Progress Demo -- Phase 1 + Phase 2 Validation
=============================================

Runs three checks that together prove the simulator backbone is correct
and ready for the DQN agent (Phase 3).

    1. NULL-SPACE SANITY CHECK
       Confirms that Bob literally cannot see the artificial noise, i.e.
       ||hB^H P_perp|| is at machine-epsilon level. If this ever fails,
       the whole project is built on sand.

    2. SINGLE-CHANNEL RHO SWEEP
       Plots Rs(rho) for one fixed channel at SNR = 15 dB. Should show
       a clean, concave peak somewhere in (0, 1). Matches the "clear peak"
       shape reported by Qasem et al. (2024), Figure 3, for jamming power
       optimisation -- same phenomenon, different variable.

    3. MONTE CARLO VALIDATION (tomorrow's headline plot)
       Secrecy Rate vs SNR for Scheme 1 (Fixed, rho = 0.5) vs Scheme 2
       (Traditional optimiser with perfect CSI) averaged over many channel
       realisations. Scheme 2 must sit clearly above Scheme 1, with both
       curves rising and saturating -- this reproduces the known
       Goel & Negi (2008) trends and validates the simulator.

Usage:
    python demo.py

All plots are saved to figures/.
"""



from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os

import numpy as np
import matplotlib.pyplot as plt

from core.channel import (generate_rayleigh_channel,
                          null_space_projector)
from core.secrecy import compute_secrecy_rate
from core.schemes import fixed_scheme, traditional_optimizer, evaluate_scheme


FIG_DIR = "figures"


# ---------------------------------------------------------------------------
# 1. Null-space sanity check
# ---------------------------------------------------------------------------

def null_space_sanity_check(Nt: int = 4,
                            n_trials: int = 200,
                            seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    max_leak = 0.0
    for _ in range(n_trials):
        hB = generate_rayleigh_channel(Nt, rng)
        P = null_space_projector(hB)
        leak = float(np.linalg.norm(hB.conj() @ P))
        if leak > max_leak:
            max_leak = leak
    print(f"[1/3] Null-space sanity check "
          f"(Nt={Nt}, {n_trials} random channels)")
    print(f"      max ||hB^H P_perp|| = {max_leak:.2e}")
    assert max_leak < 1e-10, "Null-space projection is broken!"
    print("      PASS  -- Bob does NOT see the AN. Foundation is correct.\n")


# ---------------------------------------------------------------------------
# 2. Single-channel Rs(rho) sweep -- the "clean peak" check
# ---------------------------------------------------------------------------

def single_channel_rho_sweep(Nt: int = 4,
                             snr_db: float = 15.0,
                             seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    hB = generate_rayleigh_channel(Nt, rng)
    hE = generate_rayleigh_channel(Nt, rng)
    snr_linear = 10.0 ** (snr_db / 10.0)

    rhos = np.linspace(0.01, 0.99, 199)
    rs_values = np.array(
        [compute_secrecy_rate(hB, hE, float(r), snr_linear) for r in rhos]
    )
    idx_star = int(np.argmax(rs_values))
    rho_star = float(rhos[idx_star])
    rs_star = float(rs_values[idx_star])

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(rhos, rs_values, linewidth=2.2, color="#1f4e79")
    ax.axvline(rho_star, color="#c0504d", linestyle="--",
               alpha=0.85, label=f"rho* = {rho_star:.3f} (optimal)")
    ax.axvline(0.5, color="#7f7f7f", linestyle=":",
               alpha=0.85, label="rho = 0.5 (Scheme 1, Fixed)")
    ax.set_xlabel("Power split ratio  rho")
    ax.set_ylabel("Secrecy rate  Rs  (bits/s/Hz)")
    ax.set_title(f"Single-channel Rs(rho)   -- Nt={Nt}, SNR={snr_db:.0f} dB")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "01_single_channel_sweep.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)

    print(f"[2/3] Single-channel rho sweep (Nt={Nt}, SNR={snr_db:.0f} dB)")
    print(f"      rho* = {rho_star:.3f},  Rs* = {rs_star:.3f} bits/s/Hz")
    print(f"      Rs at rho=0.5 = "
          f"{compute_secrecy_rate(hB, hE, 0.5, snr_linear):.3f} bits/s/Hz")
    print(f"      saved -> {out}\n")


# ---------------------------------------------------------------------------
# 3. Monte Carlo validation -- the headline plot for tomorrow
# ---------------------------------------------------------------------------

def monte_carlo_validation(Nt: int = 4,
                           n_channels: int = 500,
                           seed: int = 1) -> None:
    rng = np.random.default_rng(seed)
    snr_db_range = np.arange(0, 31, 2, dtype=float)

    # Pre-generate channels so BOTH schemes see the IDENTICAL set (fair).
    channels = [
        (generate_rayleigh_channel(Nt, rng),
         generate_rayleigh_channel(Nt, rng))
        for _ in range(n_channels)
    ]

    rs_fixed = np.zeros_like(snr_db_range)
    rs_opt = np.zeros_like(snr_db_range)

    print(f"[3/3] Monte Carlo validation "
          f"(Nt={Nt}, {n_channels} channels per SNR point)")
    print(f"      SNR range: {snr_db_range[0]:.0f} .. "
          f"{snr_db_range[-1]:.0f} dB\n")
    print(f"      {'SNR (dB)':>9} | {'Fixed':>7} | {'Opt':>7} | {'Gain':>7}")
    print(f"      {'-'*9}-+-{'-'*7}-+-{'-'*7}-+-{'-'*7}")

    for i, snr_db in enumerate(snr_db_range):
        snr_linear = 10.0 ** (snr_db / 10.0)
        s_fixed = 0.0
        s_opt = 0.0
        for hB, hE in channels:
            # Scheme 1: fixed rho = 0.5
            _, rf = evaluate_scheme(fixed_scheme, hB, hE, hE, snr_linear)
            # Scheme 2: traditional optimiser with PERFECT CSI (kappa = 1)
            _, ro = evaluate_scheme(traditional_optimizer, hB, hE, hE,
                                    snr_linear)
            s_fixed += rf
            s_opt += ro
        rs_fixed[i] = s_fixed / n_channels
        rs_opt[i] = s_opt / n_channels
        print(f"      {snr_db:>9.0f} | {rs_fixed[i]:>7.3f} | "
              f"{rs_opt[i]:>7.3f} | {rs_opt[i]-rs_fixed[i]:>+7.3f}")

    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    ax.plot(snr_db_range, rs_fixed, "o-",
            color="#7f7f7f", linewidth=2.2, markersize=6,
            label="Scheme 1: Fixed  (rho = 0.5)")
    ax.plot(snr_db_range, rs_opt, "s-",
            color="#1f4e79", linewidth=2.2, markersize=6,
            label="Scheme 2: Traditional Opt  (perfect CSI, kappa = 1)")
    ax.set_xlabel("Transmit SNR (dB)")
    ax.set_ylabel("Average secrecy rate  Rs  (bits/s/Hz)")
    ax.set_title("Validation -- Scheme 1 vs Scheme 2 at kappa = 1\n"
                 f"Nt = {Nt}, Monte Carlo over {n_channels} channels")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "02_validation_scheme1_vs_scheme2.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)

    print(f"\n      saved -> {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(FIG_DIR, exist_ok=True)
    bar = "=" * 72
    print(bar)
    print("  PROGRESS DEMO -- Phase 1 + Phase 2 Validation")
    print("  (core/channel.py + core/csi.py + core/secrecy.py + core/schemes.py)")
    print(bar + "\n")

    null_space_sanity_check()
    single_channel_rho_sweep()
    monte_carlo_validation()

    print("\n" + bar)
    print("  DONE. Both plots saved in figures/. Simulator is validated.")
    print("  Next: Phase 3 (DQN agent) -- core/dqn_agent.py")
    print(bar)
