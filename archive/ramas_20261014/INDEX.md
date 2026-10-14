# Archivos de ramas remotas integrados como archivo (2026-10-14)

Estado: VIGENTE
Fecha: 2026-10-14

Contenido que existe en alguna rama remota de `origin` y **no** estaba en `foundation` (2.417 rutas únicas, ~38 MB). Se conserva como **archivo histórico, no vigente**: cada carpeta `bNNN_*` es la primera rama que aportó esa ruta; la estructura interna replica la del repo. No forma parte de `edgelab/`, `tests/` ni `docs/` y no la leen los chequeos. Las ramas siguen en el remoto; esto asegura que su contenido no dependa de ellas.

| Carpeta | Rama de origen | Archivos |
|---|---|---:|
| `b001_agent-b-cycle-001-learning-p` | `agent-b/cycle-001-learning-packet-ingestion` | 4 |
| `b002_agent-c-cycle-001-kaggle-acc` | `agent-c/cycle-001-kaggle-access-audit` | 3 |
| `b003_audit-canonical-liquidity-20` | `audit/canonical-liquidity-20261004` | 1 |
| `b004_audit-cycle-001-agent-a-curr` | `audit/cycle-001-agent-a-currentness-20260921` | 1 |
| `b005_audit-edge-discovery-factory` | `audit/edge-discovery-factory-foundation-20260919` | 2 |
| `b006_audit-edgelab-continuous-ref` | `audit/edgelab-continuous-reference-20260920` | 12 |
| `b007_audit-notion-ai-sltp-p2b-pro` | `audit/notion-ai-sltp-p2b-provenance-20260830` | 191 |
| `b008_claude-focused-fermat-qjt805` | `claude/focused-fermat-qjt805` | 2 |
| `b009_claude-vibrant-clarke-s9z6e2` | `claude/vibrant-clarke-s9z6e2` | 388 |
| `b010_data-liquid-release-20261014` | `data/liquid-release-20261014` | 673 |
| `b011_docs-edgelab-product-map-202` | `docs/edgelab-product-map-20261009` | 1 |
| `b012_docs-es-apriori-2026-08-25` | `docs/es-apriori-2026-08-25` | 14 |
| `b013_docs-handoff-2026-08-25` | `docs/handoff-2026-08-25` | 5 |
| `b014_docs-safe-agent-onboarding-2` | `docs/safe-agent-onboarding-20260915` | 4 |
| `b015_docs-traceability-refresh-20` | `docs/traceability-refresh-20260828` | 3 |
| `b016_feat-crosshair-density-profi` | `feat/crosshair-density-profile-20260918` | 3 |
| `b017_feat-edge-brain-learning-gov` | `feat/edge-brain-learning-governor-20260924` | 7 |
| `b018_feat-edge-replica-port-20261` | `feat/edge-replica-port-20261004` | 32 |
| `b019_feat-frontier-expansion-lab` | `feat/frontier-expansion-lab-20260921` | 73 |
| `b020_feat-r3-gated-window-2026101` | `feat/r3-gated-window-20261010` | 2 |
| `b021_feat-research-ops-supervisor` | `feat/research-ops-supervisor-mvp` | 53 |
| `b022_fix-bigtrap2-v252-tick-expor` | `fix/bigtrap2-v252-tick-export` | 2 |
| `b023_fix-g2-a1-calibration-harden` | `fix/g2-a1-calibration-hardening` | 6 |
| `b024_fix-g2-a1-statistical-semant` | `fix/g2-a1-statistical-semantics` | 2 |
| `b025_fix-hft-certification-proven` | `fix/hft-certification-provenance-playwright-20260918` | 2 |
| `b026_fix-hft-native-termination-f` | `fix/hft-native-termination-fresh-replay-20260918` | 9 |
| `b027_indicator-four-pass-sparse-s` | `indicator/four-pass-sparse-stop-first-20261001` | 18 |
| `b028_infra-kaggle-frozen-executio` | `infra/kaggle-frozen-execution-v1-20260828` | 2 |
| `b029_prep-indicator-onboarding-re` | `prep/indicator-onboarding-registry` | 17 |
| `b030_qa-cycle001-d-kaggle-access` | `qa/cycle001-d-kaggle-access-review` | 2 |
| `b031_qa-cycle001-d-viewer-causal` | `qa/cycle001-d-viewer-causal-smoke` | 2 |
| `b032_registry-gex-familia` | `registry/gex-familia` | 1 |
| `b033_research-avolcluster-compres` | `research/avolcluster-compression-v1-20260827` | 5 |
| `b034_research-avolcluster-nq-gate` | `research/avolcluster-nq-gate1-infra-v1-20260828` | 7 |
| `b035_research-avolcluster-nq-life` | `research/avolcluster-nq-lifecycle-v1-20260830` | 1 |
| `b036_research-avzvol-dense-excurs` | `research/avzvol-dense-excursions` | 56 |
| `b037_research-avzvol-exploratory` | `research/avzvol-exploratory-bias-protocol` | 15 |
| `b038_research-avzvol-fixed-replic` | `research/avzvol-fixed-replication` | 27 |
| `b039_research-avzvol-frequency-fi` | `research/avzvol-frequency-first-grid` | 8 |
| `b040_research-avzvol-height-conte` | `research/avzvol-height-context` | 14 |
| `b041_research-avzvol-longevity-fu` | `research/avzvol-longevity-full-grid` | 216 |
| `b042_research-avzvol-partial-retu` | `research/avzvol-partial-return` | 11 |
| `b043_research-avzvol-source-reaud` | `research/avzvol-source-reaudit` | 10 |
| `b044_research-bigtrap2-multiframe` | `research/bigtrap2-multiframe-ml` | 11 |
| `b045_research-bt2a-gc-sltp-breake` | `research/bt2a-gc-sltp-breakeven-design-v1-20260830` | 2 |
| `b046_research-bt2a-nq-gate1-nrand` | `research/bt2a-nq-gate1-nrand-capacity-t2-20260830` | 43 |
| `b047_research-bt2a-nq-gate1-runne` | `research/bt2a-nq-gate1-runner-impl-v1-20260831` | 30 |
| `b048_research-bt2a-p2a-clock-hete` | `research/bt2a-p2a-clock-heterogeneity-v1-20260827` | 9 |
| `b049_research-bt2a-p2b-economic-g` | `research/bt2a-p2b-economic-gc-v1-20260827` | 6 |
| `b050_research-cross-momentum-mult` | `research/cross-momentum-multiasset-20261001` | 25 |
| `b051_research-ema-pullback-census` | `research/ema-pullback-census-20261001` | 78 |
| `b052_research-ema-pullback-econom` | `research/ema-pullback-economic-20261001` | 16 |
| `b053_research-ema3-25t-pullback-g` | `research/ema3-25t-pullback-grid-20261002` | 5 |
| `b054_research-gate-regime-context` | `research/gate-regime-context` | 42 |
| `b055_research-hp008-causal-multic` | `research/hp008-causal-multicontract-20260918` | 2 |
| `b056_research-mnq-pullback-extens` | `research/mnq-pullback-extension-20261001` | 15 |
| `b057_research-zamr1-zone-atlas` | `research/zamr1-zone-atlas` | 27 |
| `b058_results-bt2a-p2a-v1-r1-20260` | `results/bt2a-p2a-v1-r1-20260827` | 73 |
| `b059_review-research-ops-117` | `review/research-ops-117` | 4 |
| `b060_work-bt2a-gate2-l2-audit-202` | `work/bt2a-gate2-l2-audit-20260826` | 2 |
| `b061_work-bt2a-gate2-p2a-freeze-2` | `work/bt2a-gate2-p2a-freeze-20260826` | 56 |
| `b062_work-crypto-context-foundati` | `work/crypto-context-foundation-20260824` | 28 |
| `b063_work-hp007-campaign-v2-found` | `work/hp007-campaign-v2-foundation-20260915` | 19 |
| `b064_work-hp007-rejection-revisit` | `work/hp007-rejection-revisit-campaign-v2-20260915` | 8 |
| `b065_work-indicator-coordinate-st` | `work/indicator-coordinate-store-v1-20260827` | 9 |
