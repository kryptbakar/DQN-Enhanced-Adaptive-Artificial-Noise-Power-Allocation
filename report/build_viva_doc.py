"""
Build report/viva_prep.docx -- a study companion for the project viva.

Audience: the three of us walking into the viva. Style: plain language,
short sentences, lots of 'what-if' scenarios, every symbol unpacked,
and a Q&A bank covering the questions sir is most likely to ask.

This is intentionally NOT a paper. It is a memory aid. If something
appears in the report and you'd want to be reminded of it before the
viva, it should be here too.

Run from the repo root:
    python report/build_viva_doc.py
"""

from __future__ import annotations

import os
import re
import zipfile
import shutil

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH  = os.path.join(REPO_ROOT, "report", "viva_prep.docx")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_h1(doc, text):
    p = doc.add_heading(text, level=1)
    return p


def add_h2(doc, text):
    return doc.add_heading(text, level=2)


def add_h3(doc, text):
    return doc.add_heading(text, level=3)


def add_para(doc, text, *, italic=False, bold=False, size=11):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.italic = italic
    run.bold = bold
    return p


def add_bullets(doc, items, *, indent=0.0):
    for txt in items:
        p = doc.add_paragraph(style="List Bullet")
        if indent:
            p.paragraph_format.left_indent = Inches(0.25 + indent * 0.25)
        run = p.add_run(txt)
        run.font.size = Pt(11)


def add_qa(doc, question, answer):
    """Add one viva-style Q&A entry."""
    p = doc.add_paragraph()
    q_run = p.add_run("Q.  ")
    q_run.bold = True
    q_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    q_run.font.size = Pt(11)
    q_text = p.add_run(question)
    q_text.bold = True
    q_text.font.size = Pt(11)

    p2 = doc.add_paragraph()
    a_run = p2.add_run("A.  ")
    a_run.bold = True
    a_run.font.color.rgb = RGBColor(0x2C, 0xA0, 0x2C)
    a_run.font.size = Pt(11)
    a_text = p2.add_run(answer)
    a_text.font.size = Pt(11)
    p2.paragraph_format.space_after = Pt(10)


# ---------------------------------------------------------------------------
# Build the document
# ---------------------------------------------------------------------------

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)


# --- Title page ------------------------------------------------------
title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = title_p.add_run("Viva Preparation Notes")
tr.bold = True
tr.font.size = Pt(22)
tr.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

sub_p = doc.add_paragraph()
sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sub_p.add_run(
    "DQN-Enhanced Adaptive Artificial-Noise Power Allocation\n"
    "for the MISO Wiretap Channel under Imperfect CSI"
)
sr.italic = True
sr.font.size = Pt(13)

team_p = doc.add_paragraph()
team_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
team_p.add_run(
    "Muhammad Ismail (2023453)   ·   Abubakar Butt (2023352)   ·   "
    "Usman Ali (2023581)\nCY315 — Wireless and Mobile Security"
).font.size = Pt(11)

doc.add_paragraph()  # spacer


# --- 0. The 30-second pitch ------------------------------------------
add_h1(doc, "0.  The 30-second pitch")

add_para(doc,
    "If sir asks you to summarise the project in one breath, this is "
    "the line:")
quote = doc.add_paragraph()
quote.paragraph_format.left_indent = Inches(0.4)
quote.paragraph_format.right_indent = Inches(0.4)
qr = quote.add_run(
    "We trained a small neural network that decides how much of "
    "Alice's transmit power should go to the message versus the "
    "jamming signal, and it does that smartly even when Alice's "
    "knowledge of the eavesdropper's channel is noisy."
)
qr.italic = True
qr.font.size = Pt(12)

add_para(doc,
    "Why does it matter?  Because the textbook way to make that "
    "decision (just plug the noisy estimate into the optimiser) "
    "actually performs WORSE than doing nothing once the intel is "
    "bad enough.  Our network avoids that trap.")


# --- 1. The big picture ----------------------------------------------
add_h1(doc, "1.  The big picture — what is happening, in plain words")

add_para(doc,
    "Imagine three people in a room.  Alice wants to whisper a secret "
    "to Bob.  Eve is sitting nearby trying to listen in.  Alice has a "
    "trick: she can make multiple sounds at once because she has "
    "several speakers (antennas).  She uses one speaker to whisper "
    "the message at Bob, and the other speakers to play loud noise "
    "aimed away from Bob and toward Eve.  Bob hears the whisper "
    "clearly because the noise was sent in directions that cancel "
    "at his ear.  Eve hears whisper + noise mixed together, and "
    "can't tell what was said.")

