# Propuestas Cuantificadas para Monetizar Estrategias Rentables Excluidas de Core5_AltaConv

- **Universo evaluado**: Simulaciones Monte Carlo sincronizadas (`N=2000`, `H=504` dias = 24 meses, misma matriz `j_seq` por particion) sobre `POST_2020` (`2020-01-01..2026-09-30` en `REP 100%`, `REP 60%` y `HOLDOUT`), y ventana `<= 2025-10-13` para analisis exacto del modulo overnight `O` (`NQ_fabrica_O.pkl`).
- **Friccion CFD calibrada**: `$0` comision + spread mediano `USATECHIDXUSD = 1.438` pts en NQ CFD (`US500 = 0.35` pts en ES CFD).

## 1. Matriz de Correlacion OOS entre Sleeves (<= 2025-10-13, REP + HOLDOUT)

|              |   Core5_NQ |   VW_NQ |   O_NQ_50 |   O_NQ_25 |   ES_Core_CFD |   Core5_R25_NQ |
|:-------------|-----------:|--------:|----------:|----------:|--------------:|---------------:|
| Core5_NQ     |      1     |   0.43  |     0.054 |     0.08  |         0.448 |          0.973 |
| VW_NQ        |      0.43  |   1     |     0.013 |     0.039 |         0.572 |          0.413 |
| O_NQ_50      |      0.054 |   0.013 |     1     |     0.921 |         0.052 |          0.054 |
| O_NQ_25      |      0.08  |   0.039 |     0.921 |     1     |         0.075 |          0.074 |
| ES_Core_CFD  |      0.448 |   0.572 |     0.052 |     0.075 |         1     |          0.441 |
| Core5_R25_NQ |      0.973 |   0.413 |     0.054 |     0.074 |         0.441 |          1     |

## 2. Propuesta 1: Cuentas 'Call-Option' Separadas (`V + W`) vs Fusionar en `P_OPT_SF_v2`

| Arquitectura | Part | Regimen | Neto 12m (USD) | Neto 24m (USD) | P(Net>0) | Retiros 12m | Caja Min p10 (USD) | Neto/p10 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `A0_Core5_4CTA` | REP | 100% | 187,330.0 | 404,917.5 | 85.5% | 77.26 | -43,550.7 | 4.301 |
| `A0_P7_4CTA` | REP | 100% | 150,527.7 | 330,780.0 | 75.6% | 67.32 | -69,117.8 | 2.178 |
| `A1_Core5_plus_VW_BulFN` | REP | 100% | 183,554.5 | 409,077.7 | 84.4% | 79.47 | -49,019.6 | 3.745 |
| `A1b_Core5_plus_VW_Lucid50` | REP | 100% | 186,446.3 | 413,706.9 | 85.1% | 79.30 | -46,577.2 | 4.003 |
| `A2_Core5_R25_4CTA` | REP | 100% | 221,701.4 | 469,549.3 | 89.1% | 86.50 | -43,479.0 | 5.099 |
| `A0_Core5_4CTA` | REP | 60% | 80,368.3 | 193,337.9 | 61.6% | 43.94 | -79,464.2 | 1.011 |
| `A0_P7_4CTA` | REP | 60% | 59,784.6 | 149,795.5 | 53.5% | 41.02 | -108,985.4 | 0.549 |
| `A1_Core5_plus_VW_BulFN` | REP | 60% | 75,667.6 | 191,177.0 | 59.1% | 45.37 | -87,725.1 | 0.863 |
| `A1b_Core5_plus_VW_Lucid50` | REP | 60% | 78,329.9 | 196,718.2 | 60.6% | 45.18 | -82,804.4 | 0.946 |
| `A2_Core5_R25_4CTA` | REP | 60% | 91,017.1 | 212,566.7 | 63.3% | 47.56 | -83,484.0 | 1.090 |
| `A0_Core5_4CTA` | HOLDOUT | 100% | 117,539.1 | 275,101.9 | 76.1% | 55.92 | -51,451.9 | 2.284 |
| `A0_P7_4CTA` | HOLDOUT | 100% | 20,228.1 | 57,865.8 | 41.7% | 28.50 | -117,514.4 | 0.172 |
| `A1_Core5_plus_VW_BulFN` | HOLDOUT | 100% | 111,694.9 | 263,769.9 | 74.6% | 56.00 | -59,103.6 | 1.890 |
| `A1b_Core5_plus_VW_Lucid50` | HOLDOUT | 100% | 114,702.0 | 270,603.7 | 75.3% | 56.08 | -55,491.5 | 2.067 |
| `A2_Core5_R25_4CTA` | HOLDOUT | 100% | 117,355.3 | 269,495.6 | 74.4% | 55.86 | -57,805.7 | 2.030 |

