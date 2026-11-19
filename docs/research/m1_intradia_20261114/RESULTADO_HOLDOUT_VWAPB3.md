# VWAP banda 3 (reversión) — resultado del holdout (2026-11-16)
Estado: RESULTADO (apertura única de `M1_INTRADIA`). Acta: `ACTA_HOLDOUT_VWAPB3.md`. Datos: `RESULTADO_HOLDOUT_VWAPB3.json`,
resumen `RESUMEN_HOLDOUT_VWAPB3.json`. Ventana: sesiones selladas 2026-10-01 → 2026-11-13 (NQ 31, YM 29, ES 28), futuros reales.

| | n | R neto medio | ee | positivas | noviembre |
|---|---|---|---|---|---|
| **H: NQ + YM** | 12 | +0,32 | 0,77 | 3/12 | n 3, +0,77 |
| NQ | 7 | −0,12 | 0,96 | 1/7 | n 2, −1,08 |
| YM | 5 | +0,92 | 1,33 | 2/5 | n 1, +4,47 |
| ES (control) | 6 | +1,02 | 1,45 | 2/6 | n 1, +5,62 |

**NO_CONCLUYENTE, sin potencia.** La regla dispara mucho menos que lo previsto en el acta (≈ 0,2 por sesión e índice contra 0,3–0,5):
12 operaciones. La media positiva la hacen 3 ganadoras grandes (objetivo VWAP lejos) contra 9 stops; el error estándar (0,77 R) es mayor
que el efecto buscado. Fisher (desarrollo 0,5; holdout p ≈ 0,34) = 0,47. La familia queda sin más aperturas; la regla sigue en forward.