add_para(doc, "That trick is called artificial noise (AN) injection. "
              "The catch: how loud should the whisper be vs the noise?")

add_bullets(doc, [
    "Too much whisper, too little noise → Eve can hear.",
    "Too much noise, too little whisper → Bob can't hear either.",
    "There's a sweet spot in the middle.  We call that ρ "
    "(the fraction of total power on the whisper).",
])

add_para(doc,
    "Finding the sweet spot is easy when Alice knows exactly where "
    "Eve is — she can compute the optimum.  But in practice she only "
    "has a noisy guess about Eve.  And it turns out that running the "
    "optimiser on a noisy guess is worse than just splitting power "
    "50/50 and not optimising at all.  That's the failure mode our "
    "AI agent is designed to avoid.")


# --- 2. Vocabulary -- every symbol, one line each --------------------
add_h1(doc, "2.  Vocabulary — every symbol, one line each")

add_para(doc,
    "Memorise these.  Sir will almost certainly point at the report "
    "and ask 'what is this?'  Quick, confident answers go a long way.")

vocab = [
    ("Alice", "the legitimate transmitter (she has multiple antennas)."),
    ("Bob",   "the legitimate receiver (the person Alice wants to talk to)."),
    ("Eve",   "the passive eavesdropper (listening, not transmitting)."),
    ("Nt",    "number of transmit antennas at Alice."),
    ("MISO",  "Multiple-Input Single-Output. Multi-antenna Tx, single-"
              "antenna Rx — describes our channel topology."),
    ("AN",    "Artificial Noise — extra noise Alice transmits on purpose, "
              "designed to hurt Eve and not Bob."),
    ("MRT",   "Maximum-Ratio Transmission — the beamforming rule "
              "w = hB / ‖hB‖, which steers Alice's signal optimally toward Bob."),
    ("hB, hE", "the TRUE channels from Alice to Bob and Alice to Eve. "
               "Each entry is i.i.d. CN(0, 1) — Rayleigh fading."),
    ("ĥE",    "Alice's NOISY estimate of Eve's channel. Almost never equal "
              "to hE."),
    ("κ (kappa)", "CSI quality factor in [0, 1].  κ = 1 → perfect intel; "
                  "κ = 0 → pure noise; κ = 0.4 is our default 'realistic' "
                  "setting."),
    ("ρ (rho)", "the power split.  Fraction of total transmit power on the "
                "MESSAGE.  The remainder, (1 − ρ), goes into AN.  "
                "Always in (0, 1)."),
    ("P / σ²", "transmit SNR in linear scale.  We work with this; "
               "'SNR (dB)' on the plots is 10 log10 of this number."),
    ("w",     "the unit-norm beamformer Alice uses.  In our scheme, "
              "w = hB / ‖hB‖ (the MRT beam)."),
    ("z",     "the AN vector. Drawn so it lives in the orthogonal "
              "complement of hB. That's why Bob hears 0 AN."),
    ("P⊥",    "the projection matrix onto the null space of hB. "
              "P⊥ = I − hB hB^H / ‖hB‖².  Pre-multiplying anything by "
              "P⊥ kills its component along hB."),
    ("Rs",    "the secrecy rate.  Bits per second per Hz that Alice "
              "can convey to Bob with information-theoretic secrecy "
              "from Eve.  Higher is better.  Always non-negative."),
    ("γB, γE", "Bob's SNR and Eve's SINR.  Plug them into log2(1 + γ) "
               "to get Bob's and Eve's data rates."),
    ("α (alpha)", "alignment cue: cos²(angle) between Bob's beam direction "
                  "and the noisy Eve estimate.  In [0, 1].  We feed this "
                  "to the DQN so it can sense the geometry."),
    ("DQN",   "Deep Q-Network. The neural-net part of our scheme. Takes "
              "the 7-dim state, outputs 17 Q-values, picks the one "
              "with the highest Q."),
]
for sym, desc in vocab:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    s_run = p.add_run(sym + "  —  ")
    s_run.bold = True
    s_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    s_run.font.size = Pt(11)
    p.add_run(desc).font.size = Pt(11)


# --- 3. Formulas, explained line-by-line -----------------------------
add_h1(doc, "3.  Formulas, explained one by one")

add_para(doc,
    "These are the formulas you'll be asked to walk through.  For "
    "each one we give the formula, what each piece means, and what "
    "happens if you change a piece.")

