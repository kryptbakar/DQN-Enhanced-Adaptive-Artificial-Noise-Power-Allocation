"""
Streamlit demonstrator for the DQN-AN power-allocation project.

Audience-friendly version: every screen leads with a 1-sentence story,
each scheme has a persona name (Naive / Mathematician / Smart Agent),
and the technical labels live in tooltips and parentheses so the demo
is readable to a mixed class while still rigorous for the instructor.

Run from the repo root:
    streamlit run app/streamlit_app.py

Five tabs:
  1. Live test       -- pick a scenario and see who wins.
  2. Power story     -- secrecy vs transmit power (SNR sweep).
  3. Bad-intel test  -- THE HEADLINE -- secrecy vs CSI quality (kappa sweep).
  4. How often it fails -- secrecy outage probability.
  5. Picture of the setup -- conceptual Alice / Bob / Eve geometry.

All Monte Carlo evaluations are cached so the first slider drag is the
slow one; later drags are instant.
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

from core.channel import generate_rayleigh_channel
from core.csi import imperfect_csi
from core.schemes import (fixed_scheme, traditional_optimizer,
                          evaluate_scheme, make_dqn_scheme)
from core.dqn_agent import DQNAgent
from core.experiments import default_model_path


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Wiretap Defender — DQN demo",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Scheme labels — technical name first, plain-language gloss in brackets so
# the demo is readable to a mixed audience while still naming the actual
# constructs the report describes.
# ---------------------------------------------------------------------------

# Short labels for axes / chart legends
NAIVE_LABEL = "Fixed (ρ = 0.5)"
MATH_LABEL  = "Traditional"
DQN_LABEL   = "DQN (ours)"

# Long labels for metric tiles and walls of text
NAIVE_FULL = "Fixed split (Goel–Negi, ρ = 0.5)"
MATH_FULL  = "Traditional optimiser (scipy, trusts noisy ĥE)"
DQN_FULL   = "DQN agent (our proposal, sees κ)"

# One-line gloss shown next to the labels — keeps the layman story alive.
NAIVE_GLOSS = "the do-nothing baseline — always 50/50"
MATH_GLOSS  = "trusts the noisy intel and optimises"
DQN_GLOSS   = "neural net, knows when to ignore bad intel"

COLORS = {
    "fixed":       "#7f7f7f",   # grey
    "traditional": "#c0504d",   # red
    "dqn":         "#2ca02c",   # green
}


# ---------------------------------------------------------------------------
# Cached helpers
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading the trained model...")
def load_dqn_for(Nt: int):
    """Load (and cache) the DQN trained at Nt. Returns (scheme, ok, msg)."""
    path = default_model_path(Nt)
    if not os.path.isfile(path):
        return None, False, (
            f"No trained model found at `{path}`. "
            f"Train it first with `python scripts/train_dqn.py --nt {Nt}`."
        )
    agent = DQNAgent()
    agent.load(path)
    return make_dqn_scheme(agent), True, f"Loaded `{path}`."


def _sample_channels(Nt: int, n: int, rng: np.random.Generator):
    return [(generate_rayleigh_channel(Nt, rng),
             generate_rayleigh_channel(Nt, rng)) for _ in range(n)]


@st.cache_data(show_spinner="Running the test...")
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
                                                hB, hE, hE_n, snr_lin, kappa)
        rho_trd[j], rs_trd[j] = evaluate_scheme(traditional_optimizer,
                                                hB, hE, hE_n, snr_lin, kappa)
        if dqn_ok:
            rho_dqn[j], rs_dqn[j] = evaluate_scheme(dqn_scheme,
                                                    hB, hE, hE_n, snr_lin, kappa)

    return {
        "rs_fixed": rs_fix, "rs_traditional": rs_trd, "rs_dqn": rs_dqn,
        "rho_fixed": rho_fix, "rho_traditional": rho_trd, "rho_dqn": rho_dqn,
        "dqn_ok": dqn_ok,
    }


@st.cache_data(show_spinner="Sweeping power...")
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


@st.cache_data(show_spinner="Sweeping κ...")
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
# Plot helper
# ---------------------------------------------------------------------------

def lineplot(x, ys: dict, x_title: str, y_title: str, title: str = ""):
    fig = go.Figure()
    for label, (y, key) in ys.items():
        if y is None:
            continue
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers",
                                 name=label,
                                 line=dict(color=COLORS[key], width=2.8),
                                 marker=dict(size=8)))
    fig.update_layout(xaxis_title=x_title, yaxis_title=y_title,
                      title=title, template="plotly_white",
                      legend=dict(orientation="h", y=-0.22),
                      height=460, margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Wiretap Defender")
st.sidebar.caption(
    "MISO wiretap channel: Alice (multi-antenna transmitter) talks to "
    "Bob (legitimate receiver). Eve (passive eavesdropper) listens in. "
    "Alice splits power between the message and artificial noise (AN) "
    "aimed at Eve. Three schemes, one question: who keeps the secret best?"
)

with st.sidebar:
    Nt = st.selectbox(
        "Antennas at Alice  —  Nt",
        options=[2, 4, 8], index=2,
        help="Nt = number of transmit antennas. More antennas means a "
             "sharper beam at Bob and a larger null space (Nt − 1 "
             "dimensions) for AN. The DQN's edge widens with Nt."
    )
    seed = st.number_input(
        "Scenario seed",
        min_value=0, max_value=10_000, value=2026, step=1,
        help="Same seed = same random channels. Change for a fresh roll."
    )
    high_fid = st.toggle(
        "Slower but smoother",
        value=False,
        help="Run more channel samples per evaluation. "
             "Charts look cleaner but each slider drag takes longer."
    )
    n_chan_live  = 600 if high_fid else 150
    n_chan_sweep = 300 if high_fid else 80

    st.divider()
    dqn_scheme, dqn_ok, dqn_msg = load_dqn_for(Nt)
    if dqn_ok:
        st.success(f"DQN agent loaded (trained at Nt = {Nt}).")
    else:
        st.warning(dqn_msg)

    with st.expander("Glossary  —  the symbols on this page"):
        st.markdown(
            "- **MISO wiretap channel** — multi-antenna Alice, "
            "single-antenna Bob and Eve.\n"
            "- **Nt** — number of transmit antennas at Alice.\n"
            "- **MRT beam (w)** — Alice's matched-filter beam toward Bob, "
            "*w = hB / ‖hB‖*.\n"
            "- **Artificial noise (AN, z)** — jamming signal injected into "
            "the null space of Bob's channel; invisible to Bob, audible "
            "to Eve.\n"
            "- **ρ (rho)** — fraction of total power on the message. "
            "*1 − ρ* goes into AN.\n"
            "- **hE / ĥE** — Eve's true / estimated channel.\n"
            "- **κ (kappa)** — CSI quality factor in [0, 1]. "
            "*κ = 1* is perfect intel, *κ = 0* is pure guessing.\n"
            "- **Rs** — secrecy rate, the secret bits/s/Hz Alice can send "
            "while Eve still gets nothing.\n"
            "- **SNR (dB)** — total transmit SNR P/σ², in decibels."
        )

    with st.expander("The three schemes in one line each"):
        st.markdown(
            f"- **{NAIVE_FULL}** — {NAIVE_GLOSS}.\n"
            f"- **{MATH_FULL}** — {MATH_GLOSS}.\n"
            f"- **{DQN_FULL}** — {DQN_GLOSS}."
        )


# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------

st.title("Wiretap Defender")
st.markdown(
    "**One question:** under noisy CSI on Eve (κ < 1), which scheme "
    "achieves the highest average secrecy rate Rs — Fixed (ρ = 0.5), "
    "the Traditional optimiser, or our DQN? "
    "Click through the tabs in order; tab 3 (the κ sweep) is the headline."
)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_live, tab_snr, tab_kappa, tab_outage, tab_geom = st.tabs([
    "1. Live test  (single point)",
    "2. SNR sweep  (vs. transmit power)",
    "3. κ sweep  (THE headline — vs. CSI quality)",
    "4. Outage probability",
    "5. Geometry sketch",
])


# ---- Tab 1: Live test ----------------------------------------------------
with tab_live:
    st.subheader("Pick a scenario, see who keeps the secret best.")
    st.markdown(
        "Set the **transmit SNR (P/σ²)** and the **CSI quality κ**. "
        "We run all three strategies on the same batch of fresh "
        "random channels. The bar chart below shows the average "
        "secrecy rate each one achieves. **Higher is better.**"
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        snr_db = st.slider(
            "Transmit SNR  —  P/σ² in dB  (Alice's transmit power)",
            0.0, 30.0, 15.0, 0.5,
            key="live_snr",
            help="Linear SNR = 10^(SNR_dB / 10). Higher dB = louder "
                 "transmission. The action space ρ ∈ {0.05, …, 0.85} "
                 "is allocated against this total power."
        )
    with c2:
        kappa = st.slider(
            "CSI quality  —  κ  (1 = perfect intel on Eve, 0 = pure noise)",
            0.0, 1.0, 0.4, 0.05,
            key="live_kappa",
            help="κ controls how noisy Alice's estimate of Eve's "
                 "channel is. Model: ĥE = √κ·hE + √(1−κ)·e, "
                 "with e ~ CN(0, I). The DQN sees κ in its state."
        )

    out = eval_point(Nt, snr_db, kappa, n_chan_live, seed)
    rs_fix = float(out["rs_fixed"].mean())
    rs_trd = float(out["rs_traditional"].mean())
    rs_dqn = float(out["rs_dqn"].mean()) if out["dqn_ok"] else float("nan")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(NAIVE_FULL, f"{rs_fix:.3f}",
              "Rs in bits/s/Hz (higher = more secret throughput)")
    m2.metric(MATH_FULL, f"{rs_trd:.3f}",
              f"{rs_trd - rs_fix:+.3f} vs Fixed")
    if out["dqn_ok"]:
        m3.metric(DQN_FULL, f"{rs_dqn:.3f}",
                  f"{rs_dqn - rs_fix:+.3f} vs Fixed")
    else:
        m3.metric(DQN_FULL, "—", "no model for this antenna count")
    m4.metric("Monte Carlo channels", f"{n_chan_live}",
              "(toggle slow/smooth in sidebar)")

    # Bar plot — winner highlighted
    bar = go.Figure()
    names = [NAIVE_LABEL, MATH_LABEL, DQN_LABEL]
    vals  = [rs_fix, rs_trd, rs_dqn]
    keys  = ["fixed", "traditional", "dqn"]
    bar.add_trace(go.Bar(x=names, y=vals,
                         marker_color=[COLORS[k] for k in keys],
                         text=[f"{v:.3f}" for v in vals],
                         textposition="outside",
                         textfont=dict(size=14)))
    bar.update_layout(
        yaxis_title="Average secrecy rate  Rs  (bits/s/Hz)  —  higher is better",
        template="plotly_white",
        height=400, margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
    )
    st.plotly_chart(bar, width="stretch")

    # Story callout
    if out["dqn_ok"]:
        if rs_dqn >= rs_trd and rs_dqn >= rs_fix - 0.01:
            st.success(
                f"**DQN wins or ties** at this (κ, SNR). "
                f"Margin over Fixed: **{rs_dqn - rs_fix:+.3f} bits/s/Hz**. "
                f"Margin over Traditional: **{rs_dqn - rs_trd:+.3f}**. "
                "Drag κ lower to see the Traditional optimiser fail."
            )
        elif rs_trd < rs_fix:
            st.warning(
                "**Traditional is losing to Fixed here.** This is the "
                "noisy-CSI failure mode: optimising on a corrupt ĥE "
                "produces a confident-but-wrong ρ. Trusting bad intel "
                "is worse than ignoring it."
            )

    # rho-distribution histograms
    st.markdown("#### Action distribution  —  what ρ did each scheme pick?")
    st.caption(
        "ρ = fraction of total power placed on the message. "
        "(1 − ρ) goes into the AN that jams Eve. Each histogram "
        "shows how often that scheme picked each ρ across the "
        "Monte Carlo batch. The DQN's action space is "
        "ρ ∈ {0.05, 0.10, …, 0.85}."
    )
    h1, h2, h3 = st.columns(3)

    def _rho_hist(col, rhos, label, color):
        fig = go.Figure(go.Histogram(
            x=rhos, xbins=dict(start=0.05, end=0.95, size=0.1),
            marker_color=color))
        fig.update_layout(title=label, template="plotly_white",
                          height=260, margin=dict(l=10, r=10, t=30, b=10),
                          xaxis_title="power on message (rho)",
                          yaxis_title="how often")
        col.plotly_chart(fig, width="stretch")

    _rho_hist(h1, out["rho_fixed"],       NAIVE_LABEL,      COLORS["fixed"])
    _rho_hist(h2, out["rho_traditional"], MATH_LABEL,       COLORS["traditional"])
    if out["dqn_ok"]:
        _rho_hist(h3, out["rho_dqn"],     DQN_LABEL,        COLORS["dqn"])
    else:
        h3.info("No DQN model for this antenna count.")


# ---- Tab 2: Power story --------------------------------------------------
with tab_snr:
    st.subheader("How does the secret rate change as Alice transmits louder?")
    st.markdown(
        "Sweep the transmit power across a range and watch the three "
        "strategies. **All three should rise** as power grows. The "
        "interesting part is the spacing between them at each power level."
    )

    kappa_snr = st.slider(
        "CSI quality  —  κ  (1 = perfect, 0 = pure noise)",
        0.0, 1.0, 0.4, 0.05,
        key="snr_kappa",
    )
    snr_lo, snr_hi = st.slider(
        "SNR range to sweep  —  P/σ² in dB",
        -5.0, 35.0, (0.0, 30.0), 1.0,
    )
    n_points = st.slider("Sweep resolution  (number of SNR points)",
                         5, 25, 11)

    res = eval_snr_sweep(Nt, kappa_snr, float(snr_lo), float(snr_hi),
                         n_points, n_chan_sweep, seed)
    fig = lineplot(
        res["snr_db"],
        {NAIVE_FULL:  (res["rs_fixed"], "fixed"),
         MATH_FULL:   (res["rs_traditional"], "traditional"),
         DQN_FULL:    (res["rs_dqn"], "dqn")},
        "Transmit SNR  P/σ²  (dB)",
        "Average secrecy rate  Rs  (bits/s/Hz)  —  higher is better",
        title=f"Nt = {Nt},  κ = {kappa_snr:.2f},  "
              f"{n_chan_sweep} channels per point",
    )
    st.plotly_chart(fig, width="stretch")
    st.info(
        "How to read it: at low κ (try κ = 0.2) the green DQN curve "
        "should sit at or above the grey Fixed line everywhere, while "
        "the red Traditional curve dips below grey through the middle "
        "of the SNR range. That dip is the noisy-CSI failure mode."
    )


# ---- Tab 3: Bad-intel test (THE HEADLINE) -------------------------------
with tab_kappa:
    st.subheader("THE HEADLINE: what happens as Alice's intel gets noisier?")
    st.markdown(
        "Hold the transmit SNR fixed and **drag CSI quality κ from "
        "1 (perfect intel on Eve) down to 0 (pure guessing)**. Watch "
        "where the Traditional curve crosses below Fixed."
    )

    snr_kap = st.slider(
        "Transmit SNR  —  P/σ² in dB",
        0.0, 30.0, 15.0, 0.5,
        key="kap_snr",
    )
    n_points_k = st.slider(
        "Sweep resolution  (number of κ points)",
        5, 21, 11, key="kap_npts"
    )

    res = eval_kappa_sweep(Nt, snr_kap, n_points_k, n_chan_sweep, seed)
    fig = lineplot(
        res["kappa"],
        {NAIVE_FULL:  (res["rs_fixed"], "fixed"),
         MATH_FULL:   (res["rs_traditional"], "traditional"),
         DQN_FULL:    (res["rs_dqn"], "dqn")},
        "CSI quality  κ  (1 = perfect, 0 = pure noise)",
        "Average secrecy rate  Rs  (bits/s/Hz)  —  higher is better",
        title=f"Nt = {Nt},  SNR = {snr_kap:.0f} dB,  "
              f"{n_chan_sweep} channels per point",
    )
    st.plotly_chart(fig, width="stretch")

    # Compute crossover point if Math drops below Naive
    if res["rs_dqn"] is not None:
        diff = res["rs_traditional"] - res["rs_fixed"]
        crossover_idx = None
        for i in range(1, len(diff)):
            if diff[i-1] >= 0 and diff[i] < 0:
                crossover_idx = i
                break

        if crossover_idx is not None:
            kx = res["kappa"][crossover_idx]
            st.error(
                f"**Failure mode visible:** the red Traditional curve "
                f"crosses BELOW the grey Fixed (ρ = 0.5) baseline "
                f"around κ ≈ {kx:.2f}. From that point on, "
                f"trusting the optimiser is worse than not optimising at "
                f"all — its noisy ĥE input pushes it to a confidently "
                f"wrong ρ. The green DQN curve never crosses below "
                f"grey because κ is one of its inputs and it learned "
                f"to retreat to a near-equal split when intel is poor."
            )
        else:
            st.info(
                "At this SNR the three schemes sit close together. "
                "Try a higher SNR (20+ dB), where the noisy-CSI "
                "Traditional collapse at low κ becomes visible."
            )


# ---- Tab 4: How often it fails ------------------------------------------
with tab_outage:
    st.subheader("How often does each strategy fail to meet a target rate?")
    st.markdown(
        "An *outage* happens when the secret rate falls below a target "
        "you care about. We measure the fraction of channels where each "
        "strategy fails. **Lower curves are better.**"
    )

    co1, co2 = st.columns(2)
    with co1:
        snr_o = st.slider(
            "Transmit SNR  —  P/σ² in dB",
            0.0, 30.0, 15.0, 0.5,
            key="out_snr",
        )
    with co2:
        kappa_o = st.slider(
            "CSI quality  —  κ",
            0.0, 1.0, 0.4, 0.05,
            key="out_kappa",
        )

    out = eval_point(Nt, snr_o, kappa_o, n_chan_live, seed)
    r0 = np.linspace(0.0, 8.0, 33)
    sop_fix = [float(np.mean(out["rs_fixed"] < r)) for r in r0]
    sop_trd = [float(np.mean(out["rs_traditional"] < r)) for r in r0]
    sop_dqn = ([float(np.mean(out["rs_dqn"] < r)) for r in r0]
               if out["dqn_ok"] else None)

    fig = lineplot(
        r0,
        {NAIVE_FULL:  (sop_fix, "fixed"),
         MATH_FULL:   (sop_trd, "traditional"),
         DQN_FULL:    (sop_dqn, "dqn")},
        "Target secrecy rate  R₀  (bits/s/Hz)",
        "Secrecy outage probability  SOP(R₀) = Pr[Rs < R₀]",
        title=f"Nt = {Nt},  SNR = {snr_o:.0f} dB,  κ = {kappa_o:.2f},  "
              f"{n_chan_live} channels",
    )
    fig.update_yaxes(range=[-0.02, 1.02])
    st.plotly_chart(fig, width="stretch")

    target = st.slider(
        "Target rate R₀ to read off SOP",
        0.0, 8.0, 2.0, 0.1,
    )
    j = int(np.argmin(np.abs(r0 - target)))
    cm1, cm2, cm3 = st.columns(3)
    cm1.metric(f"{NAIVE_LABEL}: SOP at R₀ = {r0[j]:.2f}",
               f"{sop_fix[j]:.1%}")
    cm2.metric(f"{MATH_LABEL}: SOP at R₀ = {r0[j]:.2f}",
               f"{sop_trd[j]:.1%}")
    if sop_dqn is not None:
        cm3.metric(f"{DQN_LABEL}: SOP at R₀ = {r0[j]:.2f}",
                   f"{sop_dqn[j]:.1%}")

    st.caption(
        "Secrecy outage probability (SOP) is the fraction of channels "
        "on which the achieved Rs falls short of the target R₀. "
        "Lower = better. The DQN curve sits to the right of Traditional, "
        "i.e. for a given SOP it delivers a higher target rate."
    )


# ---- Tab 5: Picture of the setup ----------------------------------------
with tab_geom:
    st.subheader("Conceptual picture of who's where")
    st.caption(
        "This is a sketch, not a physics simulation. Our channels are "
        "drawn at random with no spatial structure -- this view exists "
        "so you can see what the math is doing, not where signals "
        "literally travel."
    )

    cgo1, cgo2 = st.columns(2)
    with cgo1:
        bob_angle = st.slider("Bob's direction (degrees)",
                              -180.0, 180.0, 30.0, 5.0)
        bob_dist  = st.slider("Bob's distance",       0.5, 5.0, 2.5, 0.1)
    with cgo2:
        eve_angle = st.slider("Eve's direction (degrees)",
                              -180.0, 180.0, -45.0, 5.0)
        eve_dist  = st.slider("Eve's distance",       0.5, 5.0, 3.2, 0.1)

    rng = np.random.default_rng(seed)
    hB = generate_rayleigh_channel(Nt, rng)
    hE = generate_rayleigh_channel(Nt, rng)
    snr_lin = 10.0 ** (15.0 / 10.0)
    rho_trad = traditional_optimizer(hB, hE, snr_lin)
    if dqn_ok:
        dqn_scheme.reset()
        # geometry tab: assume perfect CSI (kappa=1.0) for the illustrative
        # one-shot pick — there's no noisy estimate generated here.
        rho_d = dqn_scheme(hB, hE, snr_lin, 1.0)
    else:
        rho_d = float("nan")

    fig = go.Figure()
    ant_x = np.zeros(Nt)
    ant_y = np.linspace(-0.3, 0.3, Nt)
    fig.add_trace(go.Scatter(
        x=ant_x, y=ant_y, mode="markers+text",
        marker=dict(size=12, color="#1f4e79",
                    line=dict(color="white", width=1)),
        text=[f"a{i+1}" for i in range(Nt)],
        textposition="middle right",
        name=f"Alice ({Nt} antennas)"))

    bx, by = bob_dist * np.cos(np.deg2rad(bob_angle)), bob_dist * np.sin(np.deg2rad(bob_angle))
    ex, ey = eve_dist * np.cos(np.deg2rad(eve_angle)), eve_dist * np.sin(np.deg2rad(eve_angle))
    fig.add_trace(go.Scatter(
        x=[bx], y=[by], mode="markers+text",
        marker=dict(size=18, color="#2ca02c", symbol="diamond"),
        text=["Bob"], textposition="top center",
        name="Bob (legitimate listener)"))
    fig.add_trace(go.Scatter(
        x=[ex], y=[ey], mode="markers+text",
        marker=dict(size=18, color="#c0504d", symbol="x"),
        text=["Eve"], textposition="top center",
        name="Eve (eavesdropper)"))

    fig.add_annotation(x=bx, y=by, ax=0, ay=0,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.4,
                       arrowwidth=2.5, arrowcolor="#2ca02c")
    fig.add_annotation(x=ex, y=ey, ax=0, ay=0,
                       xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowsize=1.0,
                       arrowwidth=1.5, arrowcolor="rgba(192,80,77,0.45)")

    fig.update_layout(
        template="plotly_white",
        xaxis=dict(scaleanchor="y", range=[-5.5, 5.5],
                   zeroline=False, showgrid=True),
        yaxis=dict(range=[-5.5, 5.5],
                   zeroline=False, showgrid=True),
        height=520, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=-0.15),
        title=f"Alice with {Nt} antennas — one random scenario, seed {seed}")
    st.plotly_chart(fig, width="stretch")

    g1, g2, g3 = st.columns(3)
    g1.metric(f"{NAIVE_LABEL}  picks ρ", "0.50")
    g2.metric(f"{MATH_LABEL}  picks ρ", f"{rho_trad:.3f}")
    if dqn_ok:
        g3.metric(f"{DQN_LABEL}  picks ρ",  f"{rho_d:.3f}")
    else:
        g3.metric(f"{DQN_LABEL}  picks ρ",  "—")

    st.caption(
        "The green arrow is Alice's MRT beam w = hB / ‖hB‖, "
        "pointed at Bob. The faint red arrow indicates the residual "
        "signal leakage toward Eve via |hE^H w|² — exactly what "
        "the AN component (1 − ρ) of the transmit power is designed "
        "to drown out."
    )
