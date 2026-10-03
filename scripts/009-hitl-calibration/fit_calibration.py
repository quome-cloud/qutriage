#!/usr/bin/env python3
"""Fit the oversight risk scorer on TriageBench (paper 009, stage-4 calibration pulled forward).

Pure-Python logistic regression (deterministic gradient descent, zero init) of P(true_harm | signals)
over the same feature set the Rust scorer uses, then temperature scaling minimizing ECE. Writes the
fitted parameters + the recommended per-tool-risk escalation bands to a committed config that BOTH the
Rust gateway (`Calibration` is Serialize/Deserialize) and the Python experiments load. Reproducible:
fixed lr / iterations / no RNG.

The bands encode the operating-point policy (cost, not data): higher tool-risk classes escalate a wider
middle (more caution). Auto-allow only when P(harm) < allow_below; auto-deny only when P(harm) > deny_above.

Run: python3 scripts/009-hitl-calibration/fit_calibration.py
"""
import json
import math

DATA = "datasets/009-hitl-calibration/triagebench/actions.jsonl"
OUT = "datasets/009-hitl-calibration/calibration_fitted.json"

TOOL_RISK_INDEX = {"low": 0, "medium": 1, "high": 2, "life_critical": 3}

# Recommended escalation bands (allow_below, deny_above) as P(harm) thresholds. Higher risk class ->
# wider escalate band (more caution): lower allow_below AND higher deny_above.
RECOMMENDED_BANDS = {
    "low": [0.25, 0.80],
    "medium": [0.18, 0.85],
    "high": [0.12, 0.90],
    "life_critical": [0.06, 0.95],
}


def features(sig, tool_risk):
    return [
        sig["max_block_confidence"],
        sig["taint_level"] or 0.0,
        sig["policy_margin"] or 0.0,
        sig["provenance_trust"] or 0.0,
        sig["identity_trust"] or 0.0,
        TOOL_RISK_INDEX[tool_risk] / 3.0,
    ]


def sigmoid(z):
    if z < -30:
        return 0.0
    if z > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def fit_logistic(X, y, lr=0.3, iters=4000, l2=1e-4):
    n_feat = len(X[0])
    w = [0.0] * n_feat
    b = 0.0
    n = len(X)
    for _ in range(iters):
        gw = [0.0] * n_feat
        gb = 0.0
        for xi, yi in zip(X, y):
            p = sigmoid(sum(w[j] * xi[j] for j in range(n_feat)) + b)
            err = p - yi
            for j in range(n_feat):
                gw[j] += err * xi[j]
            gb += err
        for j in range(n_feat):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * (gb / n)
    return w, b


def ece(ps, ys, bins=10):
    e = 0.0
    n = len(ps)
    for k in range(bins):
        lo, hi = k / bins, (k + 1) / bins
        idx = [i for i, p in enumerate(ps) if p >= lo and (p < hi or (k == bins - 1 and p <= hi))]
        if not idx:
            continue
        conf = sum(ps[i] for i in idx) / len(idx)
        acc = sum(ys[i] for i in idx) / len(idx)
        e += len(idx) / n * abs(acc - conf)
    return e


def main():
    actions = [json.loads(l) for l in open(DATA)]
    X = [features(a["signals"], a["tool_risk"]) for a in actions]
    y = [1.0 if a["true_harm"] else 0.0 for a in actions]

    w, b = fit_logistic(X, y)

    # temperature scaling: pick T on a grid that minimizes ECE of sigmoid(logit/T)
    logits = [sum(w[j] * X[i][j] for j in range(len(w))) + b for i in range(len(X))]
    best_t, best_e = 1.0, None
    for t in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
        ps = [sigmoid(z / t) for z in logits]
        e = ece(ps, y)
        if best_e is None or e < best_e:
            best_t, best_e = t, e

    cal = {
        "version": "009-fitted-v1",
        "bias": round(b, 6),
        "w_block_conf": round(w[0], 6),
        "w_taint": round(w[1], 6),
        "w_policy": round(w[2], 6),
        "w_provenance": round(w[3], 6),
        "w_identity": round(w[4], 6),
        "w_tool_risk": round(w[5], 6),
        "temperature": best_t,
        "bands": RECOMMENDED_BANDS,
    }
    with open(OUT, "w") as f:
        json.dump(cal, f, indent=2, sort_keys=True)

    acc = sum(1 for z, yi in zip(logits, y) if (sigmoid(z) >= 0.5) == (yi == 1.0)) / len(y)
    print(f"fitted logistic: train acc={acc:.3f}  ECE(T={best_t})={best_e:.4f}")
    print(f"  weights: block={w[0]:.2f} taint={w[1]:.2f} policy={w[2]:.2f} prov={w[3]:.2f} ident={w[4]:.2f} tool={w[5]:.2f} bias={b:.2f}")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
