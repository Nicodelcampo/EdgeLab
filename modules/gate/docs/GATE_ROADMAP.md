# GATE → EdgeLab — Roadmap de complemento aplicable

Objetivo: convertir GATE de lab sintético en **productor de contexto PRE**
compatible con el contrato EdgeLab (indicador exporta → lab etiqueta → trial pre-registrado).

Cada paso incluye: entregable, criterio de hecho, y ancla de práctica externa.

---

## Paso 1 — Schema + adaptador causal + proveniencia
**Estado: HECHO (smoke)**

| | |
|--|--|
| **Entregable** | `gate_context_schema_v1.json` + `gate_adapter.py` (stub) que une eventos en \(t_0\) |
| **Hecho cuando** | Schema versionado; join solo `as_of <= t0`; campos `run_id`, `seed`, `model_id`, `commit`; fail-closed |
| **Ancla web** | Event schema + provenance/correlation ids en sistemas de trading; point-in-time / as-of joins; timestamps de disponibilidad separados del event time |

## Paso 2 — Métricas target-free del régimen
**Estado: HECHO (demo sintética)**

| | |
|--|--|
| **Entregable** | Módulo que, sin outcomes, reporta minutos/estado, persistencia, flip-flop, cobertura por sesión, **corr(régimen, ancho_ticks)** |
| **Hecho cuando** | Corr con ancho publicada; celdas con ≥40 sesiones marcadas; comparable a filtros H-ES-CTX-2 |
| **Ancla web** | Diagnóstico descriptivo de regímenes (persistencia, cambios); target-free antes de hipótesis |

## Paso 3 — Pre-registro CTX-3 (plantilla)
**Estado: HECHO (plantilla DRAFT_READY_TO_FREEZE)**

| | |
|--|--|
| **Entregable** | `H-ES-CTX-3_PREREGISTRO.md` al estilo EdgeLab (población, contexto GATE, estimando primario, MDE, Holm, cierre) |
| **Hecho cuando** | Documento congelable sin mirar outcomes; multiplicidad explícita |
| **Ancla web** | Pre-registro observacional: muestra, hipótesis, outcomes primarios/secundarios, estimadores, covariates |

## Paso 4 — Valor incremental vs baseline `pct_rv`
**Estado: HECHO (demo sintética)**

| | |
|--|--|
| **Entregable** | Comparación **incremental** (GATE \| pct_rv) vs solo pct_rv — no solo ranking relativo |
| **Hecho cuando** | Test pre-especificado de contenido informativo adicional; si no aporta, se documenta |
| **Ancla web** | Incremental vs relative information content (Biddle et al.); value-added de un predictor dado otro |

## Paso 5 — Congelar `model_id` + checklist de integración
**Estado: HECHO**

| | |
|--|--|
| **Entregable** | `model_id` inmutable (features, sticky, VPIN thr, causal-only); checklist repo (rama, no tocar .cs, firewall holdout) |
| **Hecho cuando** | Hash de config; gauntlet solo si se gatean trades |
| **Ancla web** | Versionado de schema/eventos; determinismo y audit trail |

---

## Orden de ejecución
1 → 2 → 3 → 4 → 5  
No medir estimando de familia (AbsMagnitude / ticks_por_ancho) hasta cerrar 1–3.
