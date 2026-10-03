#!/usr/bin/env python3
"""Generate paper-009 figures from the captured results JSONs. Deterministic (reads JSON, no RNG).

Writes PNGs into papers/009-hitl-calibration/figs/:
  hero.png   E3 escalation-volume vs false-allow for {fixed, calibrated, cost-sensitive} (the domination)
  e1.png     control burden (per-control false-block of legit)
  e2.png     reliability diagram (calibration)
  e4.png     care-delay frontier (TTC vs missed-harm)
  e5.png     alarm-fatigue (optimal allow_shift vs load)

Run: python3 scripts/009-hitl-calibration/make_figures.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = "results/009-hitl-calibration"
FIGS = "papers/009-hitl-calibration/figs"
INK = "#1f2937"
BLUE = "#1D4ED8"
AMBER = "#D97706"
TEAL = "#0F766E"
RED = "#b91c1c"


def load(name):
    return json.load(open(os.path.join(RES, f"{name}.json")))


def hero():
    e3 = load("e3")
    order = ["fixed", "calibrated", "cost_sensitive"]
    labels = ["Fixed\n(escalate >0.5)", "Calibrated\n(fitted bands)", "Cost-sensitive"]
    vol = [e3[k]["escalation_volume"] for k in order]
    fa = [e3[k]["false_allow"] for k in order]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    colors = [RED, BLUE, TEAL]
    ax.scatter(vol, fa, s=180, c=colors, zorder=3, edgecolors="white", linewidths=1.5)
    for x, y, l, c in zip(vol, fa, labels, colors):
        ax.annotate(l, (x, y), textcoords="offset points", xytext=(10, 8), fontsize=9, color=c, fontweight="bold")
    # arrow fixed -> calibrated (the improvement direction: down-left = better on both axes)
    ax.annotate("", xy=(vol[1], fa[1]), xytext=(vol[0], fa[0]),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.4, alpha=0.6))
    ax.text(0.32, 0.055, "lower volume\nAND lower false-allow", fontsize=8.5, color=INK, style="italic")
    ax.set_xlabel("Clinician prompt volume (fraction escalated)")
    ax.set_ylabel("False-allow rate")
    ax.set_xlim(0.15, 0.47)
    ax.set_ylim(-0.005, 0.10)
    ax.set_title("Calibrated escalation Pareto-dominates fixed-threshold", fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "hero.png"), dpi=160)
    plt.close(fig)


def e1_fig():
    e1 = load("e1")
    controls = ["policy", "egress", "identity", "retrieval"]
    fb = [e1["controls"][c]["false_block_rate"] for c in controls]
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    bars = ax.bar(controls, fb, color=[RED if v >= 0.15 else BLUE for v in fb])
    ax.axhline(0.15, ls="--", color=INK, lw=1, alpha=0.7)
    ax.text(3.1, 0.16, "H1 bar (15%)", fontsize=8, color=INK, ha="right")
    for b, v in zip(bars, fb):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.1%}", ha="center", fontsize=9)
    ax.set_ylabel("False-block rate (legit actions)")
    ax.set_title("Per-control false-deny burden", fontsize=11, fontweight="bold")
    ax.set_ylim(0, max(fb) * 1.3 + 0.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "e1.png"), dpi=160)
    plt.close(fig)


def e2_fig():
    e2 = load("e2")
    bins = e2["bins"]
    conf = [b["confidence"] for b in bins]
    acc = [b["accuracy"] for b in bins]
    fig, ax = plt.subplots(figsize=(5.0, 4.4))
    ax.plot([0, 1], [0, 1], ls="--", color=INK, alpha=0.6, label="perfect calibration")
    ax.plot(conf, acc, "o-", color=BLUE, label=f"fitted (ECE={e2['ece_scaled']}, T={e2['best_temperature']})")
    ax.set_xlabel("Predicted P(harm)")
    ax.set_ylabel("Empirical harm rate")
    ax.set_title("Risk-score reliability", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "e2.png"), dpi=160)
    plt.close(fig)


def e4_fig():
    e4 = load("e4")
    fr = e4["frontier"]
    mh = [f["missed_harm"] for f in fr]
    ttc = [f["total_ttc_min"] for f in fr]
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    ax.plot(mh, ttc, "o-", color=AMBER)
    ax.scatter([mh[0]], [ttc[0]], s=160, facecolors="none", edgecolors=BLUE, linewidths=2, zorder=4)
    ax.annotate("recommended\n(default bands)", (mh[0], ttc[0]), textcoords="offset points",
                xytext=(12, -6), fontsize=8.5, color=BLUE)
    for f in fr:
        ax.annotate(f"+{f['allow_shift']:.2f}", (f["missed_harm"], f["total_ttc_min"]),
                    textcoords="offset points", xytext=(4, 6), fontsize=7, color=INK, alpha=0.7)
    ax.set_xlabel("Missed harm (auto-allowed harmful actions)")
    ax.set_ylabel("Total time-to-care delay (min)")
    ax.set_title("Care-delay vs missed-harm frontier", fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "e4.png"), dpi=160)
    plt.close(fig)


def e5_fig():
    e5 = load("e5")
    rows = e5["by_load"]
    load_x = [r["load"] for r in rows]
    shift = [r["allow_shift"] for r in rows]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.plot(load_x, shift, "o-", color=TEAL, lw=2)
    for r in rows:
        ax.annotate(f"{r['allow_shift']:.2f}", (r["load"], r["allow_shift"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=8, color=INK)
    ax.set_xlabel("Clinician load (outstanding prompts)")
    ax.set_ylabel("Optimal auto-allow shift")
    ax.set_title("Alarm fatigue shifts the optimal threshold", fontsize=11, fontweight="bold")
    ax.grid(True, alpha=0.25)
    ax.set_ylim(-0.01, 0.32)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "e5.png"), dpi=160)
    plt.close(fig)


def main():
    os.makedirs(FIGS, exist_ok=True)
    hero()
    e1_fig()
    e2_fig()
    e4_fig()
    e5_fig()
    print(f"wrote hero/e1/e2/e4/e5 .png to {FIGS}")


if __name__ == "__main__":
    main()