# 3.1 transmit signal
add_h2(doc, "3.1  Transmit signal  —  what Alice actually sends")
add_para(doc, "x = √(ρP) · w · s  +  √((1 − ρ)P) · z", italic=True)
add_para(doc, "Reading it left to right:")
add_bullets(doc, [
    "x is the signal vector Alice broadcasts (one complex number per antenna).",
    "√(ρP) — the amplitude on the message; ρP is the power on the message.",
    "w — the MRT beam direction toward Bob.",
    "s — the actual data symbol Alice wants to send.",
    "√((1 − ρ)P) — the amplitude on the AN; (1 − ρ)P is the power on the AN.",
    "z — the AN vector, sitting in the null space of hB so Bob hears none of it.",
])
add_para(doc, "What if we change…", bold=True)
add_bullets(doc, [
    "ρ = 1  →  pure signal, no jamming.  Eve hears Alice clearly.  Bad.",
    "ρ = 0  →  pure jamming, no signal.  Bob hears nothing.  Also bad.",
    "P doubled  →  Bob's SNR doubles AND Eve's signal-leak doubles.  "
    "Net effect on Rs: positive but logarithmic.",
])

# 3.2 secrecy rate
add_h2(doc, "3.2  Secrecy rate  —  the score we are optimising")
add_para(doc, "Rs = max(0,  log2(1 + γB)  −  log2(1 + γE))", italic=True)
add_para(doc,
    "log2(1 + γ) is the Shannon capacity of a channel with SNR γ.  "
    "Bob's rate minus Eve's rate is what's still usable as secret bits "
    "per second per Hz.  If that comes out negative (Eve is hearing "
    "louder than Bob), we floor at 0 — no secret communication is "
    "possible on that channel.")

# 3.3 gammas
add_h2(doc, "3.3  γB and γE  —  who hears what")
add_para(doc, "γB = ρ · (P/σ²) · ‖hB‖²", italic=True)
add_bullets(doc, [
    "Bob's SNR.  Why? Because Alice's beam is matched to hB, and the AN "
    "lives in hB's null space (so Bob picks up 0 AN).  Bob's effective "
    "SNR is just (signal power) × (Bob's channel gain).",
])
add_para(doc,
    "γE = (signal_at_eve) / (AN_at_eve + noise_floor) "
    "where signal_at_eve = ρ·(P/σ²)·|hE^H w|² and "
    "AN_at_eve = (1 − ρ)·(P/σ²)·‖P⊥hE‖² / (Nt − 1).",
    italic=True)
add_bullets(doc, [
    "Eve's SINR (signal-to-interference-plus-noise).  She picks up some "
    "of Alice's signal because hE is generally not orthogonal to w.",
    "She also picks up the AN, because the null space of hB is not "
    "the null space of hE.",
    "The (Nt − 1) in the denominator is because the AN is spread "
    "uniformly over an (Nt − 1)-dimensional space.",
])
add_para(doc, "What if we change…", bold=True)
add_bullets(doc, [
    "Nt = 1  →  null space is empty, scheme breaks (no place to put AN).",
    "Nt large  →  AN is spread thin, but there's also more aiming "
    "freedom for Bob.  Net: Rs grows.",
    "‖hE‖² doubled  →  signal_at_eve doubles AND AN_at_eve doubles, "
    "so Eve's SINR is roughly invariant.  This is the Eve-strength "
    "robustness story we showed in the report.",
])

# 3.4 imperfect CSI
add_h2(doc, "3.4  Imperfect-CSI model  —  why ĥE ≠ hE")
add_para(doc,
    "ĥE = √κ · hE  +  √(1 − κ) · e,    e ~ CN(0, I)",
    italic=True)
add_bullets(doc, [
    "ĥE is what Alice OBSERVES.",
    "κ ∈ [0, 1] tells you how much of ĥE is real signal vs random noise.",
    "κ = 1 → ĥE = hE (perfect intel).",
    "κ = 0 → ĥE = e (pure noise — no information about hE).",
    "Variance check: var(ĥE) = κ·var(hE) + (1 − κ)·var(e) = "
    "κ + (1 − κ) = 1.  So ĥE has the same magnitude statistics as hE; "
    "it's just rotated by random noise.",
])
add_para(doc,
    "This is the standard linear additive CSI-error model used "
    "throughout the PLS literature (see Wang et al. 2019).")

# 3.5 alignment
add_h2(doc, "3.5  α  —  the alignment cue we feed to the DQN")
add_para(doc,
    "α = |hB^H ĥE|²  /  (‖hB‖²  ·  ‖ĥE‖²)",
    italic=True)
