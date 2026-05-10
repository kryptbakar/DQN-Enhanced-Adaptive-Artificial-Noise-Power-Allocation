"""Tests for core/channel.py — Rayleigh sampler, MRT beamformer, null-space projector."""

import numpy as np
import pytest

from core.channel import (generate_rayleigh_channel,
                          mrt_beamformer,
                          null_space_projector,
                          verify_null_space)


# ---------------------------------------------------------------------------
# Rayleigh sampler
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("Nt", [2, 4, 8])
def test_channel_shape_and_dtype(Nt):
    rng = np.random.default_rng(0)
    h = generate_rayleigh_channel(Nt, rng)
    assert h.shape == (Nt,), f"expected shape ({Nt},), got {h.shape}"
    assert np.iscomplexobj(h), "channel must be complex-valued"


def test_channel_unit_variance():
    """Each entry should be CN(0, 1) -> E[|h_i|^2] = 1."""
    rng = np.random.default_rng(0)
    samples = np.array([generate_rayleigh_channel(4, rng) for _ in range(20_000)])
    mean_power = float(np.mean(np.abs(samples) ** 2))
    assert abs(mean_power - 1.0) < 0.05, \
        f"E[|h|^2] should be ~1.0, got {mean_power:.4f}"


def test_channel_zero_mean():
    rng = np.random.default_rng(0)
    samples = np.array([generate_rayleigh_channel(4, rng) for _ in range(20_000)])
    mean = complex(samples.mean())
    assert abs(mean) < 0.05, f"channel mean should be ~0, got {mean}"


def test_channel_reproducible_with_seed():
    h1 = generate_rayleigh_channel(4, np.random.default_rng(42))
    h2 = generate_rayleigh_channel(4, np.random.default_rng(42))
    np.testing.assert_array_equal(h1, h2)


# ---------------------------------------------------------------------------
# MRT beamformer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("Nt", [2, 4, 8])
def test_mrt_unit_norm(Nt):
    rng = np.random.default_rng(0)
    hB = generate_rayleigh_channel(Nt, rng)
    w = mrt_beamformer(hB)
    assert abs(np.linalg.norm(w) - 1.0) < 1e-12, \
        f"MRT vector must be unit-norm, got ||w||={np.linalg.norm(w)}"


def test_mrt_aligns_with_bob():
    """|hB^H w| should equal ||hB|| (full beamforming gain)."""
    rng = np.random.default_rng(1)
    for _ in range(50):
        hB = generate_rayleigh_channel(4, rng)
        w = mrt_beamformer(hB)
        gain = abs(np.vdot(hB, w))
        assert abs(gain - np.linalg.norm(hB)) < 1e-10, \
            f"MRT gain should equal ||hB||, got {gain} vs {np.linalg.norm(hB)}"


# ---------------------------------------------------------------------------
# Null-space projector
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("Nt", [2, 4, 8])
def test_null_space_projector_is_hermitian(Nt):
    rng = np.random.default_rng(0)
    hB = generate_rayleigh_channel(Nt, rng)
    P = null_space_projector(hB)
    np.testing.assert_allclose(P, P.conj().T, atol=1e-12)


@pytest.mark.parametrize("Nt", [2, 4, 8])
def test_null_space_projector_is_idempotent(Nt):
    rng = np.random.default_rng(0)
    hB = generate_rayleigh_channel(Nt, rng)
    P = null_space_projector(hB)
    np.testing.assert_allclose(P @ P, P, atol=1e-12)


def test_null_space_no_leakage_to_bob():
    """The headline guarantee: Bob doesn't see any AN component."""
    rng = np.random.default_rng(0)
    max_leak = 0.0
    for _ in range(500):
        hB = generate_rayleigh_channel(4, rng)
        P = null_space_projector(hB)
        leak = float(np.linalg.norm(hB.conj() @ P))
        max_leak = max(max_leak, leak)
        assert verify_null_space(hB, P), \
            f"hB^H P_perp leaked: {leak}"
    assert max_leak < 1e-10, f"max leak across 500 channels = {max_leak:.2e}"


def test_null_space_dimension():
    """Trace(P_perp) = Nt - 1 for a rank-1 hB."""
    rng = np.random.default_rng(0)
    for Nt in (2, 4, 8):
        hB = generate_rayleigh_channel(Nt, rng)
        P = null_space_projector(hB)
        tr = float(np.real(np.trace(P)))
        assert abs(tr - (Nt - 1)) < 1e-10, \
            f"trace(P_perp) should be Nt-1={Nt-1}, got {tr}"
