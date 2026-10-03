#!/usr/bin/env python3
"""Python mirror of the Rust oversight scorer + router (src/oversight/{scorer,router}.rs).

Loads the FITTED calibration (`datasets/009-hitl-calibration/calibration_fitted.json`, produced by
fit_calibration.py) so the offline experiments score TriageBench with the same model the gateway ships.
The Rust `Calibration::default()` is kept in sync with this file (asserted by a Rust test). Falls back to
the hand-set defaults if the fitted config is absent.
"""
import json
import math
import os

_FITTED = "datasets/009-hitl-calibration/calibration_fitted.json"

_DEFAULT_CAL = {
    "bias": -2.5,
    "w_block_conf": 3.0,
    "w_taint": 2.0,
    "w_policy": 2.0,
    "w_provenance": 1.0,
    "w_identity": 2.5,
    "w_tool_risk": 1.5,
    "temperature": 1.0,
}
_DEFAULT_BANDS = {
    "low": (0.30, 0.90),
    "medium": (0.20, 0.85),
    "high": (0.12, 0.80),
    "life_critical": (0.05, 0.75),
}

TOOL_RISK_INDEX = {"low": 0, "medium": 1, "high": 2, "life_critical": 3}


def _load():
    if os.path.exists(_FITTED):
        cfg = json.load(open(_FITTED))
        bands = {k: tuple(v) for k, v in cfg["bands"].items()}
        cal = {k: cfg[k] for k in _DEFAULT_CAL}
        return cal, bands
    return dict(_DEFAULT_CAL), dict(_DEFAULT_BANDS)


CAL, BANDS = _load()


def logit(sig, tool_risk, cal=CAL):
    tool_idx = TOOL_RISK_INDEX[tool_risk] / 3.0
    return (
        cal["bias"]
        + cal["w_block_conf"] * sig["max_block_confidence"]
        + cal["w_taint"] * (sig["taint_level"] or 0.0)
        + cal["w_policy"] * (sig["policy_margin"] or 0.0)
        + cal["w_provenance"] * (sig["provenance_trust"] or 0.0)
        + cal["w_identity"] * (sig["identity_trust"] or 0.0)
        + cal["w_tool_risk"] * tool_idx
    )


def score(sig, tool_risk, temperature=None, cal=CAL):
    """Calibrated risk in [0,1]. `temperature` overrides cal['temperature'] when given."""
    t = max(1e-6, temperature if temperature is not None else cal["temperature"])
    return 1.0 / (1.0 + math.exp(-(logit(sig, tool_risk, cal) / t)))


def route(risk, tool_risk, allow_shift=0.0, bands=BANDS):
    """Mirror of router::route. `allow_shift` raises allow_below (the throttle)."""
    allow_below, deny_above = bands[tool_risk]
    allow_below = min(allow_below + allow_shift, deny_above)
    if risk < allow_below:
        return "auto_allow"
    if risk > deny_above:
        return "auto_deny"
    return "escalate"
