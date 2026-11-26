# Analisis Bar-Open Phase Shift (CME NQ y CFD USATECHIDXUSD)

- **Muestra Experimento A (Sub-minuto `0..55s`)**: `322` sesiones reales con ticks CME `NQ` (`291` K30 `2025-08-05..2026-09-25` + `31` Sellado `2026-10-01..2026-11-13`, excluyendo puente M1 y `2026-10-07`). Warmup previo desde `2023-01-01` con M1 canonico.
- **Convencion tecnica sub-minuto**: cada barra desplazada `[k*60+delta, (k+1)*60+delta)` se etiqueta con cierre nominal `(k+1)*60s` (`:00` seg) para preservar `ExactMinute == true` en los motores C# y aislar el efecto puro de mover el corte de las velas.
- **Sanity Check (`M1 canonico` vs `ticks delta=0s`, 322 dias)**: Core5 `canon=719 (+150.88R)` vs `delta0=730 (+152.07R)`; P7 `canon=1005 (+131.58R)` vs `delta0=1016 (+131.07R)`.

## 1. Experimento A: Barrido Sub-Minuto `delta in {0, 5, ..., 55}s` (322 dias)

- **Core5_AltaConv**: `delta=0s = +152.06 R` | mediana 12 fases = `+105.06 R` (`+79.49` .. `+152.06 R`), **12/12 fases positivas**, retencion media = `71.5%`, MaxDD rango = `[-20.70, -12.10] R`.
- **P_OPT_SF_v2 (Core7)**: `delta=0s = +131.07 R` | mediana 12 fases = `+102.47 R` (`+76.42` .. `+131.07 R`), **12/12 fases positivas**, retencion media = `77.6%`.

| Modulo Independiente | N medio | delta=0s (R) | Mediana 12f (R) | Rango [Min, Max] | Fases > 0 | Retencion Media vs d0 | Corr diaria vs d0 |
|---|---:|---:|---:|---|---:|---:|---:|
| `R_osc30_end660_ATR50` | 43 | +18.48 | +19.64 | [+15.60, +22.46] | 12/12 | 106.4% | 0.940 |
| `Z_b15_e20_eff40_ATR50` | 41 | +8.89 | +9.57 | [+8.80, +10.88] | 12/12 | 108.0% | 0.926 |
| `T_stop100_BE15R_calFalse` | 282 | +55.00 | +21.22 | [-11.64, +55.00] | 10/12 | 35.9% | 0.699 |
| `V_nm25_noCap_mae30` | 277 | -4.08 | -1.19 | [-8.29, +3.69] | 4/12 | 36.7% | 0.849 |
| `W_slope_allowReFalse_ATR25` | 89 | +7.29 | +15.50 | [+6.19, +27.81] | 12/12 | 214.7% | 0.526 |
| `N_d5_fbTrue_ATR25` | 146 | +19.41 | +17.41 | [+14.26, +20.92] | 12/12 | 90.2% | 0.944 |
| `SOMEOD_ext_NQ` | 320 | +50.94 | +48.01 | [+40.81, +58.49] | 12/12 | 96.2% | 0.893 |

## 2. Experimento B: Shifts Multi-Minuto (`2020-2026`) y Fase Pura M5 `SOMEOD`

- Evaluado sobre `1738` sesiones validas `2020-01-01..2026-11-17` (M1 canonico).

