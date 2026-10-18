# EdgeReplica (60 reglas) sobre USATECH CFD — resultado 2026-10-18
Pre-registro: `PREREG.md`. Script: `tools/edgereplica_usatech.py`. Datos: Dukascopy USATECH M1 bid/ask, 2023-01 → 2026-09-30 (holdout no leído; privado, no se commitea).
Costo = spread real (mediana 1,49 pts); sin comisión (CFD). 0 descartes por guardas.

| tramo | ops | sesiones | pts/op | IC95 | % gan |
|---|---|---|---|---|---|
| **total (primaria)** | 9.376 | 975 | **+4,08** | [+2,94; +5,27] | 49,8 |
| hasta 10-sep-2026 | 9.238 | 961 | +4,22 | [+3,08; +5,42] | 50,0 |
| 11→30-sep (post-publicación) | 138 | 14 | −5,27 | [−15,3; +5,2] | 37,7 |
| con +1 pt de slippage (sensibilidad) | 9.376 | 975 | +3,08 | [+1,94; +4,27] | 47,8 |

Por año (pts/op, spread real): **2023 −1,77 [−3,05; −0,53]**, 2024 +2,65 [+1,02; +4,33], 2025 +6,90 [+4,29; +9,65], 2026 +10,31 [+6,90; +13,91].
Largos +4,30, cortos +3,72. 56 de 60 reglas con media positiva.

## Lectura
- Lectura pre-registrada: **SOBREVIVE** (límite inferior del IC total > 0), pero la lectura honesta es más débil:
  - El resultado crece monótonamente hacia el presente (2023 negativo y significativo, 2026 el mejor). Las 60 reglas se eligieron sobre datos recientes de NQ
    (rango exacto no documentado aquí), así que 2025-2026 está contaminado por la selección; **2023 es el tramo menos contaminado y es negativo**.
    Un edge que aparece sólo donde se seleccionó es la firma del ajuste, no de una celda horaria estable.
  - Post-publicación (14 sesiones): −5,27 pts/op, IC que cruza 0; casi igual a MNQ (−5,44 en 13 sesiones, diagnóstico previo). Inconcluso, pero consistente con "decayó".
- **Correlación con MNQ** (11→30-sep, 14 sesiones, PnL diario USATECH en pts vs MNQ en USD): Pearson **0,96**, Spearman 0,78. Los dos peores días (14 y 24-sep)
  coinciden. Es el mismo comportamiento en ambos instrumentos, no evidencia independiente: USATECH sirve para réplica de la mecánica y para potencia, no como confirmación.
- Un CFD no es el futuro: sin comisión, horarios y liquidez distintos. El neto real se confirma en futuros.

## MEDIDO / NO MEDIDO
Medido: expectativa neta de spread de las 60 reglas sin cambios; por año; sensibilidad de slippage; correlación diaria en 14 sesiones.
No medido: OOS limpio (no se sabe qué período de NQ usó la selección; sin 2022 ni anterior); efecto de comisión/swap del CFD; reglas individuales con p;
si la deriva ascendente 2023→2026 es régimen o selección (con estos datos no se separa). Para eso haría falta USATECH previo a 2023 o conocer el rango exacto de selección.
