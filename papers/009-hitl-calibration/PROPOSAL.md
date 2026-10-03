> **Paper 009 proposal — Calibrating human oversight.** Imported 2026-06-07 from the local
> outline `P6` (`ongoing-papers/papers/06-hitl-calibration/`). Read with the
> [`ROADMAP.md`](../ROADMAP.md) deltas in mind: **monorepo** — features are `qfire`
> modules, not `haarf-*` crates or spin-out repos — and **confidential-enclave**
> production deployment, validated locally on Ollama via the OpenAI-compatible
> bridge. The threat model, hypotheses, experiments, datasets, and figures below
> are the pre-registered working plan; they are reconciled against the gateway as
> built at the feature-spec (stage 2) and paper-spec (stage 4) gates.

---

# Paper 6 — Calibrating Human Oversight: The Cost of Safety in Clinical AI Agents

**Crate:** `haarf-oversight` · **New dataset:** HAARF-Triage · **Status:** outline

## Abstract

Security controls that block too aggressively are themselves a clinical hazard: a
delayed order or a flood of low-value approval prompts causes alarm fatigue and patient
harm. HAARF specifies human oversight (C4) but does not quantify the *operating cost* of
its controls or how to route uncertain actions to clinicians efficiently. We study the
precision/recall and false-deny burden of the HAARF gateway's controls, design a
**risk-calibrated escalation** mechanism (`haarf-oversight`) that sends only genuinely
ambiguous actions to humans, and contribute **HAARF-Triage**, a labeled set of agent
actions with expert escalate/allow/deny decisions and time-to-care annotations. This is
the paper that makes the other controls *adoptable*: it tells deployers where to set the
dial.

## Stakeholders & expert-in-the-loop

Calibrating an oversight dial is a clinical judgment, not just a statistics exercise, so
the design and labels must be grounded in the people who live with the consequences:

- **Frontline clinician (escalation recipient)** — they are the human the router pages,
  so their answer defines the ground-truth allow/deny/escalate boundary and their
  tolerance sets the achievable prompt budget.
- **Bedside / charge nurse** — alarm fatigue is most acute in nursing; they reveal how
  prompt volume degrades response quality and validate the load model behind C4.
- **Human-factors / clinical-usability engineer** — quantifies attention load,
  interruption cost, and prompt design so over-escalation is measured, not assumed.
- **Patient-safety officer** — owns the FA/FB harm trade-off and signs off on the
  recommended operating point as an acceptable institutional risk posture.
- **Biostatistician** — fixes the precision/recall and calibration methodology (ECE,
  Brier, false-deny operating points, cost-weighted utility) so the dial is defensible.
- **Clinical workflow / change-management lead** — ensures escalation routing fits real
  shift structure and coverage, so the dark-launch-to-enforce path is actually adoptable.
- **Patient representative** — voices delayed-care harm from over-blocking, keeping
  time-to-care weighted against missed-harm rather than optimizing for the system alone.

## Problem framing

Every control produces ALLOW/DENY/ESCALATE. We care about four costs:
- **False deny (FB)** — blocking a safe, needed action ⇒ delayed care.
- **False allow (FA)** — permitting a harmful action ⇒ direct harm.
- **Over-escalation (OE)** — flooding clinicians ⇒ alarm fatigue, slow response.
- **Latency-to-care (TTC)** — wall-clock from intent to safe execution.

The thesis: there is a tunable operating point per tool-risk class, and naive
"block-everything-suspicious" is Pareto-dominated.

## Research questions

- **RQ1** What is the deny/escalate rate and false-block burden of each HAARF control
  in dark (audit-only) vs. enforcing mode on realistic traffic?
- **RQ2** Can a calibrated risk score route escalations so clinicians see only the
  ambiguous tail without raising false-allow?
- **RQ3** How does escalation volume trade against time-to-care and missed-harm?
- **RQ4** Does alarm fatigue (modeled via response degradation under load) change the
  optimal threshold?

## Hypotheses

- **H1** A non-trivial fraction (≥ 15%) of baseline-blocked actions are actually safe
  (false blocks) — i.e. naive strict enforcement has a real care-delay cost.
- **H2** Risk-calibrated escalation reduces clinician prompt volume by ≥ 60% at equal
  or lower false-allow vs. fixed-threshold escalation.
- **H3** There exists a per-risk-class operating point achieving FA ≤ target *and*
  TTC within clinical SLA; we can publish it as default gateway config.
- **H4** Modeling alarm fatigue shifts the optimal threshold measurably (showing
  static thresholds are mis-set when load is ignored).

## Experiments → figures

- **E1 Control burden (→ Fig 1):** per-control deny/escalate/false-block rate, dark vs.
  enforce; stacked bars.
