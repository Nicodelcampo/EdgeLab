# k36: walk-forward 178 sesiones vs ultimas 32 sesiones (ticks por trade, z clusterizado por sesion)

Fuente: `k36_summary.json` (salida del kernel k36, sin recalcular). WF = `trading_by_daily_frequency_walkforward_oos`, columna `freq_2.0_per_day_IDEAL`; OOS32 = `assessment_32_sessions_strict_oos_at_2trades_per_day`.

## U1_Preset1_Real_HFT_in_W1

| config | WF n | WF bruto | WF neto limite | WF neto pasivo | OOS32 n | OOS32 bruto | OOS32 neto limite | OOS32 neto pasivo |
|---|---|---|---|---|---|---|---|---|
| C0_Baseline | 344 | 0.75 (z 0.86) | -0.79 (z -0.90) | -1.84 (z -1.84) | 92 | 2.16 (z 1.24) | 0.62 (z 0.35) | -0.25 (z -0.13) |
| C1A_AsymStop | 344 | 0.90 (z 1.15) | -0.65 (z -0.84) | -1.78 (z -2.00) | 92 | 2.17 (z 1.49) | 0.63 (z 0.43) | -0.28 (z -0.18) |
| C1B_AsymStop | 370 | 0.02 (z 0.03) | -1.53 (z -2.42) | -2.25 (z -3.61) | 129 | 1.34 (z 1.34) | -0.20 (z -0.20) | -1.22 (z -1.12) |
| C1C_AsymStop | 394 | 0.19 (z 0.27) | -1.36 (z -1.96) | -2.00 (z -2.71) | 149 | 1.17 (z 1.12) | -0.38 (z -0.36) | -1.27 (z -1.05) |
| C2_Asym | 342 | 0.93 (z 1.24) | -0.61 (z -0.82) | -1.26 (z -1.83) | 113 | 2.93 (z 1.82) | 1.38 (z 0.86) | 0.41 (z 0.29) |
| C3_Asym | 376 | 0.26 (z 0.42) | -1.28 (z -2.04) | -1.97 (z -3.15) | 134 | 1.50 (z 1.56) | -0.04 (z -0.04) | -1.01 (z -0.96) |
| C4_Full | 335 | 0.47 (z 0.66) | -1.07 (z -1.51) | -1.66 (z -2.51) | 111 | 1.64 (z 1.13) | 0.10 (z 0.07) | -0.62 (z -0.47) |

Nulo de desplazamiento circular (C4, 2 trades/dia): observado neto -1.07 vs nulo -0.92, p = 0.58.

## U3_Preset2_Real_HFT_in_W1

| config | WF n | WF bruto | WF neto limite | WF neto pasivo | OOS32 n | OOS32 bruto | OOS32 neto limite | OOS32 neto pasivo |
|---|---|---|---|---|---|---|---|---|
| C0_Baseline | 349 | 0.89 (z 1.01) | -0.65 (z -0.74) | -1.12 (z -1.15) | 130 | 0.82 (z 0.65) | -0.73 (z -0.58) | -1.13 (z -0.78) |
| C1A_AsymStop | 350 | 0.81 (z 1.01) | -0.73 (z -0.91) | -1.18 (z -1.38) | 130 | 1.58 (z 1.28) | 0.03 (z 0.03) | -0.34 (z -0.25) |
| C1B_AsymStop | 321 | 0.48 (z 0.62) | -1.07 (z -1.40) | -1.73 (z -2.11) | 85 | 0.95 (z 0.68) | -0.59 (z -0.42) | -1.86 (z -1.19) |
| C1C_AsymStop | 361 | 0.40 (z 0.55) | -1.15 (z -1.58) | -1.79 (z -2.38) | 110 | 0.97 (z 0.66) | -0.58 (z -0.39) | -1.70 (z -1.14) |
| C2_Asym | 306 | 0.73 (z 0.88) | -0.81 (z -0.98) | -1.48 (z -1.70) | 95 | 1.23 (z 0.81) | -0.31 (z -0.21) | -1.41 (z -0.88) |
| C3_Asym | 329 | 0.61 (z 0.84) | -0.93 (z -1.27) | -1.64 (z -2.14) | 89 | 1.09 (z 0.85) | -0.46 (z -0.36) | -1.65 (z -1.17) |
| C4_Full | 298 | 0.56 (z 0.70) | -0.98 (z -1.22) | -1.71 (z -1.99) | 90 | 1.72 (z 1.07) | 0.18 (z 0.11) | -0.95 (z -0.55) |

Nulo de desplazamiento circular (C4, 2 trades/dia): observado neto -0.98 vs nulo -1.18, p = 0.45.

## U2_Preset2_All_Corridors_HFT_Plus_Struct

| config | WF n | WF bruto | WF neto limite | WF neto pasivo | OOS32 n | OOS32 bruto | OOS32 neto limite | OOS32 neto pasivo |
|---|---|---|---|---|---|---|---|---|
| C0_Baseline | 326 | 1.00 (z 1.42) | -0.54 (z -0.77) | -0.62 (z -0.83) | 119 | 1.18 (z 0.94) | -0.37 (z -0.30) | -0.45 (z -0.32) |
| C1A_AsymStop | 326 | 1.21 (z 1.71) | -0.34 (z -0.48) | -0.49 (z -0.65) | 119 | 1.50 (z 1.24) | -0.05 (z -0.04) | -0.15 (z -0.11) |
| C1B_AsymStop | 381 | 1.37 (z 1.77) | -0.17 (z -0.22) | -0.76 (z -0.94) | 114 | 2.43 (z 1.88) | 0.88 (z 0.68) | -0.08 (z -0.06) |
| C1C_AsymStop | 365 | 0.68 (z 0.87) | -0.87 (z -1.10) | -1.47 (z -1.83) | 108 | 1.68 (z 1.19) | 0.13 (z 0.10) | -0.98 (z -0.66) |
| C2_Asym | 332 | 0.98 (z 1.22) | -0.57 (z -0.71) | -1.14 (z -1.38) | 103 | 1.57 (z 1.21) | 0.02 (z 0.02) | -0.96 (z -0.69) |
| C3_Asym | 388 | 1.25 (z 1.59) | -0.29 (z -0.37) | -0.82 (z -1.00) | 116 | 2.22 (z 1.63) | 0.67 (z 0.49) | -0.29 (z -0.20) |
| C4_Full | 330 | 0.93 (z 1.08) | -0.62 (z -0.72) | -1.35 (z -1.61) | 102 | 1.52 (z 1.07) | -0.03 (z -0.02) | -1.03 (z -0.70) |

Nulo de desplazamiento circular (C4, 2 trades/dia): observado neto -0.62 vs nulo -1.31, p = 0.18.