### Desempeno Aislado de `(V + W)` en Cuentas Promo Baratas

| Cuenta / Sleeve | Part | Regimen | Fee Eval | Act Fee | Neto 12m (USD) | Neto 24m (USD) | P(Net>0) | Caja p10 (USD) | Ret 12m |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `VW_Bulenox150 ($65)` | REP | 100% | 65.00 | 498.00 | -3,601.7 | 2,117.8 | 11.3% | -12,091.3 | 1.19 |
| `VW_FundedNext50 ($80)` | REP | 100% | 80.00 | 0.00 | -173.7 | 2,042.5 | 17.3% | -2,720.0 | 1.02 |
| `VW_Lucid50 ($95)` | REP | 100% | 95.20 | 0.00 | -441.8 | 4,394.7 | 17.5% | -3,903.2 | 1.02 |
| `VW_Topstep50 ($95)` | REP | 100% | 95.00 | 0.00 | -3,801.9 | -1,274.7 | 14.8% | -12,350.0 | 2.05 |
| `VW_Bulenox150 ($65)` | HOLDOUT | 100% | 65.00 | 498.00 | -4,377.9 | -8,759.1 | 0.1% | -10,680.0 | 0.01 |
| `VW_FundedNext50 ($80)` | HOLDOUT | 100% | 80.00 | 0.00 | -1,466.3 | -2,572.9 | 1.6% | -3,760.0 | 0.07 |
| `VW_Lucid50 ($95)` | HOLDOUT | 100% | 95.20 | 0.00 | -1,418.6 | -2,249.1 | 1.7% | -3,522.4 | 0.08 |
| `VW_Topstep50 ($95)` | HOLDOUT | 100% | 95.00 | 0.00 | -5,830.4 | -11,163.7 | 1.2% | -12,445.0 | 0.23 |

## 3. Propuestas 2 y 3: Desbloquear `O` Overnight y Satelite `ES/US500` en Props CFD Static-DD

