"""
Imperfect-CSI model for the eavesdropper's channel.

Corresponds to Phase 1, step 3 of the project proposal.
Implements the standard linear CSI-error model used in PLS literature
(see Eq. 42 of Wang et al. 2019, reference [2]; also Gerbracht et al. 2012,
reference [6]):

        ĥE = sqrt(kappa) * hE + sqrt(1 - kappa) * e,     e ~ CN(0, I)

kappa in [0, 1] controls the quality of Alice's estimate of Eve's channel:

    kappa = 1.0  ->  perfect CSI          (ĥE == hE)
    kappa = 0.4  ->  realistic imperfect  (our headline evaluation point)
    kappa = 0.0  ->  pure noise           (no info about hE)
"""

import numpy as np


def imperfect_csi(hE: np.ndarray,
                  kappa: float,
                  rng: np.random.Generator = None) -> np.ndarray:
    """
    Produce a noisy estimate of Eve's true channel.

    Args:
        hE:    True Eve channel vector, shape (Nt,).
        kappa: CSI quality factor in [0, 1].
        rng:   Optional numpy Generator for reproducibility.

    Returns:
        ĥE, a noisy estimate of hE with the same shape.

    Raises:
        ValueError: if kappa is outside [0, 1].
    """
    if not 0.0 <= kappa <= 1.0:
        raise ValueError(f"kappa must be in [0, 1], got {kappa}")
    if rng is None:
        rng = np.random.default_rng()

    Nt = hE.shape[0]
    e = (rng.standard_normal(Nt) + 1j * rng.standard_normal(Nt)) / np.sqrt(2.0)
    return np.sqrt(kappa) * hE + np.sqrt(1.0 - kappa) * e
