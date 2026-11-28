# Inventario de ramas con trabajo fuera de la línea principal (2026-11-25)

Estado: VIGENTE  
Fecha: 2026-11-25  

Línea principal: `foundation/f0b-compatibility-probe`, que desde hoy incluye la línea de producción `fix/fundedsync-il-parity`,
el visor `viewer/lineas-horizontales` (PR #198) y la re-medición FS-IL `claude/vibrant-clarke-s9z6e2` (PR #203).

Cada rama de abajo tiene commits que la línea principal no tiene. **Nada se borró.** Cada una quedó además
preservada con una etiqueta `archivo/20261125/<rama>` en el remoto, así que borrar la rama no pierde ningún commit.
Las ramas con cambios de semántica de validación (p. ej. `fix/g2-a1-*`) NO se mergean sin decisión de Nico.

`autopilot/state` diverge a propósito (estado del autopilot) y no se archiva ni se borra.

| rama | commits fuera | último commit | autor | PR abierto | sha | último mensaje |
|---|---:|---|---|---|---|---|
| `autopilot/state` | 454 | 2026-11-25 | edgelab-autopilot | — | `69adf35bd5` | autopilot: estado 2026-11-25T09:32:54Z |
| `notion/orb-nq-filtros-20261108` | 18 | 2026-11-08 | Nicodelcampo | — | `2f086b2361` | Registra medición ORB exploratoria y alcance de auditoría |
| `gemini/familias-20261103` | 1 | 2026-11-03 | EdgeLab Baseline | — | `60b7e49a2a` | fix(research): correcciones auditoria 12 familias R (EXCLUIR_EVENTOS, cierre pre-FOMC/macro, relojes |
| `fix/install-git-como-edgelab` | 1 | 2026-10-19 | Armind - Fatek PLC | #125 | `66d1bdb5b5` | fix(deploy-debian): git como edgelab en install.sh y update.sh |
| `feat/research-ops-kaggle-control` | 13 | 2026-10-15 | Gonzalo | — | `6d38ec7d88` | docs(research-ops): plan del agente investigador autónomo en SV1 (inventario de los tres diseños, fa |
| `data/liquid-release-20261014` | 139 | 2026-10-14 | EdgeLab Baseline | — | `7afe22d492` | tools(liquid-release): verificador mas rapido (pc.unique en contract), herencia explicita por SHA-25 |
| `docs/agente-espiral-plan-20261014` | 4 | 2026-10-14 | Gonzalo | #119 | `b072eae434` | docs(plans): plan de implementación de las 17 mejoras del embudo, por impacto, con tests por tarea |
| `feat/research-ops-supervisor-mvp` | 130 | 2026-10-14 | Nicodelcampo | #117 | `aff48a81a2` | docs(audit): preserve v4 preparation block without claiming payload validation |
| `research/avzvol-longevity-full-grid` | 21 | 2026-10-12 | Nicodelcampo | #116 | `eca53ec227` | research: audit final MNQ09-26 focal and reconcile five frozen replicas |
| `review/research-ops-117` | 11 | 2026-10-12 | Nicodelcampo | #118 | `a95227bb31` | feat(research-ops): read-only composite status across queue/dispatch/checkpoint |
| `feat/r3-gated-window-20261010` | 3 | 2026-10-11 | Nicodelcampo | #81 | `ada97b2539` | fix(test): usar add_selection_review tras rebase sobre main (K-nuevo requisito del gate) |
| `port/r1-ssrn-selective-20261010` | 1 | 2026-10-11 | Nicodelcampo | #80 | `ca9e94013e` | port(edge-brain): R1 port SSRN selectivo de #67 sin retroceder main |
| `research/avzvol-dense-excursions` | 4 | 2026-10-11 | Nicodelcampo | #113 | `9731118cf4` | research: dense excursion campaign and corridor sensitivities (3/3) |
| `research/avzvol-exploratory-bias-protocol` | 2 | 2026-10-11 | Nicodelcampo | #111 | `b047753b18` | research: correct full-source alerts against catalog selected261 and separate warmup |
| `research/avzvol-fixed-replication` | 5 | 2026-10-11 | Nicodelcampo | #114 | `5e33121e52` | research: fixed contract replication rejects generalizing focal return edge |
| `research/avzvol-frequency-first-grid` | 1 | 2026-10-11 | Nicodelcampo | #107 | `2985c1c956` | research: frequency-first survey of exposed AVZVOL parameter grid; five-axis campaign not run |
| `research/avzvol-height-context` | 1 | 2026-10-11 | Nicodelcampo | #108 | `1b0e14aa4c` | research: compare high-support heights, context sensitivity and simultaneous coformations |
| `research/avzvol-partial-return` | 1 | 2026-10-11 | Nicodelcampo | #109 | `d1c54dc8a6` | research: causal partial-return symmetric prototype; market measurement pending |
| `research/avzvol-six-contract-replication` | 6 | 2026-10-11 | Nicodelcampo | #115 | `dd77d7d31b` | research: complete fixed six-contract AVZVOL replication without retuning |
| `research/avzvol-source-reaudit` | 1 | 2026-10-11 | Nicodelcampo | #110 | `8a85ac4f1f` | research: recover six tick pins, full QA and quote semantics; market campaign remains blocked |
| `research/avzvol-tick-pilot` | 1 | 2026-10-11 | Nicodelcampo | #112 | `205482002e` | research: complete sequence-causal tick pilot and 1536 frequency configurations |
| `docs/edgelab-product-map-20261009` | 3 | 2026-10-10 | Nicodelcampo | — | `eb6fee7abb` | feat(core): reconcile foundation data contracts, typed memory dependencies and portable settings |
| `docs/kaggle-es-upstream-repair-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `3a6ab4ce51` | Trace ES Sunday roll to raw event evidence and specify upstream repair inputs |
| `infra/funnel-stage-isolation-cpu-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `c5a67075ef` | fix(funnel): isolate CPU stage outcomes, bind frozen split and enforce real matrix budget |
| `infra/kaggle-agent-entrypoint-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `1d83eac40b` | Add pinned agent dataset discovery and diagnose premature ES roll; keep research blocked |
| `infra/kaggle-coverage-raw-quality-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `494e2e1bb7` | Declare full requested coverage; audit raw tick identities; block unreviewed windows |
| `infra/kaggle-full-raw-audit-quarantine-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `4122422da7` | Audit all primary tick sources and quarantine unresolved NQ source discrepancy |
| `infra/kaggle-main-quality-gated-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `e41a59df96` | Integrate technical Kaggle framework with real QA and fail-closed causal research guard |
| `infra/research-data-gate-session-reader-20261010` | 1 | 2026-10-10 | Nicodelcampo | — | `52e42f6f31` | Integrate opt-in research gate and homogeneous session reader with explicit coverage |
| `feat/ssrn-cortex-port-main-20261009` | 74 | 2026-10-09 | Nicodelcampo | #67 | `5c10da451b` | docs(kaggle): faltantes de la estructura de corridas en Kaggle (iterados) |
| `infra/kaggle-spec-framework-v2-20261009` | 5 | 2026-10-09 | Nicodelcampo | #68 | `3845cffd3d` | feat(infra): anchor full approved ES/NQ aggregate store and verified private publication |
| `audit/canonical-liquidity-20261004` | 1 | 2026-10-04 | Nicodelcampo | #65 | `ae8898746d` | audit(data): record canonical sanitation blockers and add fail-closed research gate |
| `feat/edge-replica-port-20261004` | 12 | 2026-10-04 | Nicodelcampo | #66 | `92fc907129` | docs(strategy): persist verified diagnostic integration snapshot |
| `claude/focused-fermat-qjt805` | 3 | 2026-10-03 | Claude | — | `09a46e6125` | docs(handoff): traspaso de la sesión nube del 26/09 al 03/10 (nulo f en duda, pivotes refutados, arq |
| `research/ema3-25t-pullback-grid-20261002` | 7 | 2026-10-02 | Nicodelcampo | — | `1e97460e1f` | fix: support canonical integer-tick parquet schema |
| `indicator/four-pass-sparse-stop-first-20261001` | 2 | 2026-10-01 | Nicodelcampo | — | `1724ed1c10` | FP4 v0.2: MNQ physical30tick floor, explicit crossasset profiles, targetfree evidence |
| `research/ema-pullback-census-20261001` | 10 | 2026-10-01 | Nicodelcampo | — | `db3445448d` | research: close EMA20 pullback frequency census; TF1 selected without outcomes |
| `research/ema-pullback-economic-20261001` | 12 | 2026-10-01 | Nicodelcampo | — | `848e5927a5` | Record EMA pullback economic result: no advance, matched controls and costs; MEDIDO together |
| `research/mnq-pullback-extension-20261001` | 14 | 2026-10-01 | Nicodelcampo | — | `983e58953c` | Record MNQ extension43 weakens SEP;197 no validated edge |
| `research/momentum-frequency-targetfree-20261001` | 5 | 2026-10-01 | Nicodelcampo | — | `51bd5e25bc` | research: census higher-frequency momentum without outcomes; preserve mechanical failure and QA |
| `research/momentum-short-economic-20261001` | 6 | 2026-10-01 | Nicodelcampo | — | `06ffb156f0` | research: frozen six-cell momentum short economic screen, no validated edge; preserve sealed holdout |
| `research/rty60-expanded-20261001` | 7 | 2026-10-01 | Nicodelcampo | — | `29f86de88d` | research: record RTY60 175-session expansion failure and MEDIDO together |
| `research/cross-momentum-multiasset-20261001` | 3 | 2026-09-30 | Nicodelcampo | — | `c51b1e2b50` | Research: more EMA crosses and multiasset momentum; 0/24 passes, RTY candidate only; MEDIDO |
| `research/ema3-multiasset-20261001` | 2 | 2026-09-30 | Nicodelcampo | — | `41e2c25b76` | Research: frozen EMA3 multi-asset screen, 0/24 passes; record evidence and MEDIDO |
| `research/rty-momentum-validation-20261001` | 4 | 2026-09-30 | Nicodelcampo | — | `d9378c62ff` | research: freeze RTY momentum diagnostics, record G1 failures and G2 blocks |
| `research/rty-no-l2-six-tests-20260930` | 1 | 2026-09-30 | Nicodelcampo | — | `0b7c70da1d` | research: freeze and record RTY price-only six-cell screen, 0 joint passes |
| `feat/edge-brain-learning-governor-20260924` | 9 | 2026-09-24 | Nicodelcampo | #58 | `3b4e98cb7a` | Harden one-shot audit ledger with owner-only POSIX custody, fail-closed DB opening, immutable state  |
| `agent-b/cycle-001-learning-packet-ingestion` | 2 | 2026-09-22 | Nicodelcampo | — | `f19baf3fb9` | fix(edge-brain): make packet adapter tests CI-portable |
| `agent-c/cycle-001-kaggle-access-audit` | 5 | 2026-09-22 | Nicodelcampo | — | `5658678d64` | docs(research): record Kaggle public-dataset custody incident packet |
| `audit/cycle-001-agent-a-currentness-20260921` | 4 | 2026-09-22 | Nicodelcampo | — | `e88823104e` | fix(audit): restore currentness map content with checkpoint 003 |
| `audit/edgelab-continuous-reference-20260920` | 5 | 2026-09-22 | Nicodelcampo | #49 | `7b94b1efc1` | Merge branch 'feat/reconstruct-edge-brain-complete-20260920' into audit/edgelab-continuous-reference |
| `feat/reconstruct-edge-brain-complete-20260920` | 1 | 2026-09-22 | Nicodelcampo | #46 | `70daaad098` | fix(ci): repair common CYCLE-001 failures without weakening gates (#55) |
| `feat/ssrn-bibliographic-cortex-20260921` | 2 | 2026-09-22 | Nicodelcampo | #52 | `3cb3fd21d4` | Merge branch 'feat/reconstruct-edge-brain-complete-20260920' into feat/ssrn-bibliographic-cortex-202 |
| `fix/cycle001-ci-common-cause-20260922` | 4 | 2026-09-22 | Nicodelcampo | — | `cf70f44eed` | fix(ci): triage 57 new ULP candidates via overlay and skip data-dependent tests without local data t |
| `feat/frontier-expansion-lab-20260921` | 32 | 2026-09-21 | Nicodelcampo | #54 | `d6adf23539` | fix(execution): close queue and packet-evidence gaps |
| `feat/ym-bt2a-economic-search-20260921` | 7 | 2026-09-21 | Nicodelcampo | — | `a488b39062` | fix(research): enforce session boundary and record negative screen |
| `feat/ym-bt2a-retest-kaggle-pilot-20260920` | 5 | 2026-09-21 | Nicodelcampo | — | `e1d2a6f6c8` | fix(research): require post-trigger observed retest fill |
| `feat/ym-density-corridor-discovery-20260921` | 23 | 2026-09-21 | Nicodelcampo | — | `1532b87544` | feat(brain): adopt prior-density representation from target-free NQ evidence |
| `qa/cycle001-d-kaggle-access-review` | 2 | 2026-09-21 | Nicodelcampo | — | `3a90f8881b` | test(kaggle): adversarially review access contract |
| `qa/cycle001-d-viewer-causal-smoke` | 2 | 2026-09-21 | Nicodelcampo | — | `9175930498` | test(viewer): make causal browser smoke portable |
| `audit/edge-discovery-factory-foundation-20260919` | 1 | 2026-09-20 | nicolasbuttaro-eng | #57 | `3ae3c3e710` | audit(custody): reconcile canonical manifest and close NQ v6 download custody |
| `feat/crosshair-density-profile-20260918` | 1 | 2026-09-18 | Nicodelcampo | #41 | `d2d24933ab` | feat(viewer): add causal crosshair density profile applicator |
| `fix/hft-native-termination-fresh-replay-20260918` | 10 | 2026-09-18 | Nicodelcampo | #34 | `5f2358689c` | fix(hft): make certification evidence machine-verifiable |
| `fix/hft-certification-provenance-playwright-20260918` | 1 | 2026-09-17 | Nicodelcampo | #32 | `2dde9ac523` | fix(hft): disclose parity provenance and provision Playwright |
| `research/hp008-causal-multicontract-20260918` | 1 | 2026-09-17 | Nicodelcampo | #33 | `ed5e4f0266` | research(hp008): add causal multicontract results |
| `docs/safe-agent-onboarding-20260915` | 1 | 2026-09-15 | Nicodelcampo | #27 | `86013d6f11` | docs(repo): add lossless agent onboarding snapshot |
| `fix/hftzones-nq-parity-certification-v2-20260915` | 1 | 2026-09-15 | EdgeLab Baseline | — | `3c4d384250` | feat(hp007): audit and certify HFTZones NQ parity V2, harden comparator, and implement V2 logger sch |
| `work/hp007-campaign-v2-foundation-20260915` | 6 | 2026-09-15 | Nicodelcampo | — | `3fa15ee57d` | docs: pin HP-007 campaign to contractual anchor 29cad93 |
| `work/hp007-causal-campaign-v1-20260915` | 3 | 2026-09-15 | nicolasbuttaro-eng | — | `949f7c4f33` | research(hp007): ejecucion formal, preregistrada y causal de la primera campana de corredores |
| `work/hp007-corridor-measurement-v1-20260915` | 2 | 2026-09-15 | Nicodelcampo | — | `20f2de397d` | fix(research): reuse canonical holdout boundary |
| `work/hp007-rejection-revisit-campaign-v2-20260915` | 11 | 2026-09-15 | nicolasbuttaro-eng | — | `1293cf2655` | docs(hp007): quarantine remaining machine-readable preregistration and ledger in non-canonical branc |
| `work/nq-causal-foundation-v1-20260915` | 1 | 2026-09-15 | EdgeLab Baseline | — | `04422b6d25` | feat(nq): foundation v1 - inventory, session gate, lookahead tests and memo |
| `work/bt2a-gate2-p2a-freeze-20260826` | 35 | 2026-09-06 | nicolasbuttaro-eng | — | `e50bbf3ee2` | feat(research): add EMA reversion filter findings, NT8 indicators, and execution tools for GC and NQ |
| `audit/notion-ai-sltp-p2b-provenance-20260830` | 149 | 2026-09-01 | Nicodelcampo | — | `fc02d7d84f` | audit: register causal contract-regime standard |
| `research/bt2a-nq-gate1-runner-impl-v1-20260831` | 173 | 2026-09-01 | EdgeLab Baseline | — | `755dc3cb47` | feat(bt2a-sltp-be): mechanics smoke test for the SL/TP+breakeven exit engine |
| `research/bt2a-nq-gate1-nrand-capacity-t2-20260830` | 133 | 2026-08-31 | Nicodelcampo | — | `4044e82326` | docs(bt2a-nq-gate1): registra tokens 3 y 4 de Nico (implement + run) 2026-08-31 01:08 ART [Notion AI |
| `research/avolcluster-nq-gate1-infra-v1-20260828` | 51 | 2026-08-30 | Claude (EdgeLab session) | #22 | `b5b89bb4f3` | fix(avolcluster-nq-gate1b-gate3): actually stage the stale-hash fix; resolve 3 raw_data facts |
| `research/avolcluster-nq-lifecycle-v1-20260830` | 108 | 2026-08-30 | Nicodelcampo | — | `ca1f2b8e98` | docs(research): spec lifecycle v1.2.0 — contrato de paralelismo born-parallel por contract-session c |
| `research/bt2a-gc-sltp-breakeven-design-v1-20260830` | 109 | 2026-08-30 | Nicodelcampo | — | `5dd58f2934` | feat(sltp-campaign): freeze-draft spec for the SL/TP+breakeven campaign (post-D5) + HP-005 registere |
| `research/bt2a-nq-gate1-outcomes-runner-v1-20260830` | 116 | 2026-08-30 | EdgeLab Baseline | — | `d229bbb2f8` | docs(bt2a-nq-gate1): fix residual "2-hour" docstring after D6 corrigendum ratification |
| `research/bt2a-nq-gate1-power-closure-20260830` | 120 | 2026-08-30 | Nicodelcampo | — | `cb84424432` | fix(bt2a-nq-gate1): D6 corrigendum ratified by Nico — coarse_phase is 4-hour blocks / 6 phases [Noti |
| `research/bt2a-nq-v2-sweep-v1-20260829` | 113 | 2026-08-30 | EdgeLab Baseline | — | `83884585c1` | feat(bt2a-nq-gate1): close 4 Kaggle bindings; align runner contract to authorized estimand |
| `research/bt2a-nq-gate1-v1-20260829` | 105 | 2026-08-29 | Nicodelcampo | — | `c7a81dec37` | Update V2 sweep test for FROZEN state (see prior commit for rationale) |
| `research/bt2a-nq-target-free-selection-v1-20260828` | 97 | 2026-08-29 | Nicodelcampo | — | `495ba7f972` | docs(bt2a-nq): record early-stop decision at 2/5 contracts |
| `research/bt2a-p2b-economic-gc-v1-20260827` | 43 | 2026-08-29 | Nicodelcampo | — | `54ab1437fe` | fix(bt2a-p2b-gc): simulate_cell's strictly-after check must use (ts, source_row) |
| `docs/traceability-refresh-20260828` | 3 | 2026-08-28 | Nicodelcampo | #21 | `15eb3c5895` | docs(traceability): add machine-readable remote snapshot |
| `fix/g2-a1-calibration-hardening` | 13 | 2026-08-28 | Nicodelcampo | #8 | `780365c74b` | Merge branch 'foundation/f0b-compatibility-probe' into fix/g2-a1-calibration-hardening |
| `infra/kaggle-frozen-execution-v1-20260828` | 65 | 2026-08-28 | nicolasbuttaro-eng | #24 | `efc735fafe` | feat(data): register canonical gate1 GC, ZB, and 13-month continuous MBT |
| `prep/indicator-onboarding-registry` | 7 | 2026-08-28 | Nicodelcampo | #9 | `2e8ed3bdd4` | Merge branch 'foundation/f0b-compatibility-probe' into prep/indicator-onboarding-registry |
| `research/avolcluster-nq-microticks-v1-20260828` | 35 | 2026-08-28 | nicolasbuttaro-eng | — | `3961b67d80` | feat(research): add aVolClusterPOI micro-tick and fast-bar target-free sweep on NQ |
| `research/bigtrap2-distance-matched-null` | 15 | 2026-08-28 | Nicodelcampo | — | `108823bf2a` | Merge branch 'audit/p0-bigtrap2-drift' into research/bigtrap2-distance-matched-null |
| `research/bigtrap2-nq-tickframes-sweep-v1-20260828` | 79 | 2026-08-28 | nicolasbuttaro-eng | — | `9f33a51a9f` | Merge remote-tracking branch 'origin/infra/kaggle-frozen-execution-v1-20260828' into research/bigtra |
| `research/bt2a-p2a-clock-heterogeneity-v1-20260827` | 51 | 2026-08-28 | nicolasbuttaro-eng | — | `773e7cca63` | docs(research): publish finalized GC clock heterogeneity diagnostic report |
| `research/zamr1-zone-atlas` | 28 | 2026-08-28 | Nicodelcampo | — | `08f9733c67` | Merge branch 'research/bigtrap2-local-displacement-null' into research/zamr1-zone-atlas |
| `research/avolcluster-compression-v1-20260827` | 9 | 2026-08-27 | Nicodelcampo | #19 | `e53fcf64ed` | fix(avol): fail closed and correct two-stage scientific scope |
| `results/bt2a-p2a-v1-r1-20260827` | 23 | 2026-08-27 | nicolasbuttaro-eng | — | `7a9959fb4e` | docs(research): restore Aporte al referente in LEER.md |
| `work/indicator-coordinate-store-v1-20260827` | 3 | 2026-08-27 | Nicodelcampo | #17 | `9ad26cfc0a` | ci(store): verify coordinate pipeline contract |
| `work/bt2a-gate1-all5-20260826` | 10 | 2026-08-26 | Nicodelcampo | — | `3e639e150b` | fix(gate1): restore frozen spec byte provenance |
| `work/bt2a-gate1-runner-20260826` | 6 | 2026-08-26 | Nicodelcampo | — | `f5fd49db6e` | docs(gate1): bind clean-76 registry to audited payload |
| `work/bt2a-gate2-l2-audit-20260826` | 14 | 2026-08-26 | EdgeLab Baseline | — | `f4b7e607e8` | docs(bt2a): auditoria local forense de outputs nocturnos (solo lectura) |
| `work/bt2a-gate2-l2-hardening-20260826` | 28 | 2026-08-26 | Nicodelcampo | — | `761f50ba93` | docs(bt2a): finalize Gate 2 and L2 hardening audit |
| `docs/es-apriori-2026-08-25` | 4 | 2026-08-25 | nicolasbuttaro-eng | — | `a73f57f408` | fix(research): close ES causal audit inconsistencies |
| `docs/handoff-2026-08-25` | 5 | 2026-08-25 | Nicodelcampo | — | `4b73df7ff3` | docs(mbt): auditoria del config a-priori de Antigravity (TW25; q 95 vs 97.5 pendiente) — Notion AI |
| `docs/mbt-apriori-2026-08-25` | 1 | 2026-08-25 | nicolasbuttaro-eng | — | `e2c7bf2359` | docs(research): configuracion a-priori BigTrap2Absorption para MBT 2026-08-25 |
| `research/gate-regime-context` | 9 | 2026-08-24 | Nicodelcampo | — | `c882cf5211` | docs(gate): reclasifica cimiento y cierra auditoría de once defectos |
| `work/crypto-context-foundation-20260824` | 21 | 2026-08-24 | EdgeLab Baseline | — | `3b52974f73` | docs(crypto): inventario de fuentes medido + hueco de LOT_SIZE historico declarado |
| `registry/gex-familia` | 1 | 2026-08-20 | Nicodelcampo | — | `f065df2146` | gex: registro de familia GEX-NIVELES (observacional) |
| `fix/bigtrap2-v252-tick-export` | 2 | 2026-08-11 | EdgeLab Baseline | — | `6a858fdc31` | BigTrap2 v2.5.2: fix del defecto de atribucion temporal + drenaje de cola |
| `research/bigtrap2-multiframe-ml` | 5 | 2026-08-11 | Nicodelcampo | — | `05d2da7525` | research(multiframe): opus audit, dataset contract v1, fail-closed validator and tests |
| `docs/estado-real-2026-08-10` | 1 | 2026-08-10 | Nicodelcampo | — | `16acc7d9eb` | docs: align repository with canonical state 2026-08-10 |
| `docs/h-cond-1-lux-imb` | 2 | 2026-08-10 | Nicodelcampo | — | `5530344c98` | docs: enlazar el protocolo LUX-IMB desde el README |
| `docs/h-sweep-1-ym-prerange` | 1 | 2026-08-10 | Nicodelcampo | — | `2df700f475` | docs(research): registrar familia YM-PRERANGE e hipotesis H-SWEEP-1 |
| `docs/post-merge-sync-2026-08-10` | 2 | 2026-08-10 | Nicodelcampo | — | `be1fcfab9e` | docs: avoid self-referential branch tip |
| `fix/g2-a1-statistical-semantics` | 6 | 2026-08-10 | Nicodelcampo | — | `f3b8263953` | docs(g2): replace canonical contract and persist calibration evidence |
| `backup/foundation-f0b-local` | 1 | 2026-07-22 | EdgeLab Baseline | — | `a48efcd0d0` | docs: root README for cross-machine handoff |
| `preserve/f0b-local-divergente-2026-08-04` | 1 | 2026-07-22 | EdgeLab Baseline | — | `a48efcd0d0` | docs: root README for cross-machine handoff |
