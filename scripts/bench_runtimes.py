"""
Per-call runtime micro-benchmark for the three schemes.

Measures the average wall-clock time per scheme call on a fixed batch of
unseen channels. Numbers go into the report's Complexity Discussion.

The DQN inference number is dominated by TensorFlow's per-call overhead,
not raw FLOPs -- a real deployment would batch or use TFLite/ONNX.

Usage:
    python scripts/bench_runtimes.py
"""

from __future__ import annotations

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.channel import generate_rayleigh_channel
from core.csi import imperfect_csi
from core.schemes import (fixed_scheme, traditional_optimizer,
                          make_dqn_scheme)
from core.dqn_agent import DQNAgent
from core.experiments import default_model_path


def bench(Nt: int = 4,
          n_channels: int = 1000,
          snr_db: float = 15.0,
          kappa: float = 0.4,
          seed: int = 2026) -> None:
    rng = np.random.default_rng(seed)
    snr_lin = 10.0 ** (snr_db / 10.0)
    channels = [(generate_rayleigh_channel(Nt, rng),
                 imperfect_csi(generate_rayleigh_channel(Nt, rng), kappa, rng))
                for _ in range(n_channels)]

    agent = DQNAgent()
    agent.load(default_model_path(Nt))
    dqn_scheme = make_dqn_scheme(agent)

    # ---- Fixed -------------------------------------------------------
    t0 = time.perf_counter()
    for hB, hE_n in channels:
        _ = fixed_scheme(hB, hE_n, snr_lin)
    t_fixed = (time.perf_counter() - t0) / n_channels

    # ---- Traditional (scipy bounded scalar minimiser) ----------------
    t0 = time.perf_counter()
    for hB, hE_n in channels:
        _ = traditional_optimizer(hB, hE_n, snr_lin)
    t_trad = (time.perf_counter() - t0) / n_channels

    # ---- DQN inference (single forward pass) -------------------------
    # Warm up TF (first call is slower)
    for hB, hE_n in channels[:5]:
        _ = dqn_scheme(hB, hE_n, snr_lin, kappa)
    dqn_scheme.reset()
    t0 = time.perf_counter()
    for hB, hE_n in channels:
        _ = dqn_scheme(hB, hE_n, snr_lin, kappa)
    t_dqn = (time.perf_counter() - t0) / n_channels

    bar = "=" * 64
    print(bar)
    print(f"  RUNTIME BENCHMARK  (Nt={Nt}, {n_channels} channels)")
    print(bar)
    print(f"  {'Scheme':<22} | {'us/call':>10} | relative")
    print("  " + "-" * (60 - 2))
    print(f"  {'Fixed (rho=0.5)':<22} | "
          f"{t_fixed*1e6:>10.2f} | {t_fixed/t_fixed:>6.1f} x")
    print(f"  {'Traditional (scipy)':<22} | "
          f"{t_trad*1e6:>10.2f} | {t_trad/t_fixed:>6.1f} x")
    print(f"  {'DQN inference':<22} | "
          f"{t_dqn*1e6:>10.2f} | {t_dqn/t_fixed:>6.1f} x")
    print(bar)
    print(f"  Note: DQN dominated by TF per-call overhead, not raw FLOPs.")
    print(f"  A batched / TFLite deployment would shrink this by ~10x.")
    print(bar)


if __name__ == "__main__":
    bench()
