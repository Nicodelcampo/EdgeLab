# Registro de ramas remotas — 2026-10-14

Estado: VIGENTE
Fecha: 2026-10-14

Generado con `git rev-list --count origin/foundation/f0b-compatibility-probe..<rama>` sobre 174 refs de `origin`. **Ahead = commits que la rama tiene y `foundation` no.** `main` ya está integrada (ahead 0).

- Ramas totales: 173; **integradas por completo (ahead 0): 61**; con trabajo propio sin integrar: 112.
- Regla (`CLAUDE.md`): rama auxiliar → se mergea de vuelta el mismo día. Estas ramas de investigación (bt2a, avolcluster, audit/*) son líneas congeladas de mediciones ya cerradas o instrumentos de auditoría; **no se mergean en bloque**. Para rescatar algo: checkout por ruta + pruebas, como la release líquida.

| Rama | Ahead | Último commit | Asunto |
|---|---:|---|---|
| `claude/vibrant-clarke-s9z6e2` | 208 | 2026-10-14 | EMAZ-D3: resultado de la correccion del sesgo (efecto nulo con control emparejad |
| `research/bt2a-nq-gate1-runner-impl-v1-20260831` | 173 | 2026-09-01 | feat(bt2a-sltp-be): mechanics smoke test for the SL/TP+breakeven exit engine |
| `audit/notion-ai-sltp-p2b-provenance-20260830` | 149 | 2026-09-01 | audit: register causal contract-regime standard |
| `data/liquid-release-20261014` | 139 | 2026-10-14 | tools(liquid-release): verificador mas rapido (pc.unique en contract), herencia  |
| `research/bt2a-nq-gate1-nrand-capacity-t2-20260830` | 133 | 2026-08-31 | docs(bt2a-nq-gate1): registra tokens 3 y 4 de Nico (implement + run) 2026-08-31  |
| `feat/research-ops-supervisor-mvp` | 130 | 2026-10-14 | docs(audit): preserve v4 preparation block without claiming payload validation |
| `research/bt2a-nq-gate1-power-closure-20260830` | 120 | 2026-08-30 | fix(bt2a-nq-gate1): D6 corrigendum ratified by Nico — coarse_phase is 4-hour blo |
| `research/bt2a-nq-gate1-outcomes-runner-v1-20260830` | 116 | 2026-08-30 | docs(bt2a-nq-gate1): fix residual "2-hour" docstring after D6 corrigendum ratifi |
| `research/bt2a-nq-v2-sweep-v1-20260829` | 113 | 2026-08-30 | feat(bt2a-nq-gate1): close 4 Kaggle bindings; align runner contract to authorize |
| `research/bt2a-gc-sltp-breakeven-design-v1-20260830` | 109 | 2026-08-30 | feat(sltp-campaign): freeze-draft spec for the SL/TP+breakeven campaign (post-D5 |
| `research/avolcluster-nq-lifecycle-v1-20260830` | 108 | 2026-08-30 | docs(research): spec lifecycle v1.2.0 — contrato de paralelismo born-parallel po |
| `research/bt2a-nq-gate1-v1-20260829` | 105 | 2026-08-29 | Update V2 sweep test for FROZEN state (see prior commit for rationale) |
| `research/bt2a-nq-target-free-selection-v1-20260828` | 97 | 2026-08-29 | docs(bt2a-nq): record early-stop decision at 2/5 contracts |
| `research/bigtrap2-nq-tickframes-sweep-v1-20260828` | 79 | 2026-08-28 | Merge remote-tracking branch 'origin/infra/kaggle-frozen-execution-v1-20260828'  |
| `feat/ssrn-cortex-port-main-20261009` | 74 | 2026-10-09 | docs(kaggle): faltantes de la estructura de corridas en Kaggle (iterados) |
| `infra/kaggle-frozen-execution-v1-20260828` | 65 | 2026-08-28 | feat(data): register canonical gate1 GC, ZB, and 13-month continuous MBT |
| `research/avolcluster-nq-gate1-infra-v1-20260828` | 51 | 2026-08-30 | fix(avolcluster-nq-gate1b-gate3): actually stage the stale-hash fix; resolve 3 r |
| `research/bt2a-p2a-clock-heterogeneity-v1-20260827` | 51 | 2026-08-28 | docs(research): publish finalized GC clock heterogeneity diagnostic report |
| `research/bt2a-p2b-economic-gc-v1-20260827` | 43 | 2026-08-29 | fix(bt2a-p2b-gc): simulate_cell's strictly-after check must use (ts, source_row) |
| `research/avolcluster-nq-microticks-v1-20260828` | 35 | 2026-08-28 | feat(research): add aVolClusterPOI micro-tick and fast-bar target-free sweep on  |
| `work/bt2a-gate2-p2a-freeze-20260826` | 35 | 2026-09-06 | feat(research): add EMA reversion filter findings, NT8 indicators, and execution |
| `feat/frontier-expansion-lab-20260921` | 32 | 2026-09-21 | fix(execution): close queue and packet-evidence gaps |
| `research/zamr1-zone-atlas` | 28 | 2026-08-28 | Merge branch 'research/bigtrap2-local-displacement-null' into research/zamr1-zon |
| `work/bt2a-gate2-l2-hardening-20260826` | 28 | 2026-08-26 | docs(bt2a): finalize Gate 2 and L2 hardening audit |
| `feat/ym-density-corridor-discovery-20260921` | 23 | 2026-09-21 | feat(brain): adopt prior-density representation from target-free NQ evidence |
| `results/bt2a-p2a-v1-r1-20260827` | 23 | 2026-08-27 | docs(research): restore Aporte al referente in LEER.md |
| `research/avzvol-longevity-full-grid` | 21 | 2026-10-12 | research: audit final MNQ09-26 focal and reconcile five frozen replicas |
| `work/crypto-context-foundation-20260824` | 21 | 2026-08-24 | docs(crypto): inventario de fuentes medido + hueco de LOT_SIZE historico declara |
| `research/bigtrap2-distance-matched-null` | 15 | 2026-08-28 | Merge branch 'audit/p0-bigtrap2-drift' into research/bigtrap2-distance-matched-n |
| `research/mnq-pullback-extension-20261001` | 14 | 2026-10-01 | Record MNQ extension43 weakens SEP;197 no validated edge |
| `work/bt2a-gate2-l2-audit-20260826` | 14 | 2026-08-26 | docs(bt2a): auditoria local forense de outputs nocturnos (solo lectura) |
| `fix/g2-a1-calibration-hardening` | 13 | 2026-08-28 | Merge branch 'foundation/f0b-compatibility-probe' into fix/g2-a1-calibration-har |
| `feat/edge-replica-port-20261004` | 12 | 2026-10-04 | docs(strategy): persist verified diagnostic integration snapshot |
| `research/ema-pullback-economic-20261001` | 12 | 2026-10-01 | Record EMA pullback economic result: no advance, matched controls and costs; MED |
| `review/research-ops-117` | 11 | 2026-10-12 | feat(research-ops): read-only composite status across queue/dispatch/checkpoint |
| `work/hp007-rejection-revisit-campaign-v2-20260915` | 11 | 2026-09-15 | docs(hp007): quarantine remaining machine-readable preregistration and ledger in |
| `fix/hft-native-termination-fresh-replay-20260918` | 10 | 2026-09-18 | fix(hft): make certification evidence machine-verifiable |
| `research/ema-pullback-census-20261001` | 10 | 2026-10-01 | research: close EMA20 pullback frequency census; TF1 selected without outcomes |
| `work/bt2a-gate1-all5-20260826` | 10 | 2026-08-26 | fix(gate1): restore frozen spec byte provenance |
| `feat/edge-brain-learning-governor-20260924` | 9 | 2026-09-24 | Harden one-shot audit ledger with owner-only POSIX custody, fail-closed DB openi |
| `research/avolcluster-compression-v1-20260827` | 9 | 2026-08-27 | fix(avol): fail closed and correct two-stage scientific scope |
| `research/gate-regime-context` | 9 | 2026-08-24 | docs(gate): reclasifica cimiento y cierra auditoría de once defectos |
| `feat/ym-bt2a-economic-search-20260921` | 7 | 2026-09-21 | fix(research): enforce session boundary and record negative screen |
| `prep/indicator-onboarding-registry` | 7 | 2026-08-28 | Merge branch 'foundation/f0b-compatibility-probe' into prep/indicator-onboarding |
| `research/ema3-25t-pullback-grid-20261002` | 7 | 2026-10-02 | fix: support canonical integer-tick parquet schema |
| `research/rty60-expanded-20261001` | 7 | 2026-10-01 | research: record RTY60 175-session expansion failure and MEDIDO together |
| `fix/g2-a1-statistical-semantics` | 6 | 2026-08-10 | docs(g2): replace canonical contract and persist calibration evidence |
| `research/avzvol-six-contract-replication` | 6 | 2026-10-11 | research: complete fixed six-contract AVZVOL replication without retuning |
| `research/momentum-short-economic-20261001` | 6 | 2026-10-01 | research: frozen six-cell momentum short economic screen, no validated edge; pre |
| `work/bt2a-gate1-runner-20260826` | 6 | 2026-08-26 | docs(gate1): bind clean-76 registry to audited payload |
| `work/hp007-campaign-v2-foundation-20260915` | 6 | 2026-09-15 | docs: pin HP-007 campaign to contractual anchor 29cad93 |
| `agent-c/cycle-001-kaggle-access-audit` | 5 | 2026-09-22 | docs(research): record Kaggle public-dataset custody incident packet |
| `audit/edgelab-continuous-reference-20260920` | 5 | 2026-09-22 | Merge branch 'feat/reconstruct-edge-brain-complete-20260920' into audit/edgelab- |
| `docs/handoff-2026-08-25` | 5 | 2026-08-25 | docs(mbt): auditoria del config a-priori de Antigravity (TW25; q 95 vs 97.5 pend |
| `feat/ym-bt2a-retest-kaggle-pilot-20260920` | 5 | 2026-09-21 | fix(research): require post-trigger observed retest fill |
| `infra/kaggle-spec-framework-v2-20261009` | 5 | 2026-10-09 | feat(infra): anchor full approved ES/NQ aggregate store and verified private pub |
| `research/avzvol-fixed-replication` | 5 | 2026-10-11 | research: fixed contract replication rejects generalizing focal return edge |
| `research/bigtrap2-multiframe-ml` | 5 | 2026-08-11 | research(multiframe): opus audit, dataset contract v1, fail-closed validator and |
| `research/momentum-frequency-targetfree-20261001` | 5 | 2026-10-01 | research: census higher-frequency momentum without outcomes; preserve mechanical |
| `audit/cycle-001-agent-a-currentness-20260921` | 4 | 2026-09-22 | fix(audit): restore currentness map content with checkpoint 003 |
| `docs/es-apriori-2026-08-25` | 4 | 2026-08-25 | fix(research): close ES causal audit inconsistencies |
| `fix/cycle001-ci-common-cause-20260922` | 4 | 2026-09-22 | fix(ci): triage 57 new ULP candidates via overlay and skip data-dependent tests  |
| `research/avzvol-dense-excursions` | 4 | 2026-10-11 | research: dense excursion campaign and corridor sensitivities (3/3) |
| `research/rty-momentum-validation-20261001` | 4 | 2026-09-30 | research: freeze RTY momentum diagnostics, record G1 failures and G2 blocks |
| `claude/focused-fermat-qjt805` | 3 | 2026-10-03 | docs(handoff): traspaso de la sesión nube del 26/09 al 03/10 (nulo f en duda, pi |
| `docs/edgelab-product-map-20261009` | 3 | 2026-10-10 | feat(core): reconcile foundation data contracts, typed memory dependencies and p |
| `docs/traceability-refresh-20260828` | 3 | 2026-08-28 | docs(traceability): add machine-readable remote snapshot |
| `feat/r3-gated-window-20261010` | 3 | 2026-10-11 | fix(test): usar add_selection_review tras rebase sobre main (K-nuevo requisito d |
| `fix/funnel-stage-isolation-parity-20261003` | 3 | 2026-10-03 | test(cuda): persist successful Kaggle CPU GPU parity with provenance |
| `research/cross-momentum-multiasset-20261001` | 3 | 2026-09-30 | Research: more EMA crosses and multiasset momentum; 0/24 passes, RTY candidate o |
| `work/hp007-causal-campaign-v1-20260915` | 3 | 2026-09-15 | research(hp007): ejecucion formal, preregistrada y causal de la primera campana  |
| `work/indicator-coordinate-store-v1-20260827` | 3 | 2026-08-27 | ci(store): verify coordinate pipeline contract |
| `agent-b/cycle-001-learning-packet-ingestion` | 2 | 2026-09-22 | fix(edge-brain): make packet adapter tests CI-portable |
| `docs/h-cond-1-lux-imb` | 2 | 2026-08-10 | docs: enlazar el protocolo LUX-IMB desde el README |
| `docs/post-merge-sync-2026-08-10` | 2 | 2026-08-10 | docs: avoid self-referential branch tip |
| `feat/ssrn-bibliographic-cortex-20260921` | 2 | 2026-09-22 | Merge branch 'feat/reconstruct-edge-brain-complete-20260920' into feat/ssrn-bibl |
| `fix/bigtrap2-v252-tick-export` | 2 | 2026-08-11 | BigTrap2 v2.5.2: fix del defecto de atribucion temporal + drenaje de cola |
| `indicator/four-pass-sparse-stop-first-20261001` | 2 | 2026-10-01 | FP4 v0.2: MNQ physical30tick floor, explicit crossasset profiles, targetfree evi |
| `qa/cycle001-d-kaggle-access-review` | 2 | 2026-09-21 | test(kaggle): adversarially review access contract |
| `qa/cycle001-d-viewer-causal-smoke` | 2 | 2026-09-21 | test(viewer): make causal browser smoke portable |
| `research/avzvol-exploratory-bias-protocol` | 2 | 2026-10-11 | research: correct full-source alerts against catalog selected261 and separate wa |
| `research/ema3-multiasset-20261001` | 2 | 2026-09-30 | Research: frozen EMA3 multi-asset screen, 0/24 passes; record evidence and MEDID |
| `work/hp007-corridor-measurement-v1-20260915` | 2 | 2026-09-15 | fix(research): reuse canonical holdout boundary |
| `audit/canonical-liquidity-20261004` | 1 | 2026-10-04 | audit(data): record canonical sanitation blockers and add fail-closed research g |
| `audit/edge-discovery-factory-foundation-20260919` | 1 | 2026-09-20 | audit(custody): reconcile canonical manifest and close NQ v6 download custody |
| `backup/foundation-f0b-local` | 1 | 2026-07-22 | docs: root README for cross-machine handoff |
| `docs/estado-real-2026-08-10` | 1 | 2026-08-10 | docs: align repository with canonical state 2026-08-10 |
| `docs/h-sweep-1-ym-prerange` | 1 | 2026-08-10 | docs(research): registrar familia YM-PRERANGE e hipotesis H-SWEEP-1 |
| `docs/kaggle-es-upstream-repair-20261010` | 1 | 2026-10-10 | Trace ES Sunday roll to raw event evidence and specify upstream repair inputs |
| `docs/mbt-apriori-2026-08-25` | 1 | 2026-08-25 | docs(research): configuracion a-priori BigTrap2Absorption para MBT 2026-08-25 |
| `docs/safe-agent-onboarding-20260915` | 1 | 2026-09-15 | docs(repo): add lossless agent onboarding snapshot |
| `feat/crosshair-density-profile-20260918` | 1 | 2026-09-18 | feat(viewer): add causal crosshair density profile applicator |
| `feat/reconstruct-edge-brain-complete-20260920` | 1 | 2026-09-22 | fix(ci): repair common CYCLE-001 failures without weakening gates (#55) |
| `fix/hft-certification-provenance-playwright-20260918` | 1 | 2026-09-17 | fix(hft): disclose parity provenance and provision Playwright |
| `fix/hftzones-nq-parity-certification-v2-20260915` | 1 | 2026-09-15 | feat(hp007): audit and certify HFTZones NQ parity V2, harden comparator, and imp |
| `infra/funnel-stage-isolation-cpu-20261010` | 1 | 2026-10-10 | fix(funnel): isolate CPU stage outcomes, bind frozen split and enforce real matr |
| `infra/kaggle-agent-entrypoint-20261010` | 1 | 2026-10-10 | Add pinned agent dataset discovery and diagnose premature ES roll; keep research |
| `infra/kaggle-coverage-raw-quality-20261010` | 1 | 2026-10-10 | Declare full requested coverage; audit raw tick identities; block unreviewed win |
| `infra/kaggle-full-raw-audit-quarantine-20261010` | 1 | 2026-10-10 | Audit all primary tick sources and quarantine unresolved NQ source discrepancy |
| `infra/kaggle-main-quality-gated-20261010` | 1 | 2026-10-10 | Integrate technical Kaggle framework with real QA and fail-closed causal researc |
| `infra/research-data-gate-session-reader-20261010` | 1 | 2026-10-10 | Integrate opt-in research gate and homogeneous session reader with explicit cove |
| `port/r1-ssrn-selective-20261010` | 1 | 2026-10-11 | port(edge-brain): R1 port SSRN selectivo de #67 sin retroceder main |
| `preserve/f0b-local-divergente-2026-08-04` | 1 | 2026-07-22 | docs: root README for cross-machine handoff |
| `registry/gex-familia` | 1 | 2026-08-20 | gex: registro de familia GEX-NIVELES (observacional) |
| `research/avzvol-frequency-first-grid` | 1 | 2026-10-11 | research: frequency-first survey of exposed AVZVOL parameter grid; five-axis cam |
| `research/avzvol-height-context` | 1 | 2026-10-11 | research: compare high-support heights, context sensitivity and simultaneous cof |
| `research/avzvol-partial-return` | 1 | 2026-10-11 | research: causal partial-return symmetric prototype; market measurement pending |
| `research/avzvol-source-reaudit` | 1 | 2026-10-11 | research: recover six tick pins, full QA and quote semantics; market campaign re |
| `research/avzvol-tick-pilot` | 1 | 2026-10-11 | research: complete sequence-causal tick pilot and 1536 frequency configurations |
| `research/hp008-causal-multicontract-20260918` | 1 | 2026-09-17 | research(hp008): add causal multicontract results |
| `research/rty-no-l2-six-tests-20260930` | 1 | 2026-09-30 | research: freeze and record RTY price-only six-cell screen, 0 joint passes |
| `work/nq-causal-foundation-v1-20260915` | 1 | 2026-09-15 | feat(nq): foundation v1 - inventory, session gate, lookahead tests and memo |
