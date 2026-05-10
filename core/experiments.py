"""
Phase 4 experiments — sweeps that go beyond the headline 3-scheme plot.

Each experiment_*() function:
  - takes a small set of keyword args (with sensible defaults),
  - loads the trained DQN once,
  - sweeps along the relevant axis,
  - writes a single PNG into fig_dir,
  - returns a dict of numpy arrays so the caller (or a notebook) can
    re-plot or recompute statistics without re-running the simulation.

All evaluations go through evaluate_scheme() in core/schemes.py so that
the CSI a scheme is *allowed to see* (hE_estimate) is kept distinct from
the channel that determines the *achieved* secrecy rate (hE_true).

Experiments
-----------
experiment_2_kappa_sweep
    Sweep CSI quality kappa from 0.0 (pure noise) to 1.0 (perfect) at a
    fixed SNR. Story: Traditional collapses at low kappa; DQN stays
    robust because it was trained under random kappa.

experiment_4_antenna_count
    Compare three antenna counts Nt in {2, 4, 8}, each with its own SNR
    sweep at kappa=0.4. The saved DQN was trained at Nt=4 ONLY, so we
    show DQN only on the Nt=4 panel and Fixed/Traditional on all three.

experiment_5_secrecy_outage
    Sweep a target secrecy rate R0 and report the secrecy outage
    probability SOP(R0) = P(Rs < R0) for each scheme.

policy_heatmap
    Render the trained DQN's learned policy as a 2D map over (SNR, kappa).
    For each grid cell we sample many channels, ask the agent for its action,
    and average the chosen rho. Story: shows what the DQN actually learned
    -- it pushes rho high when both transmit power and CSI quality are scarce.

eve_strength_sweep
    Sweep Eve's channel-gain advantage beta = E[||hE||^2] / E[||hB||^2]
    and report each scheme's secrecy rate. Inspired by Qasem 2024 Figure 4
    (Eve-position effect): larger beta corresponds to Eve being closer to
    Alice in a geometric model. Story: null-space AN is intrinsically
    robust to Eve's gain because signal and AN scale together at Eve.

experiment_3_optimal_rho
    Per-channel oracle comparison: for each channel realisation, brute-force
    the true rho* against the true hE, then measure how far each scheme's
    chosen rho lands from rho* and how much Rs is left on the table. Story:
    DQN chooses rho close to the oracle without ever seeing the true hE.
"""

from __future__ import annotations

import os
from typing import Dict

import numpy as np
import matplotlib.pyplot as plt

from .channel import generate_rayleigh_channel
from .csi import imperfect_csi
from .secrecy import compute_secrecy_rate
from .schemes import (fixed_scheme, traditional_optimizer,
                      evaluate_scheme, make_dqn_scheme)
from .dqn_agent import DQNAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def default_model_path(Nt: int) -> str:
    """
    Canonical on-disk path for the trained DQN at antenna count Nt.

    Mirrors scripts/train_dqn.py::model_path_for(). Kept here too so the
    Streamlit app and other consumers don't need to import a script module.
    """
    return f"models/dqn_trained_nt{int(Nt)}.keras"


def _load_dqn(model_path: str):
    """Load a trained DQN from disk and return (agent, scheme)."""
    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"{model_path} not found. "
            f"Run `python scripts/train_dqn.py --nt <Nt>` first."
        )
    agent = DQNAgent()
    agent.load(model_path)
    return agent, make_dqn_scheme(agent)


def _sample_channels(Nt: int, n: int, rng: np.random.Generator):
    return [(generate_rayleigh_channel(Nt, rng),
             generate_rayleigh_channel(Nt, rng)) for _ in range(n)]


# ---------------------------------------------------------------------------
# Experiment 2 -- kappa sweep at fixed SNR
# ---------------------------------------------------------------------------

