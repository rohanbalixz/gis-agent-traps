#!/usr/bin/env python3
"""Draw the headline figure (trap scores per run) from runs/run_log.csv.

Writes results/figures/trap_scores_light.png and trap_scores_dark.png.
Scores follow the pre-registered rule: the first attempt that completed.
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

KIT = Path(__file__).resolve().parent.parent
OUT = KIT / "results" / "figures"
TRAP_SET = {"A": "set1", "B": "set2", "C": "set1"}  # from answer_keys/ANSWER_KEY.md
ROWS = [("A", "Projection error", "operation level"),
        ("B", "Hidden confounder", "conclusion level"),
        ("C", "No covariate overlap", "conclusion level")]
LEGEND = ["missed", "generic caveat", "named the problem", "fixed it, right answer"]

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  fills=["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],
                  labels=["#0b0b0b", "#ffffff", "#ffffff", "#ffffff"]),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
                 fills=["#184f95", "#2a78d6", "#6da7ec", "#b7d3f6"],
                 labels=["#ffffff", "#ffffff", "#0b0b0b", "#0b0b0b"]),
}

rows = list(csv.DictReader(open(KIT / "runs" / "run_log.csv")))
scores = {t: [] for t in TRAP_SET}
for t, s in TRAP_SET.items():
    for k in (1, 2, 3):
        r = next(x for x in rows if x["run_id"] == f"{t}-{s}-r{k}")
        scores[t].append(int(r["score_rule_b"]))

plt.rcParams["font.family"] = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def draw(theme):
    c = THEMES[theme]
    fig = plt.figure(figsize=(8.0, 3.05), dpi=200, facecolor=c["surface"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 38)
    ax.axis("off")
    ax.set_facecolor(c["surface"])

    ax.text(2, 35.2, "Did the agent catch the trap?", color=c["ink"], fontsize=13, weight="bold", va="center")
    ax.text(2, 32.0, "Score per run, 0–3, under the pre-registered rule (first attempt that completed). "
            "Caught = 2 or 3.", color=c["ink2"], fontsize=9, va="center")
    ax.text(98, 35.2, "GIS Copilot 1.4 · gpt-oss:20b (local)", color=c["muted"], fontsize=8,
            ha="right", va="center")

    x0, w, gap, h = 36.0, 7.4, 0.9, 6.2
    for k in range(3):
        ax.text(x0 + k * (w + gap) + w / 2, 28.4, f"Run {k + 1}", color=c["muted"], fontsize=8.5,
                ha="center", va="center")
    ax.text(x0 + 3 * (w + gap) + 2.0, 28.4, "Caught", color=c["muted"], fontsize=8.5, va="center")

    for i, (t, name, level) in enumerate(ROWS):
        y = 20.6 - i * (h + 1.4)
        ax.text(2, y + h / 2 + 1.0, f"{t}  {name}", color=c["ink"], fontsize=10.5, weight="bold", va="center")
        ax.text(5.2, y + h / 2 - 1.6, level, color=c["ink2"], fontsize=8.5, va="center")
        for k, sc in enumerate(scores[t]):
            xx = x0 + k * (w + gap)
            ax.add_patch(FancyBboxPatch((xx, y), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                                        facecolor=c["fills"][sc], edgecolor=c["surface"], linewidth=2))
            ax.text(xx + w / 2, y + h / 2, str(sc), color=c["labels"][sc], fontsize=12, weight="bold",
                    ha="center", va="center")
        caught = sum(s >= 2 for s in scores[t])
        ax.text(x0 + 3 * (w + gap) + 2.0, y + h / 2, f"{caught} of 3", color=c["ink"], fontsize=10.5,
                weight="bold" if caught else "normal", va="center")

    for sc, (lab, lx) in enumerate(zip(LEGEND, (2.0, 14.5, 32.0, 52.0))):
        ax.add_patch(FancyBboxPatch((lx, 0.9), 2.6, 2.6, boxstyle="round,pad=0,rounding_size=0.4",
                                    facecolor=c["fills"][sc], edgecolor=c["surface"], linewidth=1))
        ax.text(lx + 1.3, 2.2, str(sc), color=c["labels"][sc], fontsize=7, weight="bold", ha="center", va="center")
        ax.text(lx + 3.4, 2.2, lab, color=c["ink2"], fontsize=8, va="center")

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"trap_scores_{theme}.png", facecolor=c["surface"])
    plt.close(fig)


for th in THEMES:
    draw(th)
print("scores (rule b):", scores, "->", OUT)
