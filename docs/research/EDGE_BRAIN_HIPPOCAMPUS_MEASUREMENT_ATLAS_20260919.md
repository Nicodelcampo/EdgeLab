# Edge Brain — Experimental Hippocampus & Measurement Atlas (2026-09-19)

## 1. Declaración de Arquitectura

El Edge Discovery Brain recursivo desacopla la formulación de hipótesis no probadas (`LLM_PROPOSAL_NOT_EVIDENCE`) de la verificación experimental determinista mediante cinco subsistemas acoplados por relaciones tipadas:

```text
Bibliographic Cortex (Fuentes primarias y reclamos de literatura)
        ↕ (DERIVED_FROM, EXPLAINS, OPERATIONALIZED_AS)
Experimental Hippocampus (Episodios, ejecuciones de pasos, expectativas, fallas, reparaciones)
        ↕ (REQUIRES, CONDITIONS, GATES)
Measurement & Composition Atlas (Definiciones de indicadores, contratos de composición, ablaciones)
        ↕ (APPLIES_TO, SPECIALIZES, GENERALIZES)
Procedural Memory (Reglas de aprendizaje metodológico, habilidades verificadas, guardarraíles)
        ↕ (USED_IN, HELPED, HARMED)
Working Memory / Context Pack (Selección acotada por presupuesto de tokens con hash determinista)
```

## 2. Invariantes Semánticos Obligatorios

- **LLM Proposal Not Evidence:** Ninguna propuesta generada por LLM (`causal_hypothesis` con `source_type="LLM_PROPOSAL"`) es aceptada como evidencia ni puede auto-promoverse a `CORROBORATED` o `SUPPORTED`.
- **Independencia de Revisión:** Ningún modelo o agente revisa o aprueba sus propias propuestas. `generator["effective_backend"]` y `reviewer["effective_backend"]` deben ser distintos.
- **Precedencia de Fuentes Primarias:** Las fuentes primarias superan a las síntesis derivadas. Una síntesis con contradicciones no resueltas (`has_unresolved_conflicts=True`) tiene bloqueada su promoción.
- **Retención de Falsaciones y Resultados Negativos:** Los eventos de falla (`failure_event`), contraejemplos (`counterexample`) y desenlaces negativos (`reuse_outcome="HARMED"`) son inmutables y permanentes en el ledger.
- **Cero Reutilización Silenciosa:** Todo artefacto afectado por invalidación (`INVALIDATED_BY_MEASUREMENT_ERROR`, `STALE_BY_DEPENDENCY` o `REQUIRES_REAUDIT`) es rechazado activamente si un pipeline intenta reutilizarlo.
- **Ledger Hash-Chained Append-Only:** El ledger JSONL es la única fuente de verdad canónica. Parquet ZSTD y proyecciones JSON son reconstruibles y no sustituyen el ledger.
- **Seed Atlas sin Afirmación de Edge:** Todo registro del atlas seed en estado `DRAFT` o `PROPOSED` tiene `asserts_edge=False`.

## 3. Catálogo y Componentes del Seed Atlas

- **Catalog ID:** `ATLAS-FOUNDATION`
- **Partición:** `METHODOLOGICAL_CORTEX`
- **Indicadores:**
  - `IND-EMA`: Exponential Moving Average (rol: `REGIME_GATE`, período 20, ablaciones: `no_smoothing`, `simple_moving_average`, `shuffled_bars`).
  - `IND-RSI`: Relative Strength Index (rol: `TRIGGER`, período 14, ablaciones: `unbounded_momentum`, `stochastic_oscillator`, `randomized_signal`).
- **Composición:**
  - `COMP-EMA-RSI-REGIME-TRIGGER`: Compuerta de régimen EMA con gatillo RSI. Hipótesis de interacción: la compuerta EMA reduce densidad de gatillos espurios sin lookahead temporal.
- **Concepto de Medición:**
  - `TREND_STRENGTH`: Persistencia direccional del desplazamiento relativa a volatilidad local.
