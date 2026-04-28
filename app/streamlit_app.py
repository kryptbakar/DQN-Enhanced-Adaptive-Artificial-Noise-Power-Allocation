"""
Streamlit demonstrator for the DQN-AN power-allocation project.

Run from the repo root:
    streamlit run app/streamlit_app.py

Five tabs:
  1. Live demo       -- pick (Nt, SNR, kappa) and watch the three schemes
                        evaluated on a fresh Monte Carlo channel batch.
  2. SNR sweep       -- interactive recreation of figure 04.
  3. Kappa sweep     -- interactive recreation of figure 06.
  4. Outage          -- interactive recreation of figure 08, with a target-rate slider.
  5. Geometry sketch -- conceptual Alice/Bob/Eve placement and beam direction.

Performance notes
-----------------
* DQN models are loaded with @st.cache_resource so each (Nt) is loaded once.
* Monte Carlo evaluations are wrapped in @st.cache_data keyed by all the
  inputs that affect the result (Nt, SNR, kappa, n_channels, seed). Sliding
  the same parameter back to a previous value is instant.
* For sliders we default to n_channels=150 (subsecond on CPU). A "high
  fidelity" toggle bumps to n_channels=600 for cleaner curves.

The 2.5D geometry tab is intentionally decorative -- the simulator's channel
is i.i.d. CN(0, I), with no spatial structure. The geometry plot is a
conceptual aid, not a physical layout.
"""

from __future__ import annotations

import os
import sys

# repo-root injection so 'core.*' imports work when launched via
# `streamlit run app/streamlit_app.py`
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from core.channel import (generate_rayleigh_channel,
                          mrt_beamformer,
                          null_space_projector)
from core.csi import imperfect_csi
from core.secrecy import compute_secrecy_rate
from core.schemes import (fixed_scheme, traditional_optimizer,
                          evaluate_scheme, make_dqn_scheme)
from core.dqn_agent import DQNAgent, ACTION_RHOS
from core.experiments import default_model_path


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="DQN-AN Wiretap Demonstrator",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Cached helpers
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading DQN weights...")
def load_dqn_for(Nt: int):
    """Load (and cache) the DQN trained at Nt. Returns (scheme, ok, msg)."""
    path = default_model_path(Nt)
    if not os.path.isfile(path):
        return None, False, f"No DQN found at `{path}`. Train it with `python scripts/train_dqn.py --nt {Nt}`."
    agent = DQNAgent()
    agent.load(path)
    return make_dqn_scheme(agent), True, f"Loaded `{path}`."


def _sample_channels(Nt: int, n: int, rng: np.random.Generator):
    return [(generate_rayleigh_channel(Nt, rng),
             generate_rayleigh_channel(Nt, rng)) for _ in range(n)]


@st.cache_data(show_spinner="Running Monte Carlo...")
def eval_point(Nt: int, snr_db: float, kappa: float,
               n_channels: int, seed: int) -> dict:
    """
    Run all three schemes at one (Nt, SNR, kappa) and return per-channel
    Rs arrays + the rho chosen by each scheme on each channel.
    """
    dqn_scheme, dqn_ok, _ = load_dqn_for(Nt)
    rng = np.random.default_rng(seed)
    snr_lin = 10.0 ** (snr_db / 10.0)
    chans = _sample_channels(Nt, n_channels, rng)

    rs_fix = np.zeros(n_channels)
    rs_trd = np.zeros(n_channels)
    rs_dqn = np.zeros(n_channels) if dqn_ok else None
    rho_fix = np.zeros(n_channels)
    rho_trd = np.zeros(n_channels)
    rho_dqn = np.zeros(n_channels) if dqn_ok else None

    if dqn_ok:
        dqn_scheme.reset()

    for j, (hB, hE) in enumerate(chans):
        hE_n = imperfect_csi(hE, kappa, rng)
        rho_fix[j], rs_fix[j] = evaluate_scheme(fixed_scheme,
                                                hB, hE, hE_n, snr_lin)
        rho_trd[j], rs_trd[j] = evaluate_scheme(traditional_optimizer,
                                                hB, hE, hE_n, snr_lin)
        if dqn_ok:
            rho_dqn[j], rs_dqn[j] = evaluate_scheme(dqn_scheme,
                                                    hB, hE, hE_n, snr_lin)

    return {
        "rs_fixed": rs_fix, "rs_traditional": rs_trd, "rs_dqn": rs_dqn,
        "rho_fixed": rho_fix, "rho_traditional": rho_trd, "rho_dqn": rho_dqn,
        "dqn_ok": dqn_ok,
    }