| Ventana | Firma CFD | Part | Estrategia | Neto 12m (USD) | Neto 24m (USD) | Retiros 12m (USD) | P(Net>0) | Caja p10 (USD) | Evals 24m |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| FULL_2020_2026 | `FTMO_Swing_100K` | REP | `CFD_Core5_NQ` | 14,295.3 | 39,260.4 | 14,936.0 | 89.0% | -1,080.0 | 1.45 |
| FULL_2020_2026 | `FTMO_Swing_100K` | REP | `CFD_ES_US500_Core` | -531.0 | -2.4 | 9.0 | 0.5% | -540.0 | 1.00 |
| FULL_2020_2026 | `FTMO_Swing_100K` | REP | `CFD_NQ_plus_ES` | 16,318.8 | 43,268.0 | 16,993.2 | 90.8% | -1,080.0 | 1.59 |
| FULL_2020_2026 | `The5ers_HighStakes_100K` | REP | `CFD_Core5_NQ` | 15,823.2 | 41,188.6 | 16,417.2 | 91.5% | -990.0 | 1.48 |
| FULL_2020_2026 | `The5ers_HighStakes_100K` | REP | `CFD_ES_US500_Core` | -461.4 | 481.4 | 33.6 | 1.8% | -495.0 | 1.00 |
| FULL_2020_2026 | `The5ers_HighStakes_100K` | REP | `CFD_NQ_plus_ES` | 17,929.8 | 45,391.9 | 18,555.2 | 93.5% | -990.0 | 1.60 |
| FULL_2020_2026 | `FTMO_Swing_100K` | HOLDOUT | `CFD_Core5_NQ` | 9,559.7 | 28,797.1 | 10,211.2 | 79.4% | -1,080.0 | 1.50 |
| FULL_2020_2026 | `FTMO_Swing_100K` | HOLDOUT | `CFD_ES_US500_Core` | -540.0 | -510.4 | 0.0 | 0.0% | -540.0 | 1.00 |
| FULL_2020_2026 | `FTMO_Swing_100K` | HOLDOUT | `CFD_NQ_plus_ES` | 10,779.6 | 31,168.0 | 11,453.2 | 81.2% | -1,080.0 | 1.60 |
| FULL_2020_2026 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_Core5_NQ` | 11,005.3 | 30,706.5 | 11,613.7 | 84.1% | -990.0 | 1.54 |
| FULL_2020_2026 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_ES_US500_Core` | -495.0 | -395.7 | 0.0 | 0.0% | -495.0 | 1.00 |
| FULL_2020_2026 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_NQ_plus_ES` | 12,226.4 | 33,197.1 | 12,852.8 | 85.5% | -990.0 | 1.62 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | REP | `CFD_Core5_NQ` | 9,194.4 | 27,215.3 | 9,873.8 | 76.4% | -1,080.0 | 1.63 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | REP | `CFD_ES_US500_Core` | -539.0 | -411.2 | 1.3 | 0.1% | -540.0 | 1.00 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | REP | `CFD_NQ_plus_ES` | 10,729.9 | 30,253.6 | 11,446.0 | 81.2% | -1,080.0 | 1.76 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | REP | `CFD_O_Overnight_Solo` | 402.8 | 7,036.4 | 943.1 | 23.6% | -540.0 | 1.01 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | REP | `CFD_Core5_plus_O` | 16,964.3 | 44,819.2 | 17,618.5 | 91.5% | -1,080.0 | 1.53 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | REP | `CFD_Master_NQ_O_ES` | 18,530.1 | 47,923.6 | 19,208.6 | 92.8% | -1,080.0 | 1.61 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | REP | `CFD_Core5_NQ` | 10,565.8 | 29,177.6 | 11,204.1 | 82.5% | -990.0 | 1.66 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | REP | `CFD_ES_US500_Core` | -492.8 | -178.1 | 2.4 | 0.1% | -495.0 | 1.00 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | REP | `CFD_NQ_plus_ES` | 12,170.7 | 32,346.1 | 12,843.6 | 85.4% | -990.0 | 1.81 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | REP | `CFD_O_Overnight_Solo` | 981.3 | 8,497.4 | 1,477.3 | 33.9% | -495.0 | 1.01 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | REP | `CFD_Core5_plus_O` | 18,512.1 | 46,835.2 | 19,119.3 | 94.2% | -990.0 | 1.54 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | REP | `CFD_Master_NQ_O_ES` | 20,147.1 | 50,098.2 | 20,773.0 | 94.7% | -990.0 | 1.62 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | HOLDOUT | `CFD_Core5_NQ` | 7,437.2 | 24,544.5 | 8,101.1 | 74.2% | -1,080.0 | 1.55 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | HOLDOUT | `CFD_ES_US500_Core` | -540.0 | -536.6 | 0.0 | 0.0% | -540.0 | 1.00 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | HOLDOUT | `CFD_NQ_plus_ES` | 8,172.5 | 26,068.5 | 8,856.9 | 76.2% | -1,080.0 | 1.61 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | HOLDOUT | `CFD_O_Overnight_Solo` | -409.3 | 1,092.1 | 160.4 | 4.7% | -1,080.0 | 1.14 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | HOLDOUT | `CFD_Core5_plus_O` | 11,029.8 | 31,666.4 | 11,773.1 | 82.3% | -1,080.0 | 1.88 |
| O_WINDOW_2020_202510 | `FTMO_Swing_100K` | HOLDOUT | `CFD_Master_NQ_O_ES` | 11,851.7 | 33,214.5 | 12,628.5 | 83.7% | -1,080.0 | 1.99 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_Core5_NQ` | 8,785.8 | 26,529.3 | 9,399.9 | 80.7% | -990.0 | 1.56 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_ES_US500_Core` | -495.0 | -482.2 | 0.0 | 0.0% | -495.0 | 1.00 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_NQ_plus_ES` | 9,555.6 | 28,013.4 | 10,189.2 | 82.5% | -990.0 | 1.64 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_O_Overnight_Solo` | -219.3 | 1,703.7 | 303.2 | 8.7% | -990.0 | 1.15 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_Core5_plus_O` | 12,569.9 | 33,977.6 | 13,268.6 | 87.4% | -990.0 | 1.94 |
| O_WINDOW_2020_202510 | `The5ers_HighStakes_100K` | HOLDOUT | `CFD_Master_NQ_O_ES` | 13,326.4 | 35,486.4 | 14,055.3 | 88.4% | -990.0 | 2.05 |

