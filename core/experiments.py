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
        for hB, hE in channels:
            hE_noisy = imperfect_csi(hE, float(k), rng)
            _, rf = evaluate_scheme(fixed_scheme,         hB, hE, hE_noisy, snr_lin)
            _, rt = evaluate_scheme(traditional_optimizer, hB, hE, hE_noisy, snr_lin)
            _, rd = evaluate_scheme(dqn_scheme,            hB, hE, hE_noisy, snr_lin)
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
                                        hB, hE, hE_noisy, snr_lin)
                _, rt = evaluate_scheme(traditional_optimizer,
                                        hB, hE, hE_noisy, snr_lin)
                s_fix += rf
                s_tr  += rt
                if dqn_scheme is not None:
                    _, rd = evaluate_scheme(dqn_scheme,
                                            hB, hE, hE_noisy, snr_lin)
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
                                         hB, hE, hE_noisy, snr_lin)
        _, rs_trad[j]  = evaluate_scheme(traditional_optimizer,
                                         hB, hE, hE_noisy, snr_lin)
        _, rs_dqn[j]   = evaluate_scheme(dqn_scheme,
                                         hB, hE, hE_noisy, snr_lin)

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