@st.cache_data(show_spinner="Running SNR sweep...")
def eval_snr_sweep(Nt: int, kappa: float, snr_db_min: float,
                   snr_db_max: float, n_points: int,
                   n_channels: int, seed: int) -> dict:
    snrs = np.linspace(snr_db_min, snr_db_max, n_points)
    means_fix = np.zeros(n_points)
    means_trd = np.zeros(n_points)
    means_dqn = np.zeros(n_points)
    dqn_ok_any = False
    for i, s in enumerate(snrs):
        out = eval_point(Nt, float(s), kappa, n_channels, seed)
        means_fix[i] = float(out["rs_fixed"].mean())
        means_trd[i] = float(out["rs_traditional"].mean())
        if out["dqn_ok"]:
            means_dqn[i] = float(out["rs_dqn"].mean())
            dqn_ok_any = True
    return {"snr_db": snrs,
            "rs_fixed": means_fix, "rs_traditional": means_trd,
            "rs_dqn": means_dqn if dqn_ok_any else None}


@st.cache_data(show_spinner="Running kappa sweep...")
def eval_kappa_sweep(Nt: int, snr_db: float, n_points: int,
                     n_channels: int, seed: int) -> dict:
    ks = np.linspace(0.0, 1.0, n_points)
    means_fix = np.zeros(n_points)
    means_trd = np.zeros(n_points)
    means_dqn = np.zeros(n_points)
    dqn_ok_any = False
    for i, k in enumerate(ks):
        out = eval_point(Nt, snr_db, float(k), n_channels, seed)
        means_fix[i] = float(out["rs_fixed"].mean())
        means_trd[i] = float(out["rs_traditional"].mean())
        if out["dqn_ok"]:
            means_dqn[i] = float(out["rs_dqn"].mean())
            dqn_ok_any = True
    return {"kappa": ks,
            "rs_fixed": means_fix, "rs_traditional": means_trd,
            "rs_dqn": means_dqn if dqn_ok_any else None}


# ---------------------------------------------------------------------------
# Plot helpers (Plotly)
# ---------------------------------------------------------------------------

COLORS = {"fixed": "#7f7f7f",
          "traditional": "#c0504d",
          "dqn": "#2ca02c"}


