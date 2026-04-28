"""
Train DQN agents at multiple antenna counts.

Drives scripts/train_dqn.py's train_one() over Nt in {2, 4, 8} so that
core.experiments.experiment_4_antenna_count can show a full 3-scheme
comparison on every panel of figures/07_antenna_count.png.

Hyperparameters are identical across Nt (only the channel dimension
changes), so the resulting policies are directly comparable.

Usage:
    python scripts/train_all_nt.py
    python scripts/train_all_nt.py --episodes 1000   # quick smoke test
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import time

from scripts.train_dqn import train_one, model_path_for


DEFAULT_NTS = (2, 4, 8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--nts", type=int, nargs="+", default=list(DEFAULT_NTS))
    args = parser.parse_args()

    bar = "=" * 72
    print(bar)
    print(f"  MULTI-Nt TRAINING -- Nt in {args.nts}, "
          f"{args.episodes} episodes each")
    print(bar)

    t0 = time.time()
    paths = {}
    for Nt in args.nts:
        ts = time.time()
        path = train_one(Nt=int(Nt), n_episodes=args.episodes, seed=args.seed)
        paths[int(Nt)] = path
        print(f"\n[TIME] Nt={Nt} took {time.time() - ts:.1f} s\n")

    print(bar)
    print(f"  ALL DONE in {time.time() - t0:.1f} s")
    print(bar)
    for Nt, path in paths.items():
        print(f"  Nt={Nt}: {path}")


if __name__ == "__main__":
    main()
