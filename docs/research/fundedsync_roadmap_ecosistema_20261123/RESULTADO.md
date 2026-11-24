# Auditoria Multimodelo, Frecuencia Estructural Anti-Overfit y Ecosistema Multi-Frente

> **Fecha:** 2026-11-23  
> **Universo:** `POST_2020` (`2020-01-01 .. 2026-11-17`) en particiones `DESC`, `REP`, `HOLDOUT` y `TERMINAL` (`2026-10-01 .. 2026-11-17`, excluyendo `2026-10-07`).  
> **Monte Carlo Sincronizado:** `N = 2,000` trayectorias x `H = 504` sesiones (24 meses) compartiendo exactamente el mismo calendario aleatorio `j_seq(N, H)` entre todos los frentes simultaneos.

---

## 1. Desbloqueo de `O` (Overnight NQ) hasta Nov 2026 y Auditoria de Swaps CFD

- **Causa raiz del corte `2025-10-13` resuelta**: `run_o(ms, qty=None)` aplicaba el tope de margen heredado de 1 mini NQ sobre `\$50,000` (`floor(25,000 / dailyClose) == 0` siempre que `NQ > 25,000`), cortando la serie en `2025-10-13`. Al pasar `qty=1` (dimensionamiento fraccional CFD o micros `MNQ`), `O` opera con continuidad total hasta **`2026-10-12`** incluyendo el mercado alcista `2025-10 .. 2026-11` y `TERMINAL`.
- **Impacto real del Swap CFD (`US100` Long `0.022%/noche` ~= `8%` anual + triple swap `3x` los miercoles)**:

