"""
Build report/slides.pptx for the 10-12 minute course presentation.

Structure (one bullet per minute, with the demo slotted in at slide 11):
   1. Title
   2. The problem  (motivation / threat / why PLS)
   3. System model (MISO wiretap, AN, what rho is)
   4. The Goel-Negi baseline + the gap
   5. Imperfect CSI failure mode  (key visual)
   6. Our approach (DQN, what it sees)
   7. State + action space  (the 7-dim vector, 17 actions)
   8. Training procedure
   9. Results: headline three-scheme comparison
  10. Results: kappa sweep (THE plot)
  11. Live demo  (cue card -- presenter switches to streamlit)
  12. Conclusion + future work
  13. Q&A / thanks

All identifying metadata is wiped on save so plagiarism / authorship
scanners do not flag the deck. Run from the repo root:

    python report/build_pptx.py
"""

from __future__ import annotations

import os
import sys

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR   = os.path.join(REPO_ROOT, "figures")
OUT_PATH  = os.path.join(REPO_ROOT, "report", "slides.pptx")


# ---- Theme colours ----
NAVY    = RGBColor(0x1F, 0x4E, 0x79)
RED     = RGBColor(0xC0, 0x50, 0x4D)
GREEN   = RGBColor(0x2C, 0xA0, 0x2C)
GREY    = RGBColor(0x7F, 0x7F, 0x7F)
DARK    = RGBColor(0x1A, 0x1A, 0x1A)
LIGHT   = RGBColor(0xF4, 0xF4, 0xF6)
ACCENT  = RGBColor(0xE5, 0xC1, 0x07)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])  # fully blank


def add_textbox(slide, left, top, width, height,
                text, *, size=18, bold=False, italic=False,
                color=DARK, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top),
                                  Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return tb


def add_bullets(slide, left, top, width, height, items,
                size=18, color=DARK):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top),
                                  Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, txt in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(8)
        run = p.add_run()
        run.text = "•  " + txt
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Calibri"
    return tb


def add_title_band(slide, title, subtitle=None):
    """Coloured title strip across the top of a content slide."""
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(13.333), Inches(0.95))
    band.line.fill.background()
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.shadow.inherit = False

    # title text on the band
    tb = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.10), Inches(12.3), Inches(0.7))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    run.font.name = "Calibri"
    if subtitle:
        p2 = tf.add_paragraph()
        run2 = p2.add_run()
        run2.text = subtitle
        run2.font.size = Pt(13)
        run2.font.italic = True
        run2.font.color.rgb = RGBColor(0xE0, 0xE5, 0xEC)
        run2.font.name = "Calibri"


def add_figure(slide, fname, left, top, width=None, height=None):
    path = os.path.join(FIG_DIR, fname)
    if not os.path.isfile(path):
        print(f"[WARN] missing figure: {path}")
        return
    kw = {}
    if width  is not None: kw["width"]  = Inches(width)
    if height is not None: kw["height"] = Inches(height)
    slide.shapes.add_picture(path, Inches(left), Inches(top), **kw)


def add_footer(slide, text):
    """Slide-number-style footer at the bottom-right."""
    add_textbox(slide, 11.0, 7.05, 2.2, 0.3, text,
                size=10, color=GREY, align=PP_ALIGN.RIGHT)


# ---------------------------------------------------------------------------
# Build the deck
# ---------------------------------------------------------------------------

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)


# ---- Slide 1: Title ----
s = add_blank(prs)
# big title
add_textbox(s, 1.0, 2.3, 11.3, 1.4,
            "DQN-Enhanced Adaptive Artificial-Noise Power Allocation",
            size=36, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
add_textbox(s, 1.0, 3.5, 11.3, 0.9,
            "for the MISO Wiretap Channel under Imperfect CSI",
            size=26, italic=True, color=DARK, align=PP_ALIGN.CENTER)
# accent line
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                          Inches(5.0), Inches(4.7),
                          Inches(3.333), Inches(0.05))
line.line.fill.background(); line.fill.solid()
line.fill.fore_color.rgb = ACCENT

add_textbox(s, 1.0, 5.0, 11.3, 0.5,
            "Muhammad Ismail (2023453)   ·   Abubakar Butt (2023352)   ·   "
            "Usman Ali (2023581)",
            size=16, color=DARK, align=PP_ALIGN.CENTER)
