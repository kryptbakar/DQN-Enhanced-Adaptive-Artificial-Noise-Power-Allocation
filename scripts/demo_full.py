"""
Full-system demonstration: 3-scheme comparison with a trained DQN.

Loads models/dqn_trained.keras and produces two headline figures:

    figures/04_three_scheme_comparison.png
        Top panel:    absolute Rs vs SNR for Fixed / Traditional(kappa=0.4) /
                      Traditional(kappa=1.0, upper bound) / DQN(kappa=0.4)
        Bottom panel: GAIN over Fixed (Rs_scheme - Rs_Fixed). This is where
                      the story is visible -- the absolute-Rs curves are
                      dominated by SNR and look superimposed.

    figures/05_dqn_action_distribution.png
        Histogram of the rho values the DQN actually picks, split by SNR
        bucket. Shows the learned policy is non-trivial.

Usage:
    python demo_full.py
"""



from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt

from core.channel import generate_rayleigh_channel
from core.csi import imperfect_csi
from core.secrecy import compute_secrecy_rate
from core.schemes import (fixed_scheme, traditional_optimizer,
                          evaluate_scheme, make_dqn_scheme)
from core.dqn_agent import DQNAgent, ACTION_RHOS


MODEL_PATH = "models/dqn_trained.keras"
FIG_DIR = "figures"
KAPPA_EVAL = 0.4


