# EdgeLab — Project Scope Charter & Roadmap

> Charter versionado. Fija qué está preservado, qué está pausado y cuál es la
> prioridad activa. Fecha: 2026-07-21 · Branch `foundation/f0b-compatibility-probe`.

## 1. Legacy preservado (intocable)
- **Baseline `cde6d93`** (tag `baseline-pre-foundation`) = estado original tal como se restauró el snapshot portable.
- **Backup inmutable + manifest** en `C:\ProyectosQuant\_baselines\` (ZIP + SHA-256 + `*-manifest.json`).
- Sobre el baseline: `49289a1` (entorno reproducible F0B) y `b702515` (config portable F0C).
- Nada de esto se reescribe, mergea a `main` ni se re-taggea sin aprobación.

## 2. EURUSD / ARB / tickfade — PAUSADO
- El **ARB EURUSD es un candidato NO validado**: sin EXP asociado en el ledger científico central (`CerebroSSRN/cerebro/LEDGER_EXPERIMENTOS.md`, que a EXP-044/2026-07-18 declara "ningún edge vivo"). Su ficha `EDGES_DISCOVERED.md` no pasó el gauntlet.
- **Fuera de alcance** hasta nueva orden: remediación de barras, scripts vectorbt EURUSD, port del ARB, holdout/gauntlet/MCPT/PBO/SPA del ARB, dedupe tickfade, pipelines ES/NQ legacy, optimizaciones.
- Los archivos se **preservan**, no se borran ni modifican.

## 3. Insumo de plomería explícito — TickData/ (6E)
- `TickData/` contiene exports NT8 `.Last.txt` de **6E (futuros EUR/USD)**, descargados deliberadamente como **test data del Data Contract y el conversor (F1/F2)**. Es plomería del bridge, **no** research de estrategia EURUSD → no viola el pause del punto 2.
- Formato confirmado (muestreo read-only): `;`-separado, 5 campos → `yyyyMMdd HHmmss fffffff` (fracción 100 ns) `; last ; bid ; ask ; volume`. Timestamps duplicados legítimos. **Timezone del export NO es UTC** (hora local del export) → se declara en F1, no se asume.
- `TickData/` y `*.Last.txt` quedan gitignored (data grande fuera de Git).

## 4. Prioridad activa — NT8 Indicator Bridge
Arquitectura objetivo: `NT8 ticks → Parquet → Data Contract → Indicator Contract → oráculo NT8 → Reference Python → paridad numérica → visor Lightweight Charts → aprobación humana → kernel Numba → Feature/Zone Store → adapter EdgeLab/vectorbt → registry → optimización`.

### Gates (terminología acordada)
- **P0** — contrato de ticks (formato, timezone, monotonicidad, duplicados, quotes cruzadas, empalme por contrato, fingerprint).
- **P1A / P1B** — barras / footprint.
- **P2A / P2B** — paridad de eventos / paridad de features (Reference Python ↔ oráculo NT8, y Reference ↔ Numba).

### Identidades del Store (append-only, versionadas)
`dataset_id` · `spec_id` · `parameter_set_id` · `calibration_id` · `run_id` · `zone_id`.

## 5. Orden de hitos aprobado
| Fase | Objetivo | Gate |
|---|---|---|
| **F1** | Data Contract de ticks NT8 `.Last.txt` — declarar formato y **timezone del export (NO asumir UTC; es hora local)** | P0 |
| **F2** | Conversor NT8→Parquet **propio** con auditor **P0 integrado** (motivo: el conversor de terceros produjo bases horarias mezcladas **+3h** en un empalme real; no se puede repetir) | P0 |
| **F3** | Bar Builder | P1A |
| **F4** | Réplica Python de **Gaps2** (oráculo NT8 = CSV EventLog) | P2 |
| **F5** | Store mínimo (DuckDB + Parquet) | — |
| **F6** | Visor Lightweight Charts (MVP + modo paridad) | — |
| **F7** | **HFTZones2** (calibración causal, 2 sesiones) | P2 |
| **F8** | Interfaz spec confirmable por LLM | — |
| **F9** | Adapter **GEX** (`context_snapshots`, `available_at`) | — |
| **F10+** | Otros indicadores, kernels Numba, registry (sin detallar todavía) | — |

## 6. Definición de terminado (por fase)
El terminado de una fase = **su gate en verde + evidencia reproducible** (locks, fixtures, checksums, decision trace según corresponda). Nunca "parece que anda".

## 7. Límite explícito
**Ninguna fase del bridge toca estrategias ni optimizaciones hasta que la paridad (P2) esté aprobada.** El bridge produce datos/indicadores/zonas verificados; el uso en búsqueda/optimización viene después y por separado.