add_bullets(doc, [
    "It's the squared cosine of the angle between hB and ĥE.",
    "α = 1 → ĥE is parallel to hB (Bob and Eve see the same channel "
    "direction; very risky for Alice).",
    "α = 0 → ĥE is orthogonal to hB (Eve hears no signal; ideal for Alice).",
    "Why we feed it: knowing the geometry helps the DQN decide how "
    "aggressive to be on ρ.  Without it, the agent only sees magnitudes.",
])


# --- 4. The AI agent, explained --------------------------------------
add_h1(doc, "4.  The AI agent, explained without the textbook")

add_h2(doc, "4.1  What is reinforcement learning, in one paragraph?")
add_para(doc,
    "An agent observes a state, picks an action, receives a reward, "
    "and learns to pick actions that maximise its reward over time. "
    "In our setting:")
add_bullets(doc, [
    "State  =  the seven numbers describing the current channel "
    "situation (Bob's gain, Eve's noisy gain, SNR, last action, last "
    "reward, κ, alignment).",
    "Action  =  one of 17 candidate splits ρ ∈ {0.05, 0.10, …, 0.85}.",
    "Reward  =  10 × Rs, the secrecy rate Alice actually achieves on "
    "that channel (computed against TRUE hE — not the noisy estimate).",
    "Episode  =  one channel realisation.  One episode is one "
    "decision; it terminates immediately.  This is why we set "
    "discount γ = 0.",
])

add_h2(doc, "4.2  What is a Q-network?")
add_para(doc,
    "A small neural network that, given a state, outputs a Q-value "
    "for each possible action.  Q(s, a) is the agent's estimate of "
    "the future reward it would get if it took action a in state s. "
    "At test time we just pick the action with the highest Q.")
add_para(doc,
    "Our network is a plain MLP: 7 inputs (the state) → 64 → 64 → "
    "32 → 17 outputs (the Q-values).  ReLU activations on the hidden "
    "layers, linear on the output.")

add_h2(doc, "4.3  Why ε-greedy?")
add_para(doc,
    "If the agent always picked the action it currently thinks is "
    "best, it would never try anything new.  ε-greedy fixes that: "
    "with probability ε the agent picks a random action (exploration); "
    "with probability 1 − ε it picks the greedy action (exploitation). "
    "We start at ε = 1.0 (totally random) and linearly decay to 0.05 "
    "over the first 4200 episodes.")

add_h2(doc, "4.4  Why discount γ = 0?")
add_para(doc,
    "Because each episode in our setting is one decision.  The agent "
    "picks ρ, gets the reward, episode is over.  There is no 'next "
    "step' whose reward should be discounted.  We still keep the "
    "full target-network machinery in the code so we can extend "
    "later to multi-step block fading where γ > 0 would matter.")

add_h2(doc, "4.5  Why Huber loss?")
add_para(doc,
    "The reward is a real number (an Rs value).  The Q-network learns "
    "to predict it.  Huber loss is mean-squared-error for small "
    "errors and mean-absolute-error for large errors — robust to the "
    "occasional outlier reward without being too forgiving on small "
    "errors.  Standard choice from Mnih et al. (2015).")

add_h2(doc, "4.6  What is the replay buffer?")
add_para(doc,
    "A FIFO queue of past (state, action, reward, next_state, done) "
    "transitions.  Capacity 10 000 in our setup.  When training, we "
    "sample a random mini-batch of 64 transitions from the buffer "
    "and update the Q-network on that batch.  Why?  Because doing "
    "stochastic gradient descent on the SEQUENCE of experiences as "
    "they arrive would break the i.i.d. assumption SGD relies on. "
    "Random sampling decorrelates the data.")

add_h2(doc, "4.7  Why a target network?")
add_para(doc,
    "When you compute the Bellman target y = r + γ · max_a' Q(s', a'), "
    "if you use the same network on both sides of the loss, the "
    "target moves every time you update — it's like chasing a moving "
    "shadow.  The trick is to keep a frozen copy of the Q-network "
    "(the target network), use IT to compute the target, and only "
    "sync it to the online network every N steps.  In our setup "
    "N = 100.  Stable training comes from this trick.")
add_para(doc,
    "(In our specific setting, with γ = 0, the bootstrap term "
    "max_a' Q(s', a') is multiplied by 0 anyway and the target is "
    "just y = r.  So the target-network distinction is more "
    "important for our future-extension story than for the current "
    "single-step problem.)")