| Cartera / Modulo | dM=-2m | dM=-1m | dM=0m (Base) | dM=+1m | dM=+2m | dM=+3m | dM=+4m |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CORE5` | +405.2R (77%) | +371.5R (71%) | +523.6R (100%) | +468.2R (89%) | +434.2R (83%) | +355.8R (68%) | +306.2R (58%) |
| `P7` | +432.7R (72%) | +436.2R (72%) | +602.4R (100%) | +493.6R (82%) | +508.2R (84%) | +390.3R (65%) | +309.4R (51%) |
| `T_stop100_BE15R_calFalse` | +130.9R (50%) | +102.0R (39%) | +261.0R (100%) | +135.3R (52%) | +127.0R (49%) | +86.8R (33%) | +75.0R (29%) |
| `R_osc30_end660_ATR50` | +55.7R (83%) | +56.2R (84%) | +66.9R (100%) | +91.8R (137%) | +69.8R (104%) | +55.7R (83%) | +65.4R (98%) |
| `Z_b15_e20_eff40_ATR50` | +40.4R (129%) | +37.0R (118%) | +31.3R (100%) | +37.5R (120%) | +34.3R (110%) | +33.1R (106%) | +27.3R (87%) |
| `SOMEOD_ext_NQ` | +107.9R (111%) | +109.0R (112%) | +97.6R (100%) | +99.7R (102%) | +109.7R (112%) | +97.6R (100%) | +69.1R (71%) |
| `N_d5_fbTrue_ATR25` | +61.1R (90%) | +66.6R (98%) | +68.2R (100%) | +94.9R (139%) | +93.9R (138%) | +88.3R (130%) | +88.0R (129%) |
| `W_slope_allowReFalse_ATR25` | +8.3R (13%) | +27.5R (42%) | +65.6R (100%) | +30.2R (46%) | +74.3R (113%) | +12.9R (20%) | -1.7R (-3%) |
| `V_nm25_noCap_mae30` | +113.6R (110%) | +108.6R (106%) | +102.8R (100%) | +68.2R (66%) | +75.1R (73%) | +83.0R (81%) | +58.5R (57%) |

### Fase Pura M5 en `SOMEOD` (sin mover 09:30 ni EOD 15:55, `2020-2026`)

| Fase M5 | N ops | Sum R | R/op | MaxDD R | Retencion vs p=0 |
|---|---:|---:|---:|---:|---:|
| `p=+0m` | 1737 | +98.16 | +0.0565 | -27.45 | 100.0% |
| `p=+1m` | 1736 | +100.30 | +0.0578 | -14.57 | 102.2% |
| `p=+2m` | 1736 | +110.22 | +0.0635 | -18.16 | 112.3% |
| `p=+3m` | 1736 | +97.18 | +0.0560 | -15.78 | 99.0% |
| `p=+4m` | 1736 | +69.47 | +0.0400 | -18.09 | 70.8% |

## 3. Experimento C: Auditoria Ticks Reales CFD `USATECHIDXUSD` (`2026-10-01..2026-11-15`)

- **Basis futuros vs cash al empalme (`2026-10-01 00:00Z`)**: `+267.79` pts (warmup nivelado para continuidad de ATR/EMA sin salto).
- **Comparativa Sellado limpio (`31` sesiones, `2026-10-01..2026-11-13` excl. `2026-10-07`)** aplicando friccion real por ventana en CFD (`$0` comision, solo spread mediano observado):

| Ventana Horaria NY | Ticks | Spread Medio | Mediana | p90 | p99 | Max |
|---|---:|---:|---:|---:|---:|---:|
| `ALL` | 14,127,594 | 1.298 | 1.438 | 1.537 | 1.616 | 2.47 |
| `OPEN_0930_1000` | 557,064 | 0.982 | 0.981 | 1.049 | 1.136 | 1.65 |
| `RTH_CORE_1000_1530` | 4,255,079 | 0.983 | 0.981 | 1.058 | 1.137 | 2.47 |
| `CLOSE_1530_1600` | 367,321 | 0.982 | 0.981 | 1.049 | 1.136 | 1.18 |
| `ETH_OTHER` | 8,948,130 | 1.481 | 1.481 | 1.549 | 1.636 | 2.35 |

| Feed / Fase | Cartera | N ops | Sum R Bruto | Sum R Neto | Friccion media (R) |
|---|---|---:|---:|---:|---:|
| `CME_NQ_Sellado_d00` | `CORE5` | 56 | +14.51 | +13.94 | 0.0102 |
| `CFD_USATECH_d00` | `CORE5` | 58 | +14.35 | +13.96 | 0.0066 |
| `CFD_USATECH_d15` | `CORE5` | 61 | +12.99 | +12.59 | 0.0066 |
| `CFD_USATECH_d30` | `CORE5` | 60 | +12.97 | +12.57 | 0.0067 |
| `CFD_USATECH_d45` | `CORE5` | 65 | +16.54 | +16.10 | 0.0068 |
| `CME_NQ_Sellado_d00` | `P7` | 82 | +9.02 | +8.22 | 0.0097 |
| `CFD_USATECH_d00` | `P7` | 88 | +7.86 | +7.31 | 0.0062 |
| `CFD_USATECH_d15` | `P7` | 94 | +11.93 | +11.32 | 0.0065 |
| `CFD_USATECH_d30` | `P7` | 93 | +9.41 | +8.78 | 0.0067 |
| `CFD_USATECH_d45` | `P7` | 102 | +9.68 | +8.98 | 0.0068 |
