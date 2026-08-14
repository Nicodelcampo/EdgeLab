# aVolClusterPOI — handoff 2026-08-14

Rama: `research/bigtrap2-local-displacement-null`  
HEAD útil: `55c88465` (baseline ES). **No hay ticks en Git.**

## Decisión vigente

Mejorar el indicador **no exige P2_PASS**.  
Universo: **todas las OFF_PRICE de Python**.  
Primer pasaje vs espejo: **no hay imán** en 6E ni en ES.  
“Cuando la zona funciona” es circular. Ruido = forma en t.  
**Kaggle con ticks: no.**

No concatenar. No QualityScore. No P&L. No GEX/L2/Asia en este pack.

## 6E

P2 `ABSTAIN_P2` 50/53. Baseline: 53 OFF, **27–20**, p=0.574, binomial ≈0.38.  
Doc: `docs/research/AVOL_BASELINE_FP_PYTHON_V05_2026-08-14.md`

## ES 09-26 — baseline corrido

P2: `ABSTAIN_ALIGNMENT` (CSV 1-may / parquet 8-jun).  
Parquet SHA-256 `add9bfcd46b3e8a14b26e6fe90295509dc9444309836f186661850af214146ef`.  
30.5M ticks, 66 115 barras, decode_gaps=[].

Baseline Python (`55c88465`):

- 111 OFF, **35 zona / 49 espejo / 27 empates**, p=0.417, binomial ≈0.16
- LONG 17–25. SHORT 18–24. Signo contrario a 6E.
- Doc: `docs/research/AVOL_ES_0926_BASELINE_FP_2026-08-14.md`

Pool exploratorio 6E+ES: 62–69 / 131, p=0.473. Ruido.

CSV NT8: 306 OFF, hash `aacb7adb…`. No usar TARGET/STOP.

Otros 7z (no extraídos): 03-26, 06-26, 12-25, 09-25.

## Qué sigue

1. Más n del mismo protocolo (ES 06-26 o 12-25, **uno**). No esperar otro 57%.
2. O una mejora preregistrada de **forma** (no de resultado): tirar AT_PRICE / same-bar / ancho > p90 / cluster_share chico, y **recién ahí** volver a medir.
3. P2 ES solo con parquet que cubra mayo, o CSV recortado al 8-jun+.