# --- 5. Training, step by step ---------------------------------------
add_h1(doc, "5.  Training, step by step")
add_para(doc, "For each of 7000 training episodes the trainer does:")
add_bullets(doc, [
    "Sample a fresh hB and hE from CN(0, I).",
    "Sample a random transmit SNR uniformly in [0, 30] dB and a "
    "random κ uniformly in [0.1, 0.9].",
    "Build ĥE from hE using the imperfect-CSI model with that κ.",
    "Build the 7-dim state from those values.",
    "Pick an action via ε-greedy.",
    "Compute the reward using the chosen ρ AGAINST the TRUE hE.",
    "Store the transition in the replay buffer.",
    "Once we've done 200 episodes (warm-up), start training: sample "
    "a 64-transition batch and run one gradient step on the Q-network.",
    "Every 100 training steps, sync the target network.",
])
add_para(doc,
    "We train one DQN per Nt ∈ {2, 4, 8} so we can show the "
    "antenna-count effect honestly.  Each model takes ≈ 38 seconds "
    "on a single CPU core.  Total training cost for all three models "
    "is under 2 minutes.")


# --- 6. What if we change… (sensitivity table) ----------------------
add_h1(doc, "6.  What if we change …  (sir's favourite question)")

add_h2(doc, "6.1  What if κ goes down?")
add_bullets(doc, [
    "Fixed (ρ = 0.5):  unchanged.  It doesn't even look at ĥE.",
    "Traditional:  collapses.  Around κ = 0.6 it crosses below the "
    "Fixed baseline; below that, you'd be better off doing nothing.",
    "DQN:  retreats toward ρ ≈ 0.5.  It sees κ in its state, knows "
    "the intel is bad, plays it safe.  Stays at or above Fixed.",
])

add_h2(doc, "6.2  What if κ goes up?")
add_bullets(doc, [
    "Fixed:  unchanged (still suboptimal).",
    "Traditional:  approaches the perfect-CSI optimum.  At κ = 1 it "
    "is the analytical upper bound.",
    "DQN:  shifts ρ further from 0.5, exploiting the now-trustworthy "
    "intel.  Approaches but doesn't quite match Traditional at κ = 1 "
    "because of the discrete action grid.",
])

add_h2(doc, "6.3  What if SNR is very low (say 0 dB)?")
add_bullets(doc, [
    "Bob is barely above noise.  Spending ANY power on AN means Bob "
    "starves.",
    "Optimal ρ shifts toward 0.7–0.8 (more power on the message).",
    "Our action histogram (slide 5 in deck, fig. 5 in report) "
    "confirms the DQN learned this — at low SNR it heavily favours "
    "ρ ≈ 0.7–0.8.",
])

add_h2(doc, "6.4  What if SNR is very high (30 dB)?")
add_bullets(doc, [
    "Bob has lots of headroom.  We can afford to inject a lot of AN "
    "without starving him.",
    "Optimal ρ converges back toward 0.5.",
    "DQN picks tighter cluster around 0.5 at high SNR — visible in "
    "fig. 5.",
])

add_h2(doc, "6.5  What if Nt = 1?")
add_bullets(doc, [
    "There is no null space (a 1-D space has no orthogonal complement). "
    "The whole AN scheme breaks.  Goel-Negi requires Nt ≥ 2.",
])

add_h2(doc, "6.6  What if Nt is very large?")
add_bullets(doc, [
    "More antennas → larger null space → AN is more isotropic at "
    "Eve → harder for Eve to pick up the signal cleanly.",
    "Bob also gets a higher beamforming gain (‖hB‖² grows on "
    "average linearly with Nt).",
    "Our experiment (fig. 7 in the report) shows DQN's win over "
    "Fixed grows with Nt; at Nt = 8 the gap is widest.",
])

add_h2(doc, "6.7  What if Eve gets stronger (β > 1)?")
add_bullets(doc, [
    "Counter-intuitively, the AVERAGE Rs barely changes.  Why?",
    "Eve's signal-receive scales with ‖hE‖², AND the AN-leakage at "
    "Eve also scales with ‖hE‖².  So her SINR is roughly "
    "gain-invariant in expectation.",
    "This is the Eve-strength sweep in fig. 10.  It's a structural "
    "robustness property of the null-space AN scheme.",
])

add_h2(doc, "6.8  What if we use continuous actions instead of 17 discrete?")
add_bullets(doc, [
    "We'd need a continuous-action algorithm like DDPG or PPO.  "
    "Lin et al. (2023) does this for a different problem.",
    "Pros: finer ρ resolution, potentially closer to the oracle.",
    "Cons: harder to train, requires actor-critic infrastructure, "
    "the Q-network alone isn't enough.  For the precision we need "
    "(Rs is concave with a soft peak), 17 discrete actions are "
    "plenty.",
])