def run_comparison(Nt: int = 4,
                   n_channels: int = 400,
                   seed: int = 2026) -> None:
    if not os.path.isfile(MODEL_PATH):
        raise FileNotFoundError(
            f"{MODEL_PATH} not found. Run `python train_dqn.py` first.")

    print(f"[LOAD] {MODEL_PATH}")
    agent = DQNAgent()
    agent.load(MODEL_PATH)
    dqn_scheme = make_dqn_scheme(agent)

    rng = np.random.default_rng(seed)
    channels = [
        (generate_rayleigh_channel(Nt, rng),
         generate_rayleigh_channel(Nt, rng))
        for _ in range(n_channels)
    ]

    snr_db_range = np.arange(0, 31, 3, dtype=float)

    rs_fixed   = np.zeros_like(snr_db_range)
    rs_opt_imp = np.zeros_like(snr_db_range)
    rs_opt_per = np.zeros_like(snr_db_range)
    rs_dqn     = np.zeros_like(snr_db_range)

    dqn_actions_per_snr: dict[float, list[float]] = {
        float(snr): [] for snr in snr_db_range
    }

    print(f"[EVAL] Sweeping SNR over {len(snr_db_range)} points, "
          f"{n_channels} channels each  (kappa_eval={KAPPA_EVAL}, Nt={Nt})\n")
    hdr = (f"  {'SNR':>4} | {'Fixed':>6} | {'Opt k=0.4':>9} | "
           f"{'Opt k=1.0':>9} | {'DQN k=0.4':>9} | {'DQN-Fixed':>9}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for i, snr_db in enumerate(snr_db_range):
        snr_lin = 10.0 ** (snr_db / 10.0)
        s_fix = s_oi = s_op = s_dq = 0.0

        dqn_scheme.reset()
        for hB, hE in channels:
            hE_noisy = imperfect_csi(hE, KAPPA_EVAL, rng)

            _, rf = evaluate_scheme(fixed_scheme,
                                    hB, hE, hE_noisy, snr_lin)
            _, ro_i = evaluate_scheme(traditional_optimizer,
                                      hB, hE, hE_noisy, snr_lin)
            _, ro_p = evaluate_scheme(traditional_optimizer,
                                      hB, hE, hE, snr_lin)
            rho_dqn, rd = evaluate_scheme(dqn_scheme,
                                          hB, hE, hE_noisy, snr_lin)

            s_fix += rf
            s_oi  += ro_i
            s_op  += ro_p
            s_dq  += rd
            dqn_actions_per_snr[float(snr_db)].append(rho_dqn)

        rs_fixed[i]   = s_fix / n_channels
        rs_opt_imp[i] = s_oi  / n_channels
        rs_opt_per[i] = s_op  / n_channels
        rs_dqn[i]     = s_dq  / n_channels

        print(f"  {snr_db:>4.0f} | {rs_fixed[i]:>6.3f} | "
              f"{rs_opt_imp[i]:>9.3f} | {rs_opt_per[i]:>9.3f} | "
              f"{rs_dqn[i]:>9.3f} | "
              f"{rs_dqn[i]-rs_fixed[i]:>+9.3f}")

    # -----------------------------------------------------------------
    # Figure 04 -- two-panel comparison
    # -----------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.0, 7.4), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})

    ax1.plot(snr_db_range, rs_opt_per, "^-", color="#1f4e79",
             linewidth=2.2, markersize=7,
             label="Scheme 2: Traditional (perfect CSI, k=1.0)  --  upper bound")
    ax1.plot(snr_db_range, rs_dqn, "D-", color="#2ca02c",
             linewidth=2.3, markersize=7,
             label=f"Scheme 3: DQN (imperfect CSI, k={KAPPA_EVAL})  --  PROPOSED")
    ax1.plot(snr_db_range, rs_fixed, "o-", color="#7f7f7f",
             linewidth=1.8, markersize=6,
             label="Scheme 1: Fixed (rho=0.5)")
    ax1.plot(snr_db_range, rs_opt_imp, "s--", color="#c0504d",
             linewidth=1.8, markersize=6,
             label=f"Scheme 2: Traditional (imperfect CSI, k={KAPPA_EVAL})")
    ax1.set_ylabel("Average Rs  (bits/s/Hz)")
    ax1.set_title(f"Three-scheme comparison at kappa = {KAPPA_EVAL} "
                  f"(and kappa = 1 reference)\n"
                  f"Nt = {Nt},  test set = {n_channels} unseen channels")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left", fontsize=9)

    ax2.axhline(0, color="black", linewidth=0.7, alpha=0.6)
    ax2.plot(snr_db_range, rs_opt_per - rs_fixed, "^-", color="#1f4e79",
             linewidth=2.0, markersize=6,
             label="Opt (perfect CSI)")
    ax2.plot(snr_db_range, rs_dqn - rs_fixed, "D-", color="#2ca02c",
             linewidth=2.2, markersize=6,
             label=f"DQN (k={KAPPA_EVAL})")
    ax2.plot(snr_db_range, rs_opt_imp - rs_fixed, "s--", color="#c0504d",
             linewidth=1.6, markersize=5,
             label=f"Opt (k={KAPPA_EVAL})")
    ax2.set_xlabel("Transmit SNR (dB)")
    ax2.set_ylabel("Gain over Fixed\n(bits/s/Hz)")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.text(0.02, 0.95,
             "DQN stays at/above 0 everywhere.  "
             "Opt-imperfect dips BELOW 0: noisy CSI can hurt you "
             "worse than doing nothing.",
             transform=ax2.transAxes, ha="left", va="top",
             fontsize=8.5, style="italic", alpha=0.75,
             wrap=True)

    fig.tight_layout()
    out1 = os.path.join(FIG_DIR, "04_three_scheme_comparison.png")
    fig.savefig(out1, dpi=120)
    plt.close(fig)
    print(f"\n[SAVE] {out1}")

    # -----------------------------------------------------------------
    # Figure 05 -- DQN action distribution by SNR band
    # -----------------------------------------------------------------
    buckets = {
        "Low SNR (0-9 dB)":   [s for s in snr_db_range if s <= 9],
        "Mid SNR (12-21 dB)": [s for s in snr_db_range if 12 <= s <= 21],
        "High SNR (24-30 dB)": [s for s in snr_db_range if s >= 24],
    }
    colors = {"Low SNR (0-9 dB)": "#c0504d",
              "Mid SNR (12-21 dB)": "#2ca02c",
              "High SNR (24-30 dB)": "#1f4e79"}

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), sharey=True)
    for ax, (label, snrs_in_band) in zip(axes, buckets.items()):
        rhos_in_band = []
        for s in snrs_in_band:
            rhos_in_band.extend(dqn_actions_per_snr[float(s)])
        cnt = Counter(np.round(rhos_in_band, 2))
        xs = ACTION_RHOS
        total = max(len(rhos_in_band), 1)
        ys = [cnt.get(float(x), 0) / total for x in xs]
        ax.bar(xs, ys, width=0.08, color=colors[label], alpha=0.85,
               edgecolor="black", linewidth=0.5)
        ax.axvline(0.5, color="black", linestyle=":", alpha=0.4,
                   label="rho = 0.5 (Fixed)")
        ax.set_xlabel("rho chosen by DQN")
        ax.set_title(label)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:.1f}" for x in xs], fontsize=8)
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)

    axes[0].set_ylabel("Fraction of channels")
    fig.suptitle("What rho does the DQN pick?  "
                 "(learned policy across SNR regimes)", fontsize=11)
    fig.tight_layout()
    out2 = os.path.join(FIG_DIR, "05_dqn_action_distribution.png")
    fig.savefig(out2, dpi=120)
    plt.close(fig)
    print(f"[SAVE] {out2}")


if __name__ == "__main__":
    os.makedirs(FIG_DIR, exist_ok=True)
    bar = "=" * 72
    print(bar)
    print("  FULL DEMO -- 3-Scheme Comparison with Trained DQN")
    print(bar + "\n")
    run_comparison()
    print("\n" + bar)
    print("  DONE.")
    print(bar)
