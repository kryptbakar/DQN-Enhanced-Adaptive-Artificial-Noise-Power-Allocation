"""
The three AN power-split schemes compared in this project.

    Scheme 1 -- Fixed Baseline    : rho = 0.5 always          (Goel & Negi 2008)
    Scheme 2 -- Traditional Opt   : scipy scalar optimizer    (perfect-CSI upper bound)
    Scheme 3 -- DQN Agent         : reinforcement learning    (see core/dqn_agent.py)

All scheme functions share a common signature so they can be swapped into the
same evaluation harness:

    scheme(hB, hE_estimate, snr_linear)  ->  chosen rho in (0, 1)

Note: a scheme chooses rho based only on the CSI it is *allowed* to see
(hE_estimate, which may be noisy). The *achieved* secrecy rate is then
computed against the true hE by evaluate_scheme() below.
"""

from __future__ import annotations

from typing import Callable, Tuple

import numpy as np
from scipy.optimize import minimize_scalar

from .secrecy import compute_secrecy_rate
from .dqn_agent import DQNAgent, ACTION_RHOS
from .state import build_state


# ---------------------------------------------------------------------------
# Scheme 1 -- Fixed Baseline
# ---------------------------------------------------------------------------

def fixed_scheme(hB: np.ndarray,
                 hE_estimate: np.ndarray,
                 snr_linear: float,
                 kappa: float | None = None) -> float:
    """
    Always return rho = 0.5 (equal split between signal and AN).

    This is the original baseline from Goel & Negi (2008). It uses no CSI
    and does not adapt to the channel. We keep the same signature as the
    other schemes so that evaluate_scheme() is uniform. The kappa argument
    is accepted for signature uniformity and ignored.
    """
    return 0.5


# ---------------------------------------------------------------------------
# Scheme 2 -- Traditional Optimiser (bounded scalar optimisation)
# ---------------------------------------------------------------------------

def traditional_optimizer(hB: np.ndarray,
                          hE_estimate: np.ndarray,
                          snr_linear: float,
                          kappa: float | None = None,
                          rho_bounds: Tuple[float, float] = (0.01, 0.99)
                          ) -> float:
    """
    Pick rho* = argmax Rs(rho) using scipy's bounded scalar optimiser.

    The optimiser treats `hE_estimate` as if it were the true hE. When the
    estimate is perfect (kappa = 1) this gives the mathematical upper bound
    on achievable secrecy rate; when kappa < 1 the optimiser is being lied
    to, which is exactly the failure mode our DQN is designed to avoid.

    Uses Brent's method on a bounded 1-D interval -- cheap, reliable, and
    the standard "known Eve CSI" baseline referenced throughout the
    PLS optimisation literature (e.g. Wang et al. 2019 survey).
    """
    def neg_rs(rho: float) -> float:
        return -compute_secrecy_rate(hB, hE_estimate, rho, snr_linear)

    result = minimize_scalar(
        neg_rs,
        bounds=rho_bounds,
        method="bounded",
        options={"xatol": 1e-4},
    )
    return float(result.x)


# ---------------------------------------------------------------------------
# Evaluation harness (used by demo.py and later by experiments.py)
# ---------------------------------------------------------------------------

def evaluate_scheme(scheme_fn: Callable[..., float],
                    hB: np.ndarray,
                    hE_true: np.ndarray,
                    hE_estimate: np.ndarray,
                    snr_linear: float,
                    kappa: float | None = None) -> Tuple[float, float]:
    """
    Run a scheme on one channel realisation and report (chosen_rho, achieved_Rs).

    IMPORTANT: the scheme chooses rho using ONLY the CSI it is allowed to see
    (hE_estimate, possibly noisy). The achieved secrecy rate is then measured
    against the TRUE hE. This separation is what makes the kappa sweep
    (Experiment 2) honest.

    `kappa` is the CSI-quality parameter that produced hE_estimate. It is
    treated as side information that Alice knows from her feedback-channel
    statistics (standard assumption in the PLS-imperfect-CSI literature),
    so the DQN scheme is allowed to use it. Fixed and Traditional ignore it.

    Args:
        scheme_fn:   One of fixed_scheme, traditional_optimizer, dqn_scheme...
        hB:          Bob's true channel.
        hE_true:     Eve's true channel (used for the reward).
        hE_estimate: The CSI visible to the scheme (hE_true if perfect; a
                     noisy ĥE from core.csi.imperfect_csi otherwise).
        snr_linear:  Transmit SNR in linear scale.
        kappa:       CSI quality factor that generated hE_estimate, in [0, 1].
                     Optional for backwards compatibility with old test code;
                     when omitted the DQN scheme falls back to assuming kappa=0.5.

    Returns:
        (rho_chosen, secrecy_rate_achieved)
    """
    rho = scheme_fn(hB, hE_estimate, snr_linear, kappa)
    rs = compute_secrecy_rate(hB, hE_true, rho, snr_linear)
    return rho, rs


# ---------------------------------------------------------------------------
# Scheme 3 -- DQN-based scheme factory
# ---------------------------------------------------------------------------

def make_dqn_scheme(agent: DQNAgent,
                    last_rho_init: float = 0.5,
                    last_rs_init: float = 0.0) -> Callable:
    """
    Wrap a trained DQNAgent into a scheme function with the standard signature:

        scheme(hB, hE_estimate, snr_linear) -> rho

    The wrapper maintains a small amount of state across calls so that
    (last_rho, last_rs) components of the state vector are populated the
    same way they were during training. Reset between independent Monte Carlo
    runs by calling the returned object's .reset() method.
    """
    class _DQNScheme:
        def __init__(self):
            self.last_rho = last_rho_init
            self.last_rs  = last_rs_init

        def reset(self):
            self.last_rho = last_rho_init
            self.last_rs  = last_rs_init

        def __call__(self, hB, hE_estimate, snr_linear, kappa=None):
            snr_db = 10.0 * np.log10(snr_linear)
            # If a caller forgets to pass kappa, fall back to the midpoint
            # of the training range so the network gets a sane input.
            k = 0.5 if kappa is None else float(kappa)
            state = build_state(hB, hE_estimate, snr_db,
                                self.last_rho, self.last_rs, k)
            action = agent.act(state, epsilon=0.0)    # greedy at test time
            rho = float(ACTION_RHOS[action])
            # Update memory using the CHOSEN rho evaluated against the CSI
            # the scheme was given (kept for state consistency only; true
            # reward is measured externally by evaluate_scheme()).
            self.last_rho = rho
            self.last_rs  = compute_secrecy_rate(hB, hE_estimate, rho, snr_linear)
            return rho

    return _DQNScheme()