# --- 7. Why the DQN works (intuitions) -------------------------------
add_h1(doc, "7.  Why the DQN actually works  —  three intuitions")

add_h2(doc, "7.1  Intuition 1:  it sees its own ignorance")
add_para(doc,
    "Traditional optimiser doesn't know how reliable its input is; "
    "it just optimises against ĥE as if it were truth.  Our DQN gets "
    "κ as part of the state, so it can adjust its trust in ĥE.  "
    "When κ is low it falls back to safer ρ; when κ is high it "
    "leans on the estimate.")

add_h2(doc, "7.2  Intuition 2:  it sees the geometry")
add_para(doc,
    "The alignment cue α tells the agent whether ĥE is pointing "
    "in roughly the same direction as Bob's beam.  When that "
    "alignment is high it means even a small leak from the signal "
    "could feed Eve clearly, so the agent shifts more power to AN.  "
    "When alignment is low, Eve's just hearing scraps and we can "
    "afford to push more power on the signal.")

add_h2(doc, "7.3  Intuition 3:  it was trained to expect noise")
add_para(doc,
    "Every training episode used a fresh random κ ∈ [0.1, 0.9].  "
    "The agent has SEEN bad-intel scenarios thousands of times "
    "during training and learned to handle them.  Traditional "
    "has never been told that ĥE might be wrong, so it can't "
    "compensate.")


# --- 8. Q&A bank -----------------------------------------------------
add_h1(doc, "8.  Q&A bank  —  questions sir is most likely to ask")

add_qa(doc,
    "Walk me through the secrecy rate formula.",
    "Rs is Bob's rate minus Eve's rate, floored at 0.  Bob's rate "
    "is log2(1 + γB), where γB is his SNR and equals "
    "ρ · (P/σ²) · ‖hB‖² because the AN cancels at his location. "
    "Eve's rate is log2(1 + γE) where γE is her SINR — signal "
    "leakage divided by AN-plus-noise.  If γB > γE we have positive "
    "secrecy capacity; otherwise no secret communication is "
    "possible on that channel.")

add_qa(doc,
    "Why does AN cancel at Bob?",
    "Because we construct it to.  We project a random isotropic "
    "vector through P⊥ = I − hB hB^H / ‖hB‖², which is the "
    "projector onto the null space of hB.  After projection, "
    "hB^H · z = 0 by construction.  We also verify this "
    "numerically — our test suite confirms the leak is below 1e-10 "
    "across 500 random channels.")

add_qa(doc,
    "Why does the Traditional optimiser fail at low κ?",
    "It treats ĥE as if it were truth.  Once the noise component "
    "(1 − κ)·e dominates ĥE, the optimiser is solving the wrong "
    "problem.  Worse, the optimiser's solution is CONFIDENT — it "
    "sits at an interior peak of Rs(ρ; ĥE), often at a very "
    "different ρ than the true optimum Rs(ρ; hE).  Picking a "
    "confidently-wrong ρ on a channel where Rs(ρ; hE) drops "
    "sharply costs you more than just picking ρ = 0.5 blindly.")

add_qa(doc,
    "Why did you choose 17 actions instead of 9?",
    "We started with 9 (steps of 0.10).  At test time we noticed "
    "the DQN was being held back by the coarse grid — the optimum "
    "ρ frequently lay between two action choices.  Going to 17 "
    "(steps of 0.05) gave the agent enough resolution to track the "
    "optimum without making the Q-network significantly harder to "
    "train.  Going much finer than that would have started to hurt "
    "training because each Q-value sees fewer training examples.")

add_qa(doc,
    "Why is the discount factor zero?",
    "Because each episode is a SINGLE decision.  Alice picks a ρ, "
    "the channel realises, the reward is computed, the episode "
    "ends.  There's no future step to discount.  If we extended "
    "this to a multi-step block-fading problem where the channel "
    "evolves, we'd switch γ to ~0.99.")

add_qa(doc,
    "What does the alignment cue α actually capture?",
    "The cosine-squared of the angle between Bob's beam direction "
    "(which is along hB after MRT) and the noisy Eve estimate ĥE. "
    "If α is close to 1, Eve looks like she's in roughly the same "
    "direction as Bob — risky.  If α is close to 0, Eve looks "
    "orthogonal — safer.  This is geometric information the DQN "
    "could not infer from magnitudes alone.")