- **E2 Calibration curves (→ Fig 2):** reliability diagram of the risk score (predicted
  vs. actual harm) + ECE before/after calibration.
- **E3 Escalation policy (→ Fig 3):** ROC of escalate-vs-autodecide; volume vs.
  false-allow for {fixed threshold, calibrated, cost-sensitive}.
- **E4 Care-delay frontier (→ Fig 4):** time-to-care vs. missed-harm across operating
  points; mark the recommended default.
- **E5 Alarm-fatigue model (→ Fig 5):** optimal threshold vs. clinician load /
  response-degradation function.
- **E6 End-to-end (→ Fig 6):** full gateway (all paper layers on) FA/FB/OE/TTC at the
  recommended config — the "deployable HAARF" summary figure.

## Datasets

**Public:**
- The other papers' benchmarks (HAARF-MA/Exfil/Poison/Policy) supply the *attack*
  positives; **Synthea** + **τ-bench**-style legitimate workflows supply the negatives
  (safe actions that must not be blocked).
- **MIMIC-IV** order/event timing (credentialed) to ground realistic time-to-care
  distributions, or Synthea timestamps as the open substitute.
- Calibration methodology references (temperature scaling, ECE) — methods, not data.

**New — HAARF-Triage (the contribution):**
- A pooled action stream (safe + attack, drawn from all HAARF benchmarks) where each
  action has an **expert label**: allow / deny / escalate, *plus* a severity and a
  plausible time-to-care impact.
- Multi-rater labels (≥ 3 clinicians) with inter-rater agreement, so the "right"
  decision boundary is empirically grounded, not assumed.
- A clinician-load / response model parameterization for the alarm-fatigue study.
  Apache-2.0, synthetic actions + expert annotation.

## Validation & statistics

- Calibration: **Expected Calibration Error (ECE)**, reliability diagrams, Brier score;
  compare raw vs. temperature-scaled risk.
- Decision quality: precision/recall/F1 per class with 95% CIs; cost-weighted utility
  using clinician-elicited cost ratios (FA ≫ FB ≫ OE).
- Inter-rater reliability (Fleiss' κ) reported for HAARF-Triage labels.
- Sensitivity analysis over the cost ratios (the recommended operating point should be
  robust within a plausible range).
- **Threats to validity:** expert labels are simulated-case judgments not real
  bedside decisions; alarm-fatigue is modeled, not measured in situ — both stated
  plainly as limitations.

## Rust components (`haarf-oversight`)

- **Risk scorer:** aggregates upstream control signals (deny reasons, taint level,
  provenance trust, policy margin) into a calibrated risk in [0,1].
- **Escalation router:** maps risk × tool-risk-class → {auto-allow, auto-deny,
  escalate}; thresholds are config (the paper ships defaults).
- **Escalation channel:** an `Escalate(EscalationTicket)` decision that parks the action,
  notifies a clinician, and resumes on response (with timeout fallback policy).
- **Load-aware throttle:** optional dynamic threshold responding to outstanding-prompt
  load (the alarm-fatigue mechanism).
- Calibration is offline-fit on HAARF-Triage and shipped as versioned parameters
  (audited, Paper 2).

```rust
enum OversightOutcome { AutoAllow, AutoDeny, Escalate(EscalationTicket) }
fn route(risk: f32, class: ToolRisk, load: Load, cfg: &Calibration) -> OversightOutcome
```

## Server / proxy design

- `haarf-oversight` is the **last decision layer** before execution: it consumes the
  (Allow/Deny/Transform) signals of all prior layers plus their confidence and decides
  whether a human is needed.
- Escalation tickets and their resolutions are first-class audited events (Paper 2);
  the loop integrates with break-glass (Paper 3).
- Dark-launch mode logs what *would* have escalated — this is how E1/E2 data is gathered
  before enforcement, and the recommended way every deployment tunes its dial.

## Metrics

| Metric | Definition | Target |
|---|---|---|
| FA | False-allow (harm permitted) | ≤ target (cost-set) |
| FB | False-block (safe action denied) | minimized at FA target |
| OE | Over-escalation / prompt volume | ≥ 60% reduction vs. fixed |
| TTC | Time-to-care (safe action) | within clinical SLA |
| ECE | Risk-score calibration error | report, ↓ after scaling |

## Repo scaffold

```
haarf-triage/
├── crates/haarf-oversight/         # risk scorer + router + escalation + throttle
├── dataset/haarf-triage/           # pooled actions + multi-rater labels + load model
├── analysis/                       # calibration + cost-sensitivity notebooks (Rust/py)
├── figures/
└── paper/
```
