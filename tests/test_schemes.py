"""Tests for core/schemes.py — Fixed, Traditional optimiser, evaluate_scheme harness."""

import numpy as np
import pytest

from core.channel import generate_rayleigh_channel
from core.csi import imperfect_csi
from core.secrecy import compute_secrecy_rate
from core.schemes import (fixed_scheme,
                          traditional_optimizer,
                          evaluate_scheme)


# ---------------------------------------------------------------------------
# Fixed scheme
# ---------------------------------------------------------------------------

def test_fixed_scheme_is_constant():
    """rho = 0.5 regardless of channel or SNR."""
    rng = np.random.default_rng(0)
    for _ in range(20):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        for snr_lin in (0.1, 1.0, 10.0, 1000.0):
            assert fixed_scheme(hB, hE, snr_lin) == 0.5


# ---------------------------------------------------------------------------
# Traditional optimiser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("snr_lin", [1.0, 10.0, 100.0])
def test_traditional_returns_valid_rho(snr_lin):
    """Optimal rho should land inside the (0.01, 0.99) bounds."""
    rng = np.random.default_rng(0)
    for _ in range(30):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        rho_opt = traditional_optimizer(hB, hE, snr_lin)
        assert 0.01 <= rho_opt <= 0.99, f"out-of-bounds rho={rho_opt}"


def test_traditional_beats_fixed_at_perfect_csi():
    """With perfect CSI (kappa=1), Scheme 2 must dominate Scheme 1 on average."""
    rng = np.random.default_rng(7)
    n_channels = 200
    snr_lin = 10.0 ** 1.5     # ~15 dB
    rs_fix = 0.0
    rs_opt = 0.0
    for _ in range(n_channels):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        # Perfect CSI -> hE_estimate == hE
        _, rf = evaluate_scheme(fixed_scheme,         hB, hE, hE, snr_lin)
        _, ro = evaluate_scheme(traditional_optimizer, hB, hE, hE, snr_lin)
        rs_fix += rf
        rs_opt += ro
    rs_fix /= n_channels
    rs_opt /= n_channels
    assert rs_opt > rs_fix, \
        f"Scheme 2 should beat Scheme 1 at kappa=1, got opt={rs_opt:.3f} vs fix={rs_fix:.3f}"


def test_traditional_matches_brute_force_at_perfect_csi():
    """scipy bounded scalar should agree with a 200-pt grid search to 0.02."""
    rng = np.random.default_rng(0)
    snr_lin = 10.0 ** 1.5
    grid = np.linspace(0.01, 0.99, 199)
    for _ in range(20):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        rho_scipy = traditional_optimizer(hB, hE, snr_lin)
        rs_grid = np.array([compute_secrecy_rate(hB, hE, float(r), snr_lin)
                            for r in grid])
        rho_grid_star = float(grid[int(np.argmax(rs_grid))])
        assert abs(rho_scipy - rho_grid_star) < 0.02, \
            f"scipy={rho_scipy:.4f} vs grid={rho_grid_star:.4f}"


# ---------------------------------------------------------------------------
# evaluate_scheme harness
# ---------------------------------------------------------------------------

def test_evaluate_scheme_uses_estimate_for_choice_and_true_for_reward():
    """
    Honesty check: a scheme that only sees hE_estimate must still be measured
    against hE_true. Verify by giving Traditional a noisy estimate and
    confirming the achieved Rs uses the true channel.
    """
    rng = np.random.default_rng(3)
    hB = generate_rayleigh_channel(4, rng)
    hE = generate_rayleigh_channel(4, rng)
    hE_noisy = imperfect_csi(hE, kappa=0.4, rng=rng)
    snr_lin = 10.0

    rho_chosen, rs_achieved = evaluate_scheme(traditional_optimizer,
                                              hB, hE, hE_noisy, snr_lin)

    # Manually replicate: Traditional picks rho using hE_noisy
    rho_manual = traditional_optimizer(hB, hE_noisy, snr_lin)
    # Achieved rate uses the TRUE hE
    rs_manual = compute_secrecy_rate(hB, hE, rho_manual, snr_lin)

    assert abs(rho_chosen - rho_manual) < 1e-12
    assert abs(rs_achieved - rs_manual) < 1e-12


def test_imperfect_csi_can_hurt_traditional_below_fixed():
    """
    Headline insight of the project: at noisy CSI the Traditional optimiser
    can underperform the Fixed baseline on average. Verify on a moderate
    Monte Carlo set so the test is repeatable.
    """
    rng = np.random.default_rng(11)
    n_channels = 400
    snr_lin = 10.0 ** 1.5
    kappa = 0.2     # quite noisy CSI -> Traditional should suffer

    rs_fix = 0.0
    rs_trd = 0.0
    for _ in range(n_channels):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        hE_noisy = imperfect_csi(hE, kappa, rng)
        _, rf = evaluate_scheme(fixed_scheme,         hB, hE, hE_noisy, snr_lin)
        _, rt = evaluate_scheme(traditional_optimizer, hB, hE, hE_noisy, snr_lin)
        rs_fix += rf
        rs_trd += rt
    rs_fix /= n_channels
    rs_trd /= n_channels
    # The whole point of the project: Traditional <= Fixed at low kappa
    assert rs_trd <= rs_fix + 0.05, \
        f"Expected Traditional to NOT meaningfully beat Fixed at kappa={kappa}, " \
        f"got trad={rs_trd:.3f} vs fix={rs_fix:.3f}"