def experiment_2_kappa_sweep(n_channels: int = 400,
                             snr_db: float = 15.0,
                             model_path: str | None = None,
                             fig_dir: str = "figures",
                             Nt: int = 4,
                             seed: int = 2026) -> Dict[str, np.ndarray]:
    """
    Sweep kappa from 0.0 to 1.0 in 11 steps. Compare Fixed / Traditional / DQN.

    Returns a dict with keys: 'kappa', 'rs_fixed', 'rs_traditional', 'rs_dqn'.
    """
    os.makedirs(fig_dir, exist_ok=True)
    if model_path is None:
        model_path = default_model_path(Nt)
    _, dqn_scheme = _load_dqn(model_path)

    rng = np.random.default_rng(seed)
    channels = _sample_channels(Nt, n_channels, rng)
    snr_lin = 10.0 ** (snr_db / 10.0)

    kappas = np.linspace(0.0, 1.0, 11)
    rs_fixed = np.zeros_like(kappas)
    rs_trad  = np.zeros_like(kappas)
    rs_dqn   = np.zeros_like(kappas)

    print(f"[EXP 2] kappa sweep at SNR={snr_db:.0f} dB, Nt={Nt}, "
          f"{n_channels} channels per point")
    print(f"  {'kappa':>5} | {'Fixed':>6} | {'Trad':>6} | {'DQN':>6}")
    print("  " + "-" * 34)

    for i, k in enumerate(kappas):
        s_fix = s_tr = s_dq = 0.0
        dqn_scheme.reset()
        kf = float(k)
        for hB, hE in channels:
            hE_noisy = imperfect_csi(hE, kf, rng)
            _, rf = evaluate_scheme(fixed_scheme,         hB, hE, hE_noisy, snr_lin, kf)
            _, rt = evaluate_scheme(traditional_optimizer, hB, hE, hE_noisy, snr_lin, kf)
            _, rd = evaluate_scheme(dqn_scheme,            hB, hE, hE_noisy, snr_lin, kf)
            s_fix += rf
            s_tr  += rt
            s_dq  += rd
        rs_fixed[i] = s_fix / n_channels
        rs_trad[i]  = s_tr  / n_channels
        rs_dqn[i]   = s_dq  / n_channels
        print(f"  {k:>5.2f} | {rs_fixed[i]:>6.3f} | "
              f"{rs_trad[i]:>6.3f} | {rs_dqn[i]:>6.3f}")

    # ---- plot ----
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.plot(kappas, rs_fixed, "o-", color="#7f7f7f", linewidth=1.8,
            markersize=6, label="Scheme 1: Fixed (rho=0.5)")
    ax.plot(kappas, rs_trad, "s--", color="#c0504d", linewidth=1.9,
            markersize=6, label="Scheme 2: Traditional (trusts noisy CSI)")
    ax.plot(kappas, rs_dqn, "D-", color="#2ca02c", linewidth=2.2,
            markersize=7, label="Scheme 3: DQN (proposed)")
    ax.set_xlabel("CSI quality  kappa")
    ax.set_ylabel("Average secrecy rate  Rs  (bits/s/Hz)")
    ax.set_title(f"Experiment 2 -- CSI-quality sweep\n"
                 f"Nt={Nt}, SNR={snr_db:.0f} dB, "
                 f"{n_channels} unseen channels per point")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    out = os.path.join(fig_dir, "06_kappa_sweep.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"[SAVE] {out}\n")

    return {"kappa": kappas, "rs_fixed": rs_fixed,
            "rs_traditional": rs_trad, "rs_dqn": rs_dqn}


# ---------------------------------------------------------------------------
# Experiment 4 -- antenna-count effect (SNR sweep, three Nt values)
# ---------------------------------------------------------------------------

def experiment_4_antenna_count(n_channels: int = 300,
                               kappa: float = 0.4,
                               model_paths: Dict[int, str] | None = None,
                               fig_dir: str = "figures",
                               nt_list=(2, 4, 8),
                               seed: int = 2026) -> Dict[str, Dict[str, np.ndarray]]:
    """
    For each Nt in nt_list, sweep SNR and compare Fixed / Traditional / DQN.

    A separate DQN model trained at that Nt is loaded for each panel; the
    file path defaults to default_model_path(Nt) but can be overridden via
    `model_paths={2: ..., 4: ..., 8: ...}` if you trained elsewhere. If a
    model file is missing, that panel falls back to Fixed + Traditional only
    so the function still produces a figure.

    Returns a nested dict keyed by 'Nt={N}'.
    """
    os.makedirs(fig_dir, exist_ok=True)
    snr_db_range = np.arange(0, 31, 3, dtype=float)

    if model_paths is None:
        model_paths = {int(Nt): default_model_path(int(Nt)) for Nt in nt_list}

    # Lazy-load each per-Nt DQN once. Missing files -> warn and skip DQN there.
    dqn_schemes: Dict[int, object] = {}
    for Nt in nt_list:
        path = model_paths.get(int(Nt), default_model_path(int(Nt)))
        if os.path.isfile(path):
            _, dqn_schemes[int(Nt)] = _load_dqn(path)
        else:
            print(f"[EXP 4] WARN: {path} not found -- "
                  f"DQN curve will be skipped on Nt={Nt} panel.")

    results: Dict[str, Dict[str, np.ndarray]] = {}

    fig, axes = plt.subplots(1, len(nt_list), figsize=(4.6 * len(nt_list), 4.6),
                             sharey=True)
    if len(nt_list) == 1:
        axes = [axes]

    print(f"[EXP 4] antenna-count sweep at kappa={kappa}, "
          f"{n_channels} channels per (Nt, SNR) point")

    for ax, Nt in zip(axes, nt_list):
        rng = np.random.default_rng(seed + int(Nt))
        channels = _sample_channels(int(Nt), n_channels, rng)
        dqn_scheme = dqn_schemes.get(int(Nt))

        rs_fixed = np.zeros_like(snr_db_range)
        rs_trad  = np.zeros_like(snr_db_range)
        rs_dqn   = np.zeros_like(snr_db_range) if dqn_scheme is not None else None

        print(f"\n  -- Nt = {Nt} --")
        if rs_dqn is not None:
            print(f"  {'SNR':>4} | {'Fixed':>6} | {'Trad':>6} | {'DQN':>6}")
        else:
            print(f"  {'SNR':>4} | {'Fixed':>6} | {'Trad':>6}")

        for i, snr_db in enumerate(snr_db_range):
            snr_lin = 10.0 ** (snr_db / 10.0)
            s_fix = s_tr = s_dq = 0.0

            if dqn_scheme is not None:
                dqn_scheme.reset()

            for hB, hE in channels:
                hE_noisy = imperfect_csi(hE, kappa, rng)
                _, rf = evaluate_scheme(fixed_scheme,
                                        hB, hE, hE_noisy, snr_lin, kappa)
                _, rt = evaluate_scheme(traditional_optimizer,
                                        hB, hE, hE_noisy, snr_lin, kappa)
                s_fix += rf
                s_tr  += rt
                if dqn_scheme is not None:
                    _, rd = evaluate_scheme(dqn_scheme,
                                            hB, hE, hE_noisy, snr_lin, kappa)
                    s_dq += rd

            rs_fixed[i] = s_fix / n_channels
            rs_trad[i]  = s_tr  / n_channels
            if rs_dqn is not None:
                rs_dqn[i] = s_dq / n_channels
                print(f"  {snr_db:>4.0f} | {rs_fixed[i]:>6.3f} | "
                      f"{rs_trad[i]:>6.3f} | {rs_dqn[i]:>6.3f}")
            else:
                print(f"  {snr_db:>4.0f} | {rs_fixed[i]:>6.3f} | "
                      f"{rs_trad[i]:>6.3f}")

        ax.plot(snr_db_range, rs_fixed, "o-", color="#7f7f7f",
                linewidth=1.8, markersize=5, label="Fixed")
        ax.plot(snr_db_range, rs_trad, "s--", color="#c0504d",
                linewidth=1.8, markersize=5, label=f"Traditional (k={kappa})")
        if rs_dqn is not None:
            ax.plot(snr_db_range, rs_dqn, "D-", color="#2ca02c",
                    linewidth=2.2, markersize=6,
                    label=f"DQN @ Nt={Nt} (k={kappa})")

        ax.set_title(f"Nt = {Nt}")
        ax.set_xlabel("Transmit SNR (dB)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)

        entry = {"snr_db": snr_db_range,
                 "rs_fixed": rs_fixed,
                 "rs_traditional": rs_trad}
        if rs_dqn is not None:
            entry["rs_dqn"] = rs_dqn
        results[f"Nt={Nt}"] = entry

    axes[0].set_ylabel("Average secrecy rate  Rs  (bits/s/Hz)")
    fig.suptitle(f"Experiment 4 -- Antenna-count effect at kappa = {kappa}\n"
                 f"Each panel uses a DQN trained at that Nt",
                 fontsize=11)
    fig.tight_layout()
    out = os.path.join(fig_dir, "07_antenna_count.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"\n[SAVE] {out}\n")

    return results


# ---------------------------------------------------------------------------
# Experiment 5 -- secrecy outage probability
# ---------------------------------------------------------------------------

def experiment_5_secrecy_outage(n_channels: int = 1000,
                                snr_db: float = 15.0,
                                kappa: float = 0.4,
                                model_path: str | None = None,
                                fig_dir: str = "figures",
                                Nt: int = 4,
                                seed: int = 2026) -> Dict[str, np.ndarray]:
    """
    Empirical secrecy outage probability vs target rate R0.

    For each scheme we collect Rs over n_channels independent realisations
    (each with a fresh kappa-imperfect CSI estimate), then for each target
    rate R0 we compute  SOP(R0) = mean(Rs < R0)  -- the empirical CDF.

    Returns a dict with: 'r0', 'sop_fixed', 'sop_traditional', 'sop_dqn',
    plus the raw 'rs_*' arrays for further analysis.
    """
    os.makedirs(fig_dir, exist_ok=True)
    if model_path is None:
        model_path = default_model_path(Nt)
    _, dqn_scheme = _load_dqn(model_path)

    rng = np.random.default_rng(seed)
    snr_lin = 10.0 ** (snr_db / 10.0)
    channels = _sample_channels(Nt, n_channels, rng)

    rs_fixed = np.zeros(n_channels)
    rs_trad  = np.zeros(n_channels)
    rs_dqn   = np.zeros(n_channels)

    dqn_scheme.reset()
    print(f"[EXP 5] outage at SNR={snr_db:.0f} dB, kappa={kappa}, "
          f"Nt={Nt}, {n_channels} channels")

    for j, (hB, hE) in enumerate(channels):
        hE_noisy = imperfect_csi(hE, kappa, rng)
        _, rs_fixed[j] = evaluate_scheme(fixed_scheme,
                                         hB, hE, hE_noisy, snr_lin, kappa)
        _, rs_trad[j]  = evaluate_scheme(traditional_optimizer,
                                         hB, hE, hE_noisy, snr_lin, kappa)
        _, rs_dqn[j]   = evaluate_scheme(dqn_scheme,
                                         hB, hE, hE_noisy, snr_lin, kappa)

    r0 = np.linspace(0.0, 8.0, 20)
    sop_fixed = np.array([float(np.mean(rs_fixed < r)) for r in r0])
    sop_trad  = np.array([float(np.mean(rs_trad  < r)) for r in r0])
    sop_dqn   = np.array([float(np.mean(rs_dqn   < r)) for r in r0])

    print(f"  {'R0':>4} | {'Fixed':>6} | {'Trad':>6} | {'DQN':>6}")
    print("  " + "-" * 32)
    for r, sf, st, sd in zip(r0, sop_fixed, sop_trad, sop_dqn):
        print(f"  {r:>4.2f} | {sf:>6.3f} | {st:>6.3f} | {sd:>6.3f}")

    # ---- plot ----
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.plot(r0, sop_fixed, "o-", color="#7f7f7f", linewidth=1.8,
            markersize=5, label="Scheme 1: Fixed")
    ax.plot(r0, sop_trad, "s--", color="#c0504d", linewidth=1.9,
            markersize=5, label=f"Scheme 2: Traditional (k={kappa})")
    ax.plot(r0, sop_dqn, "D-", color="#2ca02c", linewidth=2.2,
            markersize=6, label=f"Scheme 3: DQN (k={kappa})")
    ax.set_xlabel("Target secrecy rate  R0  (bits/s/Hz)")
    ax.set_ylabel("Secrecy outage probability  SOP = P(Rs < R0)")
    ax.set_title(f"Experiment 5 -- Secrecy outage probability\n"
                 f"Nt={Nt}, SNR={snr_db:.0f} dB, kappa={kappa}, "
                 f"{n_channels} channels")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(-0.02, 1.02)
    fig.tight_layout()
    out = os.path.join(fig_dir, "08_secrecy_outage.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"[SAVE] {out}\n")

    return {"r0": r0,
            "sop_fixed": sop_fixed,
            "sop_traditional": sop_trad,
            "sop_dqn": sop_dqn,
            "rs_fixed": rs_fixed,
            "rs_traditional": rs_trad,
            "rs_dqn": rs_dqn}


# ---------------------------------------------------------------------------
# Policy heatmap -- visualises the learned DQN policy as a 2D map
# ---------------------------------------------------------------------------

def policy_heatmap(model_path: str | None = None,
                   Nt: int = 4,
                   n_channels: int = 80,
                   n_snr: int = 16,
                   n_kappa: int = 11,
                   snr_db_min: float = 0.0,
                   snr_db_max: float = 30.0,
                   fig_dir: str = "figures",
                   seed: int = 2026,
                   annotate: bool = True) -> Dict[str, np.ndarray]:
    """
    Render the trained DQN's learned policy as a 2D heatmap over (SNR, kappa).

    For each (SNR, kappa) grid cell we sample n_channels random Rayleigh
    channels, build a kappa-noisy estimate of Eve's channel, ask the DQN
    which rho to play, and average the chosen rho across the batch. The
    result is a smooth picture of the policy as a function of operating
    conditions -- this is the most defendable single figure for the
    "what did the DQN actually learn?" question.

    Returns a dict with: 'snr_db', 'kappa', 'rho_mean', 'rho_std'.
    """
    os.makedirs(fig_dir, exist_ok=True)
    if model_path is None:
        model_path = default_model_path(Nt)
    _, dqn_scheme = _load_dqn(model_path)

    snrs = np.linspace(snr_db_min, snr_db_max, n_snr)
    kappas = np.linspace(0.0, 1.0, n_kappa)

    rho_mean = np.zeros((n_kappa, n_snr))
    rho_std  = np.zeros((n_kappa, n_snr))

    print(f"[POLICY] Nt={Nt}, sweeping {n_snr} SNRs x {n_kappa} kappas, "
          f"{n_channels} channels per cell")

    for ki, k in enumerate(kappas):
        for si, snr_db in enumerate(snrs):
            # fresh RNG per cell -> reproducible without ordering effects
            rng = np.random.default_rng(seed + ki * 1000 + si)
            snr_lin = 10.0 ** (snr_db / 10.0)
            dqn_scheme.reset()
            rhos_here = np.empty(n_channels)
            kf = float(k)
            for j in range(n_channels):
                hB = generate_rayleigh_channel(Nt, rng)
                hE = generate_rayleigh_channel(Nt, rng)
                hE_noisy = imperfect_csi(hE, kf, rng)
                rhos_here[j] = dqn_scheme(hB, hE_noisy, snr_lin, kf)
            rho_mean[ki, si] = float(rhos_here.mean())
            rho_std[ki, si]  = float(rhos_here.std())
        print(f"  kappa={k:.2f}: mean rho across SNR = "
              f"[{rho_mean[ki].min():.2f} .. {rho_mean[ki].max():.2f}]")

    # ---- plot: 2-panel figure (heatmap + marginal SNR dependence) ----
    rho_marginal_snr   = rho_mean.mean(axis=0)   # avg across kappa
    rho_marginal_kappa = rho_mean.mean(axis=1)   # avg across SNR

    fig, axes = plt.subplots(
        1, 2, figsize=(13.0, 5.4),
        gridspec_kw={"width_ratios": [2.2, 1.0]},
    )
    ax_hm, ax_mar = axes

    vmin = max(0.4, float(rho_mean.min()) - 0.05)
    vmax = min(0.9, float(rho_mean.max()) + 0.05)
    extent = [snrs[0] - (snrs[1]-snrs[0])/2,
              snrs[-1] + (snrs[1]-snrs[0])/2,
              kappas[0] - (kappas[1]-kappas[0])/2,
              kappas[-1] + (kappas[1]-kappas[0])/2]
    im = ax_hm.imshow(rho_mean, aspect="auto", origin="lower",
                      extent=extent, cmap="viridis", vmin=vmin, vmax=vmax)
    cbar = fig.colorbar(im, ax=ax_hm, pad=0.02)
    cbar.set_label("Mean rho chosen by DQN")

    if annotate:
        mid = 0.5 * (vmin + vmax)
        for ki in range(n_kappa):
            for si in range(n_snr):
                val = rho_mean[ki, si]
                txt_color = "white" if val < mid else "black"
                ax_hm.text(snrs[si], kappas[ki], f"{val:.2f}",
                           ha="center", va="center",
                           color=txt_color, fontsize=7.5)

    ax_hm.set_xlabel("Transmit SNR (dB)")
    ax_hm.set_ylabel("CSI quality  kappa")
    ax_hm.set_title("Learned DQN policy: rho(SNR, kappa)")

    # Marginal: rho averaged across all kappa, vs SNR
    ax_mar.plot(snrs, rho_marginal_snr, "D-", color="#2ca02c",
                linewidth=2.4, markersize=7,
                label="DQN (avg over kappa)")
    ax_mar.axhline(0.5, color="#7f7f7f", linestyle=":",
                   linewidth=1.5, label="Fixed scheme (rho=0.5)")
    ax_mar.set_xlabel("Transmit SNR (dB)")
    ax_mar.set_ylabel("Mean rho")
    ax_mar.set_ylim(0.45, 0.85)
    ax_mar.set_title("Policy vs SNR (marginal)")
    ax_mar.grid(True, alpha=0.3)
    ax_mar.legend(loc="upper right", fontsize=9)

    fig.suptitle(f"Learned DQN policy at Nt = {Nt}  "
                 f"({n_channels} channels per cell)",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    out = os.path.join(fig_dir, "09_policy_heatmap.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"[SAVE] {out}")
    print(f"  Marginal rho vs SNR: "
          f"low={rho_marginal_snr[0]:.2f}, "
          f"mid={rho_marginal_snr[len(snrs)//2]:.2f}, "
          f"high={rho_marginal_snr[-1]:.2f}")
    print(f"  Marginal rho vs kappa: "
          f"low={rho_marginal_kappa[0]:.2f}, "
          f"mid={rho_marginal_kappa[len(kappas)//2]:.2f}, "
          f"high={rho_marginal_kappa[-1]:.2f}\n")

    return {"snr_db": snrs, "kappa": kappas,
            "rho_mean": rho_mean, "rho_std": rho_std}


# ---------------------------------------------------------------------------
# Eve-strength sweep -- Qasem-inspired analysis (Eve closer to Alice = bigger beta)
# ---------------------------------------------------------------------------

def eve_strength_sweep(model_path: str | None = None,
                       Nt: int = 4,
                       n_channels: int = 400,
                       snr_db: float = 15.0,
                       kappa: float = 0.4,
                       betas_db=(-6, -3, 0, 3, 6, 9),
                       fig_dir: str = "figures",
                       seed: int = 2026) -> Dict[str, np.ndarray]:
    """
    Sweep Eve's channel-gain advantage and report each scheme's average Rs.

    We scale Eve's true channel by sqrt(beta), where beta = 10^(beta_db/10).
    In the Qasem 2024 paper this corresponds to varying the eavesdropper
    position (smaller distance -> stronger Eve channel). Our simulator has
    no geometry, so we induce the same effect through the channel-gain ratio.

    The noisy CSI estimate is built from the scaled true channel via the
    standard imperfect-CSI model in core.csi.

    Returns a dict with: 'beta_db', 'rs_fixed', 'rs_traditional', 'rs_dqn'.
    """
    os.makedirs(fig_dir, exist_ok=True)
    if model_path is None:
        model_path = default_model_path(Nt)
    _, dqn_scheme = _load_dqn(model_path)

    rng = np.random.default_rng(seed)
    snr_lin = 10.0 ** (snr_db / 10.0)
    channels = _sample_channels(Nt, n_channels, rng)

    betas_db = np.asarray(betas_db, dtype=float)
    betas    = 10.0 ** (betas_db / 10.0)

    rs_fixed = np.zeros_like(betas)
    rs_trad  = np.zeros_like(betas)
    rs_dqn   = np.zeros_like(betas)

    print(f"[EVE-STRENGTH] Nt={Nt}, SNR={snr_db:.0f} dB, kappa={kappa}, "
          f"{n_channels} channels per beta")
    print(f"  {'beta_dB':>7} | {'beta':>6} | {'Fixed':>6} | "
          f"{'Trad':>6} | {'DQN':>6}")
    print("  " + "-" * 44)

    for i, (b_db, b) in enumerate(zip(betas_db, betas)):
        s_fix = s_tr = s_dq = 0.0
        dqn_scheme.reset()
        sb = float(np.sqrt(b))
        for hB, hE in channels:
            hE_scaled = sb * hE                              # stronger/weaker Eve
            hE_noisy  = imperfect_csi(hE_scaled, kappa, rng) # CSI built from scaled
            _, rf = evaluate_scheme(fixed_scheme,
                                    hB, hE_scaled, hE_noisy, snr_lin, kappa)
            _, rt = evaluate_scheme(traditional_optimizer,
                                    hB, hE_scaled, hE_noisy, snr_lin, kappa)
            _, rd = evaluate_scheme(dqn_scheme,
                                    hB, hE_scaled, hE_noisy, snr_lin, kappa)
            s_fix += rf
            s_tr  += rt
            s_dq  += rd
        rs_fixed[i] = s_fix / n_channels
        rs_trad[i]  = s_tr  / n_channels
        rs_dqn[i]   = s_dq  / n_channels
        print(f"  {b_db:>+7.1f} | {b:>6.2f} | "
              f"{rs_fixed[i]:>6.3f} | {rs_trad[i]:>6.3f} | {rs_dqn[i]:>6.3f}")

    # ---- plot ----
    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    ax.plot(betas_db, rs_fixed, "o-", color="#7f7f7f", linewidth=1.9,
            markersize=7, label="Scheme 1: Fixed (rho=0.5)")
    ax.plot(betas_db, rs_trad, "s--", color="#c0504d", linewidth=2.0,
            markersize=7, label=f"Scheme 2: Traditional (k={kappa})")
    ax.plot(betas_db, rs_dqn, "D-", color="#2ca02c", linewidth=2.4,
            markersize=8, label=f"Scheme 3: DQN (k={kappa})")
    ax.axvline(0.0, color="black", linestyle=":", alpha=0.4,
               label="beta = 1 (Bob and Eve symmetric)")
    ax.set_xlabel("Eve channel-gain advantage  10 log10(beta)  (dB)\n"
                  "(larger = Eve is closer / has a stronger channel)")
    ax.set_ylabel("Average secrecy rate  Rs  (bits/s/Hz)")
    ax.set_title(f"Eve-strength sweep  (Qasem-inspired)\n"
                 f"Nt={Nt}, SNR={snr_db:.0f} dB, kappa={kappa}, "
                 f"{n_channels} unseen channels per point")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    out = os.path.join(fig_dir, "10_eve_strength.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"[SAVE] {out}\n")

    return {"beta_db": betas_db, "beta": betas,
            "rs_fixed": rs_fixed,
            "rs_traditional": rs_trad,
            "rs_dqn": rs_dqn}


# ---------------------------------------------------------------------------
# Experiment 3 -- optimal-rho comparison (per-channel oracle)
# ---------------------------------------------------------------------------

def experiment_3_optimal_rho(model_path: str | None = None,
                             Nt: int = 4,
                             n_channels: int = 600,
                             snr_db: float = 15.0,
                             kappa: float = 0.4,
                             fig_dir: str = "figures",
                             seed: int = 2026) -> Dict[str, np.ndarray]:
    """
    Compare each scheme's chosen rho against the per-channel oracle rho*.

    For each Monte Carlo channel realisation:
      1. Compute rho* = argmax Rs(rho) using the TRUE hE -- this is the
         oracle that no scheme can see at run time.
      2. Ask each scheme to pick its rho using only its allowed CSI.
      3. Record (rho_chosen - rho*) and (Rs_oracle - Rs_chosen).

    The figure has two panels:
      Left:  histograms of |rho_chosen - rho*| per scheme.
      Right: histograms of (Rs_oracle - Rs_chosen) per scheme.

    Returns a dict with raw arrays for further analysis.
    """
    os.makedirs(fig_dir, exist_ok=True)
    if model_path is None:
        model_path = default_model_path(Nt)
    _, dqn_scheme = _load_dqn(model_path)

    rng = np.random.default_rng(seed)
    snr_lin = 10.0 ** (snr_db / 10.0)
    channels = _sample_channels(Nt, n_channels, rng)

    # Brute-force grid for the oracle rho*
    rho_grid = np.linspace(0.05, 0.95, 91)

    rho_star = np.zeros(n_channels)
    rs_star  = np.zeros(n_channels)
    rho_fix  = np.zeros(n_channels)
    rho_trd  = np.zeros(n_channels)
    rho_dqn  = np.zeros(n_channels)
    rs_fix   = np.zeros(n_channels)
    rs_trd   = np.zeros(n_channels)
    rs_dqn   = np.zeros(n_channels)

    print(f"[EXP 3] optimal-rho comparison at SNR={snr_db:.0f} dB, "
          f"kappa={kappa}, Nt={Nt}, {n_channels} channels")

    dqn_scheme.reset()
    for j, (hB, hE) in enumerate(channels):
        # Oracle: brute-force on TRUE hE
        rs_curve = np.array([compute_secrecy_rate(hB, hE, float(r), snr_lin)
                             for r in rho_grid])
        idx = int(np.argmax(rs_curve))
        rho_star[j] = float(rho_grid[idx])
        rs_star[j]  = float(rs_curve[idx])

        # Each scheme's noisy CSI
        hE_noisy = imperfect_csi(hE, kappa, rng)
        rho_fix[j], rs_fix[j] = evaluate_scheme(fixed_scheme,
                                                hB, hE, hE_noisy, snr_lin, kappa)
        rho_trd[j], rs_trd[j] = evaluate_scheme(traditional_optimizer,
                                                hB, hE, hE_noisy, snr_lin, kappa)
        rho_dqn[j], rs_dqn[j] = evaluate_scheme(dqn_scheme,
                                                hB, hE, hE_noisy, snr_lin, kappa)

    # Aggregate stats
    err_fix = np.abs(rho_fix - rho_star)
    err_trd = np.abs(rho_trd - rho_star)
    err_dqn = np.abs(rho_dqn - rho_star)
    gap_fix = rs_star - rs_fix
    gap_trd = rs_star - rs_trd
    gap_dqn = rs_star - rs_dqn

    print(f"  Mean |rho - rho*|:  Fixed={err_fix.mean():.3f}, "
          f"Trad={err_trd.mean():.3f}, DQN={err_dqn.mean():.3f}")
    print(f"  Mean Rs gap to oracle (bits/s/Hz): "
          f"Fixed={gap_fix.mean():.3f}, "
          f"Trad={gap_trd.mean():.3f}, "
          f"DQN={gap_dqn.mean():.3f}")
    print(f"  Oracle mean Rs* = {rs_star.mean():.3f} bits/s/Hz")

    # ---- plot: 2-panel ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 5.2))

    bins_err = np.linspace(0.0, 0.9, 19)
    ax1.hist([err_fix, err_trd, err_dqn], bins=bins_err,
             label=[f"Fixed (mean={err_fix.mean():.2f})",
                    f"Traditional (mean={err_trd.mean():.2f})",
                    f"DQN (mean={err_dqn.mean():.2f})"],
             color=["#7f7f7f", "#c0504d", "#2ca02c"],
             alpha=0.85, edgecolor="black", linewidth=0.4)
    ax1.set_xlabel("|rho_chosen - rho*|")
    ax1.set_ylabel("Channels")
    ax1.set_title("How far is each scheme from the oracle rho*?")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(True, alpha=0.3, axis="y")

    bins_gap = np.linspace(0.0, max(gap_fix.max(), gap_trd.max(),
                                    gap_dqn.max(), 0.5), 25)
    ax2.hist([gap_fix, gap_trd, gap_dqn], bins=bins_gap,
             label=[f"Fixed (mean={gap_fix.mean():.3f})",
                    f"Traditional (mean={gap_trd.mean():.3f})",
                    f"DQN (mean={gap_dqn.mean():.3f})"],
             color=["#7f7f7f", "#c0504d", "#2ca02c"],
             alpha=0.85, edgecolor="black", linewidth=0.4)
    ax2.set_xlabel("Rs_oracle - Rs_chosen  (bits/s/Hz)")
    ax2.set_ylabel("Channels")
    ax2.set_title("Secrecy rate left on the table")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(True, alpha=0.3, axis="y")

    fig.suptitle(f"Experiment 3 -- per-channel oracle comparison\n"
                 f"Nt={Nt}, SNR={snr_db:.0f} dB, kappa={kappa}, "
                 f"{n_channels} unseen channels", fontsize=11)
    fig.tight_layout()
    out = os.path.join(fig_dir, "11_optimal_rho_comparison.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"[SAVE] {out}\n")

    return {"rho_star": rho_star, "rs_star": rs_star,
            "rho_fixed": rho_fix, "rho_traditional": rho_trd, "rho_dqn": rho_dqn,
            "rs_fixed": rs_fix, "rs_traditional": rs_trd, "rs_dqn": rs_dqn,
            "err_fixed": err_fix, "err_traditional": err_trd, "err_dqn": err_dqn,
            "gap_fixed": gap_fix, "gap_traditional": gap_trd, "gap_dqn": gap_dqn}