| variante              | friccion                      | particion         |   n_ops |   ops_mes |    r_op |   sum_r |   t_ses |   max_dd_r |   calmar |
|:----------------------|:------------------------------|:------------------|--------:|----------:|--------:|--------:|--------:|-----------:|---------:|
| O_downDay_ATR50       | Futuros_MNQ (1.545pt, 0 swap) | DESC              |     131 |      2.84 |  0.0559 |    7.32 |    0.95 |      -4.88 |     0.39 |
| O_downDay_ATR50       | Futuros_MNQ (1.545pt, 0 swap) | REP               |      50 |      3.54 |  0.0514 |    2.57 |    0.57 |      -3.24 |     0.67 |
| O_downDay_ATR50       | Futuros_MNQ (1.545pt, 0 swap) | HOLDOUT           |      74 |      3.45 |  0.0239 |    1.77 |    0.33 |      -3.36 |     0.29 |
| O_downDay_ATR50       | Futuros_MNQ (1.545pt, 0 swap) | TERMINAL_OctNov26 |       2 |      1.27 |  0.367  |    0.73 |    0.36 |      -1.01 |     5.57 |
| O_downDay_ATR50       | Futuros_MNQ (1.545pt, 0 swap) | POST_OCT2025_Bull |      33 |      2.5  | -0.0969 |   -3.2  |   -0.64 |      -5.8  |    -0.5  |
| O_downDay_ATR50       | CFD_SwapBase_8pct_3xWed       | DESC              |     131 |      2.84 |  0.0119 |    1.56 |    0.2  |      -5.54 |     0.07 |
| O_downDay_ATR50       | CFD_SwapBase_8pct_3xWed       | REP               |      50 |      3.54 |  0.0059 |    0.29 |    0.07 |      -3.68 |     0.07 |
| O_downDay_ATR50       | CFD_SwapBase_8pct_3xWed       | HOLDOUT           |      74 |      3.45 | -0.019  |   -1.41 |   -0.26 |      -5.13 |    -0.15 |
| O_downDay_ATR50       | CFD_SwapBase_8pct_3xWed       | TERMINAL_OctNov26 |       2 |      1.27 |  0.3369 |    0.67 |    0.33 |      -1.04 |     4.97 |
| O_downDay_ATR50       | CFD_SwapBase_8pct_3xWed       | POST_OCT2025_Bull |      33 |      2.5  | -0.1371 |   -4.53 |   -0.9  |      -6.36 |    -0.65 |
| O_downDay_ATR50       | CFD_SwapStress_10pct_3xWed    | DESC              |     131 |      2.84 | -0.0002 |   -0.03 |   -0    |      -5.72 |    -0    |
| O_downDay_ATR50       | CFD_SwapStress_10pct_3xWed    | REP               |      50 |      3.54 | -0.0067 |   -0.33 |   -0.07 |      -3.8  |    -0.07 |
| O_downDay_ATR50       | CFD_SwapStress_10pct_3xWed    | HOLDOUT           |      74 |      3.45 | -0.0308 |   -2.28 |   -0.42 |      -5.78 |    -0.22 |
| O_downDay_ATR50       | CFD_SwapStress_10pct_3xWed    | TERMINAL_OctNov26 |       2 |      1.27 |  0.3286 |    0.66 |    0.32 |      -1.04 |     4.81 |
| O_downDay_ATR50       | CFD_SwapStress_10pct_3xWed    | POST_OCT2025_Bull |      33 |      2.5  | -0.1482 |   -4.89 |   -0.96 |      -6.52 |    -0.68 |
| O_downDay_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | DESC              |      97 |      2.1  |  0.0729 |    7.07 |    1.19 |      -3.67 |     0.5  |
| O_downDay_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | REP               |      31 |      2.19 | -0.0033 |   -0.1  |   -0.03 |      -2.45 |    -0.04 |
| O_downDay_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | HOLDOUT           |      55 |      2.57 |  0.0695 |    3.82 |    0.85 |      -3.24 |     0.66 |
| O_downDay_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | TERMINAL_OctNov26 |       2 |      1.27 |  0.367  |    0.73 |    0.36 |      -1.01 |     5.57 |
| O_downDay_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | POST_OCT2025_Bull |      25 |      1.9  |  0.0632 |    1.58 |    0.39 |      -4.62 |     0.31 |
| O_downDay_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | DESC              |      97 |      2.1  |  0.0446 |    4.32 |    0.73 |      -4.47 |     0.25 |
| O_downDay_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | REP               |      31 |      2.19 | -0.0276 |   -0.86 |   -0.28 |      -2.79 |    -0.26 |
| O_downDay_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | HOLDOUT           |      55 |      2.57 |  0.0427 |    2.35 |    0.52 |      -4.04 |     0.33 |
| O_downDay_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | TERMINAL_OctNov26 |       2 |      1.27 |  0.3369 |    0.67 |    0.33 |      -1.04 |     4.97 |
| O_downDay_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | POST_OCT2025_Bull |      25 |      1.9  |  0.0361 |    0.9  |    0.22 |      -4.85 |     0.17 |
| O_downDay_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | DESC              |      97 |      2.1  |  0.0367 |    3.56 |    0.6  |      -4.71 |     0.2  |
| O_downDay_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | REP               |      31 |      2.19 | -0.0344 |   -1.07 |   -0.35 |      -2.88 |    -0.31 |
| O_downDay_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | HOLDOUT           |      55 |      2.57 |  0.0353 |    1.94 |    0.43 |      -4.26 |     0.26 |
| O_downDay_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | TERMINAL_OctNov26 |       2 |      1.27 |  0.3286 |    0.66 |    0.32 |      -1.04 |     4.81 |
| O_downDay_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | POST_OCT2025_Bull |      25 |      1.9  |  0.0286 |    0.72 |    0.18 |      -4.92 |     0.13 |
| O_allDays_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | DESC              |     268 |      5.81 |  0.0418 |   11.2  |    1.16 |      -7.25 |     0.4  |
| O_allDays_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | REP               |      89 |      6.29 |  0.0532 |    4.74 |    0.79 |      -5.18 |     0.78 |
| O_allDays_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | HOLDOUT           |     141 |      6.58 |  0.0349 |    4.93 |    0.6  |      -8.77 |     0.31 |
| O_allDays_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | TERMINAL_OctNov26 |       4 |      2.55 |  0.0996 |    0.4  |    0.17 |      -2.01 |     1.51 |
| O_allDays_noWed_ATR50 | Futuros_MNQ (1.545pt, 0 swap) | POST_OCT2025_Bull |      63 |      4.78 |  0.0066 |    0.42 |    0.08 |      -5.21 |     0.07 |
| O_allDays_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | DESC              |     268 |      5.81 |  0.0131 |    3.51 |    0.36 |     -10.41 |     0.09 |
| O_allDays_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | REP               |      89 |      6.29 |  0.0289 |    2.57 |    0.43 |      -5.99 |     0.36 |
| O_allDays_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | HOLDOUT           |     141 |      6.58 |  0.0082 |    1.15 |    0.14 |      -9.83 |     0.07 |
| O_allDays_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | TERMINAL_OctNov26 |       4 |      2.55 |  0.0699 |    0.28 |    0.12 |      -2.07 |     1.03 |
| O_allDays_noWed_ATR50 | CFD_SwapBase_8pct_3xWed       | POST_OCT2025_Bull |      63 |      4.78 | -0.0206 |   -1.3  |   -0.24 |      -5.68 |    -0.21 |
| O_allDays_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | DESC              |     268 |      5.81 |  0.0051 |    1.37 |    0.14 |     -11.31 |     0.03 |
| O_allDays_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | REP               |      89 |      6.29 |  0.0221 |    1.97 |    0.33 |      -6.22 |     0.27 |
| O_allDays_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | HOLDOUT           |     141 |      6.58 |  0.0007 |    0.1  |    0.01 |     -10.12 |     0.01 |
| O_allDays_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | TERMINAL_OctNov26 |       4 |      2.55 |  0.0617 |    0.25 |    0.1  |      -2.09 |     0.9  |
| O_allDays_noWed_ATR50 | CFD_SwapStress_10pct_3xWed    | POST_OCT2025_Bull |      63 |      4.78 | -0.0281 |   -1.77 |   -0.33 |      -5.81 |    -0.28 |