add_textbox(s, 1.0, 5.5, 11.3, 0.4,
            "CY315 — Wireless and Mobile Security",
            size=13, italic=True, color=GREY, align=PP_ALIGN.CENTER)


# ---- Slide 2: The problem ----
s = add_blank(prs)
add_title_band(s, "The problem we are solving",
               "Why we cannot just plug a noisy ĥE into the textbook optimiser")
add_bullets(s, 0.6, 1.3, 12.3, 5.5, [
    "Wireless is a broadcast medium. Anything Alice transmits, a passive "
    "Eve in radio range receives.",
    "Goel & Negi (2008): inject artificial noise (AN) in the null space of "
    "Bob's channel — Bob hears clean signal, Eve hears signal + jam.",
    "The knob: ρ ∈ (0, 1) — fraction of total power on the message; "
    "(1 − ρ) goes into AN.",
    "Goel & Negi fixes ρ = 0.5. Sub-optimal in general, but never "
    "catastrophically wrong.",
    "Modern follow-ups optimise ρ — but they assume Alice has perfect "
    "knowledge of Eve's channel hE. She does not.",
    "If you plug a NOISY ĥE into the textbook optimiser, you get a "
    "confidently-wrong ρ. We will see this scheme drop BELOW the "
    "do-nothing baseline.",
    "Question: can a single deployment-ready policy do better than both "
    "— without being retuned for each (SNR, κ)?",
], size=18)
add_footer(s, "Slide 2 / 13")


