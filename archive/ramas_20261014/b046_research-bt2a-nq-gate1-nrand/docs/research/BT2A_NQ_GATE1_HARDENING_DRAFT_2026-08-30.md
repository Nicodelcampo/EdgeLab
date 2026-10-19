# BT2A NQ Gate 1 — hardening draft from the 2026-08-28 base

- Date: 2026-08-30
- Source: user delegation at 00:01 ART plus repository sequence.
- Base limitation: GitHub tools required admin re-approval, so this is a rebaseable patch against the supplied 28-Aug ZIP, not a claim about the live tip.
- Outcomes opened by this work: false.
- Holdout touched by this work: false.

## Closed in code

1. An informal 2/5 choice can no longer be mislabeled as `SELECTED_STABLE_NQ_CONFIGURATION`.
2. The Event Store accepts the informal route only through a hash-bound, frozen provenance amendment and forces `confirmatory_eligible=false` / `promotion_eligible=false`.
3. The absence of a macro adjustment is made explicit; an empty unknown calendar is not silently accepted.
4. Power now exposes a missing assumption in the original 11-field preflight: MDE + ICC + session count do not determine power without paired-session variance and arm density.
5. A runner contract records the exact unresolved choices and keeps both implementation and execution disabled.

## Intentionally still blocked

- Three missing fixed-config coordinate partitions and their all-5 manifest: being produced externally; no hashes in this ZIP.
- Clean BigTrap2 V2 result: external Kaggle run reported in progress.
- Event Store build: amendment is draft and runtime hashes are null.
- Gate 1 preflight: power assumptions/arm densities are not frozen.
- Outcome runner: current repo protocol forbids implementation before preflight and the current spec does not define primary outcome encoding, primary contrast, multiplicity across comparators or paired-session variance.

## Aporte al referente

The route to Gate 1 is made executable without laundering informal provenance or fabricating power; remaining blockers correspond to real external artifacts or explicit scientific decisions.
