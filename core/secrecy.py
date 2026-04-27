"""
Secrecy-rate computation for the MISO wiretap channel with null-space AN.

Corresponds to Phase 1, step 4 of the project proposal.
Uses the AN-averaged closed-form expression: we average out the random AN
vector analytically so that Rs(rho) is deterministic per channel realisation.
This is standard in the PLS literature and removes a source of Monte Carlo
variance that would otherwise make scheme comparisons noisy.

Derivation (normalised so that noise variance sigma^2 = 1 and P is the
transmit SNR = P / sigma^2):

    Transmit signal:
        x = sqrt(rho * P) * w * s + sqrt((1 - rho) * P) * z_AN
        w = hB* / ||hB||                   (MRT beamformer)
        z_AN lives in null(hB)             (injected via P_perp)

    Bob:
        y_B = hB^H x + n_B = sqrt(rho*P) * ||hB|| * s + n_B
        SNR_B = rho * P * ||hB||^2

    Eve (averaging over z_AN, with total AN power (1-rho)*P spread
    uniformly over the (Nt-1)-dim null space):
        E[|hE^H z_AN|^2] = ((1-rho)*P / (Nt-1)) * ||P_perp hE||^2
        SINR_E = rho*P*|hE^H w|^2 /
                 ((1-rho)*P/(Nt-1) * ||P_perp hE||^2 + 1)

    Secrecy rate:
        Rs = max(0, log2(1 + SNR_B) - log2(1 + SINR_E))
"""

from __future__ import annotations

import numpy as np

from .channel import mrt_beamformer, null_space_projector


def compute_secrecy_rate(hB: np.ndarray,
                         hE: np.ndarray,
                         rho: float,
                         snr_linear: float) -> float:
    """
    Secrecy rate for one channel realisation (AN-averaged, deterministic).

    Args:
        hB:         Bob's true channel vector, shape (Nt,).
        hE:         Eve's channel vector used for rate evaluation, shape (Nt,).
                    Pass the true hE when computing achieved Rs (reward).
                    Pass the noisy estimate ĥE when a CSI-limited scheme is
                    *choosing* rho based on what it thinks Eve looks like.
        rho:        Power split in (0, 1). Fraction of total power on signal.
        snr_linear: Transmit SNR, P / sigma^2, in linear scale (not dB).

    Returns:
        Secrecy rate in bits/s/Hz, always non-negative.
    """
    Nt = hB.shape[0]

    w = mrt_beamformer(hB)
    P_perp = null_space_projector(hB)

    # --- Bob: null-space AN leaks nothing into him ---
    snr_bob = rho * snr_linear * float(np.linalg.norm(hB) ** 2)

    # --- Eve: signal leakage + averaged AN interference ---
    signal_at_eve = rho * snr_linear * float(np.abs(np.vdot(hE, w)) ** 2)

    P_hE = P_perp @ hE
    an_dim = max(Nt - 1, 1)                      # null-space dimension
    an_at_eve = ((1.0 - rho) * snr_linear
                 * float(np.linalg.norm(P_hE) ** 2)
                 / an_dim)

    sinr_eve = signal_at_eve / (an_at_eve + 1.0)  # sigma^2 = 1

    rate_bob = np.log2(1.0 + snr_bob)
    rate_eve = np.log2(1.0 + sinr_eve)

    return float(max(0.0, rate_bob - rate_eve))