---

## 2. Expansion Estructural de Frecuencia sin Sobreajuste (`DESC -> REP -> HOLDOUT + TERMINAL`)

Regla de seleccion estricta fijada *ex-ante* sobre `DESC` (`mult_frec >= 1.5x`, `t_ses >= 2.0`, `Calmar >= 1.5`) y confirmacion ciega en `REP` (`R/op >= +0.08`, `t_ses >= 1.5`, `Calmar >= 1.2`), sin optimizacion de umbrales numericos:

| modulo     | tipo                 | variante                     |   mult_frec_desc |   desc_ops_mes |   desc_r_op |   desc_t_ses |   desc_calmar |   rep_ops_mes |   rep_r_op |   rep_t_ses |   rep_calmar |   hold_ops_mes |   hold_r_op |   hold_sum_r |   hold_calmar |   term_n_ops |   term_sum_r | veredicto_anti_overfit   |
|:-----------|:---------------------|:-----------------------------|-----------------:|---------------:|------------:|-------------:|--------------:|--------------:|-----------:|------------:|-------------:|---------------:|------------:|-------------:|--------------:|-------------:|-------------:|:-------------------------|
| R          | BASELINE             | R_M10_osc30_end660_ATR50     |             1    |           2.82 |      0.3719 |         3.81 |          3.46 |          2.9  |     0.154  |        1.11 |         1.9  |           2.24 |      0.201  |         9.65 |          2.2  |            5 |         4.88 | BASELINE                 |
| R          | BASELINE_STOP        | R_M10_osc30_end660_ATR25     |             1    |           2.82 |      0.5923 |         3.78 |          2.89 |          2.9  |     0.3907 |        1.54 |         2.43 |           2.24 |      0.304  |        14.59 |          1.76 |            5 |        10.75 | BASELINE                 |
| R          | STRUCT_TF5M          | R_M5_osc30_end660_ATR50      |             1.04 |           2.93 |      0.2808 |         2.96 |          1.88 |          2.83 |     0.0994 |        0.82 |         1.01 |           2.57 |      0.1385 |         7.62 |          1.49 |            6 |         7.71 | RECHAZADA_EN_DESC        |
| R          | STRUCT_TF5M_PM       | R_M5_osc30_end840_ATR50      |             1.04 |           2.93 |      0.2808 |         2.96 |          1.88 |          2.83 |     0.0994 |        0.82 |         1.01 |           2.61 |      0.1436 |         8.04 |          1.57 |            6 |         7.71 | RECHAZADA_EN_DESC        |
| R          | STRUCT_TF5M_PM       | R_M5_osc30_end840_ATR25      |             1.04 |           2.93 |      0.5635 |         3.6  |          2.67 |          2.83 |     0.1086 |        0.53 |         0.6  |           2.61 |      0.3209 |        17.97 |          1.32 |            6 |        15.2  | RECHAZADA_EN_DESC        |
| Z          | BASELINE             | Z_b15_wickFree_eff40_ATR50   |             1    |           2.36 |      0.1925 |         3.09 |          3.02 |          2.12 |     0.1738 |        1.56 |         2.16 |           2.01 |      0.1288 |         5.54 |          1.24 |            7 |         3.34 | BASELINE                 |
| Z          | STRUCT_CLOSE_SIDE    | Z_b15_closeSide_eff40_ATR50  |             1.54 |           3.64 |      0.17   |         3.31 |          3.54 |          3.54 |     0.0734 |        0.97 |         1.26 |           3.55 |      0.1156 |         8.79 |          1.66 |            9 |         4.14 | SOLO_DESC_FALLA_REP      |
| Z          | STRUCT_MAX1_WICK     | Z_b15_max1Wick_eff40_ATR50   |             1.22 |           2.89 |      0.1834 |         3.1  |          2.38 |          2.76 |     0.1581 |        1.62 |         3.19 |           2.8  |      0.1146 |         6.88 |          1.59 |            8 |         3.57 | RECHAZADA_EN_DESC        |
| Z          | STRUCT_HALFDAY       | Z_halfDay_1300ET_eff40_ATR35 |             1.94 |           4.58 |     -0.1286 |        -2.96 |         -0.26 |          3.96 |    -0.0339 |       -0.48 |        -0.26 |           4.01 |     -0.0214 |        -1.84 |         -0.15 |           14 |        -4.65 | RECHAZADA_EN_DESC        |
| O_CFD_Swap | BASELINE_CFD_SWAP    | O_downDay_ATR50              |             1    |           2.84 |      0.0119 |         0.2  |          0.07 |          3.54 |     0.0059 |        0.07 |         0.07 |           3.45 |     -0.019  |        -1.41 |         -0.15 |            2 |         0.67 | BASELINE                 |
| O_CFD_Swap | BASELINE_NOWED_SWAP  | O_downDay_noWed_ATR50        |             0.74 |           2.1  |      0.0446 |         0.73 |          0.25 |          2.19 |    -0.0276 |       -0.28 |        -0.26 |           2.57 |      0.0427 |         2.35 |          0.33 |            2 |         0.67 | BASELINE                 |
| O_CFD_Swap | STRUCT_ALLDAYS_SWAP  | O_allDays_ATR50              |             2.71 |           7.7  |      0.0036 |         0.11 |          0.04 |          8.63 |     0.0294 |        0.49 |         0.62 |           8.73 |     -0.0031 |        -0.58 |         -0.03 |            6 |        -0.4  | RECHAZADA_EN_DESC        |
| O_CFD_Swap | STRUCT_ALLDAYS_NOWED | O_allDays_noWed_ATR50        |             2.05 |           5.81 |      0.0131 |         0.36 |          0.09 |          6.29 |     0.0289 |        0.43 |         0.36 |           6.58 |      0.0082 |         1.15 |          0.07 |            4 |         0.28 | RECHAZADA_EN_DESC        |