## 4. Propuesta 4: Swap `R_maeATR25` y Especializacion de Ciclo de Vida (`EdgeLabFundedSyncSingleModule`)

| Modo Ciclo de Vida (`LucidFlex 150K`) | Part | Regimen | Neto 12m (USD) | Neto 24m (USD) | P(Net>0) | Retiros 12m | Caja p10 (USD) | Neto/p10 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `Base: Core5 -> Core5` | REP | 100% | 38,359.4 | 60,784.1 | 87.0% | 17.46 | -10,926.8 | 3.511 |
| `SpeedEval: T_Only -> Core5` | REP | 100% | 32,334.7 | 56,200.9 | 82.3% | 14.63 | -8,998.5 | 3.593 |
| `CushionFund: Core5 -> SnipersRZ` | REP | 100% | 111.8 | 18,010.6 | 32.1% | 1.92 | -8,570.0 | 0.013 |
| `T_Only -> SnipersRZ` | REP | 100% | -752.6 | 15,676.8 | 24.6% | 1.38 | -7,927.2 | -0.095 |
| `Base: Core5 -> Core5` | HOLDOUT | 100% | 27,632.4 | 54,172.0 | 78.7% | 13.80 | -13,069.2 | 2.114 |
| `SpeedEval: T_Only -> Core5` | HOLDOUT | 100% | 29,371.3 | 58,139.7 | 82.5% | 13.40 | -7,498.8 | 3.917 |
| `CushionFund: Core5 -> SnipersRZ` | HOLDOUT | 100% | -3,330.5 | 10,574.0 | 15.8% | 0.75 | -9,427.0 | -0.353 |
| `T_Only -> SnipersRZ` | HOLDOUT | 100% | -1,786.9 | 11,906.4 | 14.2% | 0.63 | -5,570.5 | -0.321 |

## 5. Propuesta 5: Cuenta Personal Sin Topes DD + Cartera Ortogonal `cartera_20261116`

| Sleeve / Blend Personal | N dias OOS | Sum R Equiv | R / mes | Sharpe | MaxDD R | Calmar |
|---|---:|---:|---:|---:|---:|---:|
| `Core5_NQ (2020-26 OOS)` | 747 | +152.95 | +4.300 | 1.90 | -21.34 | 2.42 |
| `VW_NQ (2020-26 OOS)` | 747 | +9.77 | +0.275 | 0.27 | -19.27 | 0.17 |
| `ES_Core_CFD (2020-26 OOS)` | 747 | +21.23 | +0.597 | 1.16 | -6.75 | 1.06 |
| `Personal_3_Sleeves (2020-26 OOS)` | 747 | +84.23 | +2.368 | 1.75 | -11.15 | 2.55 |
| `Core5_NQ (<=2025-10 OOS)` | 604 | +102.26 | +3.555 | 1.62 | -21.34 | 2.00 |
| `O_Overnight_Cap25 (<=2025-10 OOS)` | 604 | +35.68 | +1.241 | 1.16 | -10.55 | 1.41 |
| `Personal_4_Sleeves+O (<=2025-10 OOS)` | 604 | +55.28 | +1.922 | 1.65 | -10.79 | 2.14 |

- **Bloque ortogonal externo (`cartera_20261116`)**: 8 reglas multi-indice/multi-activo (`NQ, ES, YM, RTY, CL, MGC`) con correlacion cruzada cercana a cero (`rho ~= -0.02`) y `+15.9 R` en el holdout reciente de oct-nov 2026 segun `docs/research/cartera_20261116/RESULTADO.md`, aplicable como manga paralela en cuentas personales o satelite futuros.