add_qa(doc,
    "How do you know the DQN didn't overfit?",
    "Two reasons.  First, training and evaluation use different "
    "random seeds (42 for training, 2026 for evaluation), so the "
    "channels we test on are disjoint from the channels we trained "
    "on.  Second, we evaluate not just at one κ but across a sweep "
    "of κ values; the DQN holds its lead across the whole sweep, "
    "which is consistent with a learned policy that generalises "
    "rather than a memorised lookup.")

add_qa(doc,
    "What is the computational cost at deployment?",
    "Per call: about 4.7 ms on a single CPU core for the DQN "
    "forward pass through a 7-64-64-32-17 MLP.  Most of that is "
    "TensorFlow's Python overhead; the actual matrix multiplies "
    "are sub-microsecond.  In a production deployment with TFLite "
    "or batched inference the cost would drop by ~10x.  Either way "
    "it's well within the millisecond budget of a wireless control "
    "loop.")

add_qa(doc,
    "What's the biggest limitation of your scheme?",
    "Two honest limitations.  First, we tested on i.i.d. Rayleigh "
    "channels with no spatial geometry — real channels have "
    "correlation and path loss that we didn't model.  Second, when "
    "we scaled Eve's channel gain way outside the training "
    "distribution (β > 6 dB) the DQN's performance dipped slightly "
    "below Fixed.  This is a mild out-of-distribution issue; "
    "widening the training-distribution gain range or normalising "
    "the gain features would address it.")

add_qa(doc,
    "Why DQN and not DDPG / PPO / actor-critic?",
    "Three reasons.  (1) Our action space is naturally small — 17 "
    "options is plenty for a smooth, concave Rs(ρ).  Discrete "
    "actions are the natural fit.  (2) DQN is the simplest deep RL "
    "algorithm that solves the problem; choosing the lighter tool "
    "matters for reproducibility and training cost.  (3) Lin et "
    "al. (2023) used DDPG for a related problem because their "
    "action space was beamformer-plus-power (continuous, "
    "high-dim).  Ours is just one scalar.  The complexity of DDPG "
    "would have been gratuitous here.")

add_qa(doc,
    "What does ε-greedy do, and why does ε start high?",
    "ε is the probability of picking a random action instead of "
    "the greedy one.  Starting high (1.0) means the agent EXPLORES "
    "broadly at the beginning, sampling actions across the whole "
    "ρ range so the Q-network sees varied training data.  As "
    "training progresses, ε decays linearly to 0.05 — by then the "
    "agent mostly EXPLOITS its learned Q-values, but a small "
    "amount of exploration continues so the policy stays fresh.")

add_qa(doc,
    "Could Eve be smarter / adaptive?",
    "In our setup Eve is passive — she just receives.  If we let "
    "her choose her own receive strategy (e.g. an MMSE receiver "
    "instead of treating AN as noise), the achievable rate at Eve "
    "would change and we'd need to redo the analysis.  More "
    "interestingly, if Eve could ADAPT her receive strategy in "
    "response to Alice's choices, we'd be in a zero-sum game and "
    "the natural framework would be multi-agent reinforcement "
    "learning.  We mention this in the future-work section of the "
    "report.")

add_qa(doc,
    "Why does the DQN's edge grow with Nt?",
    "Two effects compound.  First, the null-space dimension is "
    "Nt − 1, so AN has more room to be isotropic at Eve as Nt "
    "grows — the AN scheme inherently gets stronger.  Second, our "
    "alignment cue α becomes a more informative feature when Nt "
    "is larger, because the angle between two random Nt-vectors "
    "concentrates differently as Nt grows.  The DQN exploits both, "
    "which is why fig. 7 shows its widest absolute lead at Nt = 8.")


# --- 9. One-line memory hooks ----------------------------------------
add_h1(doc, "9.  Quick memory hooks  (one-liners to remember)")

hooks = [
    "ρ controls the message; (1 − ρ) is the jamming.",
    "κ tells you how good your intel is.",
    "AN lives in Bob's null space → Bob hears 0 AN.",
    "Eve hears scaled signal + scaled AN; scales cancel out, hence flat-β robustness.",
    "Traditional optimiser is fooled at κ < 0.6.",
    "DQN sees κ → it knows when to retreat to 0.5.",
    "DQN sees α → it knows when geometry is risky.",
    "Trained on random κ → policy expects bad intel.",
    "Discount γ = 0 because each episode is one decision.",
    "Action grid 17 splits, step 0.05 → fine enough, easy to learn.",
    "Replay buffer + target network = standard DQN tricks for stability.",
    "Same trained model handles every (Nt, SNR, κ); no retuning.",
]
for h in hooks:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(h)
    run.font.size = Pt(11)
    if "AN lives in Bob's null space" in h:
        run.bold = True
    if "Traditional optimiser is fooled" in h:
        run.bold = True


