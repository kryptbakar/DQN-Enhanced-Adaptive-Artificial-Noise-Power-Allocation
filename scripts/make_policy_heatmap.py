"""
Render the trained DQN's policy as a 2D heatmap over (SNR, kappa).

Produces:
    figures/09_policy_heatmap.png

Story: this is the single most defendable answer to "what did the DQN
actually learn?" The bright (high-rho) corner sits at low SNR + low
kappa -- exactly where trusting the noisy CSI would be most dangerous,
the agent learned to put more power on the signal.

Usage:
    python scripts/make_policy_heatmap.py              # Nt=4 by default
    python scripts/make_policy_heatmap.py --nt 8       # use the Nt=8 model
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse

from core.experiments import policy_heatmap, default_model_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nt", type=int, default=4, choices=[2, 4, 8],
                        help="Antenna count (selects which trained model to use)")
    parser.add_argument("--n-channels", type=int, default=80,
                        help="Channels averaged per (SNR, kappa) cell")
    parser.add_argument("--n-snr", type=int, default=16,
                        help="SNR grid resolution")
    parser.add_argument("--n-kappa", type=int, default=11,
                        help="Kappa grid resolution")
    args = parser.parse_args()

    bar = "=" * 72
    print(bar)
    print(f"  POLICY HEATMAP -- visualising the learned DQN policy (Nt={args.nt})")
    print(bar + "\n")

    policy_heatmap(model_path=default_model_path(args.nt),
                   Nt=args.nt,
                   n_channels=args.n_channels,
                   n_snr=args.n_snr,
                   n_kappa=args.n_kappa)

    print(bar)
    print("  DONE.")
    print(bar)


if __name__ == "__main__":
    main()
