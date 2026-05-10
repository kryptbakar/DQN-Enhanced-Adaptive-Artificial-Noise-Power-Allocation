"""
Rayleigh fading channel generator + MISO beamforming primitives.

Corresponds to Phase 1, steps 1 and 2 of the project proposal.
All math follows the Goel & Negi (2008) MISO artificial-noise framework
(reference [1] in the proposal).

Exported functions
------------------
generate_rayleigh_channel(Nt, rng)   -> complex channel vector h of shape (Nt,)
mrt_beamformer(hB)                   -> unit-norm beamforming vector w
null_space_projector(hB)             -> orthogonal projector P_perp of shape (Nt, Nt)
verify_null_space(hB, P_perp)        -> sanity check (Bob must not see the AN)
"""

import numpy as np


def generate_rayleigh_channel(Nt: int,
                              rng: np.random.Generator = None) -> np.ndarray:
    """
    Sample one complex Rayleigh-fading MISO channel vector.

    Each entry is i.i.d. CN(0, 1): the real and imaginary parts are
    independent Gaussians with variance 1/2 each, so E[|h_i|^2] = 1.

    Args:
        Nt:  Number of transmit antennas at Alice.
        rng: Optional numpy Generator for reproducibility.

    Returns:
        Complex vector of shape (Nt,).
    """
    if rng is None:
        rng = np.random.default_rng()
    real = rng.standard_normal(Nt)
    imag = rng.standard_normal(Nt)
    return (real + 1j * imag) / np.sqrt(2.0)


def mrt_beamformer(hB: np.ndarray) -> np.ndarray:
    """
    Maximum-Ratio-Transmission (MRT) beamforming vector pointing toward Bob.

        w = hB / ||hB||

    Under the standard wireless convention y = h^H x + n, this is the
    unit-norm direction that maximises |hB^H w|^2, by Cauchy-Schwarz, with
    maximum value ||hB||^2. All of the signal power then arrives at Bob,
    while every direction orthogonal to hB sees zero signal contribution.

    Args:
        hB: Bob's channel vector, shape (Nt,).

    Returns:
        Unit-norm beamforming vector w, shape (Nt,).
    """
    return hB / np.linalg.norm(hB)


def null_space_projector(hB: np.ndarray) -> np.ndarray:
    """
    Orthogonal projector onto the null space of Bob's channel.

        P_perp = I - (hB hB^H) / ||hB||^2          (Hermitian, idempotent)

    Any vector z satisfies hB^H (P_perp z) = 0, so Bob never sees it.
    The artificial-noise vector z_AN is sampled inside this subspace,
    which is why Bob's received SNR is unaffected by the AN power.

    Args:
        hB: Bob's channel vector, shape (Nt,).

    Returns:
        Hermitian projector matrix, shape (Nt, Nt).
    """
    Nt = hB.shape[0]
    hB_col = hB.reshape(-1, 1)                      # (Nt, 1)
    norm_sq = float(np.vdot(hB, hB).real)           # ||hB||^2
    return np.eye(Nt) - (hB_col @ hB_col.conj().T) / norm_sq


def verify_null_space(hB: np.ndarray,
                      P_perp: np.ndarray,
                      tol: float = 1e-10) -> bool:
    """
    Sanity check: Bob must not see the artificial noise.

    Returns True iff ||hB^H P_perp|| < tol (should be ~machine epsilon).
    Use this in tests — if it ever fails, the simulator is broken.
    """
    leakage = np.linalg.norm(hB.conj() @ P_perp)
    return bool(leakage < tol)