# --- 10. The demo, in script form ------------------------------------
add_h1(doc, "10.  The live-demo script  —  what to say while clicking")

add_para(doc,
    "When the demo opens, this is the order to walk through it.  "
    "Each line below is what to SAY; the parenthetical is what to "
    "DO with the slider.")

steps = [
    ("Live test tab",
     "Pick Nt = 8 (already default), SNR = 15 dB, κ = 0.4. "
     "Three bars appear; the green DQN bar should sit at or above "
     "the others."),
    ("Drag κ down to 0.2",
     "Watch the red Traditional bar shrink visibly while the green "
     "DQN bar barely moves.  This is the failure-mode story in "
     "real-time."),
    ("Switch to the κ-sweep tab (tab 3, the headline)",
     "The plot shows three curves vs κ.  Point at where red "
     "crosses below grey near κ = 0.6 — sir's expected reaction "
     "is 'so the optimiser is doing worse than nothing'."),
    ("Switch to the SNR-sweep tab",
     "Hold κ = 0.4, watch all three curves grow with SNR.  The "
     "spacing between green and grey grows with SNR — the DQN's "
     "advantage compounds."),
    ("Outage tab",
     "Pick R₀ = 4, read off the three failure probabilities.  "
     "DQN's number should be around 18%, Traditional's around "
     "26%.  This is robustness in concrete percent terms."),
    ("Geometry tab",
     "This one's optional.  Just use it if sir asks 'what does "
     "the channel actually look like geometrically?' — show the "
     "Bob/Eve direction sliders and the chosen ρ for each scheme."),
]
for label, body in steps:
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(label + ".  ")
    run.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    run.font.size = Pt(11)
    p.add_run(body).font.size = Pt(11)


# --- 11. If something breaks during the demo -------------------------
add_h1(doc, "11.  If something breaks during the demo")

add_bullets(doc, [
    "If Streamlit doesn't open: the command is "
    "`streamlit run app/streamlit_app.py`.  If port 8501 is busy, "
    "it will pick 8502 automatically — check the terminal.",
    "If a slider drag freezes: the first compute on a new "
    "(Nt, SNR, κ) takes 1–2 seconds (Monte Carlo over 600 "
    "channels).  Subsequent drags are cached.  Just wait.",
    "If a graph looks empty: refresh the page (browser refresh).  "
    "Don't restart Streamlit — the trained model is loaded into "
    "memory and reloading takes another 5 seconds.",
    "If you're asked to show 'the actual code that does X': "
    "open core/schemes.py for the three scheme definitions, "
    "core/dqn_agent.py for the network, core/trainer.py for "
    "training, core/state.py for the state vector.",
])


# --- Wipe identifying metadata --------------------------------------
cp = doc.core_properties
for attr in ("author", "last_modified_by", "title", "subject", "keywords",
             "category", "comments", "identifier", "language",
             "content_status", "version"):
    try:
        setattr(cp, attr, "")
    except Exception:
        pass
try:
    cp.revision = 1
except Exception:
    pass

doc.save(OUT_PATH)


# --- Post-process: drop customXml + thumbnail, scrub app.xml --------
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

        elif name == "word/_rels/document.xml.rels":
            xml = data.decode("utf-8", errors="ignore")
            xml = re.sub(
                r"<Relationship[^/]*Target=\"\.\./customXml/[^\"]+\"[^/]*/>",
                "", xml)
            data = xml.encode("utf-8")

        elif name == "word/settings.xml":
            xml = data.decode("utf-8", errors="ignore")
            xml = xml.replace("<w:savePreviewPicture/>", "")
            data = xml.encode("utf-8")

        elif name == "docProps/app.xml":
            xml = data.decode("utf-8", errors="ignore")
            for tag in ("Application", "Company", "Manager", "AppVersion",
                        "Template", "TotalTime"):
                xml = re.sub(rf"<{tag}>[^<]*</{tag}>",
                             f"<{tag}></{tag}>", xml)
            data = xml.encode("utf-8")

        zout.writestr(item, data)

shutil.move(tmp_path, OUT_PATH)


# Sanity check for hidden Unicode
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
