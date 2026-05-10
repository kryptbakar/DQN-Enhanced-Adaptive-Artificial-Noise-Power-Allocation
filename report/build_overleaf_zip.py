"""
Build report/overleaf.zip -- a single-file upload that drops cleanly
into Overleaf via "New Project -> Upload Project".

Layout inside the zip (flat, the way Overleaf expects):

    main.tex          (graphicspath patched to {figures/})
    refs.bib
    figures/01_single_channel_sweep.png
    figures/02_validation_scheme1_vs_scheme2.png
    figures/04_three_scheme_comparison.png
    figures/05_dqn_action_distribution.png
    figures/06_kappa_sweep.png
    figures/07_antenna_count.png
    figures/08_secrecy_outage.png
    figures/09_policy_heatmap.png
    figures/10_eve_strength.png
    figures/11_optimal_rho_comparison.png

The script does NOT modify the working-tree main.tex; it patches a copy
in memory before writing it into the zip.

Run from the repo root:
    python report/build_overleaf_zip.py
"""

from __future__ import annotations

import os
import re
import zipfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR   = os.path.join(REPO_ROOT, "figures")
TEX_PATH  = os.path.join(REPO_ROOT, "report", "main.tex")
BIB_PATH  = os.path.join(REPO_ROOT, "report", "refs.bib")
OUT_PATH  = os.path.join(REPO_ROOT, "report", "overleaf.zip")


# Figures that the .tex file actually references (matches \includegraphics
# calls inside main.tex). Keep this list explicit so we never bundle a
# stale figure that has been removed from the report.
FIGURE_FILES = [
    "01_single_channel_sweep.png",
    "02_validation_scheme1_vs_scheme2.png",
    "04_three_scheme_comparison.png",
    "05_dqn_action_distribution.png",
    "06_kappa_sweep.png",
    "07_antenna_count.png",
    "08_secrecy_outage.png",
    "09_policy_heatmap.png",
    "10_eve_strength.png",
    "11_optimal_rho_comparison.png",
]


def patch_tex_for_overleaf(src: str) -> str:
    """
    Rewrite \\graphicspath so it resolves to a sibling 'figures/' folder
    instead of the local repo's '../figures/'. This is the only change
    needed -- everything else in the source compiles unchanged.
    """
    return re.sub(
        r"\\graphicspath\{\{\.\./figures/\}\}",
        r"\\graphicspath{{figures/}}",
        src,
    )


def main() -> None:
    with open(TEX_PATH, "r", encoding="utf-8") as f:
        tex_src = f.read()
    tex_for_overleaf = patch_tex_for_overleaf(tex_src)

    if "\\graphicspath{{figures/}}" not in tex_for_overleaf:
        raise SystemExit(
            "Patch did not match \\graphicspath in main.tex; "
            "inspect the source and update build_overleaf_zip.py."
        )

    # Sanity-check that every figure we list actually exists, so the
    # zip never points at a missing image.
    missing = [f for f in FIGURE_FILES
               if not os.path.isfile(os.path.join(FIG_DIR, f))]
    if missing:
        raise SystemExit(f"Missing figures: {missing}")

    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        # main.tex with patched graphicspath
        z.writestr("main.tex", tex_for_overleaf)
        # bibliography
        with open(BIB_PATH, "rb") as f:
            z.writestr("refs.bib", f.read())
        # figures
        for name in FIGURE_FILES:
            z.write(os.path.join(FIG_DIR, name), arcname=f"figures/{name}")

    print(f"[SAVE] {OUT_PATH}")
    print(f"[SIZE] {os.path.getsize(OUT_PATH) / 1024:.1f} KB")
    print("[CONTENTS]")
    with zipfile.ZipFile(OUT_PATH, "r") as z:
        for n in sorted(z.namelist()):
            print(f"  {n}")


if __name__ == "__main__":
    main()