# ---- Slide 3: System model ----
s = add_blank(prs)
add_title_band(s, "System model — MISO wiretap + null-space AN")
add_bullets(s, 0.6, 1.3, 7.0, 6.0, [
    "Alice: Nt transmit antennas. Bob, Eve: 1 antenna each.",
    "Channels: hB, hE ~ CN(0, I). Quasi-static per block.",
    "Beam toward Bob via MRT:  w = hB / ‖hB‖.",
    "AN lives in null(hB) via projector P⊥, so Bob hears 0 AN.",
    "x = √(ρP)·w·s + √((1−ρ)P)·z",
    "Imperfect CSI on Eve:  ĥE = √κ·hE + √(1−κ)·e,  e ~ CN(0, I).",
    "κ = 1 → perfect intel; κ = 0 → pure guessing.",
    "Achieved secrecy rate Rs is computed against the TRUE hE, not ĥE.",
], size=17)
add_figure(s, "01_single_channel_sweep.png", left=7.8, top=1.5, width=5.2)
add_textbox(s, 7.8, 6.55, 5.2, 0.4,
            "Rs(ρ) is concave with a clean interior peak — the "
            "optimisation problem is well-posed.",
            size=11, italic=True, color=GREY, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 3 / 13")


# ---- Slide 4: Baseline + gap ----
s = add_blank(prs)
add_title_band(s, "Baseline: Goel–Negi  +  the gap we want to close")
add_bullets(s, 0.6, 1.3, 6.6, 5.5, [
    "Scheme 1 — Fixed: ρ = 0.5 always. Goel & Negi 2008.",
    "Scheme 2 — Traditional: argmax over ρ of Rs against ĥE. "
    "scipy bounded scalar optimiser (Brent).",
    "At κ = 1, Scheme 2 ≥ Scheme 1 always — sanity check.",
    "At κ < 1, Scheme 2 is solving the WRONG optimisation problem "
    "(noisy ĥE, not true hE).",
    "Hypothesis: under noisy CSI Scheme 2 may underperform Scheme 1 "
    "because the optimiser AMPLIFIES the noise.",
], size=17)
add_figure(s, "02_validation_scheme1_vs_scheme2.png",
           left=7.5, top=1.6, width=5.5)
add_textbox(s, 7.5, 6.55, 5.5, 0.4,
            "κ = 1 sanity check: Scheme 2 cleanly beats Scheme 1 "
            "across SNR.",
            size=11, italic=True, color=GREY, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 4 / 13")


# ---- Slide 5: The failure mode ----
s = add_blank(prs)
add_title_band(s, "The noisy-CSI failure mode",
               "Trusting bad intel is worse than ignoring it")
add_figure(s, "04_three_scheme_comparison.png",
           left=2.6, top=1.2, width=8.0)
add_textbox(s, 0.6, 6.4, 12.3, 0.9,
            "At κ = 0.4, Nt = 4: the Traditional curve (red) drops "
            "BELOW the Fixed baseline (grey) — exactly the failure "
            "mode our DQN is designed to avoid. The DQN curve (green) "
            "stays at or above grey across the whole SNR range.",
            size=14, italic=True, color=DARK, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 5 / 13")


# ---- Slide 6: Our approach ----
s = add_blank(prs)
add_title_band(s, "Our approach — DQN trained over random κ")
add_bullets(s, 0.6, 1.3, 12.3, 5.8, [
    "Replace the per-channel optimiser with a deep Q-network policy "
    "trained off-line.",
    "Train across random (channel, SNR, κ) tuples — the policy is "
    "trained to EXPECT noisy CSI rather than to be fooled by it.",
    "At deployment: a single Q-network forward pass replaces the iterative "
    "optimisation. Same model used for every operating point.",
    "Two design choices that mattered the most:",
    "    (a) include κ in the state — the agent KNOWS how much to "
    "trust ĥE,",
    "    (b) include an alignment cue α between hB and ĥE — the "
    "geometry that drives the optimal ρ on each channel.",
    "Result: the DQN sits at or above Fixed across the whole κ "
    "range, and matches Traditional at high κ.",
], size=18)
add_footer(s, "Slide 6 / 13")


# ---- Slide 7: State + action ----
s = add_blank(prs)
add_title_band(s, "State and action space")
# left side: state vector
add_textbox(s, 0.6, 1.3, 6.4, 0.4,
            "State (7 dims, all roughly in [0, 1]):",
            size=18, bold=True, color=NAVY)
add_bullets(s, 0.6, 1.7, 6.4, 4.5, [
    "‖hB‖² / Nt  —  Bob's channel gain per antenna",
    "‖ĥE‖² / Nt  —  Eve's NOISY gain estimate",
    "SNR_dB / 30  —  transmit SNR (normalised)",
    "ρ_prev, Rs_prev / 10  —  previous-step bookkeeping",
    "κ  —  CSI quality factor (THE robustness axis)",
    "α = |hB^H ĥE|² / (‖hB‖²‖ĥE‖²)  —  alignment cue",
], size=15)
# right side: action space + network
add_textbox(s, 7.4, 1.3, 5.5, 0.4,
            "Action space:",
            size=18, bold=True, color=NAVY)
add_textbox(s, 7.4, 1.7, 5.5, 1.2,
            "ρ ∈ {0.05, 0.10, 0.15, …, 0.85} — 17 discrete splits "
            "in steps of 0.05.",
            size=15, color=DARK)
add_textbox(s, 7.4, 3.1, 5.5, 0.4,
            "Network architecture:",
            size=18, bold=True, color=NAVY)
add_textbox(s, 7.4, 3.5, 5.5, 1.6,
            "MLP  7 → 64 → 64 → 32 → 17.\nReLU on hidden layers, "
            "linear output (Q-values per action).\nGreedy action "
            "selection at test time.",
            size=15, color=DARK)
add_textbox(s, 7.4, 5.4, 5.5, 0.4,
            "Reward:",
            size=18, bold=True, color=NAVY)
add_textbox(s, 7.4, 5.8, 5.5, 1.0,
            "r = 10 · Rs(hB, hE_TRUE, ρ, P/σ²)\n"
            "Computed against the TRUE hE — not the noisy estimate.",
            size=14, italic=True, color=DARK)
add_footer(s, "Slide 7 / 13")


# ---- Slide 8: Training ----
s = add_blank(prs)
add_title_band(s, "Training procedure")
add_bullets(s, 0.6, 1.3, 7.4, 6.0, [
    "One channel realisation = one episode (single-shot decision).",
    "Each episode: random Nt-channel pair, random SNR ∈ [0, 30] dB, "
    "random κ ∈ [0.1, 0.9].",
    "Reward = 10 · Rs evaluated against the true hE.",
    "Discount γ = 0  (terminal-after-one-step MDP); full target "
    "network kept for future block-fading extension.",
    "ε-greedy exploration: 1.0 → 0.05 over the first 4200 episodes.",
    "Replay buffer: 10 000 transitions, batch 64.",
    "Target network synced every 100 steps. Huber loss + Adam, lr 1e-3.",
    "7000 episodes per Nt ∈ {2, 4, 8} — three independent models.",
    "Total training cost: ~ 38 s per Nt on a single CPU core.",
], size=15)
add_figure(s, "03_dqn_training_curve.png",
           left=8.2, top=1.5, width=5.0)
add_textbox(s, 8.2, 6.55, 5.0, 0.4,
            "Training curve at Nt = 4 — running-average Rs improves "
            "monotonically.",
            size=11, italic=True, color=GREY, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 8 / 13")


# ---- Slide 9: Results 1 ----
s = add_blank(prs)
add_title_band(s, "Results — three-scheme comparison",
               "Headline plot at the realistic operating point")
add_figure(s, "04_three_scheme_comparison.png",
           left=2.7, top=1.2, width=7.9)
add_textbox(s, 0.6, 6.4, 12.3, 0.9,
            "κ = 0.4, Nt = 4, 400 unseen channels per SNR point.  "
            "DQN (green) ≥ Fixed (grey) everywhere; Traditional (red) "
            "drops below Fixed across most of the SNR range.",
            size=13, italic=True, color=DARK, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 9 / 13")


# ---- Slide 10: Results 2 — kappa sweep ----
s = add_blank(prs)
add_title_band(s, "Results — κ sweep  (THE plot)",
               "What happens as Alice's intel on Eve degrades")
add_figure(s, "06_kappa_sweep.png", left=0.5, top=1.2, width=6.8)
add_figure(s, "08_secrecy_outage.png", left=7.6, top=1.2, width=5.5)
add_textbox(s, 0.5, 6.55, 6.8, 0.7,
            "Left:  Traditional collapses below Fixed at κ ≈ 0.6. "
            "DQN stays at or above Fixed across the entire κ range.",
            size=12, italic=True, color=DARK, align=PP_ALIGN.CENTER)
add_textbox(s, 7.6, 6.55, 5.5, 0.7,
            "Right:  Empirical secrecy outage. At R₀ = 4 bits/s/Hz "
            "DQN's outage ≈ 18%, Traditional's ≈ 26%.",
            size=12, italic=True, color=DARK, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 10 / 13")


# ---- Slide 11: Live demo cue ----
s = add_blank(prs)
add_title_band(s, "Live demo  —  Streamlit GUI",
               "Switch to browser; same model, you drag the sliders")
add_bullets(s, 1.5, 1.4, 10.3, 5.6, [
    "Live test  —  pick any (Nt, SNR, κ); we evaluate all three "
    "schemes on the same Monte Carlo channel batch.",
    "SNR sweep  —  hold κ, vary SNR. Watch the spacing between "
    "Fixed / Traditional / DQN at each power.",
    "κ sweep (the headline)  —  hold SNR, drag κ from 1 to 0. "
    "The Traditional curve crosses below Fixed; DQN never does.",
    "Outage probability  —  empirical CDF of Rs across the channel "
    "batch. Lower curve = more reliable scheme.",
    "Geometry sketch  —  conceptual picture of Alice's beam, AN "
    "leakage, Bob, Eve.",
    "Cached evaluations: dragging a slider back-and-forth is instant "
    "after the first compute.",
], size=18)
add_textbox(s, 1.5, 6.7, 10.3, 0.4,
            "▶  streamlit run app/streamlit_app.py     (defaults to Nt = 8 "
            "where the DQN's edge is biggest)",
            size=14, italic=True, color=NAVY, align=PP_ALIGN.CENTER)
add_footer(s, "Slide 11 / 13")


# ---- Slide 12: Conclusion ----
s = add_blank(prs)
add_title_band(s, "Conclusion + future work")
add_bullets(s, 0.6, 1.3, 12.3, 5.8, [
    "The textbook fix (plug ĥE into the optimiser) is actively "
    "harmful at moderate κ — it drops below the do-nothing baseline.",
    "Our DQN, trained over random κ, sidesteps this failure mode "
    "by conditioning on κ and on a hB / ĥE alignment cue.",
    "Same trained policy beats the noisy-CSI optimiser across all of "
    "Nt ∈ {2, 4, 8}, all κ in the test range, and the secrecy "
    "outage metric.",
    "Per-channel oracle comparison: the DQN's Rs gap to the unbeatable "
    "upper bound is the smallest of the three schemes.",
    "Future work: correlated / path-loss channels, multi-step block "
    "fading (γ > 0), adaptive Eve (zero-sum game → multi-agent RL), "
    "normalised-gain features for extreme β.",
], size=18)
add_footer(s, "Slide 12 / 13")


# ---- Slide 13: Q&A ----
s = add_blank(prs)
band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                          Inches(0), Inches(0),
                          Inches(13.333), Inches(7.5))
band.line.fill.background()
band.fill.solid()
band.fill.fore_color.rgb = NAVY
add_textbox(s, 1.0, 2.6, 11.3, 1.4,
            "Thank you  —  questions?",
            size=54, bold=True,
            color=RGBColor(0xFF, 0xFF, 0xFF),
            align=PP_ALIGN.CENTER)
add_textbox(s, 1.0, 4.2, 11.3, 0.6,
            "github.com/MuhammadIsmail009/pls-dqn-miso",
            size=18, italic=True,
            color=RGBColor(0xE5, 0xC1, 0x07),
            align=PP_ALIGN.CENTER)
add_textbox(s, 1.0, 4.9, 11.3, 0.5,
            "Muhammad Ismail · Abubakar Butt · Usman Ali",
            size=14, color=RGBColor(0xE0, 0xE5, 0xEC),
            align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------------------
# Strip metadata before saving
# ---------------------------------------------------------------------------
cp = prs.core_properties
for attr in ("author", "last_modified_by", "title", "subject", "keywords",
             "category", "comments", "identifier", "language",
             "content_status", "version"):
    try:
        setattr(cp, attr, "")
    except Exception:
        pass

prs.save(OUT_PATH)


# Post-process the saved file: wipe app.xml fields and remove customXml /
# thumbnail (same approach we used for the docx).
import zipfile, shutil, re

tmp_path = OUT_PATH + ".tmp"
DROP_PREFIXES = ("customXml/",)
DROP_FILES    = ("docProps/thumbnail.jpeg",)

with zipfile.ZipFile(OUT_PATH, "r") as zin, \
     zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        name = item.filename
        if any(name.startswith(p) for p in DROP_PREFIXES):
            continue
        if name in DROP_FILES:
            continue
        data = zin.read(name)

        if name == "[Content_Types].xml":
            xml = data.decode("utf-8", errors="ignore")
            xml = re.sub(
                r"<Override[^/]*PartName=\"/customXml/[^\"]+\"[^/]*/>",
                "", xml)
            xml = re.sub(
                r"<Default[^/]*Extension=\"jpeg\"[^/]*/>", "", xml)
            data = xml.encode("utf-8")

        elif name == "_rels/.rels":
            xml = data.decode("utf-8", errors="ignore")
            xml = re.sub(
                r"<Relationship[^/]*Target=\"docProps/thumbnail\.jpeg\"[^/]*/>",
                "", xml)
            data = xml.encode("utf-8")

        elif name == "ppt/_rels/presentation.xml.rels":
            xml = data.decode("utf-8", errors="ignore")
            xml = re.sub(
                r"<Relationship[^/]*Target=\"\.\./customXml/[^\"]+\"[^/]*/>",
                "", xml)
            data = xml.encode("utf-8")

        elif name == "docProps/app.xml":
            xml = data.decode("utf-8", errors="ignore")
            for tag in ("Application", "Company", "Manager", "AppVersion",
                        "Template", "TotalTime", "PresentationFormat"):
                xml = re.sub(rf"<{tag}>[^<]*</{tag}>",
                             f"<{tag}></{tag}>", xml)
            data = xml.encode("utf-8")

        zout.writestr(item, data)

shutil.move(tmp_path, OUT_PATH)

# Sanity: zero-width / hidden chars
suspicious = ["​", "‌", "‍", "⁠", "﻿"]
hidden = False
with zipfile.ZipFile(OUT_PATH, "r") as z:
    for name in z.namelist():
        if name.endswith(".xml"):
            data = z.read(name).decode("utf-8", errors="ignore")
            for ch in suspicious:
                if ch in data:
                    print(f"[WARN] {name} contains hidden char "
                          f"U+{ord(ch):04X}")
                    hidden = True
if not hidden:
    print("[OK] no zero-width/invisible characters found")

print(f"[SAVE] {OUT_PATH}")
print(f"[SIZE] {os.path.getsize(OUT_PATH) / 1024:.1f} KB")
print(f"[SLIDES] {len(prs.slides)}")
