# CYCLE-001 — Agent D Viewer causal QA

- WORK-ID: `CYCLE001-D-VIEWER-QA-001`
- Owner: D
- Starting branch: `feat/unified-nt8-viewer-20260920`
- Starting HEAD: `ba970b39dcbee867ce5ab5a78f6e1d26b83158b1`
- Audit branch: `qa/cycle001-d-viewer-causal-smoke`
- Scope: synthetic pre-holdout causal QA only
- Outcomes: disabled
- Holdout: disabled
- Promotion ceiling: `LESSON_CANDIDATE`

## Material checks

1. Executed the five producer/exporter causal functions from `tests/bridge/test_bigtrap2_available_ts.py`: 5/5 PASS.
2. Added an independent three-check smoke at `tests/qa/test_cycle001_viewer_causal_smoke.py`.
3. Executed the smoke directly: 3/3 PASS, including real headless Chromium.
4. Verified that a tick-formed legacy zone without `available_ts` remains `UNAVAILABLE` even when displayed on `time_5m`.
5. Verified a single strict `parseBarDurationSec` helper, no `barDurationSec` scope leak, no universal 300-second default, and both renderer call sites using the strict parser.

## Negative findings and repaired audit defects

- First direct focal run was blocked because `pytest` is absent from the environment. The same pure test functions were executed directly and passed.
- First new smoke run failed because the repository root was not on `sys.path`; the test runner was made self-contained.
- Second smoke run found Chromium at `/usr/local/bin/chromium`, not `/usr/bin/chromium`; the explicit executable path was corrected and the browser check passed.

## RUN-LEARNING-PACKET

```txt
run_id / parent_episode: CYCLE001-D-VIEWER-QA-001 / CYCLE-001
code commit + dirty state: ba970b39dcbee867ce5ab5a78f6e1d26b83158b1 + two exclusive uncommitted audit files before push
dataset version + hashes: none; synthetic fixtures only
config/prompt hash: not applicable
construct_id + measurement contract: VIEWER-CAUSAL-AVAILABILITY; display_bar_key must not determine formation or availability
causal window and availability: synthetic timestamps strictly before 2026-07-01; missing explicit availability => abstain unless temporal formation is explicit
cardinality / coverage / missingness: 5 existing focal checks + 3 independent checks; no market rows
result summary: 8/8 PASS after repairing two audit-environment defects
negative results: pytest unavailable; wrong initial Chromium path; both preserved above
triangulation agreement/disagreement: exporter unit behavior, static renderer audit and real Chromium helper execution agree
measurement failures: none after runner repair
software/data defects: no PR #48 causal regression reproduced in tested scope; full canonical page/data browser integration remains untested
repairs attempted: self-contained sys.path; correct Chromium executable
sensitivity / robustness: tick legacy, valid temporal formation, invalid bar keys, zero-duration time key
new counterexamples: time_5m display applied to legacy tick zone must remain UNAVAILABLE
new constraints/gates: browser smoke must not rely on guessed Chromium path; no 300-second fallback
novelty class: QA_CAPABILITY
next best hypothesis: exercise canonical index with a minimal generated data bundle and assert zero page errors through drawZones/drawCorredoresDemo
artifacts + hashes: tests/qa/test_cycle001_viewer_causal_smoke.py; this report; hashes recorded at checkpoint
hippocampus records emitted: pending Agent B ingestion
review status: REQUESTED_FROM_A
```

## Review correction after Agent A

Agent A returned `CHANGES_REQUIRED`: the first smoke hard-coded `/usr/local/bin/chromium` and assumed Node/Playwright existed, while the current CI workflow does not provision them.

The test now:

- discovers `node` and Chromium with `shutil.which`;
- checks whether the optional Node Playwright module resolves;
- skips only the browser subtest when optional dependencies are unavailable;
- always runs the dependency-free exporter and static renderer falsifiers;
- passes with browser dependencies present and also passes with the browser dependency path removed, recording one explicit skip.

This makes the causal gate portable without weakening the static fail-closed checks or adding CI dependencies.

## Limitations

This checkpoint validates the temporal helper and exporter fail-closed contract. It does not certify the complete canonical Viewer, CI, economic behavior, outcomes, validation or holdout.

Aporte al referente: agrega un falsificador independiente y portable que impide que el timeframe de display fabrique disponibilidad causal para zonas legacy tick-driven, y preserva los fallos del entorno como aprendizaje reproducible.
