# Espiral Fase 2 — Síntesis Integrada (DESC+REP; HOLDOUT A5 del Pool Nuevo Sellado)

Estado: VIGENTE — análisis descriptivo sobre `167m` comunes `DESC+REP` (`N_eff PCA 5F = 4.62 / 5,00`).

## 1. Pools en `167m` DESC+REP y proyección K27 (`63m` sellados)
| Pool | `DESC Sh` | `REP Sh` | `DR Sh (t)` | `MDD@10%` | `K27 @0.7x` | `K27 @1.0x` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Pool_Sellado_2F_EQ (MVC+MRV)` | `0.941` | `1.158` | **`0.965 (3.6)`** | `-9.82%` | `0.461` | `0.714` |
| `Pool_Sellado_3F_EQ (MVC+MRV+FXF3)` | `1.087` | `0.974` | **`1.06 (3.95)`** | `-15.2%` | `0.522` | `0.783` |
| `Pool_Sellado_40_40_20 (MVC+MRV+FXF3)` | `1.073` | `1.117` | **`1.071 (3.99)`** | `-9.94%` | `0.529` | `0.791` |
| `Arquitectura_5F_20y (C2+RP4+MVC+MRV+FXF3)` | `1.222` | `1.346` | **`1.25 (4.66)`** | `-10.74%` | `0.641` | `0.889` |

## 2. Matriz de correlación mensual `DESC+REP`
|                 |   Carril2_Sell16 |   Macro_RP4 |   MVC_CTA_VRP |   MRV_PreFOMC |   FXF3_TreasuryME |   FXF_Canasta |
|:----------------|-----------------:|------------:|--------------:|--------------:|------------------:|--------------:|
| Carril2_Sell16  |            1     |       0.058 |         0.048 |        -0.038 |             0.129 |         0     |
| Macro_RP4       |            0.058 |       1     |         0.335 |        -0.207 |             0.083 |        -0.032 |
| MVC_CTA_VRP     |            0.048 |       0.335 |         1     |         0.021 |            -0.025 |         0.135 |
| MRV_PreFOMC     |           -0.038 |      -0.207 |         0.021 |         1     |            -0.141 |         0.003 |
| FXF3_TreasuryME |            0.129 |       0.083 |        -0.025 |        -0.141 |             1     |         0.664 |
| FXF_Canasta     |            0     |      -0.032 |         0.135 |         0.003 |             0.664 |         1     |

Aporte al referente: integra los 4 pilares de Fase 2 con los frentes de Fase 1 sin abrir ningún holdout sellado.