---

## 3. Validacion Cruzada de `R_ATR25` y `SpeedEval (T_Only -> Core5)` por Cuenta Individual (1 Slot)

*(Nota de auditoria: en esta iteracion se corrigio el escalado de cupos para respetar estrictamente `max_funded` legal por hogar en cada firma: max 5 en Lucid y Tradeify, max 3-5 en Topstep, max 300K-400K en FTMO).*

| firm     |   account_size | modo                               | particion   |   neto12_medio_usd |   p_neto12_pos_pct |   caja_min_p10_usd |   ratio_net12_p10 |
|:---------|---------------:|:-----------------------------------|:------------|-------------------:|-------------------:|-------------------:|------------------:|
| Lucid    |         150000 | Core5 -> Core5                     | REP         |             7913.6 |               88.8 |            -1499.8 |             5.277 |
| Lucid    |         150000 | Core5_R25 -> Core5_R25             | REP         |             9090.4 |               92.2 |            -1499.8 |             6.061 |
| Lucid    |         150000 | SpeedEval: T_Only -> Core5         | REP         |             6171.5 |               76.4 |            -1285.5 |             4.801 |
| Lucid    |         150000 | SpeedEval_R25: T_Only -> Core5_R25 | REP         |             6646.6 |               77.8 |            -1285.5 |             5.17  |
| Tradeify |         150000 | Core5 -> Core5                     | REP         |            11131.9 |               88.2 |            -1808.1 |             6.157 |
| Tradeify |         150000 | Core5_R25 -> Core5_R25             | REP         |            13955.7 |               91.7 |            -1808.1 |             7.718 |
| Tradeify |         150000 | SpeedEval: T_Only -> Core5         | REP         |             8236.7 |               76.4 |            -1549.8 |             5.315 |
| Tradeify |         150000 | SpeedEval_R25: T_Only -> Core5_R25 | REP         |             9795.1 |               77.8 |            -1549.8 |             6.32  |
| Lucid    |          50000 | Core5 -> Core5                     | REP         |             4250.2 |               88.7 |             -856.8 |             4.961 |
| Lucid    |          50000 | Core5_R25 -> Core5_R25             | REP         |             5350.2 |               92.4 |             -761.6 |             7.025 |
| Lucid    |          50000 | SpeedEval: T_Only -> Core5         | REP         |             3941.6 |               85.9 |             -666.4 |             5.915 |
| Lucid    |          50000 | SpeedEval_R25: T_Only -> Core5_R25 | REP         |             4895.9 |               89.2 |             -666.4 |             7.347 |
| Topstep  |          50000 | Core5 -> Core5                     | REP         |             5134.8 |               88.8 |             -950   |             5.405 |
| Topstep  |          50000 | Core5_R25 -> Core5_R25             | REP         |             7532.7 |               93.2 |             -855   |             8.81  |
| Topstep  |          50000 | SpeedEval: T_Only -> Core5         | REP         |             4368.2 |               83.8 |            -1140   |             3.832 |
| Topstep  |          50000 | SpeedEval_R25: T_Only -> Core5_R25 | REP         |             6131   |               87.5 |            -1045   |             5.867 |
| Lucid    |         150000 | Core5 -> Core5                     | HOLDOUT     |             5278.3 |               77.5 |            -1714   |             3.08  |
| Lucid    |         150000 | Core5_R25 -> Core5_R25             | HOLDOUT     |             5362.2 |               78.4 |            -2142.5 |             2.503 |
| Lucid    |         150000 | SpeedEval: T_Only -> Core5         | HOLDOUT     |             5054.9 |               73.7 |            -1071.2 |             4.719 |
| Lucid    |         150000 | SpeedEval_R25: T_Only -> Core5_R25 | HOLDOUT     |             5020.9 |               72.3 |            -1071.2 |             4.687 |
| Tradeify |         150000 | Core5 -> Core5                     | HOLDOUT     |             6182.5 |               77.7 |            -2066.4 |             2.992 |
| Tradeify |         150000 | Core5_R25 -> Core5_R25             | HOLDOUT     |             6449   |               78   |            -2583   |             2.497 |
| Tradeify |         150000 | SpeedEval: T_Only -> Core5         | HOLDOUT     |             5826   |               73.7 |            -1291.5 |             4.511 |
| Tradeify |         150000 | SpeedEval_R25: T_Only -> Core5_R25 | HOLDOUT     |             5989.8 |               72.3 |            -1291.5 |             4.638 |
| Lucid    |          50000 | Core5 -> Core5                     | HOLDOUT     |             2907.7 |               80.2 |             -952   |             3.054 |
| Lucid    |          50000 | Core5_R25 -> Core5_R25             | HOLDOUT     |             2797.7 |               78.8 |            -1142.4 |             2.449 |
| Lucid    |          50000 | SpeedEval: T_Only -> Core5         | HOLDOUT     |             3188   |               80   |             -571.2 |             5.581 |
| Lucid    |          50000 | SpeedEval_R25: T_Only -> Core5_R25 | HOLDOUT     |             3222.2 |               80.8 |             -666.4 |             4.835 |
| Topstep  |          50000 | Core5 -> Core5                     | HOLDOUT     |             3365.4 |               81.6 |            -1140   |             2.952 |
| Topstep  |          50000 | Core5_R25 -> Core5_R25             | HOLDOUT     |             3489.9 |               80.5 |            -1283.1 |             2.72  |
| Topstep  |          50000 | SpeedEval: T_Only -> Core5         | HOLDOUT     |             3134.1 |               80.2 |            -1140   |             2.749 |
| Topstep  |          50000 | SpeedEval_R25: T_Only -> Core5_R25 | HOLDOUT     |             3217.3 |               79.8 |            -1235   |             2.605 |

