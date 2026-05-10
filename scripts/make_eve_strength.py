"""
Eve-strength sweep -- inspired by Qasem 2024's eavesdropper-position analysis.

Produces:
    figures/10_eve_strength.png

Story: in Qasem 2024 the secrecy rate is plotted against Eve's x-coordinate,
which physically translates into Eve's path-loss attenuation. Our simulator
is geometry-free (i.i.d. CN(0, I) channels), so we induce the same effect by
scaling Eve's true channel by sqrt(beta), where beta = E[||hE||^2] / E[||hB||^2].
beta < 1 -> Eve is "farther", weaker channel -> higher secrecy.
beta > 1 -> Eve is "closer", stronger channel -> harder to hide.

Usage:
    python scripts/make_eve_strength.py
    python scripts/make_eve_strength.py --nt 8 --snr 20
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse

from core.experiments import eve_strength_sweep, default_model_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nt", type=int, default=4, choices=[2, 4, 8])
    parser.add_argument("--snr", type=float, default=15.0,
                        help="Transmit SNR in dB")
    parser.add_argument("--kappa", type=float, default=0.4,
                        help="CSI quality factor")
    parser.add_argument("--n-channels", type=int, default=400,
                        help="Channels per beta point")
    args = parser.parse_args()

    bar = "=" * 72
    print(bar)
    print(f"  EVE-STRENGTH SWEEP  (Nt={args.nt}, SNR={args.snr:.0f} dB, "
          f"kappa={args.kappa})")
    print(bar + "\n")

    eve_strength_sweep(model_path=default_model_path(args.nt),
                       Nt=args.nt,
                       snr_db=args.snr,
                       kappa=args.kappa,
                       n_channels=args.n_channels)

    print(bar)
    print("  DONE.")
    print(bar)


if __name__ == "__main__":
    main()
