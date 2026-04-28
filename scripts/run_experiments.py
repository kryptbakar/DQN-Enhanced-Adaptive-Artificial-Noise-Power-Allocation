"""
Phase 4 driver -- run all three follow-up experiments end-to-end.

Produces:
    figures/06_kappa_sweep.png         -- CSI-quality sweep at fixed SNR
    figures/07_antenna_count.png       -- antenna-count effect, 1x3 panel
    figures/08_secrecy_outage.png      -- empirical secrecy outage probability

Loads the trained DQN(s) from models/dqn_trained_nt{Nt}.keras. Experiments
2 and 5 use the Nt=4 model. Experiment 4 loads a separate DQN trained at
each Nt in {2, 4, 8}; if a per-Nt model file is missing, that panel falls
back to Fixed + Traditional only (and the script prints a warning).

Usage:
    python scripts/run_experiments.py
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os

from core.experiments import (experiment_2_kappa_sweep,
                              experiment_4_antenna_count,
                              experiment_5_secrecy_outage)


MODEL_PATH_NT4 = "models/dqn_trained_nt4.keras"
FIG_DIR        = "figures"


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)
    bar = "=" * 72
    print(bar)
    print("  PHASE 4 -- Follow-up experiments (kappa / Nt / outage)")
    print(bar + "\n")

    # ---- Experiment 2 -- CSI quality sweep ----
    print("-" * 72)
    print("  Experiment 2: kappa sweep (CSI quality)")
    print("-" * 72)
    res2 = experiment_2_kappa_sweep(n_channels=400, snr_db=15.0,
                                    model_path=MODEL_PATH_NT4,
                                    fig_dir=FIG_DIR)

    # ---- Experiment 4 -- antenna-count effect ----
    print("-" * 72)
    print("  Experiment 4: antenna-count effect")
    print("-" * 72)
    res4 = experiment_4_antenna_count(n_channels=300, kappa=0.4,
                                      fig_dir=FIG_DIR)

    # ---- Experiment 5 -- secrecy outage probability ----
    print("-" * 72)
    print("  Experiment 5: secrecy outage probability")
    print("-" * 72)
    res5 = experiment_5_secrecy_outage(n_channels=1000, snr_db=15.0,
                                       kappa=0.4,
                                       model_path=MODEL_PATH_NT4,
                                       fig_dir=FIG_DIR)

    # ---- summary ----
    print(bar)
    print("  SUMMARY")
    print(bar)
    print(f"\n[EXP 2] kappa sweep at SNR=15 dB:")
    print(f"  At kappa=0.0: Fixed={res2['rs_fixed'][0]:.3f}, "
          f"Trad={res2['rs_traditional'][0]:.3f}, "
          f"DQN={res2['rs_dqn'][0]:.3f}")
    print(f"  At kappa=1.0: Fixed={res2['rs_fixed'][-1]:.3f}, "
          f"Trad={res2['rs_traditional'][-1]:.3f}, "
          f"DQN={res2['rs_dqn'][-1]:.3f}")

    print(f"\n[EXP 4] antenna count at kappa=0.4 (mean over SNR):")
    for key, entry in res4.items():
        msg = (f"  {key}: Fixed mean={entry['rs_fixed'].mean():.3f}, "
               f"Trad mean={entry['rs_traditional'].mean():.3f}")
        if "rs_dqn" in entry:
            msg += f", DQN mean={entry['rs_dqn'].mean():.3f}"
        print(msg)

    print(f"\n[EXP 5] secrecy outage at SNR=15, kappa=0.4 (target R0=2):")
    j = int((res5['r0'] >= 2.0).argmax())
    print(f"  SOP@R0={res5['r0'][j]:.2f}: "
          f"Fixed={res5['sop_fixed'][j]:.3f}, "
          f"Trad={res5['sop_traditional'][j]:.3f}, "
          f"DQN={res5['sop_dqn'][j]:.3f}")

    print(f"\n[FIGURES]")
    for fname in ("06_kappa_sweep.png",
                  "07_antenna_count.png",
                  "08_secrecy_outage.png"):
        path = os.path.join(FIG_DIR, fname)
        ok = "OK" if os.path.isfile(path) else "MISSING"
        print(f"  [{ok}] {path}")

    print("\n" + bar)
    print("  DONE.")
    print(bar)


if __name__ == "__main__":
    main()