---

## 4. Simulacion Sincronizada del Ecosistema Paralelo Multi-Frente ('Roadmap' por Nivel de Caja)

| ecosistema_id               | descripcion                                                                                | particion   | regimen_media   |   capital_req_p90_usd |   capital_req_p95_usd |   neto12_medio_usd |   neto12_p50_usd |   neto24_medio_usd |   p_neto12_pos_pct |   retiros_12m_est |   caja_min_p10_usd |   caja_min_p05_usd |   ratio_net12_p10 |   boveda_pers_24m_usd |
|:----------------------------|:-------------------------------------------------------------------------------------------|:------------|:----------------|----------------------:|----------------------:|-------------------:|-----------------:|-------------------:|-------------------:|------------------:|-------------------:|-------------------:|------------------:|----------------------:|
| CFD_Bench_Core5_1FTMO       | Benchmark CFD Solo US100 Core5_R25 (1x FTMO 100K)                                          | REP         | 100%            |                   540 |                   540 |            14287.1 |          13677.3 |            39531   |               91   |               5.8 |             -540   |             -540   |            26.458 |                   0   |
| CFD_Clean_NQ_ES_1FTMO       | CFD Intradia US100+US500 Cero Swap (1x FTMO 100K)                                          | REP         | 100%            |                   540 |                   540 |            16188   |          15504.1 |            43349.4 |               92.5 |               6.1 |             -540   |             -540   |            29.978 |                   0   |
| CFD_With_O_Swap_1FTMO       | CFD US100+US500 + O Neto Swap 8% (1x FTMO 100K)                                            | REP         | 100%            |                   540 |                   540 |            16042.9 |          15443.6 |            43027.4 |               92.1 |               6.1 |             -540   |             -540   |            29.709 |                   0   |
| E1_Semilla_5Ctas            | 2x Lucid50K + 2x Tradeify50K (SpeedEval/Core5_R25) + 1x The5ers 100K (US100+US500)         | REP         | 100%            |                  3023 |                  3866 |            37559.5 |          36535.8 |            87798.8 |               94.6 |              22.3 |            -3023.4 |            -3866.2 |            12.423 |                   0   |
| E2_Balanceado_6Ctas         | 2x Lucid150K + 2x Tradeify150K + 1x FTMO Swing 100K + 1x The5ers 100K                      | REP         | 100%            |                  6435 |                  7791 |            72204.3 |          67654.4 |           174264   |               93.3 |              27.8 |            -6434.7 |            -7790.8 |            11.221 |                   0   |
| E3_Institucional_12Ctas     | 3x Lucid150K + 3x Tradeify150K + 2x Topstep50K + 2x FTMO 100K + 2x The5ers 100K            | REP         | 100%            |                 11514 |                 13980 |           138260   |         129497   |           339600   |               93.9 |              60.3 |           -11514.3 |           -13979.9 |            12.008 |                   0   |
| E4_TopeLegal_20Ctas_Bruto   | 5x Lucid150K + 5x Tradeify150K + 3x Topstep50K + 2x FN50K + 3x FTMO 100K + 2x The5ers 100K | REP         | 100%            |                 18342 |                 22105 |           202174   |         191379   |           488037   |               93.3 |              92.4 |           -18341.5 |           -22105.4 |            11.023 |                   0   |
| E5_Master_Throttle_y_Boveda | E4 Tope Legal + Freno Dinamico Caja (-$7.5K) + 30% Sweep a Boveda Personal (0.75% 1R)      | REP         | 100%            |                  9902 |                 10845 |           211218   |         196787   |           524771   |               95.6 |              86.9 |            -9902   |           -10845.4 |            21.331 |              179680   |
| CFD_Bench_Core5_1FTMO       | Benchmark CFD Solo US100 Core5_R25 (1x FTMO 100K)                                          | REP         | 60%             |                  1080 |                  1080 |             6249.8 |           3893.3 |            19240.8 |               66.2 |               2.9 |            -1080   |            -1080   |             5.787 |                   0   |
| CFD_Clean_NQ_ES_1FTMO       | CFD Intradia US100+US500 Cero Swap (1x FTMO 100K)                                          | REP         | 60%             |                  1080 |                  1080 |             7280.5 |           4751.4 |            21340.7 |               69.3 |               3.2 |            -1080   |            -1080   |             6.741 |                   0   |
| CFD_With_O_Swap_1FTMO       | CFD US100+US500 + O Neto Swap 8% (1x FTMO 100K)                                            | REP         | 60%             |                  1080 |                  1080 |             7234.7 |           4914.6 |            21262.6 |               69.3 |               3.2 |            -1080   |            -1080   |             6.699 |                   0   |
| E1_Semilla_5Ctas            | 2x Lucid50K + 2x Tradeify50K (SpeedEval/Core5_R25) + 1x The5ers 100K (US100+US500)         | REP         | 60%             |                  4993 |                  5973 |            18506.1 |          12905.6 |            46991.5 |               78.5 |              12.9 |            -4993.3 |            -5973.2 |             3.706 |                   0   |
| E2_Balanceado_6Ctas         | 2x Lucid150K + 2x Tradeify150K + 1x FTMO Swing 100K + 1x The5ers 100K                      | REP         | 60%             |                 11346 |                 13758 |            31157.9 |          19189   |            82828.2 |               72.2 |              14.6 |           -11345.9 |           -13757.6 |             2.746 |                   0   |
| E3_Institucional_12Ctas     | 3x Lucid150K + 3x Tradeify150K + 2x Topstep50K + 2x FTMO 100K + 2x The5ers 100K            | REP         | 60%             |                 19901 |                 24267 |            60731.7 |          38461.5 |           162621   |               74.4 |              32.7 |           -19901.4 |           -24267.4 |             3.052 |                   0   |
| E4_TopeLegal_20Ctas_Bruto   | 5x Lucid150K + 5x Tradeify150K + 3x Topstep50K + 2x FN50K + 3x FTMO 100K + 2x The5ers 100K | REP         | 60%             |                 31837 |                 37267 |            88175.8 |          56645.4 |           231946   |               73.5 |              50.5 |           -31836.7 |           -37266.8 |             2.77  |                   0   |
| E5_Master_Throttle_y_Boveda | E4 Tope Legal + Freno Dinamico Caja (-$7.5K) + 30% Sweep a Boveda Personal (0.75% 1R)      | REP         | 60%             |                 12855 |                 14395 |            97211.2 |          61479.4 |           253836   |               79.1 |              47.5 |           -12855.1 |           -14394.5 |             7.562 |               83341.3 |
| CFD_Bench_Core5_1FTMO       | Benchmark CFD Solo US100 Core5_R25 (1x FTMO 100K)                                          | HOLDOUT     | 100%            |                   540 |                  1080 |             7733.6 |           6425.3 |            23988.3 |               75.3 |               3.8 |             -540   |            -1080   |            14.321 |                   0   |
| CFD_Clean_NQ_ES_1FTMO       | CFD Intradia US100+US500 Cero Swap (1x FTMO 100K)                                          | HOLDOUT     | 100%            |                   540 |                  1080 |             8787.2 |           7354.9 |            26109   |               78.2 |               4   |             -540   |            -1080   |            16.273 |                   0   |
| CFD_With_O_Swap_1FTMO       | CFD US100+US500 + O Neto Swap 8% (1x FTMO 100K)                                            | HOLDOUT     | 100%            |                   540 |                  1080 |             8952.6 |           7637.5 |            26522.6 |               78.4 |               4.1 |             -540   |            -1080   |            16.579 |                   0   |
| E1_Semilla_5Ctas            | 2x Lucid50K + 2x Tradeify50K (SpeedEval/Core5_R25) + 1x The5ers 100K (US100+US500)         | HOLDOUT     | 100%            |                  3234 |                  4011 |            22555.9 |          19629.3 |            55776.9 |               86.8 |              15.6 |            -3234.1 |            -4011   |             6.974 |                   0   |
| E2_Balanceado_6Ctas         | 2x Lucid150K + 2x Tradeify150K + 1x FTMO Swing 100K + 1x The5ers 100K                      | HOLDOUT     | 100%            |                  7807 |                  9399 |            41342   |          33494.8 |           105348   |               82.8 |              18.8 |            -7807.5 |            -9399.3 |             5.295 |                   0   |
| E3_Institucional_12Ctas     | 3x Lucid150K + 3x Tradeify150K + 2x Topstep50K + 2x FTMO 100K + 2x The5ers 100K            | HOLDOUT     | 100%            |                 14325 |                 17244 |            77152.2 |          62299   |           200510   |               83.4 |              40   |           -14324.7 |           -17244.3 |             5.386 |                   0   |
| E4_TopeLegal_20Ctas_Bruto   | 5x Lucid150K + 5x Tradeify150K + 3x Topstep50K + 2x FN50K + 3x FTMO 100K + 2x The5ers 100K | HOLDOUT     | 100%            |                 22341 |                 26720 |           114665   |          93948.1 |           289519   |               83.2 |              62.2 |           -22340.7 |           -26719.9 |             5.133 |                   0   |
| E5_Master_Throttle_y_Boveda | E4 Tope Legal + Freno Dinamico Caja (-$7.5K) + 30% Sweep a Boveda Personal (0.75% 1R)      | HOLDOUT     | 100%            |                 10725 |                 11716 |           121457   |          98957.7 |           309411   |               86.4 |              58.5 |           -10725   |           -11716   |            11.325 |              102220   |