def lineplot(x, ys: dict, x_title: str, y_title: str, title: str = ""):
    fig = go.Figure()
    for label, (y, key) in ys.items():
        if y is None:
            continue
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers",
                                 name=label,
                                 line=dict(color=COLORS[key], width=2.5),
                                 marker=dict(size=7)))
    fig.update_layout(xaxis_title=x_title, yaxis_title=y_title,
                      title=title, template="plotly_white",
                      legend=dict(orientation="h", y=-0.18),
                      height=460, margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Sidebar (global controls)
# ---------------------------------------------------------------------------

st.sidebar.title("Wiretap demonstrator")
st.sidebar.caption("DQN-enhanced AN power allocation under imperfect CSI.")

with st.sidebar:
    Nt = st.selectbox("Antenna count Nt",
                      options=[2, 4, 8], index=1,
                      help="MRT beamforming + null-space AN dimension Nt-1.")
    seed = st.number_input("Random seed", min_value=0, max_value=10_000,
                           value=2026, step=1)
    high_fid = st.toggle("High-fidelity Monte Carlo",
                         value=False,
                         help="More channels per estimate (slower, smoother).")
    n_chan_live  = 600 if high_fid else 150
    n_chan_sweep = 300 if high_fid else 80

    st.divider()
    dqn_scheme, dqn_ok, dqn_msg = load_dqn_for(Nt)
    if dqn_ok:
        st.success(f"DQN @ Nt={Nt} loaded.")
    else:
        st.warning(dqn_msg)

    with st.expander("About this project"):
        st.markdown(
            "Three schemes for splitting Alice's transmit power between "
            "the signal beam (toward Bob) and artificial noise injected "
            "in Bob's null space (jamming Eve):\n\n"
            "* **Fixed** — `rho = 0.5` (Goel & Negi 2008).\n"
            "* **Traditional** — `argmax Rs(rho)` using the noisy estimate "
            "of Eve's channel; matches the perfect-CSI optimum at kappa=1.\n"
            "* **DQN** — trained Q-network picks rho from a 5-dim state "
            "containing the noisy CSI features. Learned policy from "
            "5000 random-(SNR, kappa) episodes.\n\n"
            "The DQN is trained per-Nt; the active model file is "
            f"`{default_model_path(Nt)}`."
        )


# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------

tab_live, tab_snr, tab_kappa, tab_outage, tab_geom = st.tabs([
    "Live demo", "SNR sweep", "Kappa sweep", "Outage", "Geometry sketch",
])


# ---- Tab 1: Live demo ----------------------------------------------------
with tab_live:
    st.subheader("Live three-scheme comparison")
    st.caption("Pick a single operating point and watch the schemes "
               "evaluated on a fresh batch of channels.")

    c1, c2 = st.columns([1, 1])
    with c1:
        snr_db = st.slider("Transmit SNR (dB)", 0.0, 30.0, 15.0, 0.5,
                           key="live_snr")
    with c2:
        kappa = st.slider("CSI quality kappa", 0.0, 1.0, 0.4, 0.05,
                          key="live_kappa")

    out = eval_point(Nt, snr_db, kappa, n_chan_live, seed)
    rs_fix = float(out["rs_fixed"].mean())
    rs_trd = float(out["rs_traditional"].mean())
    rs_dqn = float(out["rs_dqn"].mean()) if out["dqn_ok"] else float("nan")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scheme 1 — Fixed (rho=0.5)", f"{rs_fix:.3f}", "bits/s/Hz")
    m2.metric("Scheme 2 — Traditional",     f"{rs_trd:.3f}",
              f"{rs_trd - rs_fix:+.3f} vs Fixed")
    if out["dqn_ok"]:
        m3.metric("Scheme 3 — DQN",
                  f"{rs_dqn:.3f}",
                  f"{rs_dqn - rs_fix:+.3f} vs Fixed")
    else:
        m3.metric("Scheme 3 — DQN", "—", "no model for this Nt")
    m4.metric("Channels evaluated", f"{n_chan_live}",
              "(toggle high-fidelity in sidebar)")

    # Bar plot of mean Rs
    bar = go.Figure()
    names = ["Fixed", "Traditional", "DQN"]
    vals  = [rs_fix, rs_trd, rs_dqn]
    keys  = ["fixed", "traditional", "dqn"]
    bar.add_trace(go.Bar(x=names, y=vals,
                         marker_color=[COLORS[k] for k in keys],
                         text=[f"{v:.3f}" for v in vals],
                         textposition="outside"))
    bar.update_layout(yaxis_title="Mean Rs  (bits/s/Hz)",
                      template="plotly_white",
                      height=380, margin=dict(l=10, r=10, t=20, b=10),
                      showlegend=False)
    st.plotly_chart(bar, width="stretch")

    # rho-distribution histograms
    st.markdown("**What rho does each scheme actually pick?**")
    h1, h2, h3 = st.columns(3)

    def _rho_hist(col, rhos, label, color):
        fig = go.Figure(go.Histogram(x=rhos, xbins=dict(start=0.05, end=0.95, size=0.1),
                                     marker_color=color))
        fig.update_layout(title=label, template="plotly_white",
                          height=260, margin=dict(l=10, r=10, t=30, b=10),
                          xaxis_title="rho",
                          yaxis_title="count")
        col.plotly_chart(fig, width="stretch")

    _rho_hist(h1, out["rho_fixed"],       "Fixed",       COLORS["fixed"])
    _rho_hist(h2, out["rho_traditional"], "Traditional", COLORS["traditional"])
    if out["dqn_ok"]:
        _rho_hist(h3, out["rho_dqn"],     "DQN",         COLORS["dqn"])
    else:
        h3.info("No DQN model for this Nt.")


# ---- Tab 2: SNR sweep ----------------------------------------------------
with tab_snr:
    st.subheader("Average secrecy rate vs transmit SNR")
    kappa_snr = st.slider("CSI quality kappa", 0.0, 1.0, 0.4, 0.05,
                          key="snr_kappa")
    snr_lo, snr_hi = st.slider("SNR range (dB)",
                               -5.0, 35.0, (0.0, 30.0), 1.0)
    n_points = st.slider("Sweep resolution", 5, 25, 11)

    res = eval_snr_sweep(Nt, kappa_snr, float(snr_lo), float(snr_hi),
                         n_points, n_chan_sweep, seed)
    fig = lineplot(res["snr_db"],
                   {"Scheme 1: Fixed":       (res["rs_fixed"], "fixed"),
                    "Scheme 2: Traditional": (res["rs_traditional"], "traditional"),
                    f"Scheme 3: DQN @ Nt={Nt}": (res["rs_dqn"], "dqn")},
                   "Transmit SNR (dB)",
                   "Mean Rs (bits/s/Hz)",
                   title=f"Nt={Nt}, kappa={kappa_snr:.2f}, "
                         f"{n_chan_sweep} channels per point")
    st.plotly_chart(fig, width="stretch")
    st.caption("Same family of curves as figures/04_three_scheme_comparison.png "
               "but for any (Nt, kappa) you choose.")


# ---- Tab 3: Kappa sweep --------------------------------------------------
with tab_kappa:
    st.subheader("Average secrecy rate vs CSI quality kappa")
    snr_kap = st.slider("Transmit SNR (dB)", 0.0, 30.0, 15.0, 0.5,
                        key="kap_snr")
    n_points_k = st.slider("Sweep resolution", 5, 21, 11, key="kap_npts")

    res = eval_kappa_sweep(Nt, snr_kap, n_points_k, n_chan_sweep, seed)
    fig = lineplot(res["kappa"],
                   {"Scheme 1: Fixed":       (res["rs_fixed"], "fixed"),
                    "Scheme 2: Traditional": (res["rs_traditional"], "traditional"),
                    f"Scheme 3: DQN @ Nt={Nt}": (res["rs_dqn"], "dqn")},
                   "CSI quality kappa",
                   "Mean Rs (bits/s/Hz)",
                   title=f"Nt={Nt}, SNR={snr_kap:.0f} dB, "
                         f"{n_chan_sweep} channels per point")
    st.plotly_chart(fig, width="stretch")
    st.caption("Lower kappa = more CSI noise. Traditional collapses fastest "
               "when its only input is being lied to; DQN was trained under "
               "random kappa so it stays flatter.")


# ---- Tab 4: Outage -------------------------------------------------------
with tab_outage:
    st.subheader("Empirical secrecy outage probability  P(Rs < R0)")
    co1, co2 = st.columns(2)
    with co1:
        snr_o = st.slider("Transmit SNR (dB)", 0.0, 30.0, 15.0, 0.5,
                          key="out_snr")
    with co2:
        kappa_o = st.slider("CSI quality kappa", 0.0, 1.0, 0.4, 0.05,
                            key="out_kappa")

    out = eval_point(Nt, snr_o, kappa_o, n_chan_live, seed)
    r0 = np.linspace(0.0, 8.0, 33)
    sop_fix = [float(np.mean(out["rs_fixed"] < r)) for r in r0]
    sop_trd = [float(np.mean(out["rs_traditional"] < r)) for r in r0]
    sop_dqn = ([float(np.mean(out["rs_dqn"] < r)) for r in r0]
               if out["dqn_ok"] else None)

    fig = lineplot(r0,
                   {"Scheme 1: Fixed":       (sop_fix, "fixed"),
                    "Scheme 2: Traditional": (sop_trd, "traditional"),
                    f"Scheme 3: DQN @ Nt={Nt}": (sop_dqn, "dqn")},
                   "Target secrecy rate R0 (bits/s/Hz)",
                   "P(Rs < R0)",
                   title=f"Nt={Nt}, SNR={snr_o:.0f} dB, kappa={kappa_o:.2f}, "
                         f"{n_chan_live} channels")
    fig.update_yaxes(range=[-0.02, 1.02])
    st.plotly_chart(fig, width="stretch")

    target = st.slider("Pick a target R0 (bits/s/Hz) to read off SOP",
                       0.0, 8.0, 2.0, 0.1)
    j = int(np.argmin(np.abs(r0 - target)))
    cm1, cm2, cm3 = st.columns(3)
    cm1.metric(f"SOP @ R0={r0[j]:.2f} — Fixed",       f"{sop_fix[j]:.3f}")
    cm2.metric(f"SOP @ R0={r0[j]:.2f} — Traditional", f"{sop_trd[j]:.3f}")
    if sop_dqn is not None:
        cm3.metric(f"SOP @ R0={r0[j]:.2f} — DQN",     f"{sop_dqn[j]:.3f}")


# ---- Tab 5: Geometry sketch ----------------------------------------------
with tab_geom:
    st.subheader("Conceptual Alice / Bob / Eve geometry")
    st.caption("Channel realisations in this simulator are i.i.d. CN(0, I) "
               "and have **no spatial structure** -- this view is purely "
               "illustrative. The MRT beam direction and AN cone visualise "
               "*what the math is doing*, not where signals literally go.")

    cgo1, cgo2 = st.columns(2)
    with cgo1:
        bob_angle = st.slider("Bob azimuth (deg)", -180.0, 180.0, 30.0, 5.0)
        bob_dist  = st.slider("Bob distance",       0.5,    5.0, 2.5, 0.1)
    with cgo2:
        eve_angle = st.slider("Eve azimuth (deg)",  -180.0, 180.0, -45.0, 5.0)
        eve_dist  = st.slider("Eve distance",       0.5,    5.0, 3.2, 0.1)

    rng = np.random.default_rng(seed)
    hB = generate_rayleigh_channel(Nt, rng)
    hE = generate_rayleigh_channel(Nt, rng)
    snr_lin = 10.0 ** (15.0 / 10.0)
    rho_trad = traditional_optimizer(hB, hE, snr_lin)
    if dqn_ok:
        dqn_scheme.reset()
        rho_d = dqn_scheme(hB, hE, snr_lin)
    else:
        rho_d = float("nan")

    fig = go.Figure()
    # Alice antenna array along y-axis
    ant_x = np.zeros(Nt)
    ant_y = np.linspace(-0.3, 0.3, Nt)
    fig.add_trace(go.Scatter(x=ant_x, y=ant_y, mode="markers+text",
                             marker=dict(size=12, color="#1f4e79",
                                         line=dict(color="white", width=1)),
                             text=[f"a{i+1}" for i in range(Nt)],
                             textposition="middle right",
                             name="Alice (Nt antennas)"))

    bx, by = bob_dist * np.cos(np.deg2rad(bob_angle)), bob_dist * np.sin(np.deg2rad(bob_angle))
    ex, ey = eve_dist * np.cos(np.deg2rad(eve_angle)), eve_dist * np.sin(np.deg2rad(eve_angle))
    fig.add_trace(go.Scatter(x=[bx], y=[by], mode="markers+text",
                             marker=dict(size=18, color="#2ca02c", symbol="diamond"),
                             text=["Bob"], textposition="top center",
                             name="Bob (legitimate Rx)"))
    fig.add_trace(go.Scatter(x=[ex], y=[ey], mode="markers+text",
                             marker=dict(size=18, color="#c0504d", symbol="x"),
                             text=["Eve"], textposition="top center",
                             name="Eve (eavesdropper)"))

    # MRT beam toward Bob
    fig.add_annotation(x=bx, y=by, ax=0, ay=0,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.4,
                       arrowwidth=2.5, arrowcolor="#2ca02c")
    # AN "leakage" arrow toward Eve (faint)
    fig.add_annotation(x=ex, y=ey, ax=0, ay=0,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowsize=1.0,
                       arrowwidth=1.5, arrowcolor="rgba(192,80,77,0.45)")

    fig.update_layout(template="plotly_white",
                      xaxis=dict(scaleanchor="y", range=[-5.5, 5.5],
                                 zeroline=False, showgrid=True),
                      yaxis=dict(range=[-5.5, 5.5],
                                 zeroline=False, showgrid=True),
                      height=520, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.15),
                      title=f"Nt = {Nt}  |  one channel realisation, seed={seed}")
    st.plotly_chart(fig, width="stretch")

    g1, g2, g3 = st.columns(3)
    g1.metric("rho — Fixed",       "0.50")
    g2.metric("rho — Traditional", f"{rho_trad:.3f}")
    if dqn_ok:
        g3.metric("rho — DQN",     f"{rho_d:.3f}")
    else:
        g3.metric("rho — DQN", "—")
