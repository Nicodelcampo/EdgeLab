# DIAG-CAIDA-2026: resultado

Estado: RESULTADO (EF2, descriptivo; pre-registro `PREREGISTRO_DIAG_CAIDA_2026.md`, 10 pruebas contadas)  
Fecha: 2026-11-25  
Datos: `PARTE_A_SIZING_VS_PRECIO.csv`, `PARTE_B_PERCENTILES.json`, `PARTE_B_RASGOS_MENSUALES_{NQ,ES}.csv` (`tools/diag_caida_2026.py`).
Diagnóstico de grilla: no aplica (sin perillas; descriptivo, ver pre-registro).

## Parte A — sizing vs precio (2024–2025 contra 2026-04 → 2026-09, 1 contrato fijo, veto activo)

| Estrategia | R/op 2024–25 → 2026Q2–Q3 | USD/op riesgo constante ($200) | stop % precio |
|---|---|---|---|
| RQ5_ES | +0,086 → −0,109 | +17 → −22 | 0,46 → 0,48 |
| RQ5_NQ | +0,115 → −0,093 | +23 → −19 | 0,64 → 0,82 |
| ES5N_ES | +0,123 → −0,246 | +25 → −49 | 0,46 → 0,49 |
| Franklin_NQ | +0,049 → −0,065 | +10 → −13 | 0,48 → 0,62 |
| T_ES | +0,194 → −0,054 | +39 → −11 | 0,22 → 0,24 |
| V_NQ | +0,075 → +0,031 | +15 → +6 | 0,47 → 0,60 |
| T_NQ | +0,217 → +0,197 | +43 → +39 | 0,38 → 0,34 |
| SOM sin_finde NQ | +0,065 → +0,126 | +13 → +25 | 0,75 → 0,91 |
| R_NQ | +0,216 → +0,413 | +43 → +83 | 0,78 → 0,96 |
| C2_VZ_NQ | +0,038 → +0,191 | +8 → +38 | 2,00 → 2,78 |

**La caída está en R por operación (independiente del sizing): es del movimiento del precio.** El sizing de 1 contrato fijo
sólo la amplifica en dólares cuando el stop crece en % del precio; con riesgo constante sigue negativa. Hipótesis «es el
sizing»: refutada para RQ5, ES5N, Franklin y T_ES.

## Parte B — rasgos de la apertura (percentil de 2026-04 → 2026-09 contra ventanas de 6 meses de 2018–2025)

| Rasgo | NQ | ES |
|---|---|---|
| `cont_orb` (la ruptura de 09:30–09:45 sigue al cierre) | 55 | 82 |
| `ef_manana` (eficiencia 09:30–11:30) | 40 | **99** |
| `frac_noche` (parte nocturna del movimiento diario) | **94,5** | 75 |
| `rv_rel` (rango 5 d / 60 d) | 41 | 15 |
| `ac5_manana` (autocorrelación 5 min en la mañana) | 31 | **7,7** |

- Hipótesis «menos rupturas que continúan»: **refutada** (`cont_orb` normal en NQ y alto en ES).
- Lo que sí cambió: en ES, mañanas con tendencia muy eficiente pero **más reversión de corto plazo** (5 min); en NQ, **más
  movimiento de noche** (menos recorrido para la sesión). Coincide con quién ganó: las que mantienen de un día para otro (SOM
  sin_finde, C2_VZ) y las de fase/tendencia del día (R) subieron; las de entrada en la mañana con stop corto (RQ5, ES5N,
  Franklin, T_ES) bajaron.
- Lectura descriptiva (≈ 16 ventanas independientes): sirve para orientar EXP-7, no para operar un filtro.
