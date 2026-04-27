"""
State-vector construction for the DQN agent.

Lives in its own module so that both core/trainer.py and core/schemes.py
can import it without forming an import cycle (schemes.py wraps a trained
agent into a scheme function and needs the same state encoding the
trainer used).

State vector layout (all approximately in [0, 1] range):

    state[0] = ||hB||^2 / Nt      -- Bob's channel gain, per-antenna
    state[1] = ||hE_est||^2 / Nt  -- Eve's NOISY gain estimate
    state[2] = snr_db / 30        -- transmit SNR normalised
    state[3] = last_rho           -- previous action
    state[4] = last_rs / 10       -- previous reward, normalised
"""

from __future__ import annotations

import numpy as np


def build_state(hB: np.ndarray,
                hE_est: np.ndarray,
                snr_db: float,
                last_rho: float,
                last_rs: float) -> np.ndarray:
    """Assemble the 5-element state vector (see module docstring)."""
    Nt = hB.shape[0]
    return np.array([
        float(np.linalg.norm(hB) ** 2) / Nt,
        float(np.linalg.norm(hE_est) ** 2) / Nt,
        snr_db / 30.0,
        last_rho,
        last_rs / 10.0,
    ], dtype=np.float32)
