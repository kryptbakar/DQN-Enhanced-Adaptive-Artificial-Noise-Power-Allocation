"""Tests for core/secrecy.py — Rs(rho) closed-form."""

import numpy as np
import pytest

from core.channel import generate_rayleigh_channel
from core.secrecy import compute_secrecy_rate
from core.csi import imperfect_csi


# ---------------------------------------------------------------------------
# Basic invariants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rho", [0.05, 0.25, 0.5, 0.75, 0.95])
def test_secrecy_rate_nonnegative(rho):
    """Rs is clipped at 0 by construction."""
    rng = np.random.default_rng(0)
    for _ in range(100):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        rs = compute_secrecy_rate(hB, hE, rho, snr_linear=10.0)
        assert rs >= 0.0, f"Rs must be >= 0, got {rs}"


def test_secrecy_rate_finite_and_real():
    rng = np.random.default_rng(0)
    for _ in range(50):
        hB = generate_rayleigh_channel(4, rng)
        hE = generate_rayleigh_channel(4, rng)
        rs = compute_secrecy_rate(hB, hE, 0.5, snr_linear=100.0)
        assert np.isfinite(rs), f"Rs should be finite, got {rs}"
        assert isinstance(rs, float)


# ---------------------------------------------------------------------------
# Sanity edges
# ---------------------------------------------------------------------------

def test_zero_snr_gives_zero_rate():
    """At P/sigma^2 -> 0, both rates collapse and Rs = 0."""
    rng = np.random.default_rng(0)
    hB = generate_rayleigh_channel(4, rng)
    hE = generate_rayleigh_channel(4, rng)
    rs = compute_secrecy_rate(hB, hE, 0.5, snr_linear=1e-9)
    assert rs < 1e-6, f"At zero SNR Rs should be ~0, got {rs}"


def test_eve_much_weaker_than_bob_gives_positive_rate():
    """If hE is tiny, Bob always wins."""
    rng = np.random.default_rng(0)
    hB = generate_rayleigh_channel(4, rng)
    hE = 1e-3 * generate_rayleigh_channel(4, rng)
    rs = compute_secrecy_rate(hB, hE, 0.5, snr_linear=10.0)
    assert rs > 1.0, \
        f"Vanishing Eve channel should yield Rs > 1, got {rs}"


def test_concavity_peak_in_unit_interval():
    """Rs(rho) should peak strictly inside (0, 1) for typical channels."""
    rng = np.random.default_rng(2)
    hB = generate_rayleigh_channel(4, rng)
    hE = generate_rayleigh_channel(4, rng)
    rhos = np.linspace(0.01, 0.99, 199)
    rs_vals = np.array(
        [compute_secrecy_rate(hB, hE, float(r), snr_linear=10**1.5)
         for r in rhos]
    )
    idx_star = int(np.argmax(rs_vals))
    rho_star = float(rhos[idx_star])
    assert 0.05 < rho_star < 0.95, \
        f"Optimal rho should sit inside (0.05, 0.95), got {rho_star}"


def test_perfect_csi_matches_true_when_kappa_one():
    """imperfect_csi(hE, kappa=1) == hE -> Rs(noisy) == Rs(true)."""
    rng = np.random.default_rng(0)
    hB = generate_rayleigh_channel(4, rng)
    hE = generate_rayleigh_channel(4, rng)
    hE_noisy = imperfect_csi(hE, kappa=1.0, rng=rng)
    np.testing.assert_allclose(hE_noisy, hE, atol=1e-12)
    r_true  = compute_secrecy_rate(hB, hE,       0.4, snr_linear=10.0)
    r_noisy = compute_secrecy_rate(hB, hE_noisy, 0.4, snr_linear=10.0)
    assert abs(r_true - r_noisy) < 1e-12


# ---------------------------------------------------------------------------
# Imperfect-CSI model
# ---------------------------------------------------------------------------

def test_imperfect_csi_kappa_zero_is_pure_noise():
    """At kappa=0 the estimate is pure CN(0, I) and uncorrelated with hE."""
    rng = np.random.default_rng(0)
    hE = generate_rayleigh_channel(4, rng)
    estimates = np.array([imperfect_csi(hE, 0.0, rng) for _ in range(5_000)])
    # Each draw should have mean ~0 and unit variance
    assert abs(estimates.mean()) < 0.1
    assert abs(np.mean(np.abs(estimates) ** 2) - 1.0) < 0.1


def test_imperfect_csi_rejects_out_of_range_kappa():
    rng = np.random.default_rng(0)
    hE = generate_rayleigh_channel(4, rng)
    for bad in (-0.1, 1.1, 2.0, -1.0):
        with pytest.raises(ValueError):
            imperfect_csi(hE, bad, rng)
