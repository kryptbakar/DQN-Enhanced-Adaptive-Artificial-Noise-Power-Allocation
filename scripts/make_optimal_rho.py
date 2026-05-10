"""
Experiment 3 -- per-channel oracle rho* comparison.

Produces:
    figures/11_optimal_rho_comparison.png

Story: for each Monte Carlo channel, brute-force the *true* optimal rho*
against the *true* hE -- this is the upper bound no scheme can beat. Then
ask each scheme to pick its rho using only the noisy CSI it is allowed to
see, and measure (a) how far the chosen rho lands from rho*, and (b) how
much secrecy rate is left on the table.

Usage:
    python scripts/make_optimal_rho.py
    python scripts/make_optimal_rho.py --nt 8 --snr 25 --kappa 0.6
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse

from core.experiments import experiment_3_optimal_rho, default_model_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nt", type=int, default=4, choices=[2, 4, 8])
    parser.add_argument("--snr", type=float, default=15.0)
    parser.add_argument("--kappa", type=float, default=0.4)
    parser.add_argument("--n-channels", type=int, default=600)
    args = parser.parse_args()

    bar = "=" * 72
    print(bar)
    print(f"  EXPERIMENT 3 -- optimal-rho comparison  "
          f"(Nt={args.nt}, SNR={args.snr:.0f} dB, kappa={args.kappa})")
    print(bar + "\n")

    experiment_3_optimal_rho(model_path=default_model_path(args.nt),
                             Nt=args.nt,
                             snr_db=args.snr,
                             kappa=args.kappa,
                             n_channels=args.n_channels)

    print(bar)
    print("  DONE.")
    print(bar)


if __name__ == "__main__":
    main()
